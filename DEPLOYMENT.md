# 🚀 Hướng Dẫn Deploy Lên Render

## 📋 Tổng Quan

Dự án đã được tách thành 2 phần:
- **Backend**: FastAPI service (Python)
- **Frontend**: Static website (HTML/CSS/JS)

## 🏗️ Cấu Trúc Dự Án

```
.
├── backend/              # Backend API
│   ├── app.py           # FastAPI application
│   ├── inference.py      # AI model inference
│   └── requirements.txt # Python dependencies
├── frontend/            # Frontend static files
│   ├── index.html
│   ├── style.css
│   ├── chat.js
│   ├── config.js        # API configuration
│   └── img/            # Images
├── qwen3-0.6B-instruct-trafficlaws/  # Model checkpoint
└── render.yaml          # Render configuration
```

## 🔧 Deploy Backend Lên Render

### Bước 1: Tạo Web Service trên Render

1. Đăng nhập vào [Render](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Kết nối repository GitHub/GitLab của bạn
4. Cấu hình:
   - **Name**: `legal-ai-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python app.py`
   - **Plan**: Chọn plan phù hợp (Starter/Standard)

### Bước 2: Environment Variables

Thêm các biến môi trường:

```
PORT=8000
HOST=0.0.0.0
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=your_huggingface_token_here
# Hoặc dùng local path (nếu không dùng Hugging Face):
# MODEL_PATH=../qwen3-0.6B-instruct-trafficlaws/model
CORS_ORIGINS=https://your-frontend-url.onrender.com
DATABASE_URL=sqlite:///./feedback.db
```

**Lưu ý về Model:**
- **Khuyến nghị**: Dùng Hugging Face Hub - Model đã có tại: `sigmaloop/qwen3-0.6B-instruct-trafficlaws`
- Set `MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws` và `MODEL_HF_SUBFOLDER=model`
- **Nếu repo là Private**: Cần set `HF_TOKEN=your_huggingface_token` để authenticate
  - Lấy token tại: https://huggingface.co/settings/tokens
  - Tạo token với quyền "Read" là đủ
- **Alternative**: Dùng local path - set `MODEL_PATH=../qwen3-0.6B-instruct-trafficlaws/model`
- Model sẽ tự động download từ Hugging Face Hub khi deploy (lần đầu có thể mất vài phút)

**Lưu ý về Database:**
- **Development**: Sử dụng SQLite (mặc định) - file `feedback.db` sẽ được tạo tự động
- **Production**: Nên dùng PostgreSQL (tạo PostgreSQL database trên Render và set `DATABASE_URL`)

**Lưu ý**: 
- `CORS_ORIGINS` nên set thành URL frontend của bạn
- Nếu deploy cùng domain, có thể dùng `*` (không khuyến nghị cho production)

### Bước 3: Upload Model Checkpoint

**Khuyến nghị: Sử dụng Hugging Face Hub** (Dễ nhất!)

Xem hướng dẫn chi tiết trong [UPLOAD_TO_HUGGINGFACE.md](./UPLOAD_TO_HUGGINGFACE.md)

**Quick steps:**
1. Upload model lên Hugging Face Hub
2. Set environment variable: `MODEL_HF_REPO=your-username/repo-name`
3. Model sẽ tự động download khi deploy

**Các cách khác:**

#### Cách 2: Sử dụng Git LFS
```bash
# Cài Git LFS
git lfs install

# Track model files
git lfs track "qwen3-0.6B-instruct-trafficlaws/**"

# Commit và push
git add .gitattributes
git add qwen3-0.6B-instruct-trafficlaws/
git commit -m "Add model with LFS"
git push
```

#### Cách 3: Sử dụng External Storage
- Upload model lên S3/Google Cloud Storage
- Download trong build command:
```bash
# Thêm vào build command
wget https://your-storage-url/model.zip && unzip model.zip
```

### Bước 4: Deploy

1. Click **"Create Web Service"**
2. Render sẽ tự động build và deploy
3. Lưu lại URL backend (ví dụ: `https://legal-ai-backend.onrender.com`)

## 🌐 Deploy Frontend

### Option 1: Static Site trên Render

1. Tạo **Static Site** trên Render
2. Cấu hình:
   - **Build Command**: `echo "No build needed"`
   - **Publish Directory**: `frontend`
3. Thêm Environment Variable:
   ```
   API_BASE_URL=https://your-backend-url.onrender.com
   ```
4. Cập nhật `frontend/config.js` để đọc từ environment variable

### Option 2: Sử dụng Static Hosting Khác

#### Vercel:
```bash
npm i -g vercel
cd frontend
vercel
```

#### Netlify:
1. Kéo thả thư mục `frontend` vào Netlify
2. Set build command: `echo "No build needed"`
3. Set publish directory: `frontend`

#### GitHub Pages:
1. Push code lên GitHub
2. Settings → Pages
3. Source: `frontend` folder

### Cấu Hình API URL

Sau khi deploy frontend, cần cập nhật API URL:

**Cách 1**: Sử dụng `config.js` (đã có sẵn)
- Frontend tự động detect API URL từ `window.API_BASE_URL`
- Có thể set trong build process

**Cách 2**: Sử dụng environment variable
- Thêm script vào `index.html`:
```html
<script>
  window.API_BASE_URL = 'https://your-backend-url.onrender.com';
</script>
```

## 🔐 Cấu Hình CORS

Sau khi có URL frontend, cập nhật CORS trong backend:

1. Vào Render Dashboard → Backend Service → Environment
2. Cập nhật `CORS_ORIGINS`:
```
CORS_ORIGINS=https://your-frontend-url.onrender.com,https://your-custom-domain.com
```

## 📊 Monitoring & Logs

### Xem Logs:
- Render Dashboard → Service → Logs
- Hoặc dùng Render CLI:
```bash
render logs --service legal-ai-backend
```

### Health Check:
- Backend health endpoint: `https://your-backend-url.onrender.com/health`
- Kiểm tra model đã load: Xem logs

## ⚠️ Lưu Ý Quan Trọng

### 1. Model Size
- Model checkpoint có thể rất lớn (>1GB)
- Render free tier có giới hạn
- Cân nhắc sử dụng Git LFS hoặc external storage

### 2. Memory Requirements
- Model 0.6B cần ~2-4GB RAM
- Render Starter plan: 512MB RAM (có thể không đủ)
- Khuyến nghị: Standard plan (2GB RAM) hoặc cao hơn

### 3. Cold Start
- Render free tier có cold start (~30s-2min)
- Model loading mất thêm thời gian
- Cân nhắc upgrade plan để tránh sleep

### 4. Timeout
- Render có timeout limit
- Model inference có thể mất >30s
- Cân nhắc tăng timeout hoặc optimize model

## 🐛 Troubleshooting

### Lỗi: Model không load được
- Kiểm tra `MODEL_PATH` environment variable
- Kiểm tra logs để xem đường dẫn model
- Đảm bảo model files đã được upload

### Lỗi: CORS
- Kiểm tra `CORS_ORIGINS` environment variable
- Đảm bảo frontend URL đúng format
- Thử set `*` tạm thời để test

### Lỗi: Out of Memory
- Upgrade plan lên Standard hoặc cao hơn
- Sử dụng quantization (8-bit)
- Giảm `max_new_tokens` trong inference.py

### Lỗi: Timeout
- Tăng timeout trong Render settings
- Optimize model loading
- Sử dụng response caching

## 📝 Checklist Deploy

- [ ] Backend service đã tạo và deploy thành công
- [ ] Model checkpoint đã được upload
- [ ] Environment variables đã set đúng
- [ ] Database đã được setup (SQLite hoặc PostgreSQL)
- [ ] Frontend đã deploy và có thể truy cập
- [ ] API URL đã được cấu hình trong frontend
- [ ] CORS đã được cấu hình đúng
- [ ] Health check endpoint hoạt động
- [ ] Test chat functionality
- [ ] Test feedback functionality

## 🎉 Hoàn Thành!

Sau khi deploy xong, bạn sẽ có:
- Backend API: `https://your-backend.onrender.com`
- Frontend: `https://your-frontend.onrender.com`

Truy cập frontend URL để sử dụng ứng dụng!

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra logs trên Render Dashboard
2. Xem [OPTIMIZATION_GUIDE.md](./OPTIMIZATION_GUIDE.md) để tối ưu
3. Kiểm tra [Render Documentation](https://render.com/docs)

