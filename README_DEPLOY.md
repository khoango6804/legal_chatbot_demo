# 🚀 Quick Start - Deploy Guide

## 📁 Cấu Trúc Dự Án Sau Khi Tách

```
.
├── backend/                    # Backend API (FastAPI)
│   ├── app.py                 # Main application
│   ├── inference.py            # AI model logic
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
├── render.yaml                 # Render configuration
└── DEPLOYMENT.md              # Chi tiết deployment
```

## 🎯 Deploy Nhanh

### Backend (Render)

1. **Tạo Web Service trên Render**
   - Name: `legal-ai-backend`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && python app.py`

2. **Environment Variables**
   ```
   PORT=8000
   MODEL_PATH=../qwen3-0.6B-instruct-trafficlaws/model
   CORS_ORIGINS=*
   ```

3. **Upload Model**: Sử dụng Git LFS hoặc external storage

### Frontend (Render Static Site)

1. **Tạo Static Site trên Render**
   - Publish Directory: `frontend`
   - Build Command: `echo "No build needed"`

2. **Cấu hình API URL**
   - Thêm vào `frontend/index.html`:
   ```html
   <script>
     window.API_BASE_URL = 'https://your-backend-url.onrender.com';
   </script>
   ```

## 📖 Xem Chi Tiết

Xem file [DEPLOYMENT.md](./DEPLOYMENT.md) để biết hướng dẫn chi tiết!

## ⚠️ Lưu Ý

- Model cần ~2-4GB RAM → Cần Standard plan trở lên
- Free tier có cold start → Có thể chậm lần đầu
- Model files lớn → Cần Git LFS hoặc external storage

