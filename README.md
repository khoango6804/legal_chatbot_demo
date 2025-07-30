# 🤖 AI Legal Assistant - Trợ lý AI Tư vấn Pháp luật

Một ứng dụng web sử dụng AI để tư vấn các vấn đề pháp luật Việt Nam, được xây dựng với FastAPI và Qwen2 model.

## Tính năng

- **Tư vấn pháp luật chuyên nghiệp**: Trả lời các câu hỏi về pháp luật Việt Nam
- **Giao diện web thân thiện**: Chat interface dễ sử dụng
- **Streaming response**: Hiển thị câu trả lời theo thời gian thực
- **Hỗ trợ GPU**: Tối ưu hóa cho NVIDIA GPU (RTX 4080)
- **Lịch sử chat**: Lưu trữ và hiển thị lịch sử trò chuyện

## Công nghệ sử dụng

- **Backend**: FastAPI, Python
- **AI Model**: Qwen2 (trained checkpoint)
- **Frontend**: HTML, CSS, JavaScript
- **Deep Learning**: PyTorch, Transformers
- **GPU Support**: CUDA 12.1, NVIDIA RTX 4080

## Yêu cầu hệ thống

- Python 3.11+
- NVIDIA GPU (khuyến nghị RTX 4080 hoặc tương đương)
- CUDA 12.1+
- RAM: 16GB+
- VRAM: 8GB+ (cho GPU)

## Cài đặt

### 1. Clone repository
```bash
git clone <your-repository-url>
cd your-path
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cài đặt PyTorch với CUDA support
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Cài đặt thư viện Qwen
```bash
pip install qwen
```

## Sử dụng

### Khởi động ứng dụng
```bash
python app.py
```

### Truy cập ứng dụng
Mở trình duyệt và truy cập: `http://127.0.0.1:8000`

## 📁 Cấu trúc dự án

```
inference_simpleQA_dsp391m/
├── app.py                 # FastAPI application
├── inference.py           # AI model inference logic
├── checkpoint/            # Trained Qwen2 model checkpoint
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer.json
│   └── ...
├── static/               # Frontend files
│   ├── index.html
│   ├── style.css
│   ├── chat.js
│   └── ...
├── img/                  # Images and icons
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose
└── README.md           # This file
```

## Cấu hình

### Model Configuration
- **Model Type**: Qwen2
- **Architecture**: Qwen2ForCausalLM
- **Hidden Size**: 896
- **Layers**: 24
- **Attention Heads**: 14
- **Vocab Size**: 151,936
- **Max Position**: 32,768

### Generation Parameters
- **Max New Tokens**: 512
- **Temperature**: 0.7
- **Top-p**: 0.9
- **Repetition Penalty**: 1.1
- **Beam Search**: 1

## Giao diện

Ứng dụng có giao diện web hiện đại với:
- Chat interface thân thiện
- Streaming responses
- Responsive design
- Dark/Light theme
- Custom background support

## Hiệu suất

- **CPU Mode**: ~12-15 giây/câu trả lời
- **GPU Mode**: ~4-5 giây/câu trả lời (RTX 4080)
- **Memory Usage**: ~8GB VRAM
- **Model Size**: ~3GB (float16)

## Các chủ đề pháp luật được hỗ trợ

- Quyền lao động
- Hợp đồng
- Đăng ký kinh doanh
- Thuế
- Sở hữu trí tuệ
- Giao thông
- Nghĩa vụ quân sự
- Và nhiều chủ đề khác...

## 🐳 Docker

### Build và chạy với Docker
```bash
docker-compose up --build
```

### Hoặc sử dụng Dockerfile
```bash
docker build -t ai-legal-assistant .
docker run -p 8000:8000 ai-legal-assistant
```

## 🔧 Troubleshooting

### Lỗi CUDA không khả dụng
```bash
# Kiểm tra CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Cài đặt lại PyTorch với CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Lỗi model loading
```bash
# Kiểm tra checkpoint
ls -la checkpoint/

# Test model loading
python test_model.py
```

### Lỗi memory
- Giảm `max_new_tokens` trong `inference.py`
- Sử dụng `torch.float16` thay vì `torch.float32`
- Tăng swap memory

## API Endpoints

### POST /chat
Gửi câu hỏi và nhận câu trả lời

**Request:**
```json
{
  "question": "Câu hỏi pháp luật",
  "chat_history": []
}
```

**Response:**
```
Streaming text response
```
⭐ Nếu dự án này hữu ích, hãy cho một star! 
