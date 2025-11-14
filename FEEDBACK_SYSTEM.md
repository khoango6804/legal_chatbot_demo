# 📝 Hệ Thống Feedback

## 🎯 Tổng Quan

Hệ thống feedback cho phép người dùng báo cáo khi:
- **Câu trả lời sai** (`wrong`): Câu trả lời không chính xác
- **Lỗi kỹ thuật** (`error`): Lỗi khi xử lý hoặc hiển thị
- **Cần cải thiện** (`improvement`): Đề xuất cải thiện câu trả lời

## 🗄️ Database Schema

### Feedback Table

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    feedback_type VARCHAR(50) NOT NULL,
    message TEXT,
    user_agent VARCHAR(500),
    ip_address VARCHAR(50),
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🔌 API Endpoints

### POST /feedback

Gửi feedback từ người dùng.

**Request:**
```json
{
  "question": "Câu hỏi của người dùng",
  "answer": "Câu trả lời từ AI",
  "feedback_type": "wrong|error|improvement",
  "message": "Chi tiết phản hồi (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cảm ơn bạn đã gửi phản hồi!",
  "feedback_id": 1
}
```

### GET /feedback

Lấy danh sách feedback (admin).

**Query Parameters:**
- `skip`: Số lượng bỏ qua (pagination)
- `limit`: Số lượng trả về (default: 50)
- `resolved`: Filter theo trạng thái (true/false/null)

**Response:**
```json
{
  "total": 10,
  "skip": 0,
  "limit": 50,
  "feedbacks": [...]
}
```

### PATCH /feedback/{feedback_id}/resolve

Đánh dấu feedback đã được xử lý.

## 💻 Frontend Usage

### Cách Sử Dụng

1. Sau khi nhận câu trả lời từ AI, rating panel sẽ hiển thị
2. Click nút **"Báo lỗi / Góp ý"**
3. Modal feedback sẽ hiển thị với:
   - Preview câu hỏi và câu trả lời
   - Dropdown chọn loại feedback
   - Textarea để nhập chi tiết
4. Click **"Gửi Phản Hồi"** để submit

### Code Example

```javascript
// Gửi feedback
fetch('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        question: "Câu hỏi",
        answer: "Câu trả lời",
        feedback_type: "wrong",
        message: "Chi tiết"
    })
});
```

## 🗄️ Database Setup

### SQLite (Development)

Database tự động tạo file `feedback.db` trong thư mục backend.

### PostgreSQL (Production - Render)

1. Tạo PostgreSQL database trên Render
2. Set environment variable:
   ```
   DATABASE_URL=postgresql://user:password@host:port/dbname
   ```
3. Database sẽ tự động tạo tables khi app start

### Manual Setup

```python
from database import init_db
init_db()
```

## 📊 Xem Feedback

### Qua API

```bash
# Lấy tất cả feedback chưa xử lý
curl https://your-api.com/feedback?resolved=false

# Lấy 10 feedback đầu tiên
curl https://your-api.com/feedback?skip=0&limit=10
```

### Qua Database

```sql
-- Xem tất cả feedback
SELECT * FROM feedback ORDER BY created_at DESC;

-- Xem feedback chưa xử lý
SELECT * FROM feedback WHERE is_resolved = FALSE;

-- Thống kê theo loại
SELECT feedback_type, COUNT(*) as count 
FROM feedback 
GROUP BY feedback_type;
```

## 🔐 Security Notes

- **IP Address**: Được lưu tự động (có thể ẩn nếu cần)
- **User Agent**: Được lưu để debug
- **Authentication**: Endpoint GET/PATCH nên có authentication (chưa implement)
- **Rate Limiting**: Nên thêm rate limiting để tránh spam

## 🚀 Future Improvements

1. **Email Notifications**: Gửi email khi có feedback mới
2. **Admin Dashboard**: UI để xem và quản lý feedback
3. **Analytics**: Thống kê feedback theo thời gian
4. **Auto-resolution**: Tự động đánh dấu resolved sau khi xử lý
5. **Feedback Categories**: Thêm categories chi tiết hơn

## 📝 Notes

- Feedback được lưu vĩnh viễn trong database
- Có thể export feedback để phân tích
- Nên backup database thường xuyên

