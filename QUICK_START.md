# 🚀 Quick Start Guide

## ⚡ Deploy Nhanh Với Hugging Face Hub

Model đã được upload tại: **https://huggingface.co/sigmaloop/qwen3-0.6B-instruct-trafficlaws**

### Bước 1: Deploy Backend trên Render

1. **Tạo Web Service**
   - Name: `legal-ai-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && python app.py`

2. **Set Environment Variables:**
   ```
   PORT=8000
   HOST=0.0.0.0
   MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
   MODEL_HF_SUBFOLDER=model
   HF_TOKEN=your_huggingface_token_here
   CORS_ORIGINS=*
   DATABASE_URL=sqlite:///./feedback.db
   ```
   
   ⚠️ **Lưu ý**: Nếu repo là **Private**, bắt buộc phải set `HF_TOKEN`!
   - Lấy token tại: https://huggingface.co/settings/tokens
   - Xem hướng dẫn: [HUGGINGFACE_PRIVATE_REPO.md](./HUGGINGFACE_PRIVATE_REPO.md)

3. **Deploy!** Model sẽ tự động download từ Hugging Face Hub.

### Bước 2: Deploy Frontend trên Render

1. **Tạo Static Site**
   - Publish Directory: `frontend`
   - Build Command: `echo "No build needed"`

2. **Cấu hình API URL:**
   Thêm vào `frontend/index.html` (trước `</head>`):
   ```html
   <script>
     window.API_BASE_URL = 'https://your-backend-url.onrender.com';
   </script>
   ```

### Bước 3: Test

1. Mở frontend URL
2. Chat với AI
3. Test feedback functionality

## 🧪 Test Local

### Setup Backend

```bash
cd backend

# Set environment variables
# Windows PowerShell:
$env:MODEL_HF_REPO="sigmaloop/qwen3-0.6B-instruct-trafficlaws"
$env:MODEL_HF_SUBFOLDER="model"

# Linux/Mac:
export MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
export MODEL_HF_SUBFOLDER=model

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

### Setup Frontend

```bash
cd frontend

# Set API URL trong index.html
# Thêm: window.API_BASE_URL = 'http://localhost:8000';

# Run HTTP server
python -m http.server 8080
```

Mở browser: http://localhost:8080

## 📝 Environment Variables Summary

### Backend (Render)
```
PORT=8000
HOST=0.0.0.0
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
CORS_ORIGINS=https://your-frontend-url.onrender.com
DATABASE_URL=postgresql://... (nếu dùng PostgreSQL)
```

### Frontend
```html
<script>
  window.API_BASE_URL = 'https://your-backend-url.onrender.com';
</script>
```

## ✅ Checklist

- [ ] Backend deployed trên Render
- [ ] Environment variables đã set đúng
- [ ] Frontend deployed trên Render
- [ ] API URL đã được cấu hình
- [ ] Test chat functionality
- [ ] Test feedback functionality

## 🎉 Done!

Sau khi deploy, bạn sẽ có:
- Backend: `https://your-backend.onrender.com`
- Frontend: `https://your-frontend.onrender.com`
- Model tự động load từ Hugging Face Hub!

---

**Model Repository**: https://huggingface.co/sigmaloop/qwen3-0.6B-instruct-trafficlaws

