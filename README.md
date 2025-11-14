# 🤖 AI Legal Assistant - Trợ lý AI Tư vấn Pháp luật Giao thông

Một ứng dụng web sử dụng AI để tư vấn các vấn đề pháp luật về giao thông tại Việt Nam, được xây dựng với FastAPI và Qwen3 model.

## 🚀 Tính năng

- **Tư vấn pháp luật chuyên nghiệp**: Trả lời các câu hỏi về pháp luật giao thông Việt Nam
- **Giao diện web hiện đại**: Chat interface với design Apple-inspired
- **Streaming response**: Hiển thị câu trả lời theo thời gian thực
- **Hỗ trợ CPU/GPU**: Tối ưu hóa cho cả CPU và GPU
- **Lịch sử chat**: Lưu trữ và quản lý lịch sử trò chuyện
- **Feedback system**: Người dùng có thể báo lỗi và góp ý
- **Dark/Light mode**: Hỗ trợ chế độ sáng/tối
- **Responsive design**: Hoạt động tốt trên mobile và desktop

## 🏗️ Cấu Trúc Dự Án

```
.
├── backend/                    # Backend API (FastAPI)
│   ├── app.py                 # Main application
│   ├── inference.py           # AI model inference
│   ├── database.py            # Database models
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # Frontend (Static)
│   ├── index.html             # Main HTML
│   ├── style.css              # Styles
│   ├── chat.js                # Chat functionality
│   ├── config.js              # API configuration
│   └── img/                   # Images
│
├── qwen3-0.6B-instruct-trafficlaws/  # Model checkpoint
│   └── model/
│
├── DEPLOYMENT.md              # Hướng dẫn deploy
├── FEEDBACK_SYSTEM.md         # Hướng dẫn feedback system
├── OPTIMIZATION_GUIDE.md      # Hướng dẫn tối ưu hóa
└── README.md                  # File này
```

## 🛠️ Công nghệ sử dụng

- **Backend**: FastAPI, Python 3.11+
- **AI Model**: Qwen3 0.6B (trained on traffic laws)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Deep Learning**: PyTorch, Transformers
- **Deployment**: Render.com

## 📋 Yêu cầu hệ thống

### Development
- Python 3.11+
- RAM: 8GB+ (khuyến nghị 16GB+)
- Disk: 5GB+ (cho model)

### Production (Render)
- Starter plan: 512MB RAM (có thể không đủ)
- Standard plan: 2GB RAM (khuyến nghị)
- Model size: ~2-4GB

## 🚀 Cài đặt Local

### 1. Clone repository
```bash
git clone <your-repository-url>
cd "web chatbot"
```

### 2. Cài đặt Backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Cấu hình Model (Hugging Face Hub)

Model đã được upload tại: **https://huggingface.co/sigmaloop/qwen3-0.6B-instruct-trafficlaws**

Set environment variables:
```bash
# Windows PowerShell:
$env:MODEL_HF_REPO="sigmaloop/qwen3-0.6B-instruct-trafficlaws"
$env:MODEL_HF_SUBFOLDER="model"

# Linux/Mac:
export MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
export MODEL_HF_SUBFOLDER=model
```

Model sẽ tự động download từ Hugging Face Hub khi chạy lần đầu.

### 3. Cài đặt PyTorch (nếu cần GPU)
```bash
# CPU only
pip install torch torchvision torchaudio

# GPU (CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Chạy Backend
```bash
cd backend
python app.py
```

Backend sẽ chạy tại: `http://localhost:8000`

### 5. Chạy Frontend

Có 2 cách:

**Cách 1: Dùng Python HTTP server**
```bash
cd frontend
python -m http.server 8080
```

**Cách 2: Dùng Live Server (VS Code extension)**
- Cài extension "Live Server"
- Right-click `frontend/index.html` → "Open with Live Server"

Frontend sẽ chạy tại: `http://localhost:8080`

### 6. Cấu hình API URL

Mở `frontend/index.html` và thêm trước thẻ `</head>`:
```html
<script>
  window.API_BASE_URL = 'http://localhost:8000';
</script>
```

## 📖 Sử dụng

1. Mở frontend trong browser
2. Nhập câu hỏi về pháp luật giao thông
3. Nhận câu trả lời từ AI
4. Có thể gửi feedback nếu câu trả lời sai hoặc cần cải thiện

## 🗄️ Database

### Development (SQLite)
Database tự động tạo file `backend/feedback.db` khi chạy app.

### Production (PostgreSQL)
Xem hướng dẫn trong [DEPLOYMENT.md](./DEPLOYMENT.md)

## 🚀 Deploy

Xem hướng dẫn chi tiết trong [DEPLOYMENT.md](./DEPLOYMENT.md)

### Quick Deploy trên Render:

1. **Backend**: Tạo Web Service
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && python app.py`

2. **Frontend**: Tạo Static Site
   - Publish Directory: `frontend`

## 📝 API Endpoints

- `POST /chat` - Chat với AI
- `POST /feedback` - Gửi feedback
- `GET /feedback` - Xem feedback (admin)
- `GET /health` - Health check

Xem chi tiết trong [FEEDBACK_SYSTEM.md](./FEEDBACK_SYSTEM.md)

## 🔧 Tối Ưu Hóa

Xem hướng dẫn chi tiết trong [OPTIMIZATION_GUIDE.md](./OPTIMIZATION_GUIDE.md)

### Các tối ưu đã áp dụng:
- ✅ Quantization (8-bit) cho CPU
- ✅ Model compilation (torch.compile)
- ✅ Response caching
- ✅ CPU threading optimization
- ✅ Memory optimization

## 🐛 Troubleshooting

### Model không load được
- Kiểm tra đường dẫn model trong `backend/inference.py`
- Đảm bảo model files đã được download

### Database errors
- Kiểm tra `DATABASE_URL` environment variable
- Đảm bảo có quyền write (SQLite) hoặc kết nối (PostgreSQL)

### CORS errors
- Kiểm tra `CORS_ORIGINS` trong backend
- Đảm bảo frontend URL đúng

## 📚 Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Hướng dẫn deploy
- [FEEDBACK_SYSTEM.md](./FEEDBACK_SYSTEM.md) - Hệ thống feedback
- [OPTIMIZATION_GUIDE.md](./OPTIMIZATION_GUIDE.md) - Tối ưu hóa

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📄 License

Dự án này được phát hành dưới MIT License - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 👨‍💻 Tác giả

- **Tên**: [Your Name]
- **Email**: [your.email@example.com]

## 🙏 Cảm ơn

- Hugging Face Transformers
- Alibaba Qwen team
- FastAPI community
- PyTorch team

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra [Issues](../../issues)
2. Tạo issue mới với mô tả chi tiết
3. Xem documentation trong các file .md

---

⭐ Nếu dự án này hữu ích, hãy cho một star!
