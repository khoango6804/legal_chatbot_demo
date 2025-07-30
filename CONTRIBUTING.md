# 🤝 Hướng dẫn đóng góp

Cảm ơn bạn quan tâm đến việc đóng góp cho dự án AI Legal Assistant! 

## 📋 Cách đóng góp

### 1. Báo cáo lỗi (Bug Reports)

Nếu bạn tìm thấy lỗi, vui lòng:

1. Kiểm tra xem lỗi đã được báo cáo chưa trong [Issues](../../issues)
2. Tạo issue mới với:
   - Mô tả chi tiết về lỗi
   - Các bước để tái tạo lỗi
   - Thông tin hệ thống (OS, Python version, GPU)
   - Log lỗi (nếu có)

### 2. Đề xuất tính năng (Feature Requests)

Nếu bạn có ý tưởng về tính năng mới:

1. Kiểm tra xem tính năng đã được đề xuất chưa
2. Tạo issue với label "enhancement"
3. Mô tả chi tiết tính năng và lý do cần thiết

### 3. Đóng góp code

#### Chuẩn bị môi trường

1. Fork repository
2. Clone về máy local:
   ```bash
   git clone https://github.com/your-username/inference_simpleQA_dsp391m.git
   cd inference_simpleQA_dsp391m
   ```

3. Tạo virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # hoặc
   venv\Scripts\activate     # Windows
   ```

4. Cài đặt dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Quy trình phát triển

1. Tạo branch mới:
   ```bash
   git checkout -b feature/your-feature-name
   # hoặc
   git checkout -b fix/your-bug-fix
   ```

2. Thực hiện thay đổi và test:
   ```bash
   python app.py
   # Test ứng dụng tại http://127.0.0.1:8000
   ```

3. Commit changes:
   ```bash
   git add .
   git commit -m "Add: mô tả ngắn gọn về thay đổi"
   ```

4. Push lên repository:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Tạo Pull Request

#### Quy tắc commit message

Sử dụng format:
```
Type: mô tả ngắn gọn

- Add: thêm tính năng mới
- Fix: sửa lỗi
- Update: cập nhật tính năng
- Remove: xóa tính năng
- Refactor: tái cấu trúc code
- Docs: cập nhật tài liệu
```

## 🧪 Testing

### Test cơ bản

1. Test model loading:
   ```bash
   python test_model.py
   ```

2. Test API:
   ```bash
   python -c "import requests; response = requests.post('http://127.0.0.1:8000/chat', json={'question': 'test', 'chat_history': []}); print(response.status_code)"
   ```

3. Test frontend:
   - Mở http://127.0.0.1:8000
   - Gửi câu hỏi test
   - Kiểm tra response

### Test GPU (nếu có)

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

## 📝 Code Style

### Python
- Tuân thủ PEP 8
- Sử dụng type hints
- Viết docstring cho functions
- Độ dài dòng tối đa 88 ký tự

### JavaScript
- Sử dụng ES6+
- Tuân thủ ESLint rules
- Comment cho logic phức tạp

### CSS
- Sử dụng CSS variables
- Responsive design
- Mobile-first approach

## 🔍 Review Process

1. **Code Review**: Tất cả PR sẽ được review
2. **Testing**: Code phải pass tất cả tests
3. **Documentation**: Cập nhật README nếu cần
4. **Performance**: Kiểm tra hiệu suất

## 🏷️ Labels

- `bug`: Lỗi cần sửa
- `enhancement`: Tính năng mới
- `documentation`: Cập nhật tài liệu
- `good first issue`: Phù hợp cho người mới
- `help wanted`: Cần hỗ trợ
- `priority: high`: Ưu tiên cao
- `priority: low`: Ưu tiên thấp

## 📞 Liên hệ

- **Email**: [your.email@example.com]
- **GitHub Issues**: [Issues](../../issues)
- **Discussions**: [Discussions](../../discussions)

## 🙏 Cảm ơn

Cảm ơn bạn đã đóng góp cho dự án! Mọi đóng góp, dù nhỏ hay lớn, đều rất có giá trị.

---

⭐ Nếu hướng dẫn này hữu ích, hãy cho một star! 