# 🚀 Hướng Dẫn Deploy Lên Render - Step by Step

## 📋 Chuẩn Bị

### 1. Tài Khoản Render
- Đăng ký tại: https://render.com
- Đăng nhập vào dashboard

### 2. Git Repository
- Code đã được push lên GitHub/GitLab/Bitbucket
- Repository phải là **public** hoặc kết nối với Render

### 3. Hugging Face Token
- Token đã có: `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`
- Hoặc tạo mới tại: https://huggingface.co/settings/tokens

---

## 🔧 Bước 1: Deploy Backend

### 1.1. Tạo Web Service

1. Vào Render Dashboard: https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Kết nối repository:
   - Nếu lần đầu: Click **"Connect account"** → Chọn GitHub/GitLab
   - Chọn repository của bạn
   - Click **"Connect"**

### 1.2. Cấu Hình Backend Service

**Basic Settings:**
- **Name**: `legal-ai-backend` (hoặc tên bạn muốn)
- **Region**: Chọn gần nhất (Singapore, US, etc.)
- **Branch**: `main` (hoặc branch bạn muốn)
- **Root Directory**: Để trống (hoặc `backend` nếu cần)

**Build & Deploy:**
- **Environment**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r backend/requirements.txt
  ```
- **Start Command**: 
  ```bash
  cd backend && python app.py
  ```

**Plan:**
- **Starter**: 512MB RAM (có thể không đủ cho model)
- **Standard**: 2GB RAM (khuyến nghị) - $7/tháng
- **Pro**: 4GB RAM - $25/tháng

### 1.3. Environment Variables

Click **"Environment"** tab và thêm:

```
PORT=8000
HOST=0.0.0.0
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=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
CORS_ORIGINS=*
DATABASE_URL=sqlite:///./feedback.db
```

**Lưu ý:**
- `HF_TOKEN`: Token của bạn (nếu repo private)
- `CORS_ORIGINS`: Sẽ cập nhật sau khi có frontend URL
- `DATABASE_URL`: SQLite cho free tier, hoặc tạo PostgreSQL sau

### 1.4. Deploy Backend

1. Click **"Create Web Service"**
2. Render sẽ tự động:
   - Clone repository
   - Install dependencies
   - Download model từ Hugging Face Hub
   - Start service

3. **Chờ deploy hoàn thành** (có thể mất 5-10 phút lần đầu)
   - Build: ~2-3 phút
   - Model download: ~3-5 phút (tùy kích thước)

4. **Lưu lại URL backend**: 
   - Ví dụ: `https://legal-ai-backend.onrender.com`
   - URL này sẽ dùng cho frontend

### 1.5. Kiểm Tra Backend

1. Mở URL backend trong browser
2. Kiểm tra health: `https://your-backend.onrender.com/health`
3. Xem logs trong Render Dashboard → Logs
4. Tìm dòng: `✅ Authenticated with Hugging Face Hub`
5. Tìm dòng: `Model loaded successfully!`

---

## 🌐 Bước 2: Deploy Frontend

### 2.1. Tạo Static Site

1. Vào Render Dashboard
2. Click **"New +"** → **"Static Site"**
3. Kết nối repository (cùng repo với backend)

### 2.2. Cấu Hình Frontend

**Basic Settings:**
- **Name**: `legal-ai-frontend`
- **Branch**: `main`
- **Root Directory**: `frontend`

**Build Settings:**
- **Build Command**: 
  ```bash
  echo "No build needed"
  ```
- **Publish Directory**: `frontend`

### 2.3. Environment Variables (Optional)

Có thể set để inject vào HTML:
```
API_BASE_URL=https://your-backend.onrender.com
```

### 2.4. Cấu Hình API URL

**Cách 1: Sửa trực tiếp trong code**

Mở `frontend/index.html` và thêm trước `</head>`:

```html
<script>
  window.API_BASE_URL = 'https://your-backend.onrender.com';
</script>
```

**Cách 2: Sử dụng Build Command**

Thêm vào Build Command:
```bash
sed -i "s|window.API_BASE_URL = ''|window.API_BASE_URL = 'https://your-backend.onrender.com'|g" frontend/index.html || echo "No build needed"
```

### 2.5. Deploy Frontend

1. Click **"Create Static Site"**
2. Render sẽ deploy frontend
3. **Lưu lại URL frontend**: 
   - Ví dụ: `https://legal-ai-frontend.onrender.com`

---

## 🔗 Bước 3: Cấu Hình CORS

Sau khi có frontend URL:

1. Vào Backend Service → **Environment**
2. Cập nhật `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://legal-ai-frontend.onrender.com
   ```
3. Click **"Save Changes"**
4. Render sẽ tự động redeploy

---

## 🗄️ Bước 4: Setup Database (Optional - Khuyến nghị)

### 4.1. Tạo PostgreSQL Database

1. Render Dashboard → **"New +"** → **"PostgreSQL"**
2. Cấu hình:
   - **Name**: `legal-ai-db`
   - **Database**: `legal_ai`
   - **User**: Tự động tạo
   - **Plan**: Free tier (nếu có) hoặc Starter
3. Click **"Create Database"**

### 4.2. Lấy Connection String

1. Vào Database dashboard
2. Copy **"Internal Database URL"** hoặc **"External Database URL"**
3. Format: `postgresql://user:password@host:port/dbname`

### 4.3. Cập Nhật Backend

1. Vào Backend → **Environment**
2. Cập nhật `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   ```
3. Save → Backend sẽ tự động redeploy

---

## ✅ Bước 5: Test

### 5.1. Test Backend

```bash
# Health check
curl https://your-backend.onrender.com/health

# Test chat (cần model đã load)
curl -X POST https://your-backend.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Xử phạt vượt đèn đỏ là gì?"}'
```

### 5.2. Test Frontend

1. Mở frontend URL trong browser
2. Thử chat với AI
3. Kiểm tra feedback functionality
4. Kiểm tra dark/light mode

### 5.3. Kiểm Tra Logs

**Backend Logs:**
- Render Dashboard → Backend Service → Logs
- Tìm: `Model loaded successfully!`
- Tìm: `Application startup complete`

**Frontend Logs:**
- Render Dashboard → Frontend Service → Logs
- Kiểm tra có lỗi không

---

## 🔧 Troubleshooting

### Lỗi: Model không load được

**Kiểm tra:**
1. `HF_TOKEN` đã set đúng chưa?
2. Token có quyền truy cập repo không?
3. Xem logs để tìm lỗi cụ thể

**Giải pháp:**
- Kiểm tra token tại: https://huggingface.co/settings/tokens
- Test token: `huggingface-cli whoami --token YOUR_TOKEN`

### Lỗi: Out of Memory

**Triệu chứng:**
- Service bị restart liên tục
- Logs: "Killed" hoặc "Out of memory"

**Giải pháp:**
- Upgrade plan lên Standard (2GB) hoặc Pro (4GB)
- Hoặc sử dụng quantization (8-bit)

### Lỗi: CORS

**Triệu chứng:**
- Frontend không gọi được API
- Browser console: "CORS policy"

**Giải pháp:**
- Kiểm tra `CORS_ORIGINS` đã set đúng frontend URL chưa
- Đảm bảo không có trailing slash
- Format: `https://frontend.onrender.com` (không có `/` cuối)

### Lỗi: Database Connection

**Triệu chứng:**
- Feedback không lưu được
- Logs: "Connection refused" hoặc "Authentication failed"

**Giải pháp:**
- Kiểm tra `DATABASE_URL` format đúng chưa
- Đảm bảo database đã được tạo
- Kiểm tra database đang running

### Lỗi: Cold Start Chậm

**Triệu chứng:**
- Lần đầu request mất rất lâu (~30s-2min)

**Giải pháp:**
- Đây là bình thường với free tier
- Upgrade lên paid plan để tránh sleep
- Hoặc dùng health check endpoint để keep-alive

---

## 📊 Monitoring

### Health Check

Tạo health check endpoint (đã có sẵn):
- URL: `https://your-backend.onrender.com/health`
- Response: `{"status": "healthy"}`

### Logs

- **Backend**: Dashboard → Service → Logs
- **Frontend**: Dashboard → Service → Logs
- **Database**: Dashboard → Database → Logs

### Metrics

Render cung cấp metrics:
- CPU usage
- Memory usage
- Request count
- Response time

---

## 🔄 Update Code

Khi có code mới:

1. **Push lên Git:**
   ```bash
   git add .
   git commit -m "Update code"
   git push
   ```

2. **Render tự động deploy:**
   - Render sẽ detect push
   - Tự động build và deploy
   - Có thể xem progress trong Dashboard

3. **Manual Deploy (nếu cần):**
   - Dashboard → Service → Manual Deploy
   - Chọn commit → Deploy

---

## 💰 Pricing

### Free Tier
- **Web Service**: 750 hours/month (có thể hết)
- **Static Site**: Unlimited
- **PostgreSQL**: 90 days free trial
- **Limitations**: 
  - Service sleep sau 15 phút không dùng
  - Cold start chậm

### Paid Plans
- **Starter**: $7/month - 512MB RAM
- **Standard**: $25/month - 2GB RAM (khuyến nghị)
- **Pro**: $85/month - 4GB RAM

---

## ✅ Checklist Deploy

### Backend
- [ ] Repository đã được kết nối
- [ ] Build command đúng: `pip install -r backend/requirements.txt`
- [ ] Start command đúng: `cd backend && python app.py`
- [ ] Environment variables đã set:
  - [ ] `MODEL_HF_REPO`
  - [ ] `MODEL_HF_SUBFOLDER`
  - [ ] `HF_TOKEN`
  - [ ] `CORS_ORIGINS`
  - [ ] `DATABASE_URL`
- [ ] Service đã deploy thành công
- [ ] Health check hoạt động
- [ ] Model đã load (check logs)

### Frontend
- [ ] Static site đã được tạo
- [ ] Publish directory: `frontend`
- [ ] API URL đã được cấu hình
- [ ] Frontend đã deploy thành công
- [ ] Có thể truy cập được

### Integration
- [ ] CORS đã được cấu hình đúng
- [ ] Frontend có thể gọi backend API
- [ ] Chat functionality hoạt động
- [ ] Feedback system hoạt động

---

## 🎉 Hoàn Thành!

Sau khi hoàn thành tất cả bước:

- ✅ Backend: `https://your-backend.onrender.com`
- ✅ Frontend: `https://your-frontend.onrender.com`
- ✅ Database: Đã setup (nếu dùng PostgreSQL)
- ✅ Model: Tự động load từ Hugging Face Hub

**Truy cập frontend URL để sử dụng ứng dụng!**

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra logs trong Render Dashboard
2. Xem [DEPLOYMENT.md](./DEPLOYMENT.md) để biết thêm chi tiết
3. Render Documentation: https://render.com/docs
4. Render Support: support@render.com

