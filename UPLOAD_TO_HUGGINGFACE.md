# 📤 Hướng Dẫn Upload Model Lên Hugging Face Hub

## 🎯 Tại Sao Nên Dùng Hugging Face Hub?

✅ **Lợi ích:**
- Không cần Git LFS
- Không cần external storage
- Tự động cache trên server
- Dễ dàng version control
- Miễn phí cho public repos
- Tự động download khi cần

## 📋 Yêu Cầu

1. Tài khoản Hugging Face: https://huggingface.co/join
2. Cài đặt `huggingface-hub`:
   ```bash
   pip install huggingface-hub
   ```
3. Login vào Hugging Face:
   ```bash
   huggingface-cli login
   ```

## 🚀 Các Bước Upload

### Bước 1: Chuẩn Bị Model

Đảm bảo model checkpoint đã có đầy đủ files:
```
qwen3-0.6B-instruct-trafficlaws/
└── model/
    ├── config.json
    ├── tokenizer.json
    ├── tokenizer_config.json
    ├── vocab.json
    ├── merges.txt
    ├── special_tokens_map.json
    ├── added_tokens.json
    ├── chat_template.jinja
    └── model.safetensors (hoặc model.bin, model-*.safetensors)
```

### Bước 2: Tạo Repository Trên Hugging Face

1. Vào https://huggingface.co/new
2. Chọn **Model**
3. Đặt tên: `qwen3-0.6B-instruct-trafficlaws` (hoặc tên bạn muốn)
4. Chọn **Public** hoặc **Private**
5. Click **Create repository**

### Bước 3: Upload Model

**Cách 1: Dùng Python Script**

Tạo file `upload_model.py`:

```python
from huggingface_hub import HfApi, login
import os

# Login (hoặc dùng token)
# login(token="your_token_here")
# Hoặc đã login qua CLI: huggingface-cli login

api = HfApi()

# Repository name (thay bằng username/repo của bạn)
repo_id = "your-username/qwen3-0.6B-instruct-trafficlaws"

# Đường dẫn đến model folder
model_path = "./qwen3-0.6B-instruct-trafficlaws/model"

print(f"Uploading model to {repo_id}...")
print(f"From: {model_path}")

# Upload toàn bộ folder
api.upload_folder(
    folder_path=model_path,
    repo_id=repo_id,
    repo_type="model",
    ignore_patterns=["*.git*", "*.DS_Store"]
)

print(f"✅ Upload completed! Model available at: https://huggingface.co/{repo_id}")
```

Chạy script:
```bash
python upload_model.py
```

**Cách 2: Dùng Hugging Face CLI**

```bash
# Install CLI
pip install huggingface-hub[cli]

# Login
huggingface-cli login

# Upload
huggingface-cli upload your-username/qwen3-0.6B-instruct-trafficlaws \
    ./qwen3-0.6B-instruct-trafficlaws/model \
    --repo-type model
```

**Cách 3: Dùng Git (Khuyến nghị cho files lớn)**

```bash
# Clone empty repo
git clone https://huggingface.co/your-username/qwen3-0.6B-instruct-trafficlaws
cd qwen3-0.6B-instruct-trafficlaws

# Copy model files
cp -r ../qwen3-0.6B-instruct-trafficlaws/model/* .

# Commit và push
git add .
git commit -m "Upload model"
git push
```

### Bước 4: Kiểm Tra

Vào https://huggingface.co/your-username/qwen3-0.6B-instruct-trafficlaws

Đảm bảo tất cả files đã được upload:
- ✅ config.json
- ✅ tokenizer files
- ✅ model weights (.safetensors hoặc .bin)

## 🔧 Cấu Hình Code

### Environment Variable

Set trong Render hoặc local:

```env
MODEL_HF_REPO=your-username/qwen3-0.6B-instruct-trafficlaws
```

**Lưu ý:** Nếu set `MODEL_HF_REPO`, code sẽ tự động load từ Hugging Face Hub.
Nếu không set, sẽ fallback về `MODEL_PATH` (local path).

### Render Environment Variables

Trong Render Dashboard → Environment:
```
MODEL_HF_REPO=your-username/qwen3-0.6B-instruct-trafficlaws
```

**Không cần** set `MODEL_PATH` nữa nếu dùng Hugging Face Hub.

## 🧪 Test Local

```python
# Test load từ Hugging Face
import os
os.environ["MODEL_HF_REPO"] = "your-username/qwen3-0.6B-instruct-trafficlaws"

from backend.inference import load_model
load_model()
```

## 📝 README Template cho Hugging Face Repo

Tạo file `README.md` trong repo Hugging Face:

```markdown
---
license: mit
tags:
- legal
- vietnamese
- traffic-laws
- qwen3
- fine-tuned
base_model: Qwen/Qwen3-0.6B-Instruct
---

# Qwen3-0.6B-Instruct-TrafficLaws

Model được fine-tune để tư vấn pháp luật giao thông Việt Nam.

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "your-username/qwen3-0.6B-instruct-trafficlaws",
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(
    "your-username/qwen3-0.6B-instruct-trafficlaws",
    trust_remote_code=True
)
```
```

## 🔐 Private Repository

Nếu dùng private repo, cần set token:

```env
HF_TOKEN=your_huggingface_token
```

Code sẽ tự động sử dụng token nếu có.

## ⚡ Lần Đầu Load

- Lần đầu load sẽ download model (có thể mất vài phút)
- Model sẽ được cache trong `~/.cache/huggingface/`
- Các lần sau sẽ load từ cache (nhanh hơn)

## 🎯 So Sánh

| Method | Pros | Cons |
|--------|------|------|
| **Hugging Face Hub** | ✅ Dễ dàng<br>✅ Tự động cache<br>✅ Version control | ⚠️ Lần đầu download chậm |
| **Git LFS** | ✅ Version control | ❌ Cần setup<br>❌ Files lớn |
| **External Storage** | ✅ Không giới hạn | ❌ Cần setup<br>❌ Chi phí |

## ✅ Checklist

- [ ] Tạo tài khoản Hugging Face
- [ ] Login qua CLI: `huggingface-cli login`
- [ ] Tạo repository trên Hugging Face
- [ ] Upload model files
- [ ] Kiểm tra files đã upload đầy đủ
- [ ] Set `MODEL_HF_REPO` environment variable
- [ ] Test load model từ Hugging Face
- [ ] Deploy và test trên production

## 🚀 Sau Khi Upload

1. **Update code**: Code đã được cập nhật để hỗ trợ Hugging Face Hub
2. **Set environment variable**: `MODEL_HF_REPO=your-username/repo-name`
3. **Deploy**: Model sẽ tự động download khi deploy
4. **Done!**: Không cần lo về model files nữa!

---

**Lưu ý:** Model sẽ được download tự động khi app start lần đầu. Đảm bảo server có đủ disk space (~2-4GB).

