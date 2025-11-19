#!/usr/bin/env python3
"""Script để force load model với environment variables đúng"""
import os
import sys

# Set environment variables TRƯỚC KHI import inference
os.environ["MODEL_HF_REPO"] = "sigmaloop/qwen3-0.6B-instruct-trafficlaws"
os.environ["MODEL_HF_SUBFOLDER"] = "model"
os.environ["HF_TOKEN"] = "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"

print("Environment variables set:")
print(f"  MODEL_HF_REPO: {os.environ.get('MODEL_HF_REPO')}")
print(f"  MODEL_HF_SUBFOLDER: {os.environ.get('MODEL_HF_SUBFOLDER')}")
print(f"  HF_TOKEN: {'***' if os.environ.get('HF_TOKEN') else 'NOT SET'}")
print()

# Import sau khi set env vars
from inference import load_model, model_loaded

print("=" * 60)
print("Force loading model...")
print("=" * 60)
print()

result = load_model()

print()
print("=" * 60)
if result:
    print("[OK] Model loaded successfully!")
    print(f"model_loaded flag: {model_loaded}")
else:
    print("[ERROR] Model loading failed!")
    print(f"model_loaded flag: {model_loaded}")
print("=" * 60)

