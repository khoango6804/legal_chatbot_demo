#!/usr/bin/env python3
"""
Script để upload model lên Hugging Face Hub
"""

from huggingface_hub import HfApi, login
import os
import sys
from pathlib import Path

def upload_model():
    """Upload model lên Hugging Face Hub"""
    
    # Repository name - THAY BẰNG USERNAME VÀ REPO CỦA BẠN
    repo_id = input("Nhập Hugging Face repository (ví dụ: username/qwen3-0.6B-trafficlaws): ").strip()
    
    if not repo_id:
        print("Repository name không được để trống!")
        return
    
    # Đường dẫn đến model folder
    model_path = Path("./qwen3-0.6B-instruct-trafficlaws/model")
    
    if not model_path.exists():
        print(f"Không tìm thấy model tại: {model_path}")
        print("   Đảm bảo model files đã có trong thư mục này.")
        return
    
    # Kiểm tra files cần thiết
    required_files = ["config.json", "tokenizer.json"]
    missing_files = []
    for file in required_files:
        if not (model_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"Thiếu các files: {', '.join(missing_files)}")
        return
    
    # Check if logged in
    try:
        api = HfApi()
        # Test if logged in by getting user info
        user = api.whoami()
        print(f"Đã login với tài khoản: {user.get('name', 'Unknown')}")
    except Exception as e:
        print("Chưa login vào Hugging Face!")
        print("   Chạy lệnh: huggingface-cli login")
        print("   Hoặc: python -c 'from huggingface_hub import login; login()'")
        return
    
    # Confirm upload
    print(f"\nSẵn sàng upload model:")
    print(f"   Repository: {repo_id}")
    print(f"   Source: {model_path}")
    print(f"\nLưu ý: Nếu repository chưa tồn tại, sẽ được tạo tự động.")
    
    confirm = input("\nTiếp tục? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Đã hủy upload.")
        return
    
    try:
        print(f"\nĐang upload model lên {repo_id}...")
        print("   (Quá trình này có thể mất vài phút tùy vào kích thước model)")
        
        # Upload folder
        api.upload_folder(
            folder_path=str(model_path),
            repo_id=repo_id,
            repo_type="model",
            ignore_patterns=["*.git*", "*.DS_Store", "__pycache__", "*.pyc"]
        )
        
        print(f"\nUpload thành công!")
        print(f"   Model available at: https://huggingface.co/{repo_id}")
        print(f"\nBước tiếp theo:")
        print(f"   1. Set environment variable: MODEL_HF_REPO={repo_id}")
        print(f"   2. Deploy và model sẽ tự động download")
        
    except Exception as e:
        print(f"\nLỗi khi upload: {e}")
        print("\nTips:")
        print("   - Đảm bảo đã login: huggingface-cli login")
        print("   - Kiểm tra repository name đúng format: username/repo-name")
        print("   - Kiểm tra kết nối internet")
        return

if __name__ == "__main__":
    print("=" * 60)
    print("Upload Model Lên Hugging Face Hub")
    print("=" * 60)
    print("\nYêu cầu:")
    print("   1. Tài khoản Hugging Face: https://huggingface.co/join")
    print("   2. Đã login: huggingface-cli login")
    print("   3. Model files đã sẵn sàng trong qwen3-0.6B-instruct-trafficlaws/model/")
    print()
    
    # Check if huggingface_hub is installed
    try:
        import huggingface_hub
    except ImportError:
        print("Chưa cài huggingface-hub!")
        print("   Chạy: pip install huggingface-hub")
        sys.exit(1)
    
    upload_model()

