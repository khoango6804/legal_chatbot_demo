# 🔐 Hướng Dẫn Sử Dụng Private Hugging Face Repo

## ⚠️ Lưu Ý Bảo Mật

**KHÔNG BAO GIỜ commit token vào Git!**

Token của bạn: `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`

⚠️ **Quan trọng**: Token này đã được expose trong chat. Nên tạo token mới và revoke token cũ!

## 🔑 Tạo Token Mới (Khuyến nghị)

1. Vào https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Đặt tên: `render-deployment` (hoặc tên khác)
4. Chọn quyền: **Read** (đủ để download model)
5. Click **"Generate token"**
6. **Copy token ngay** (chỉ hiển thị 1 lần)

## 📝 Cấu Hình

### Local Development

**Windows PowerShell:**
```powershell
$env:MODEL_HF_REPO="sigmaloop/qwen3-0.6B-instruct-trafficlaws"
$env:MODEL_HF_SUBFOLDER="model"
$env:HF_TOKEN="your_token_here"
```

**Linux/Mac:**
```bash
export MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
export MODEL_HF_SUBFOLDER=model
export HF_TOKEN=your_token_here
```

**Hoặc tạo file `.env` trong thư mục `backend/`:**
```env
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=your_token_here
```

### Render Deployment

Trong Render Dashboard → Environment Variables:

```
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=your_token_here
```

⚠️ **Lưu ý**: Thay `your_token_here` bằng token thực tế của bạn!

## ✅ Kiểm Tra

Sau khi set token, khi chạy backend bạn sẽ thấy:
```
✅ Authenticated with Hugging Face Hub
Loading model from Hugging Face Hub: sigmaloop/qwen3-0.6B-instruct-trafficlaws/model
```

Nếu không có token hoặc token sai, sẽ thấy lỗi:
```
401 Client Error: Unauthorized for url: https://huggingface.co/...
```

## 🔒 Security Best Practices

1. **Không commit token vào Git**
   - Token đã có trong `.gitignore`
   - Kiểm tra lại trước khi commit

2. **Sử dụng Environment Variables**
   - Không hardcode token trong code
   - Chỉ set trong environment variables

3. **Rotate Token Thường Xuyên**
   - Tạo token mới định kỳ
   - Revoke token cũ

4. **Minimal Permissions**
   - Chỉ cần quyền "Read"
   - Không cần "Write" hoặc "Admin"

## 🧪 Test Local

```bash
# Set token
export HF_TOKEN=your_token_here

# Chạy backend
cd backend
python app.py
```

Kiểm tra logs để xem có authenticate thành công không.

## 🚨 Nếu Token Bị Lộ

1. **Revoke token ngay**: https://huggingface.co/settings/tokens
2. **Tạo token mới**
3. **Cập nhật trong Render** environment variables
4. **Kiểm tra logs** để đảm bảo hoạt động

## 📚 Tham Khảo

- Hugging Face Tokens: https://huggingface.co/docs/hub/security-tokens
- Environment Variables: https://render.com/docs/environment-variables

