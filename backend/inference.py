from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
from transformers.generation.streamers import TextIteratorStreamer
import torch
import io
import threading
import os
import json
import time
import hashlib
import re
from functools import lru_cache
import sys

# Import RAG pipeline
try:
    import sys as sys_module
    # Add parent directory to path to import RAG pipeline
    rag_path = os.path.join(os.path.dirname(__file__), '..')
    if rag_path not in sys_module.path:
        sys_module.path.insert(0, rag_path)
    from rag_pipeline_with_points import TrafficLawRAGWithPoints
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"Warning: RAG pipeline not available: {e}")
    print("   Install required dependencies or check rag_pipeline_with_points.py path")

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass  # Ignore if reconfigure fails

# Safe print function for Windows console
def safe_print(*args, **kwargs):
    """Print function that handles encoding errors on Windows"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII with replacement
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', errors='replace').decode('ascii'))
            else:
                safe_args.append(str(arg).encode('ascii', errors='replace').decode('ascii'))
        print(*safe_args, **kwargs)

# Detect and fix mojibake (double-encoded UTF-8) in user questions
MOJIBAKE_MARKERS = ["Ã", "Â", "Æ", "Ê", "Ð", "Á", "À", "¤", "¢", "»", "¼", "½", "¾", "µ", "¥"]
ENCODING_GUESSES = ["latin1", "cp1252", "cp1258"]

def has_mojibake(text: str) -> bool:
    """Check if text contains common mojibake markers"""
    if not text:
        return False
    return any(marker in text for marker in MOJIBAKE_MARKERS) or "á»" in text or "áº" in text

def normalize_input_text(text):
    """
    Normalize user input to proper UTF-8.
    Handles cases where UTF-8 text was mistakenly decoded as latin1/cp1252.
    """
    try:
        if text is None:
            return ""
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8")
            except UnicodeDecodeError:
                text = text.decode("utf-8", errors="ignore")
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return text
        if has_mojibake(text):
            for encoding in ENCODING_GUESSES:
                try:
                    candidate = text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore").strip()
                    if candidate and not has_mojibake(candidate):
                        safe_print(f"[RAG] Fixed mojibake via {encoding}: {candidate[:120]}")
                        return candidate
                except UnicodeError:
                    continue
        return text
    except Exception as e:
        safe_print(f"[RAG] normalize_input_text error: {e}")
        return text

ENGLISH_BLOCKLIST = [
    "speed", "red", "color", "code", "months", "month", "pdf",
    "cost", "analysis", "however", "therefore", "please", "thank you",
    "follows", "generate", "summary", "processed", "human", "analyst",
    "events", "however", "since", "none", "outside", "standard",
    "system", "natural", "disasters", "engineering", "design"
]

def needs_vietnamese_fallback(answer: str) -> bool:
    """Detect if answer drifts into English or gibberish."""
    if not answer:
        return True
    normalized = answer.strip()
    total_chars = len(normalized)
    if total_chars == 0:
        return True
    ascii_chars = sum(1 for ch in normalized if ord(ch) < 128)
    if ascii_chars / total_chars > 0.35:
        return True
    lower = normalized.lower()
    for word in ENGLISH_BLOCKLIST:
        if word in lower:
            return True
    return False

def build_answer_from_context(rag_context: str) -> str:
    """Construct deterministic Vietnamese answer directly from RAG context."""
    if not rag_context:
        return "Xin lỗi, hiện chưa có thông tin phù hợp trong cơ sở dữ liệu."
    law = ""
    content = ""
    phat = ""
    tru = ""
    tước = ""
    extra = []
    for line in rag_context.splitlines():
        text = line.strip()
        if text.startswith("[DIEU_LUAT_CHINH]"):
            law = text.split("]", 1)[1].strip()
        elif text.startswith("[NOI_DUNG]"):
            content = text.split("]", 1)[1].strip()
        elif text.startswith("[MUC_PHAT]"):
            phat = text.split("]", 1)[1].strip()
        elif text.startswith("[TRU_DIEM]"):
            tru = text.split("]", 1)[1].strip()
        elif text.startswith("[TUOC_GPLX]"):
            tước = text.split("]", 1)[1].strip()
        elif text.startswith("  - "):
            extra.append(text[4:].strip())
    segments = []
    if law:
        segments.append(f"Theo {law},")
    if content:
        segments.append(content)
    if phat:
        segments.append(f"Mức phạt: {phat}.")
    if tru:
        segments.append(f"Trừ điểm: {tru}.")
    if tước:
        segments.append(f"Tước GPLX: {tước}.")
    if extra:
        segments.append("Thông tin liên quan: " + "; ".join(extra) + ".")
    if not segments:
        return "Xin lỗi, hiện chưa có thông tin rõ ràng cho tình huống này."
    return " ".join(segments).strip()

def format_chat_history(chat_history):
    if not chat_history:
        return ""
    formatted_history = ""
    for i, (user_msg, ai_msg) in enumerate(chat_history):
        formatted_history += f"### Hỏi trước đó:\n{normalize_input_text(user_msg)}\n\n### Trả lời trước đó:\n{normalize_input_text(ai_msg)}\n\n"
    return formatted_history

# Hugging Face token cho private repos
try:
    from huggingface_hub import login as hf_login
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    print("Warning: huggingface_hub not available. Install with: pip install huggingface-hub")

# Kiểm tra quantization support
try:
    from transformers import BitsAndBytesConfig
    QUANTIZATION_AVAILABLE = True
except ImportError:
    QUANTIZATION_AVAILABLE = False
    print("Warning: bitsandbytes not available. Install with: pip install bitsandbytes")

device = (
    "cuda"
    if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available() else "cpu"
)

# Tối ưu hóa cho CPU
if device == "cpu":
    # Tự động detect số cores và sử dụng tối đa
    import multiprocessing
    num_threads = min(multiprocessing.cpu_count(), 8)  # Tối đa 8 threads
    torch.set_num_threads(num_threads)
    torch.set_num_interop_threads(num_threads)
    print(f"CPU Mode: Using {num_threads} threads")
    # Sử dụng float32 cho CPU (tốt hơn float16 trên CPU)
    USE_FLOAT32 = True
else:
    USE_FLOAT32 = False

# Tối ưu hóa cho GPU
if device == "cuda":
    torch.backends.cudnn.benchmark = True  # Tối ưu hóa CUDNN
    torch.backends.cuda.matmul.allow_tf32 = True  # Cho phép TF32

# Response cache để tránh tính toán lại
response_cache = {}
MAX_CACHE_SIZE = 100  # Giới hạn cache size

# Global variables for model and tokenizer
model = None
tokenizer = None
model_loaded = False

# Global RAG instance
rag_instance = None
RAG_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'nd168_metadata_clean.json')

# Flag để hiển thị RAG context trong response (tạm thời để debug)
SHOW_RAG_CONTEXT = os.getenv("SHOW_RAG_CONTEXT", "false").lower() == "true"

# Flag để quyết định có dùng mô hình sinh câu trả lời hay chỉ dựng trực tiếp từ RAG
USE_GENERATIVE_MODEL = os.getenv("USE_GENERATIVE_MODEL", "false").lower() == "true"

# Global variable để lưu RAG debug info
rag_debug_info = ""

def load_model():
    global model, tokenizer, model_loaded
    if model_loaded:
        return True
    
    # Đường dẫn model - ưu tiên Hugging Face Hub, sau đó mới dùng local path
    # Có thể set qua environment variable:
    # - MODEL_HF_REPO: Hugging Face repository (ví dụ: "username/qwen3-0.6B-trafficlaws")
    #   Nếu model nằm trong subfolder, có thể dùng: "username/repo/model" hoặc set MODEL_HF_SUBFOLDER
    # - MODEL_HF_SUBFOLDER: Subfolder trong repo (mặc định: None, sẽ tìm trong root)
    # - MODEL_PATH: Local path (fallback)
    model_hf_repo = os.getenv("MODEL_HF_REPO", None)
    model_hf_subfolder = os.getenv("MODEL_HF_SUBFOLDER", None)
    model_path = os.getenv("MODEL_PATH", "../qwen3-0.6B-instruct-trafficlaws/model")
    
    # Quyết định sử dụng Hugging Face Hub hay local path
    use_hf_hub = model_hf_repo is not None and model_hf_repo.strip() != ""
    
    if use_hf_hub:
        # Kiểm tra Hugging Face token cho private repos
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        
        if hf_token and HF_HUB_AVAILABLE:
            try:
                # Login với token (nếu chưa login)
                hf_login(token=hf_token, add_to_git_credential=False)
                print("[OK] Authenticated with Hugging Face Hub")
            except Exception as e:
                safe_print(f"[WARNING] Could not login to Hugging Face: {e}")
                safe_print("   Model download may fail if repo is private")
        elif not hf_token:
            print("[INFO] No HF_TOKEN found - assuming public repo or already authenticated")
        
        # Lưu repo và subfolder riêng (không combine thành path)
        actual_model_path = model_hf_repo
        print(f"Loading model from Hugging Face Hub: {model_hf_repo}" + (f" (subfolder: {model_hf_subfolder})" if model_hf_subfolder else ""))
    else:
        print(f"Loading model from local path: {model_path}")
        actual_model_path = model_path
    
    try:
        print("Loading model from checkpoint...")
        print(f"Device: {device}")
        print(f"Model source: {'Hugging Face Hub' if use_hf_hub else 'Local path'}")
        print(f"Model path/repo: {actual_model_path}")
        
        # First, try to load config to understand the model type
        # Nếu dùng Hugging Face Hub và có token, pass token vào
        load_kwargs = {"trust_remote_code": True}
        if use_hf_hub:
            hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
            if hf_token:
                load_kwargs["token"] = hf_token
            # Nếu có subfolder, truyền như parameter riêng
            if model_hf_subfolder:
                load_kwargs["subfolder"] = model_hf_subfolder
        
        config = AutoConfig.from_pretrained(actual_model_path, **load_kwargs)
        print(f"Model type: {config.model_type}")
        print(f"Architectures: {config.architectures}")
        
        # Chọn dtype phù hợp
        if device == "cuda":
            model_dtype = torch.float16
        elif USE_FLOAT32:
            model_dtype = torch.float32
        else:
            model_dtype = torch.float16
        
        # Tối ưu hóa cho CPU: sử dụng quantization nếu có
        use_quantization = (device == "cpu" and QUANTIZATION_AVAILABLE)
        
        if use_quantization:
            print("Attempting 8-bit quantization for CPU optimization...")
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
            )
        else:
            quantization_config = None
        
        # Try different loading strategies
        loading_strategies = []
        
        # Base kwargs cho tất cả loading strategies
        base_kwargs = {
            "trust_remote_code": True,
            "ignore_mismatched_sizes": True
        }
        if use_hf_hub:
            hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
            if hf_token:
                base_kwargs["token"] = hf_token
            # Nếu có subfolder, truyền như parameter riêng
            if model_hf_subfolder:
                base_kwargs["subfolder"] = model_hf_subfolder
        
        # Strategy 1: Quantized (CPU only)
        if use_quantization:
            loading_strategies.append(
                lambda: AutoModelForCausalLM.from_pretrained(
                    actual_model_path,
                    **base_kwargs,
                    quantization_config=quantization_config,
                    device_map="auto",
                    low_cpu_mem_usage=True
                )
            )
        
        # Strategy 2: GPU với float16
        if device == "cuda":
            loading_strategies.append(
                lambda: AutoModelForCausalLM.from_pretrained(
                    actual_model_path,
                    **base_kwargs,
                    torch_dtype=model_dtype,
                    device_map="auto"
                )
            )
        
        # Strategy 3: CPU với float32 và low_cpu_mem_usage
        loading_strategies.append(
            lambda: AutoModelForCausalLM.from_pretrained(
                actual_model_path,
                **base_kwargs,
                torch_dtype=model_dtype,
                low_cpu_mem_usage=True
            )
        )
        
        # Strategy 4: Load with config
        loading_strategies.append(
            lambda: AutoModelForCausalLM.from_pretrained(
                actual_model_path,
                config=config,
                **base_kwargs,
                torch_dtype=model_dtype,
                low_cpu_mem_usage=True
            )
        )
        
        # Try each strategy
        for i, strategy in enumerate(loading_strategies):
            try:
                print(f"Trying loading strategy {i+1}...")
                model = strategy()
                if device != "cuda" and not use_quantization:
                    model = model.to(device)
                # Tối ưu hóa model
                model.eval()  # Set to evaluation mode
                break
            except Exception as e:
                safe_print(f"Strategy {i+1} failed: {e}")
                continue
        else:
            raise Exception("All loading strategies failed")
        
        # Load tokenizer với token nếu cần
        tokenizer_kwargs = {
            "trust_remote_code": True,
            "model_max_length": 2048
        }
        if use_hf_hub:
            hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
            if hf_token:
                tokenizer_kwargs["token"] = hf_token
            # Nếu có subfolder, truyền như parameter riêng
            if model_hf_subfolder:
                tokenizer_kwargs["subfolder"] = model_hf_subfolder
        
        tokenizer = AutoTokenizer.from_pretrained(
            actual_model_path, 
            **tokenizer_kwargs
        )
        
        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        model_loaded = True
        print("Model loaded successfully!")
        
        # Thống kê model
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
        
        # Tối ưu hóa với torch.compile (PyTorch 2.0+)
        try:
            if hasattr(torch, 'compile') and device == "cpu":
                print("Compiling model with torch.compile for better CPU performance...")
                model = torch.compile(model, mode="reduce-overhead")
                print("Model compiled successfully!")
        except Exception as e:
            safe_print(f"Could not compile model: {e}")
        
        return True
        
    except Exception as e:
        safe_print(f"Failed to load model: {e}")
        print("Falling back to mock responses...")
        return False

prompt_template = """Bạn là trợ lý pháp luật giao thông VIỆT NAM.

--- DỮ LIỆU PHÁP LUẬT ---
{rag_context}

--- LỊCH SỬ HỘI THOẠI ---
{chat_history}

--- CÂU HỎI ---
{question}

--- HƯỚNG DẪN BẮT BUỘC ---
1. CHỈ dùng thông tin trong phần DỮ LIỆU PHÁP LUẬT.
2. Nếu không có dữ liệu → trả lời đúng 1 câu: "Không có thông tin cụ thể trong cơ sở dữ liệu."
3. Trả lời hoàn toàn bằng TIẾNG VIỆT, không có bất kỳ từ tiếng Anh hoặc tiếng Trung.
4. Cấu trúc câu trả lời:
   - Điều luật: ...
   - Mức phạt: ...
   - Trừ điểm/Tước GPLX (nếu có)
   - Lưu ý bổ sung (nếu có)
5. Dùng tối đa 4 câu, ngắn gọn, rõ ràng, không lặp lại.
"""

def get_mock_response(question):
    """Provide a mock response when model is not available"""
    mock_responses = {
        "quyền": "Theo Bộ luật Lao động Việt Nam, người lao động có các quyền cơ bản sau:\n\n1. Quyền được làm việc và lựa chọn việc làm\n2. Quyền được trả lương theo thỏa thuận\n3. Quyền được nghỉ ngơi, nghỉ phép\n4. Quyền được bảo hiểm xã hội\n5. Quyền được đào tạo, nâng cao trình độ\n6. Quyền được thành lập và tham gia công đoàn\n7. Quyền được bảo vệ sức khỏe, tính mạng\n8. Quyền được bảo vệ danh dự, nhân phẩm",
        "hợp đồng": "Để một hợp đồng được coi là hợp lệ, cần đáp ứng các điều kiện sau:\n\n1. Người tham gia có năng lực hành vi dân sự\n2. Mục đích và nội dung không vi phạm điều cấm của luật\n3. Người tham gia hoàn toàn tự nguyện\n4. Hình thức hợp đồng phù hợp với quy định của pháp luật\n\nHợp đồng phải có các nội dung cơ bản: đối tượng, số lượng, chất lượng, giá cả, thời hạn, địa điểm, phương thức thực hiện.",
        "vượt đèn đỏ": "Theo Luật Giao thông đường bộ Việt Nam, vi phạm vượt đèn đỏ sẽ bị xử phạt:\n\n**Đối với xe máy:**\n- Phạt tiền: 600.000 - 1.000.000 đồng\n- Tước quyền sử dụng Giấy phép lái xe: 1-3 tháng\n- Điểm trừ: 5 điểm\n\n**Đối với ô tô:**\n- Phạt tiền: 1.200.000 - 2.000.000 đồng\n- Tước quyền sử dụng Giấy phép lái xe: 1-3 tháng\n- Điểm trừ: 5 điểm\n\n**Hậu quả khác:**\n- Có thể gây tai nạn giao thông nghiêm trọng\n- Ảnh hưởng đến an toàn của bản thân và người khác\n- Có thể bị tước bằng lái vĩnh viễn nếu gây tai nạn chết người",
        "giao thông": "Các quy định giao thông cơ bản tại Việt Nam:\n\n**Tốc độ tối đa:**\n- Trong khu dân cư: 40-50 km/h\n- Ngoài khu dân cư: 60-80 km/h\n- Đường cao tốc: 80-120 km/h\n\n**Quy tắc ưu tiên:**\n- Xe ưu tiên (cứu thương, cảnh sát, cứu hỏa)\n- Xe đi trên đường ưu tiên\n- Xe đi bên phải\n\n**Vi phạm thường gặp:**\n- Vượt đèn đỏ\n- Đi ngược chiều\n- Không đội mũ bảo hiểm\n- Vượt quá tốc độ\n- Đỗ xe sai quy định"
    }
    
    question_lower = question.lower()
    for key, response in mock_responses.items():
        if key in question_lower:
            return response
    
    return "Xin chào! Tôi là trợ lý AI tư vấn pháp luật về giao thông. Hiện tại mô hình AI chưa được tải thành công, nhưng tôi có thể cung cấp thông tin cơ bản về:\n\n• Quyền lao động\n• Hợp đồng\n• Giao thông (vượt đèn đỏ, tốc độ, vi phạm)\n\nVui lòng hỏi cụ thể về một trong các chủ đề trên."

def generate_answer_text(question, chat_history=None):
    global rag_debug_info, SHOW_RAG_CONTEXT
    question = normalize_input_text(question)
    
    history_for_cache = chat_history if chat_history else []
    use_cache = len(history_for_cache) == 0
    
    if use_cache:
        cache_key = get_cache_key(question, None)
        if cache_key in response_cache:
            cached = response_cache[cache_key]
            if SHOW_RAG_CONTEXT and not cached.startswith("[RAG DEBUG]"):
                cached = f"[RAG DEBUG] (cache)\n\n{cached}"
            return cached
    
    rag_debug_info = ""
    rag_context = get_rag_context(question)
    if not rag_context.strip():
        rag_context = "[KHÔNG CÓ DỮ LIỆU]"
    
    if not USE_GENERATIVE_MODEL:
        answer = build_answer_from_context(rag_context)
        if use_cache:
            cache_key = get_cache_key(question, None)
            if len(response_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(response_cache))
                del response_cache[oldest_key]
            response_cache[cache_key] = answer
        return answer
    
    if not load_model():
        return get_mock_response(question)
    
    formatted_history = format_chat_history(chat_history)
    formatted_input = prompt_template.format(
        question=question,
        chat_history=formatted_history or "[KHÔNG CÓ LỊCH SỬ]",
        rag_context=rag_context
    )
    inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
    
    generation_kwargs = dict(
        **inputs,
        max_new_tokens=220,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        num_beams=4,
        temperature=0.0,
        repetition_penalty=1.25,
    )
    
    with torch.no_grad():
        output = model.generate(**generation_kwargs)
    
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    if formatted_input in generated_text:
        answer = generated_text.split(formatted_input, 1)[-1].strip()
    else:
        answer = generated_text.strip()
    
    # Remove stop tokens if present
    for stop_token in ["<|im_end|>", "<|endoftext|>", "###", "### Trả lời", "### Response"]:
        if stop_token in answer:
            answer = answer.split(stop_token)[0]
    
    # Clean output: remove timestamps, Chinese text, English words, and other artifacts
    answer = re.sub(r'\d{4}-\d{2}-\d{2}[\s:]*\d{2}:\d{2}:\d{2}.*', '', answer)
    answer = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', answer)
    
    chinese_patterns = [
        r'如果[^。]*。',
        r'法规',
        r'请[^。]*。',
        r'[^\x00-\x7F\u00C0-\u1EF9\s.,!?;:()\[\]{}\-]+',
    ]
    for pattern in chinese_patterns:
        answer = re.sub(pattern, '', answer)
    
    english_words = [
        'speed', 'red', 'color code', 'color', 'code', 'if there', 'if you',
        'please', 'thank you', 'months', 'month', '12 months', 'if', 'there',
        'you', 'can', 'will', 'should', 'and', 'or', 'the', 'a', 'an', 'is',
        'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'done', 'get', 'got', 'go', 'went', 'gone', 'come', 'came'
    ]
    for word in english_words:
        answer = re.sub(r'\b' + re.escape(word) + r'\b', '', answer, flags=re.IGNORECASE)
    
    answer = re.sub(r'\s+', ' ', answer).strip()
    
    if len(answer) < 10 or needs_vietnamese_fallback(answer):
        answer = build_answer_from_context(rag_context)
    
    if SHOW_RAG_CONTEXT:
        debug_prefix = rag_debug_info if rag_debug_info else "[RAG DEBUG] Không có dữ liệu"
        answer = f"{debug_prefix}\n\n{answer}"
    
    if use_cache:
        cache_key = get_cache_key(question, None)
        if len(response_cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(response_cache))
            del response_cache[oldest_key]
        response_cache[cache_key] = answer
    
    return answer

def get_rag_context(question):
    """Retrieve relevant context from RAG pipeline"""
    global rag_instance, rag_debug_info
    
    if not RAG_AVAILABLE:
        rag_debug_info = "[RAG DEBUG] RAG not available"
        return ""
    
    try:
        # Initialize RAG if not already initialized
        if rag_instance is None:
            if os.path.exists(RAG_DATA_PATH):
                print(f"Initializing RAG pipeline with {RAG_DATA_PATH}")
                rag_instance = TrafficLawRAGWithPoints(RAG_DATA_PATH)
                print("RAG pipeline initialized successfully")
            else:
                print(f"Warning: RAG data file not found at {RAG_DATA_PATH}")
                return ""
        
        # Retrieve relevant chunks
        # Ensure question is properly encoded (fix encoding issues)
        try:
            # Normalize encoding - ensure UTF-8
            question_clean = normalize_input_text(question)
            
            # Debug: print question to check encoding (use safe_print to avoid console encoding issues)
            safe_print(f"[RAG] Final query: {question_clean[:100]}")
            result = rag_instance.retrieve(question_clean)
        except Exception as retrieve_error:
            safe_print(f"Error in RAG retrieve call: {retrieve_error}")
            import traceback
            traceback.print_exc()
            rag_debug_info = f"[RAG DEBUG] Retrieve error: {str(retrieve_error)[:100]}"
            return ""
        
        if result.get("status") == "success":
            primary = result.get("primary_chunk", {})
            related = result.get("related_chunks", [])
            context_parts = []
            
            # Check if question has multiple violations (e.g., "không đội mũ vượt đèn đỏ")
            # If related chunks exist and have different references, include them
            has_multiple_violations = len(related) > 0 and any(
                rel.get("reference") != primary.get("reference") for rel in related
            )
            
            # Format primary chunk
            if primary.get("reference"):
                context_parts.append(f"[DIEU_LUAT_CHINH] {primary['reference']}")
            
            if primary.get("content"):
                # Giới hạn content để không quá dài
                content = primary['content']
                if len(content) > 250:
                    content = content[:250] + "..."
                context_parts.append(f"[NOI_DUNG] {content}")
            
            # Add penalty information
            if primary.get("penalty"):
                penalty = primary["penalty"]
                if penalty.get("text"):
                    context_parts.append(f"[MUC_PHAT] {penalty['text']}")
            
            # Add point deduction
            if primary.get("point_deduction"):
                context_parts.append(f"[TRU_DIEM] {primary['point_deduction']} điểm")
            
            # Add license suspension
            if primary.get("license_suspension"):
                suspension = primary["license_suspension"]
                if suspension.get("text"):
                    context_parts.append(f"[TUOC_GPLX] {suspension['text']}")
            
            # If multiple violations detected, add related chunks
            if has_multiple_violations:
                context_parts.append("\n[VI_PHAM_KET_HOP]")
                for rel in related[:2]:  # Lấy tối đa 2 related chunks
                    if rel.get("reference") and rel.get("reference") != primary.get("reference"):
                        rel_content = rel.get('content', '')[:150]
                        if rel.get("penalty") and rel["penalty"].get("text"):
                            context_parts.append(f"  - {rel['reference']}: {rel['penalty']['text']}")
                        else:
                            context_parts.append(f"  - {rel['reference']}: {rel_content}...")
            elif related:
                # Single violation but has related info
                context_parts.append("\n[THONG_TIN_BO_SUNG]")
                for rel in related[:1]:  # Chỉ lấy 1 related chunk
                    if rel.get("reference"):
                        rel_content = rel.get('content', '')[:100]
                        context_parts.append(f"  - {rel['reference']}: {rel_content}...")
            
            if context_parts:
                rag_context = "\n".join(context_parts)
                print(f"[RAG] Retrieved context: {len(rag_context)} chars")
                print(f"[RAG] Primary: {primary.get('reference', 'N/A')}")
                if has_multiple_violations:
                    print(f"[RAG] Multiple violations detected: {len([r for r in related if r.get('reference') != primary.get('reference')])} related")
                
                # Tạo summary cho hiển thị debug
                rag_summary = f"[RAG DEBUG] Đã retrieve: {primary.get('reference', 'N/A')}"
                if primary.get("penalty") and primary["penalty"].get("text"):
                    penalty_text = primary["penalty"]["text"]
                    if len(penalty_text) > 50:
                        penalty_text = penalty_text[:50] + "..."
                    rag_summary += f" | Phạt: {penalty_text}"
                if primary.get("point_deduction"):
                    rag_summary += f" | Trừ điểm: {primary['point_deduction']}"
                
                # Lưu summary vào global để dùng sau
                rag_debug_info = rag_summary
                
                return f"=== THÔNG TIN PHÁP LUẬT (BẮT BUỘC SỬ DỤNG) ===\n{rag_context}\n\n"
            else:
                print("RAG retrieved but no context parts available")
                rag_debug_info = "[RAG DEBUG] Không có context parts"
                return ""
        else:
            # RAG failed - still show debug info
            error_msg = result.get('message', 'Unknown error')
            status = result.get('status', 'unknown')
            print(f"RAG retrieval failed: {error_msg} (status: {status})")
            rag_debug_info = f"[RAG DEBUG] Retrieve failed ({status}): {error_msg}"
            # Return empty context but keep debug info for display
            return ""
    except Exception as e:
        safe_print(f"Error in RAG retrieval: {e}")
        import traceback
        traceback.print_exc()
        rag_debug_info = f"[RAG DEBUG] Error: {str(e)[:100]}"
        return ""

def get_answer(question):
    global rag_debug_info, SHOW_RAG_CONTEXT
    
    # Normalize question encoding
    question = normalize_input_text(question)
    
    try:
        # Reset RAG debug info trước khi retrieve
        rag_debug_info = ""
        
        # Retrieve RAG context (question đã được fix encoding ở trên)
        rag_context = get_rag_context(question)
        
        if not USE_GENERATIVE_MODEL:
            return build_answer_from_context(rag_context)
        
        if not load_model():
            return get_mock_response(question)
        
        formatted_input = prompt_template.format(
            question=question, 
            chat_history="",
            rag_context=rag_context
        )
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        
        # Add stop sequences to prevent Chinese/English output
        stop_sequences = ["如果", "请", "if", "speed", "red", "color code", "###", "2025-", "2024-"]
        stop_token_ids = []
        if tokenizer.eos_token_id:
            stop_token_ids.append(tokenizer.eos_token_id)
        for seq in stop_sequences:
            try:
                seq_ids = tokenizer.encode(seq, add_special_tokens=False)
                if seq_ids:
                    stop_token_ids.extend(seq_ids)
            except:
                pass
        
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=250,  # Giảm thêm để tránh dài dòng và lạc đề
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.3,  # Giảm thêm để chính xác và không lạc đề
                top_p=0.75,  # Giảm top_p
                repetition_penalty=1.7,  # Tăng thêm để tránh lặp lại
                num_beams=1,
            )
        
        generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
        if formatted_input in generated_text:
            answer = generated_text.split(formatted_input, 1)[-1].strip()
        else:
            answer = generated_text
        # Remove stop tokens if present
        for stop_token in ["<|im_end|>", "<|endoftext|>", "###", "### Trả lời", "### Response"]:
            if stop_token in answer:
                answer = answer.split(stop_token)[0]
        
        # Clean output: remove timestamps, Chinese text, English words, and other artifacts
        import re
        # Remove timestamp patterns (2025-01-01, 2024-12-31, etc.)
        answer = re.sub(r'\d{4}-\d{2}-\d{2}[\s:]*\d{2}:\d{2}:\d{2}.*', '', answer)
        answer = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', answer)
        
        # Remove Chinese characters and common Chinese phrases (more aggressive)
        chinese_patterns = [
            r'如果[^。]*。',  # Remove Chinese sentences starting with 如果
            r'法规',  # Remove Chinese word for "law"
            r'请[^。]*。',  # Remove Chinese sentences starting with 请
            r'[^\x00-\x7F\u00C0-\u1EF9\s.,!?;:()\[\]{}\-]+',  # Remove all non-Vietnamese characters
        ]
        for pattern in chinese_patterns:
            answer = re.sub(pattern, '', answer)
        
        # Remove common English words that shouldn't appear in Vietnamese legal text (more comprehensive)
        english_words = ['speed', 'red', 'color code', 'color', 'code', 'if there', 'if you', 'please', 'thank you', 
                        'months', 'month', '12 months', 'if', 'there', 'you', 'can', 'will', 'should', 'and', 'or', 
                        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                        'do', 'does', 'did', 'done', 'get', 'got', 'go', 'went', 'gone', 'come', 'came']
        for word in english_words:
            # Case insensitive replacement with word boundaries
            answer = re.sub(r'\b' + re.escape(word) + r'\b', '', answer, flags=re.IGNORECASE)
        
        # Remove any remaining English phrases
        english_phrases = ['if there', 'if you', 'thank you', '12 months', 'color code']
        for phrase in english_phrases:
            answer = re.sub(re.escape(phrase), '', answer, flags=re.IGNORECASE)
        
        # Remove multiple spaces
        answer = re.sub(r'\s+', ' ', answer)
        # Remove leading/trailing whitespace
        answer = answer.strip()
        
        # If answer is too short or seems corrupted, return a fallback
        if len(answer) < 10 or answer.count(' ') < 2:
            return "Xin lỗi, tôi không thể tạo câu trả lời phù hợp. Vui lòng thử lại với câu hỏi cụ thể hơn."
        
        # Hiển thị RAG debug info nếu enabled (LUÔN hiển thị nếu có)
        if SHOW_RAG_CONTEXT:
            if rag_debug_info:
                answer = f"{rag_debug_info}\n\n{answer}"
                rag_debug_info = ""  # Reset sau khi dùng
            else:
                # Nếu không có debug info, thêm warning
                answer = f"[RAG DEBUG] Không có debug info\n\n{answer}"
        
        return answer
    except Exception as e:
        safe_print(f"Error generating answer: {e}")
        return get_mock_response(question)

def get_cache_key(question, chat_history):
    """Tạo cache key từ question và chat history"""
    if chat_history:
        history_str = json.dumps(chat_history, sort_keys=True)
    else:
        history_str = ""
    key = hashlib.md5((question + history_str).encode()).hexdigest()
    return key

def get_answer_stream(question, chat_history=None):
    # Normalize question encoding
    question = normalize_input_text(question)
    
    # Kiểm tra cache (chỉ cache khi không có chat history)
    if chat_history is None or len(chat_history) == 0:
        cache_key = get_cache_key(question, None)
        if cache_key in response_cache:
            print("Using cached response")
            cached_response = response_cache[cache_key]
            for word in cached_response.split():
                yield word + " "
            return
    
    # Reset RAG debug info trước khi retrieve
    global rag_debug_info, SHOW_RAG_CONTEXT
    rag_debug_info = ""
    
    # Retrieve RAG context (question đã được fix encoding ở trên)
    rag_context = get_rag_context(question)
    
    if not USE_GENERATIVE_MODEL:
        answer = build_answer_from_context(rag_context)
        if chat_history is None or len(chat_history) == 0:
            cache_key = get_cache_key(question, None)
            if len(response_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(response_cache))
                del response_cache[oldest_key]
            response_cache[cache_key] = answer
        for word in answer.split():
            yield word + " "
        return
    
    if not load_model():
        # Return mock response as stream
        mock_response = get_mock_response(question)
        for word in mock_response.split():
            yield word + " "
        return
    
    if chat_history is None:
        chat_history = ""
    else:
        # Format chat history
        formatted_history = ""
        for i, (user_msg, ai_msg) in enumerate(chat_history):
            formatted_history += f"### Instruction:\n{user_msg}\n\n### Response:\n{ai_msg}\n\n"
        chat_history = formatted_history
    
    try:
        formatted_input = prompt_template.format(
            question=question, 
            chat_history=chat_history,
            rag_context=rag_context
        )
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        # Tối ưu generation parameters cho CPU
        if device == "cpu":
            # CPU: sử dụng sampling với temperature thấp để câu trả lời chính xác và không lặp lại
            generation_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=250,  # Giảm thêm để tránh dài dòng và lạc đề
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,  # Cho phép sampling
                temperature=0.3,  # Giảm thêm để chính xác và không lạc đề
                top_p=0.75,  # Giảm top_p
                repetition_penalty=1.7,  # Tăng thêm để tránh lặp lại
            )
        else:
            # GPU: giữ nguyên settings
            generation_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=512,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                num_beams=1,
            )
        
        # Bắt đầu đo thời gian
        start_time = time.time()
        token_count = 0
        speed_displayed = False
        generation_start_time = None
        full_response = ""  # Để cache response
        
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()
        
        # Hiển thị RAG debug info ở đầu stream nếu enabled (LUÔN hiển thị)
        if SHOW_RAG_CONTEXT:
            if rag_debug_info:
                yield f"{rag_debug_info}\n\n"
                rag_debug_info = ""  # Reset sau khi dùng
            else:
                # Nếu không có debug info, thêm warning để biết RAG không chạy
                yield f"[RAG DEBUG] Không có debug info (RAG có thể chưa chạy)\n\n"
        
        import re
        for new_text in streamer:
            # Clean text immediately: remove timestamps and Chinese
            cleaned_text = new_text
            # Remove timestamp patterns
            cleaned_text = re.sub(r'\d{4}-\d{2}-\d{2}[\s:]*\d{2}:\d{2}:\d{2}.*', '', cleaned_text)
            cleaned_text = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', cleaned_text)
            # Remove Chinese characters and phrases (more aggressive)
            chinese_patterns = [
                r'如果[^。]*。',  # Remove Chinese sentences starting with 如果
                r'法规',  # Remove Chinese word for "law"
                r'请[^。]*。',  # Remove Chinese sentences starting with 请
                r'[^\x00-\x7F\u00C0-\u1EF9\s.,!?;:()\[\]{}\-]+',  # Remove all non-Vietnamese characters
            ]
            for pattern in chinese_patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text)
            
            # Remove common English words (more comprehensive)
            english_words = ['speed', 'red', 'color code', 'color', 'code', 'months', 'month', '12 months', 
                           'if', 'there', 'you', 'can', 'will', 'should', 'and', 'or', 'the', 'a', 'an',
                           'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had']
            for word in english_words:
                cleaned_text = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_text, flags=re.IGNORECASE)
            
            # Remove any remaining English phrases
            english_phrases = ['if there', 'if you', 'thank you', '12 months', 'color code']
            for phrase in english_phrases:
                cleaned_text = re.sub(re.escape(phrase), '', cleaned_text, flags=re.IGNORECASE)
            
            # Stop if we hit certain patterns (Chinese, English, or stop sequences)
            stop_patterns = ["###", "2025-", "2024-", "请", "如果", "### trả lời", "### response", 
                           "if there", "if you", "please", "thank you"]
            if any(stop in cleaned_text.lower() for stop in stop_patterns):
                break
            
            if cleaned_text.strip():  # Only yield non-empty cleaned text
                full_response += cleaned_text
                # Đếm số token trong chunk mới (ước tính: 1 token ≈ 4 ký tự)
                estimated_tokens = len(cleaned_text.encode('utf-8')) // 4
                token_count += estimated_tokens
                
                # Ghi nhận thời điểm bắt đầu có output thực sự
                if generation_start_time is None and estimated_tokens > 0:
                    generation_start_time = time.time()
                
                # Tính tốc độ token/s
                elapsed_time = time.time() - start_time
                
                # Hiển thị tốc độ khi có đủ dữ liệu và chưa hiển thị
                if not speed_displayed and token_count > 5:
                    if generation_start_time is not None:
                        # Tính tốc độ từ khi bắt đầu có output
                        generation_elapsed = time.time() - generation_start_time
                        if generation_elapsed > 0.1:  # Đảm bảo có đủ thời gian để tính
                            tokens_per_second = token_count / generation_elapsed
                        else:
                            tokens_per_second = token_count / elapsed_time
                    else:
                        tokens_per_second = token_count / elapsed_time
                    
                    yield f"[Tốc độ: {tokens_per_second:.2f} token/s] {cleaned_text}"
                    speed_displayed = True
                else:
                    yield cleaned_text
        
        # Cache response nếu không có chat history
        if (chat_history is None or chat_history == "") and len(full_response) > 0:
            cache_key = get_cache_key(question, None)
            # Giới hạn cache size
            if len(response_cache) >= MAX_CACHE_SIZE:
                # Xóa item cũ nhất (FIFO)
                oldest_key = next(iter(response_cache))
                del response_cache[oldest_key]
            response_cache[cache_key] = full_response
            
    except Exception as e:
        safe_print(f"Error in streaming: {e}")
        mock_response = get_mock_response(question)
        for word in mock_response.split():
            yield word + " "

