# 📖 Hướng Dẫn Deploy Render - Từng Bước Chi Tiết

## 🎯 Mục Tiêu

Deploy ứng dụng lên Render với:
- ✅ Backend API (FastAPI)
- ✅ Frontend (Static Site)
- ✅ Model từ Hugging Face Hub
- ✅ Database (SQLite/PostgreSQL)

---

## 📋 BƯỚC 1: Chuẩn Bị

### 1.1. Đảm Bảo Code Đã Push Lên Git

```bash
# Kiểm tra
git status

# Nếu chưa push
git add .
git commit -m "Ready for deployment"
git push
```

### 1.2. Chuẩn Bị Thông Tin

- ✅ Git repository URL
- ✅ Hugging Face token: `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`
- ✅ Model repo: `sigmaloop/qwen3-0.6B-instruct-trafficlaws`

---

## 🔧 BƯỚC 2: Deploy Backend

### 2.1. Tạo Web Service

1. Đăng nhập: https://dashboard.render.com
2. Click nút **"New +"** (góc trên bên phải)
3. Chọn **"Web Service"**

### 2.2. Kết Nối Repository

**Nếu lần đầu:**
1. Click **"Connect account"**
2. Chọn **GitHub** (hoặc GitLab/Bitbucket)
3. Authorize Render
4. Chọn repository của bạn
5. Click **"Connect"**

**Nếu đã kết nối:**
1. Chọn repository từ dropdown
2. Click **"Connect"**

### 2.3. Cấu Hình Service

Điền thông tin:

| Field | Value |
|-------|-------|
| **Name** | `legal-ai-backend` |
| **Region** | Singapore (hoặc gần nhất) |
| **Branch** | `main` (hoặc branch của bạn) |
| **Root Directory** | (Để trống) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && python app.py` |

### 2.4. Chọn Plan

- **Starter** (Free): 512MB RAM - Có thể không đủ
- **Standard** ($7/tháng): 2GB RAM - **Khuyến nghị** ✅
- **Pro** ($25/tháng): 4GB RAM - Nếu cần nhiều hơn

**Khuyến nghị**: Chọn **Standard** để đảm bảo model load được.

### 2.5. Set Environment Variables

Click tab **"Environment"** và thêm từng biến:

**1. PORT**
```
Key: PORT
Value: 8000
```

**2. HOST**
```
Key: HOST
Value: 0.0.0.0
```

**3. MODEL_HF_REPO**
```
Key: MODEL_HF_REPO
Value: sigmaloop/qwen3-0.6B-instruct-trafficlaws
```

**4. MODEL_HF_SUBFOLDER**
```
Key: MODEL_HF_SUBFOLDER
Value: model
```

**5. HF_TOKEN** (Quan trọng cho private repo!)
```
Key: HF_TOKEN
Value: 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
```

**6. CORS_ORIGINS** (Tạm thời, sẽ cập nhật sau)
```
Key: CORS_ORIGINS
Value: *
```

**7. DATABASE_URL**
```
Key: DATABASE_URL
Value: sqlite:///./feedback.db
```

### 2.6. Deploy

1. Click nút **"Create Web Service"** (màu xanh)
2. Render sẽ bắt đầu:
   - Clone repository
   - Install dependencies
   - Download model từ Hugging Face
   - Start service

3. **Chờ deploy** (5-10 phút lần đầu):
   - Build: ~2-3 phút
   - Model download: ~3-5 phút
   - Start: ~30 giây

### 2.7. Kiểm Tra Deploy

**Xem Logs:**
1. Click vào service vừa tạo
2. Tab **"Logs"**
3. Tìm các dòng:
   - ✅ `✅ Authenticated with Hugging Face Hub`
   - ✅ `Loading model from Hugging Face Hub: sigmaloop/qwen3-0.6B-instruct-trafficlaws/model`
   - ✅ `Model loaded successfully!`
   - ✅ `Application startup complete`

**Test Health:**
1. Copy URL từ dashboard (ví dụ: `https://legal-ai-backend.onrender.com`)
2. Mở browser: `https://your-backend.onrender.com/health`
3. Phải thấy: `{"status":"healthy","service":"Legal AI Assistant API"}`

**Lưu lại Backend URL**: `https://________________.onrender.com`

---

## 🌐 BƯỚC 3: Deploy Frontend

### 3.1. Cấu Hình API URL

**Sửa file `frontend/index.html`:**

Tìm dòng:
```html
    <script>
        window.API_BASE_URL = window.API_BASE_URL || '';
    </script>
```

Thay bằng:
```html
    <script>
        window.API_BASE_URL = 'https://your-backend.onrender.com';
    </script>
```

**Thay `your-backend.onrender.com` bằng URL backend thực tế của bạn!**

**Commit và push:**
```bash
git add frontend/index.html
git commit -m "Update API URL for production"
git push
```

### 3.2. Tạo Static Site

1. Render Dashboard → **"New +"** → **"Static Site"**
2. **Connect** cùng repository
3. Chọn repository

### 3.3. Cấu Hình

| Field | Value |
|-------|-------|
| **Name** | `legal-ai-frontend` |
| **Branch** | `main` |
| **Root Directory** | `frontend` |
| **Build Command** | `echo "No build needed"` |
| **Publish Directory** | `frontend` |

### 3.4. Deploy

1. Click **"Create Static Site"**
2. Chờ deploy (thường < 1 phút)
3. **Lưu lại Frontend URL**: `https://________________.onrender.com`

---

## 🔗 BƯỚC 4: Cấu Hình CORS

### 4.1. Cập Nhật CORS

1. Vào **Backend Service** → Tab **"Environment"**
2. Tìm biến `CORS_ORIGINS`
3. Click **"Edit"**
4. Thay `*` bằng frontend URL:
   ```
   https://legal-ai-frontend.onrender.com
   ```
5. Click **"Save Changes"**
6. Render sẽ tự động redeploy backend

### 4.2. Kiểm Tra

Sau khi redeploy xong:
1. Mở frontend URL
2. Mở Browser DevTools (F12) → Console
3. Thử chat với AI
4. Không có lỗi CORS là OK ✅

---

## 🗄️ BƯỚC 5: Database (Optional)

### 5.1. Tạo PostgreSQL (Khuyến nghị cho Production)

1. Render Dashboard → **"New +"** → **"PostgreSQL"**
2. Cấu hình:
   - **Name**: `legal-ai-db`
   - **Database**: `legal_ai`
   - **Plan**: Free (nếu có) hoặc Starter
3. Click **"Create Database"**

### 5.2. Lấy Connection String

1. Vào Database dashboard
2. Tab **"Connections"**
3. Copy **"Internal Database URL"**
   - Format: `postgresql://user:password@host:port/dbname`

### 5.3. Cập Nhật Backend

1. Backend → **Environment**
2. Tìm `DATABASE_URL`
3. Thay bằng PostgreSQL URL vừa copy
4. **Save** → Chờ redeploy

---

## ✅ BƯỚC 6: Test Toàn Bộ

### 6.1. Test Backend

```bash
# Health check
curl https://your-backend.onrender.com/health

# Expected: {"status":"healthy","service":"Legal AI Assistant API"}
```

### 6.2. Test Frontend

1. Mở frontend URL
2. Test các tính năng:
   - ✅ Chat với AI
   - ✅ Feedback modal
   - ✅ Dark/Light mode
   - ✅ Chat history
   - ✅ Export chat

### 6.3. Test Integration

1. Frontend → Chat với AI
2. Kiểm tra:
   - ✅ Câu trả lời hiển thị
   - ✅ Streaming hoạt động
   - ✅ Feedback có thể gửi
   - ✅ Không có lỗi trong console

---

## 🎉 Hoàn Thành!

Bạn đã có:
- ✅ Backend API: `https://your-backend.onrender.com`
- ✅ Frontend: `https://your-frontend.onrender.com`
- ✅ Model tự động load từ Hugging Face Hub
- ✅ Database hoạt động

**Truy cập frontend URL để sử dụng ứng dụng!**

---

## 📊 Monitoring

### Xem Logs

- **Backend**: Dashboard → Service → Logs
- **Frontend**: Dashboard → Service → Logs

### Health Check

- URL: `https://your-backend.onrender.com/health`
- Render tự động check mỗi 5 phút

### Metrics

- Dashboard → Service → Metrics
- Xem CPU, Memory, Requests

---

## 🔄 Update Code

Khi có code mới:

```bash
git add .
git commit -m "Update"
git push
```

Render sẽ tự động deploy!

---

## 🆘 Nếu Có Lỗi

### Model không load
- ✅ Kiểm tra `HF_TOKEN` đúng chưa
- ✅ Xem logs để tìm lỗi cụ thể
- ✅ Test token: `huggingface-cli whoami --token YOUR_TOKEN`

### CORS error
- ✅ Kiểm tra `CORS_ORIGINS` có frontend URL
- ✅ Đảm bảo không có trailing slash
- ✅ Clear browser cache

### Out of Memory
- ✅ Upgrade lên Standard plan
- ✅ Hoặc giảm model size

### Service không start
- ✅ Xem logs để tìm lỗi
- ✅ Kiểm tra environment variables
- ✅ Kiểm tra build command đúng chưa

---

## 📞 Hỗ Trợ

- Render Docs: https://render.com/docs
- Render Support: support@render.com
- Xem [RENDER_DEPLOY_GUIDE.md](./RENDER_DEPLOY_GUIDE.md) để biết thêm chi tiết

---

**Chúc bạn deploy thành công! 🚀**

