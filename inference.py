from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
from transformers.generation.streamers import TextIteratorStreamer
import torch
import io
import threading
import os
import json
import time

device = (
    "cuda"
    if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available() else "cpu"
)

# Tối ưu hóa cho CPU
if device == "cpu":
    torch.set_num_threads(4)  # Sử dụng 4 threads cho CPU

# Tối ưu hóa cho GPU
if device == "cuda":
    torch.backends.cudnn.benchmark = True  # Tối ưu hóa CUDNN
    torch.backends.cuda.matmul.allow_tf32 = True  # Cho phép TF32

# Global variables for model and tokenizer
model = None
tokenizer = None
model_loaded = False

def load_model():
    global model, tokenizer, model_loaded
    if model_loaded:
        return True
    
    model_path = "./checkpoint"
    
    try:
        print("Loading model from checkpoint...")
        
        # First, try to load config to understand the model type
        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        print(f"Model type: {config.model_type}")
        print(f"Architectures: {config.architectures}")
        
        # Try different loading strategies
        loading_strategies = [
            # Strategy 1: Load with ignore_mismatched_sizes (works with qwen library)
            lambda: AutoModelForCausalLM.from_pretrained(
                model_path, 
                trust_remote_code=True,
                ignore_mismatched_sizes=True,
                torch_dtype=torch.float16,  # Sử dụng float16 cho GPU
                device_map="auto" if device == "cuda" else None
            ),
            
            # Strategy 2: Load with config
            lambda: AutoModelForCausalLM.from_pretrained(
                model_path,
                config=config,
                trust_remote_code=True,
                ignore_mismatched_sizes=True,
                torch_dtype=torch.float16,  # Sử dụng float16 cho GPU
                device_map="auto" if device == "cuda" else None
            ),
            
            # Strategy 3: Load without device_map
            lambda: AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                ignore_mismatched_sizes=True,
                torch_dtype=torch.float16  # Sử dụng float16 cho GPU
            ),
            
            # Strategy 4: Load with low_cpu_mem_usage
            lambda: AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                ignore_mismatched_sizes=True,
                torch_dtype=torch.float16,  # Sử dụng float16 cho GPU
                low_cpu_mem_usage=True
            )
        ]
        
        # Try each strategy
        for i, strategy in enumerate(loading_strategies):
            try:
                print(f"Trying loading strategy {i+1}...")
                model = strategy()
                if device != "cuda":
                    model = model.to(device)
                break
            except Exception as e:
                print(f"Strategy {i+1} failed: {e}")
                continue
        else:
            raise Exception("All loading strategies failed")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_path, 
            trust_remote_code=True,
            model_max_length=2048
        )
        
        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        model_loaded = True
        print("Model loaded successfully!")
        return True
        
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("Falling back to mock responses...")
        return False

prompt_template = """ Bạn là một trợ lí tư vấn các vấn đề liên quan đến pháp luật. Hãy trả lời như một luật sư chuyên nghiệp. 

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
        "kinh doanh": "Thủ tục đăng ký kinh doanh tại Việt Nam bao gồm:\n\n1. Chuẩn bị hồ sơ đăng ký doanh nghiệp\n2. Nộp hồ sơ tại Phòng Đăng ký kinh doanh\n3. Nhận Giấy chứng nhận đăng ký doanh nghiệp\n4. Khắc dấu và công bố mẫu dấu\n5. Đăng ký thuế và mở tài khoản ngân hàng\n\nThời gian xử lý thường từ 3-5 ngày làm việc.",
        "thuế": "Nghĩa vụ thuế cơ bản của doanh nghiệp:\n\n1. Thuế giá trị gia tăng (VAT)\n2. Thuế thu nhập doanh nghiệp\n3. Thuế thu nhập cá nhân (nếu có)\n4. Các loại thuế khác tùy theo ngành nghề\n\nDoanh nghiệp nhỏ có thể được hưởng các ưu đãi thuế theo quy định.",
        "sở hữu trí tuệ": "Để bảo vệ quyền sở hữu trí tuệ:\n\n1. Đăng ký bảo hộ tại Cục Sở hữu trí tuệ\n2. Sử dụng dấu hiệu phân biệt\n3. Ký kết hợp đồng bảo mật\n4. Giám sát và phát hiện vi phạm\n5. Khởi kiện khi bị xâm phạm\n\nCác đối tượng được bảo hộ: nhãn hiệu, sáng chế, kiểu dáng công nghiệp, bản quyền tác giả.",
        "vượt đèn đỏ": "Theo Luật Giao thông đường bộ Việt Nam, vi phạm vượt đèn đỏ sẽ bị xử phạt:\n\n**Đối với xe máy:**\n- Phạt tiền: 600.000 - 1.000.000 đồng\n- Tước quyền sử dụng Giấy phép lái xe: 1-3 tháng\n- Điểm trừ: 5 điểm\n\n**Đối với ô tô:**\n- Phạt tiền: 1.200.000 - 2.000.000 đồng\n- Tước quyền sử dụng Giấy phép lái xe: 1-3 tháng\n- Điểm trừ: 5 điểm\n\n**Hậu quả khác:**\n- Có thể gây tai nạn giao thông nghiêm trọng\n- Ảnh hưởng đến an toàn của bản thân và người khác\n- Có thể bị tước bằng lái vĩnh viễn nếu gây tai nạn chết người",
        "giao thông": "Các quy định giao thông cơ bản tại Việt Nam:\n\n**Tốc độ tối đa:**\n- Trong khu dân cư: 40-50 km/h\n- Ngoài khu dân cư: 60-80 km/h\n- Đường cao tốc: 80-120 km/h\n\n**Quy tắc ưu tiên:**\n- Xe ưu tiên (cứu thương, cảnh sát, cứu hỏa)\n- Xe đi trên đường ưu tiên\n- Xe đi bên phải\n\n**Vi phạm thường gặp:**\n- Vượt đèn đỏ\n- Đi ngược chiều\n- Không đội mũ bảo hiểm\n- Vượt quá tốc độ\n- Đỗ xe sai quy định",
        "quan hệ tình dục": "Theo Bộ luật Hình sự Việt Nam, quan hệ tình dục với trẻ em dưới 18 tuổi là tội phạm nghiêm trọng:\n\n**Tội hiếp dâm người dưới 16 tuổi:**\n- Phạt tù từ 7 năm đến 15 năm\n- Nếu gây thương tích nặng: 12-20 năm\n- Nếu gây chết người: 20 năm, chung thân hoặc tử hình\n\n**Tội giao cấu với người từ đủ 13 tuổi đến dưới 16 tuổi:**\n- Phạt tù từ 1 năm đến 5 năm\n- Nếu có tổ chức: 3-10 năm\n\n**Tội dâm ô với người dưới 16 tuổi:**\n- Phạt tù từ 6 tháng đến 3 năm\n- Nếu có tổ chức: 2-7 năm\n\n**Lưu ý:**\n- Trẻ em dưới 18 tuổi được pháp luật bảo vệ đặc biệt\n- Mọi hành vi xâm hại tình dục đều bị xử lý nghiêm minh\n- Người phạm tội có thể bị cấm hành nghề, cấm cư trú"
    }
    
    question_lower = question.lower()
    for key, response in mock_responses.items():
        if key in question_lower:
            return response
    
    return "Xin chào! Tôi là trợ lý AI tư vấn pháp luật. Hiện tại mô hình AI chưa được tải thành công, nhưng tôi có thể cung cấp thông tin cơ bản về:\n\n• Quyền lao động\n• Hợp đồng\n• Đăng ký kinh doanh\n• Thuế\n• Sở hữu trí tuệ\n• Giao thông (vượt đèn đỏ, tốc độ, vi phạm)\n• Quan hệ tình dục với trẻ em (hình phạt, tội phạm)\n\nVui lòng hỏi cụ thể về một trong các chủ đề trên."

def get_answer(question):
    if not load_model():
        return get_mock_response(question)
    
    try:
        formatted_input = prompt_template.format(question=question, chat_history="")
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=512,  # Giảm từ 1024 xuống 512
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.1,  # Tăng từ 0.6 lên 0.7
                top_p=0.9,
                repetition_penalty=1.1,  # Giảm từ 1.2 xuống 1.1
                num_beams=1,  # Thêm beam search
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

def get_answer_stream(question, chat_history=None):
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
        formatted_input = prompt_template.format(question=question, chat_history=chat_history)
        inputs = tokenizer([formatted_input], return_tensors="pt").to(device)
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=512,  # Giảm từ 1024 xuống 512
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.7,  # Tăng từ 0.6 lên 0.7
            top_p=0.9,
            repetition_penalty=1.1,  # Giảm từ 1.2 xuống 1.1
            num_beams=1,  # Thêm beam search
        )
        
        # Bắt đầu đo thời gian
        start_time = time.time()
        token_count = 0
        speed_displayed = False
        generation_start_time = None
        
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()
        
        for new_text in streamer:
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
            
    except Exception as e:
        print(f"Error in streaming: {e}")
        mock_response = get_mock_response(question)
        for word in mock_response.split():
            yield word + " "
