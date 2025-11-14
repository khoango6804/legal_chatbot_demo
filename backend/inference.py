from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
from transformers.generation.streamers import TextIteratorStreamer
import torch
import io
import threading
import os
import json
import time
import hashlib
from functools import lru_cache

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
                print("✅ Authenticated with Hugging Face Hub")
            except Exception as e:
                print(f"⚠️  Warning: Could not login to Hugging Face: {e}")
                print("   Model download may fail if repo is private")
        elif not hf_token:
            print("ℹ️  No HF_TOKEN found - assuming public repo or already authenticated")
        
        # Nếu có subfolder, thêm vào repo path
        if model_hf_subfolder:
            actual_model_path = f"{model_hf_repo}/{model_hf_subfolder}"
        else:
            # Kiểm tra nếu repo path đã có subfolder
            actual_model_path = model_hf_repo
        print(f"Loading model from Hugging Face Hub: {actual_model_path}")
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
                print(f"Strategy {i+1} failed: {e}")
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
            print(f"Could not compile model: {e}")
        
        return True
        
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("Falling back to mock responses...")
        return False

prompt_template = """ Bạn là một trợ lí tư vấn các vấn đề liên quan đến pháp luật về giao thông. Hãy trả lời như một luật sư chuyên nghiệp. 

{chat_history}

### Instruction:
{question}

### Response:
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

def get_answer(question):
    if not load_model():
        return get_mock_response(question)
    
    try:
        formatted_input = prompt_template.format(question=question, chat_history="")
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=512,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                repetition_penalty=1.1,
                num_beams=1,
            )
        
        generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
        if formatted_input in generated_text:
            answer = generated_text.split(formatted_input, 1)[-1].strip()
        else:
            answer = generated_text
        # Remove stop tokens if present
        for stop_token in ["<|im_end|>", "<|endoftext|>"]:
            if stop_token in answer:
                answer = answer.split(stop_token)[0]
        return answer.strip()
    except Exception as e:
        print(f"Error generating answer: {e}")
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
    if not load_model():
        # Return mock response as stream
        mock_response = get_mock_response(question)
        for word in mock_response.split():
            yield word + " "
        return
    
    # Kiểm tra cache (chỉ cache khi không có chat history)
    if chat_history is None or len(chat_history) == 0:
        cache_key = get_cache_key(question, None)
        if cache_key in response_cache:
            print("Using cached response")
            cached_response = response_cache[cache_key]
            for word in cached_response.split():
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
        formatted_input = prompt_template.format(question=question, chat_history=chat_history)
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        # Tối ưu generation parameters cho CPU
        if device == "cpu":
            # CPU: sử dụng greedy decoding (nhanh hơn) và giảm max tokens
            generation_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=256,  # Giảm cho CPU
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=False,  # Greedy decoding nhanh hơn
                repetition_penalty=1.1,
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
        
        for new_text in streamer:
            full_response += new_text
            # Đếm số token trong chunk mới (ước tính: 1 token ≈ 4 ký tự)
            estimated_tokens = len(new_text.encode('utf-8')) // 4
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
                
                yield f"[Tốc độ: {tokens_per_second:.2f} token/s] {new_text}"
                speed_displayed = True
            else:
                yield new_text
        
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
        print(f"Error in streaming: {e}")
        mock_response = get_mock_response(question)
        for word in mock_response.split():
            yield word + " "

