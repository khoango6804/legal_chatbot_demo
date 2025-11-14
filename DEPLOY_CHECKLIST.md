# ✅ Deploy Checklist - Render

## 📋 Trước Khi Deploy

### Code Preparation
- [ ] Code đã được push lên Git repository
- [ ] Repository là public hoặc đã kết nối với Render
- [ ] Tất cả files cần thiết đã có trong repo
- [ ] `.gitignore` đã đúng (không commit .env, token, etc.)

### Model Preparation
- [ ] Model đã upload lên Hugging Face Hub
- [ ] Repository: `sigmaloop/qwen3-0.6B-instruct-trafficlaws`
- [ ] Model nằm trong thư mục `model/`
- [ ] Đã có Hugging Face token (nếu repo private)

### Environment Variables List
Chuẩn bị sẵn các giá trị:
- [ ] `MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws`
- [ ] `MODEL_HF_SUBFOLDER=model`
- [ ] `HF_TOKEN=hf_...` (nếu repo private)
- [ ] `CORS_ORIGINS=*` (sẽ cập nhật sau)
- [ ] `DATABASE_URL=sqlite:///./feedback.db` (hoặc PostgreSQL URL)

---

## 🚀 Deploy Backend

### Step 1: Tạo Web Service
- [ ] Vào Render Dashboard
- [ ] Click "New +" → "Web Service"
- [ ] Kết nối Git repository
- [ ] Chọn repository

### Step 2: Cấu Hình
- [ ] Name: `legal-ai-backend`
- [ ] Region: Chọn gần nhất
- [ ] Branch: `main`
- [ ] Root Directory: (để trống hoặc `backend`)
- [ ] Environment: `Python 3`
- [ ] Build Command: `pip install -r backend/requirements.txt`
- [ ] Start Command: `cd backend && python app.py`
- [ ] Plan: Chọn plan (Starter/Standard)

### Step 3: Environment Variables
- [ ] `PORT=8000`
- [ ] `HOST=0.0.0.0`
- [ ] `MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws`
- [ ] `MODEL_HF_SUBFOLDER=model`
- [ ] `HF_TOKEN=your_token_here` (nếu repo private)
- [ ] `CORS_ORIGINS=*` (tạm thời, sẽ cập nhật sau)
- [ ] `DATABASE_URL=sqlite:///./feedback.db`

### Step 4: Deploy
- [ ] Click "Create Web Service"
- [ ] Chờ build hoàn thành
- [ ] Chờ model download (có thể mất vài phút)
- [ ] Kiểm tra logs: `Model loaded successfully!`
- [ ] Lưu backend URL: `https://your-backend.onrender.com`

### Step 5: Test Backend
- [ ] Mở: `https://your-backend.onrender.com/health`
- [ ] Kiểm tra response: `{"status": "healthy"}`
- [ ] Xem logs để đảm bảo model đã load

---

## 🌐 Deploy Frontend

### Step 1: Tạo Static Site
- [ ] Render Dashboard → "New +" → "Static Site"
- [ ] Kết nối cùng repository
- [ ] Chọn repository

### Step 2: Cấu Hình
- [ ] Name: `legal-ai-frontend`
- [ ] Branch: `main`
- [ ] Root Directory: `frontend`
- [ ] Build Command: `echo "No build needed"`
- [ ] Publish Directory: `frontend`

### Step 3: Cấu Hình API URL

**Option A: Sửa code trước khi push**
- [ ] Mở `frontend/index.html`
- [ ] Thêm trước `</head>`:
  ```html
  <script>
    window.API_BASE_URL = 'https://your-backend.onrender.com';
  </script>
  ```
- [ ] Commit và push

**Option B: Sử dụng Build Command**
- [ ] Thêm vào Build Command:
  ```bash
  sed -i "s|window.API_BASE_URL = ''|window.API_BASE_URL = 'https://your-backend.onrender.com'|g" index.html || echo "No build needed"
  ```

### Step 4: Deploy
- [ ] Click "Create Static Site"
- [ ] Chờ deploy hoàn thành
- [ ] Lưu frontend URL: `https://your-frontend.onrender.com`

### Step 5: Test Frontend
- [ ] Mở frontend URL
- [ ] Kiểm tra có load được không
- [ ] Test chat functionality

---

## 🔗 Cấu Hình CORS

- [ ] Vào Backend → Environment
- [ ] Cập nhật `CORS_ORIGINS`:
  ```
  CORS_ORIGINS=https://your-frontend.onrender.com
  ```
- [ ] Save changes
- [ ] Chờ redeploy
- [ ] Test lại frontend → backend connection

---

## 🗄️ Database (Optional)

### Nếu dùng PostgreSQL:
- [ ] Tạo PostgreSQL database trên Render
- [ ] Copy connection string
- [ ] Cập nhật `DATABASE_URL` trong backend
- [ ] Save và chờ redeploy
- [ ] Test feedback functionality

### Nếu dùng SQLite:
- [ ] Đã set: `DATABASE_URL=sqlite:///./feedback.db`
- [ ] Database sẽ tự động tạo khi app start

---

## ✅ Final Testing

### Backend Tests
- [ ] Health check: `/health`
- [ ] Chat endpoint: `/chat` (POST)
- [ ] Feedback endpoint: `/feedback` (POST)
- [ ] Logs không có lỗi

### Frontend Tests
- [ ] Page load được
- [ ] Chat với AI hoạt động
- [ ] Feedback modal hoạt động
- [ ] Dark/Light mode hoạt động
- [ ] Responsive design OK

### Integration Tests
- [ ] Frontend gọi được backend API
- [ ] Chat streaming hoạt động
- [ ] Feedback lưu vào database
- [ ] Không có CORS errors

---

## 📝 URLs Summary

Sau khi deploy xong, lưu lại:

- **Backend URL**: `https://________________.onrender.com`
- **Frontend URL**: `https://________________.onrender.com`
- **Health Check**: `https://________________.onrender.com/health`
- **API Docs**: `https://________________.onrender.com/docs`

---

## 🎯 Next Steps

Sau khi deploy thành công:

1. **Custom Domain** (Optional):
   - Render Dashboard → Service → Settings → Custom Domain
   - Thêm domain của bạn

2. **Monitoring**:
   - Setup alerts trong Render
   - Monitor logs thường xuyên

3. **Backup**:
   - Backup database định kỳ
   - Backup code repository

4. **Optimization**:
   - Monitor performance
   - Optimize model loading
   - Cache responses

---

## 🆘 Nếu Có Lỗi

1. **Check Logs**: Render Dashboard → Service → Logs
2. **Check Environment Variables**: Đảm bảo đã set đúng
3. **Check Model**: Đảm bảo model đã upload và accessible
4. **Check Token**: Test token với `huggingface-cli whoami --token YOUR_TOKEN`
5. **Check CORS**: Đảm bảo frontend URL đúng trong CORS_ORIGINS

---

**Status**: ⏳ Ready to Deploy
**Last Updated**: [Current Date]

