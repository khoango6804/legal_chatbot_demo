# 🚀 Hướng Dẫn Tối Ưu Hóa Cho Server CPU

## 📊 Đánh Giá Hiệu Suất

Model **Qwen3 0.6B** (28 layers, 1024 hidden size) có thể chạy trên CPU server, nhưng cần tối ưu hóa để đạt hiệu suất tốt.

### Hiệu Suất Dự Kiến:
- **CPU (không tối ưu)**: ~5-10 giây/câu trả lời
- **CPU (đã tối ưu)**: ~2-5 giây/câu trả lời
- **GPU**: ~1-2 giây/câu trả lời

## ✅ Các Tối Ưu Đã Áp Dụng

### 1. **Quantization (8-bit)**
- Giảm memory usage xuống ~50%
- Tăng tốc độ inference ~30-40%
- Cài đặt: `pip install bitsandbytes`

### 2. **CPU Threading Optimization**
- Tự động detect số CPU cores
- Sử dụng tối đa 8 threads
- Tối ưu inter-op và intra-op threads

### 3. **Model Compilation (torch.compile)**
- Compile model với PyTorch 2.0+
- Tăng tốc độ ~20-30%
- Chỉ áp dụng cho CPU mode

### 4. **Response Caching**
- Cache 100 câu trả lời gần nhất
- Tránh tính toán lại cho câu hỏi giống nhau
- Tăng tốc độ phản hồi lên ~100x cho câu hỏi đã cache

### 5. **Generation Parameters Optimization**
- **CPU**: Greedy decoding (nhanh hơn sampling)
- **CPU**: Giảm max_new_tokens từ 512 → 256
- **GPU**: Giữ nguyên settings tối ưu

### 6. **Memory Optimization**
- `low_cpu_mem_usage=True`
- Sử dụng float32 cho CPU (tốt hơn float16)
- Efficient memory management

## 🔧 Cài Đặt Tối Ưu

### Bước 1: Cài đặt dependencies cơ bản
```bash
pip install -r requirements.txt
```

### Bước 2: Cài đặt quantization (Tùy chọn - Khuyến nghị)
```bash
# Windows (cần Visual Studio Build Tools)
pip install bitsandbytes

# Linux/Mac
pip install bitsandbytes
```

### Bước 3: Kiểm tra PyTorch version
```bash
python -c "import torch; print(torch.__version__)"
# Cần PyTorch 2.0+ để sử dụng torch.compile
```

## 📈 Benchmarking

### Test hiệu suất:
```bash
python speed_test.py
```

### So sánh trước/sau tối ưu:
```bash
python compare_speed.py
```

## 🎯 Khuyến Nghị Cho Production

### Server Requirements:
- **CPU**: 4+ cores (khuyến nghị 8+ cores)
- **RAM**: 8GB+ (khuyến nghị 16GB+)
- **OS**: Linux (tốt hơn Windows cho CPU inference)

### Tối Ưu Thêm:

1. **Sử dụng ONNX Runtime** (Tùy chọn - nâng cao):
   ```bash
   pip install onnxruntime
   ```
   - Chuyển đổi model sang ONNX format
   - Tăng tốc độ thêm ~20-30%

2. **Sử dụng GGML/llama.cpp** (Tùy chọn - nâng cao):
   - Chuyển đổi model sang GGML format
   - Tối ưu cực kỳ cho CPU
   - Cần compile từ source

3. **Load Balancing**:
   - Sử dụng multiple workers với uvicorn
   ```bash
   uvicorn app:app --workers 2 --host 0.0.0.0 --port 8000
   ```

4. **Caching Layer**:
   - Sử dụng Redis cho distributed caching
   - Tăng khả năng scale

5. **CDN/Reverse Proxy**:
   - Sử dụng Nginx để cache static files
   - Giảm tải cho application server

## ⚙️ Cấu Hình Nâng Cao

### Environment Variables:
```bash
# Số threads cho CPU
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

# Tối ưu memory
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Uvicorn Configuration:
```python
# app.py
if __name__ == "__main__":
    import multiprocessing
    workers = min(multiprocessing.cpu_count(), 4)
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        workers=workers,  # Multiple workers
        log_level="info"
    )
```

## 📊 Monitoring

### Theo dõi hiệu suất:
- Tốc độ token/s được hiển thị trong response
- Log CPU usage và memory
- Monitor response time

### Tools:
- `htop` hoặc `top` để monitor CPU/RAM
- `nvidia-smi` nếu có GPU
- Application logs

## 🐛 Troubleshooting

### Lỗi: "bitsandbytes not available"
- **Giải pháp**: Cài đặt `bitsandbytes` hoặc bỏ qua (code sẽ tự động fallback)

### Lỗi: "torch.compile not available"
- **Giải pháp**: Nâng cấp PyTorch lên 2.0+ hoặc bỏ qua (code sẽ tự động fallback)

### Chậm trên CPU:
1. Kiểm tra số CPU cores: `python -c "import multiprocessing; print(multiprocessing.cpu_count())"`
2. Tăng số threads trong code nếu cần
3. Sử dụng quantization
4. Giảm `max_new_tokens` xuống 128-192

### Memory issues:
1. Giảm `MAX_CACHE_SIZE` trong `inference.py`
2. Sử dụng quantization
3. Tăng swap memory
4. Giảm số workers

## 📝 Notes

- Model 0.6B khá nhỏ, phù hợp cho CPU inference
- Với model lớn hơn (>1B), nên cân nhắc GPU hoặc quantization mạnh hơn
- Response caching rất hiệu quả cho production (nhiều user hỏi câu tương tự)

## 🎉 Kết Luận

Với các tối ưu đã áp dụng, model Qwen3 0.6B có thể chạy tốt trên server CPU với:
- ✅ Tốc độ: 2-5 giây/câu trả lời
- ✅ Memory: ~2-4GB RAM
- ✅ Có thể handle nhiều requests đồng thời
- ✅ Response caching giúp tăng tốc độ đáng kể

**Khuyến nghị**: Sử dụng quantization và response caching cho production!

