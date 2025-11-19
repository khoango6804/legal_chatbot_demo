#!/usr/bin/env python3
"""Script để test model loading"""
import os
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Set environment variables
os.environ["MODEL_HF_REPO"] = "sigmaloop/qwen3-0.6B-instruct-trafficlaws"
os.environ["MODEL_HF_SUBFOLDER"] = "model"
os.environ["HF_TOKEN"] = "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"

print("=" * 60)
print("Testing Model Loading")
print("=" * 60)
print()

# Test 1: Check Hugging Face connection
print("[1/5] Testing Hugging Face connection...")
try:
    from huggingface_hub import login as hf_login
    try:
        hf_login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)
        print("[OK] Hugging Face authentication: OK")
    except Exception as e:
        print(f"[ERROR] Hugging Face authentication failed: {e}")
        sys.exit(1)
except ImportError:
    print("[ERROR] huggingface_hub not installed")
    sys.exit(1)

# Test 2: Check if repo exists and is accessible
print("\n[2/5] Checking model repository...")
try:
    from huggingface_hub import HfApi
    api = HfApi(token=os.environ["HF_TOKEN"])
    repo_id = os.environ["MODEL_HF_REPO"]
    subfolder = os.environ.get("MODEL_HF_SUBFOLDER", None)
    
    try:
        repo_info = api.repo_info(repo_id=repo_id, repo_type="model")
        print(f"[OK] Repository exists: {repo_id}")
        print(f"   Private: {repo_info.private}")
        
        if subfolder:
            # Check if subfolder exists
            files = api.list_repo_files(repo_id=repo_id, repo_type="model")
            subfolder_files = [f for f in files if f.startswith(f"{subfolder}/")]
            if subfolder_files:
                print(f"[OK] Subfolder '{subfolder}' exists with {len(subfolder_files)} files")
            else:
                print(f"[WARNING] Subfolder '{subfolder}' not found or empty")
        else:
            print("[OK] No subfolder specified")
    except Exception as e:
        print(f"[ERROR] Cannot access repository: {e}")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error checking repository: {e}")
    sys.exit(1)

# Test 3: Try to load config
print("\n[3/5] Testing config loading...")
try:
    from transformers import AutoConfig
    
    model_path = os.environ['MODEL_HF_REPO']
    subfolder = os.environ.get('MODEL_HF_SUBFOLDER', None)
    
    config_kwargs = {
        "token": os.environ["HF_TOKEN"],
        "trust_remote_code": True
    }
    if subfolder:
        config_kwargs["subfolder"] = subfolder
    
    config = AutoConfig.from_pretrained(model_path, **config_kwargs)
    print(f"[OK] Config loaded successfully")
    print(f"   Model type: {config.model_type}")
    print(f"   Architectures: {config.architectures}")
except Exception as e:
    print(f"[ERROR] Config loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Try to load tokenizer
print("\n[4/5] Testing tokenizer loading...")
try:
    from transformers import AutoTokenizer
    
    model_path = os.environ['MODEL_HF_REPO']
    subfolder = os.environ.get('MODEL_HF_SUBFOLDER', None)
    
    tokenizer_kwargs = {
        "token": os.environ["HF_TOKEN"],
        "trust_remote_code": True,
        "model_max_length": 2048
    }
    if subfolder:
        tokenizer_kwargs["subfolder"] = subfolder
    
    tokenizer = AutoTokenizer.from_pretrained(model_path, **tokenizer_kwargs)
    print(f"[OK] Tokenizer loaded successfully")
    print(f"   Vocab size: {len(tokenizer)}")
except Exception as e:
    print(f"[ERROR] Tokenizer loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Try to load model (just start, don't wait for full load)
print("\n[5/5] Testing model loading (this may take a while)...")
print("   Starting model load...")
try:
    import torch
    from transformers import AutoModelForCausalLM
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   Device: {device}")
    
    model_path = os.environ['MODEL_HF_REPO']
    subfolder = os.environ.get('MODEL_HF_SUBFOLDER', None)
    
    print(f"   Loading from: {model_path}" + (f" (subfolder: {subfolder})" if subfolder else ""))
    print("   This may take 2-5 minutes on first run...")
    
    # Try loading with low_cpu_mem_usage
    model_kwargs = {
        "token": os.environ["HF_TOKEN"],
        "trust_remote_code": True,
        "torch_dtype": torch.float32 if device == "cpu" else torch.float16,
        "low_cpu_mem_usage": True
    }
    if subfolder:
        model_kwargs["subfolder"] = subfolder
    
    model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)
    
    if device != "cuda":
        model = model.to(device)
    
    model.eval()
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[OK] Model loaded successfully!")
    print(f"   Total parameters: {total_params:,}")
    
except Exception as e:
    print(f"[ERROR] Model loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("[OK] All tests passed! Model can be loaded successfully.")
print("=" * 60)

