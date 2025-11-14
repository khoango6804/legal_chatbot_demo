# 🚀 Deploy Lên Render - Hướng Dẫn Đơn Giản

## ⚡ Quick Start (5 phút)

### Bước 1: Push Code Lên Git

```bash
# Nếu chưa có Git repo
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### Bước 2: Deploy Backend

1. **Vào Render**: https://dashboard.render.com
2. **New +** → **Web Service**
3. **Connect** repository của bạn
4. **Cấu hình:**
   - Name: `legal-ai-backend`
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && python app.py`
   - Plan: **Standard** (2GB RAM) - $25/tháng hoặc Starter (512MB) - Free

5. **Environment Variables** (tab Environment):
   ```
   PORT=8000
   HOST=0.0.0.0
   MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
   MODEL_HF_SUBFOLDER=model
   HF_TOKEN=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
   CORS_ORIGINS=*
   DATABASE_URL=sqlite:///./feedback.db
   ```

6. **Create Web Service** → Chờ deploy (5-10 phút)
7. **Lưu URL**: `https://legal-ai-backend.onrender.com`

### Bước 3: Cấu Hình Frontend

**Sửa `frontend/index.html`** - Thêm trước `</head>`:

```html
<script>
  window.API_BASE_URL = 'https://legal-ai-backend.onrender.com';
</script>
```

**Commit và push:**
```bash
git add frontend/index.html
git commit -m "Update API URL"
git push
```

### Bước 4: Deploy Frontend

1. **Render Dashboard** → **New +** → **Static Site**
2. **Connect** cùng repository
3. **Cấu hình:**
   - Name: `legal-ai-frontend`
   - Root Directory: `frontend`
   - Build: `echo "No build needed"`
   - Publish: `frontend`

4. **Create Static Site** → Chờ deploy
5. **Lưu URL**: `https://legal-ai-frontend.onrender.com`

### Bước 5: Cập Nhật CORS

1. **Backend** → **Environment**
2. Cập nhật: `CORS_ORIGINS=https://legal-ai-frontend.onrender.com`
3. **Save** → Chờ redeploy

### Bước 6: Test

1. Mở frontend URL
2. Chat với AI
3. ✅ Done!

---

## 📝 Environment Variables Checklist

### Backend (Render Dashboard → Environment)

```
✅ PORT=8000
✅ HOST=0.0.0.0
✅ MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
✅ MODEL_HF_SUBFOLDER=model
✅ HF_TOKEN=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
✅ CORS_ORIGINS=https://legal-ai-frontend.onrender.com
✅ DATABASE_URL=sqlite:///./feedback.db
```

---

## 🎯 URLs Sau Khi Deploy

- **Backend**: `https://________________.onrender.com`
- **Frontend**: `https://________________.onrender.com`
- **Health**: `https://________________.onrender.com/health`

---

## ⚠️ Lưu Ý Quan Trọng

1. **Token Security**: Token đã được expose - nên tạo token mới!
2. **Plan**: Standard plan (2GB) khuyến nghị cho model 0.6B
3. **Cold Start**: Free tier có cold start (~30s) - paid plan không có
4. **Model Download**: Lần đầu deploy mất 5-10 phút để download model

---

## 🆘 Troubleshooting

**Model không load?**
- Kiểm tra `HF_TOKEN` đúng chưa
- Xem logs trong Render Dashboard

**CORS error?**
- Kiểm tra `CORS_ORIGINS` có frontend URL chưa
- Đảm bảo không có trailing slash

**Out of Memory?**
- Upgrade lên Standard plan (2GB RAM)

---

Xem chi tiết trong [RENDER_DEPLOY_GUIDE.md](./RENDER_DEPLOY_GUIDE.md)

