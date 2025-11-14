# 🛠️ Hướng Dẫn Setup Local Development

## 📋 Yêu Cầu

- Python 3.11+
- pip
- Git

## 🚀 Setup Nhanh

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd "web chatbot"
```

### 2. Setup Backend

```bash
# Vào thư mục backend
cd backend

# Tạo virtual environment (khuyến nghị)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 3. Kiểm Tra Model

Đảm bảo model checkpoint đã có trong:
```
qwen3-0.6B-instruct-trafficlaws/model/
```

Nếu chưa có, bạn cần:
- Download model files
- Hoặc copy từ nơi khác

### 4. Chạy Backend

```bash
cd backend
python app.py
```

Backend sẽ chạy tại: `http://localhost:8000`

**Kiểm tra:**
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 5. Setup Frontend

**Cách 1: Python HTTP Server**
```bash
cd frontend
python -m http.server 8080
```

**Cách 2: Live Server (VS Code)**
1. Cài extension "Live Server"
2. Right-click `frontend/index.html`
3. Chọn "Open with Live Server"

**Cách 3: Node.js (nếu có)**
```bash
cd frontend
npx http-server -p 8080
```

### 6. Cấu Hình API URL

Mở `frontend/index.html` và thêm trước `</head>`:

```html
<script>
  window.API_BASE_URL = 'http://localhost:8000';
</script>
```

Hoặc chỉnh trong `frontend/config.js`:

```javascript
const API_CONFIG = {
    baseURL: 'http://localhost:8000'
};
```

## 🧪 Test

### Test Backend
```bash
# Health check
curl http://localhost:8000/health

# Test chat (cần model đã load)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Xử phạt vượt đèn đỏ là gì?"}'
```

### Test Frontend
1. Mở browser: http://localhost:8080
2. Thử chat với AI
3. Kiểm tra feedback functionality

## 🗄️ Database

### SQLite (Development)
Database tự động tạo file `backend/feedback.db` khi chạy app lần đầu.

### Xem Database
```bash
# Cài sqlite3 (nếu chưa có)
# Windows: Download từ sqlite.org
# Linux: sudo apt-get install sqlite3
# Mac: brew install sqlite3

# Xem feedback
sqlite3 backend/feedback.db "SELECT * FROM feedback;"
```

## 🔧 Troubleshooting

### Lỗi: Module not found
```bash
# Đảm bảo đã activate virtual environment
# Và cài đặt dependencies
pip install -r backend/requirements.txt
```

### Lỗi: Model not found
- Kiểm tra đường dẫn trong `backend/inference.py`
- Đảm bảo model files đã có trong `qwen3-0.6B-instruct-trafficlaws/model/`

### Lỗi: Port already in use
```bash
# Windows: Tìm process dùng port
netstat -ano | findstr :8000
# Kill process
taskkill /PID <PID> /F

# Linux/Mac: Tìm và kill
lsof -ti:8000 | xargs kill
```

### Lỗi: CORS
- Đảm bảo `CORS_ORIGINS` trong backend cho phép `http://localhost:8080`
- Hoặc set `CORS_ORIGINS=*` cho development

## 📝 Environment Variables

Tạo file `.env` trong thư mục `backend/`:

```env
PORT=8000
HOST=0.0.0.0
MODEL_PATH=../qwen3-0.6B-instruct-trafficlaws/model
DATABASE_URL=sqlite:///./feedback.db
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

## 🎯 Development Workflow

1. **Terminal 1**: Chạy backend
   ```bash
   cd backend
   python app.py
   ```

2. **Terminal 2**: Chạy frontend
   ```bash
   cd frontend
   python -m http.server 8080
   ```

3. **Browser**: Mở http://localhost:8080

4. **Edit code**: Thay đổi code và refresh browser

## 💡 Tips

- Sử dụng VS Code với extensions:
  - Python
  - Live Server
  - Prettier
- Enable auto-save trong VS Code
- Sử dụng browser DevTools để debug
- Check backend logs trong terminal

## 🚀 Next Steps

Sau khi setup xong local:
1. Test tất cả tính năng
2. Xem [DEPLOYMENT.md](./DEPLOYMENT.md) để deploy
3. Xem [OPTIMIZATION_GUIDE.md](./OPTIMIZATION_GUIDE.md) để tối ưu

