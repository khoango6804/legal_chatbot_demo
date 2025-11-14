#!/usr/bin/env python3
"""
Script để chạy cả backend và frontend local development
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def run_backend():
    """Chạy backend server"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("🚀 Starting Backend Server...")
    print("📍 Backend will run at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    print("-" * 50)
    
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Backend server stopped")

def run_frontend():
    """Chạy frontend server"""
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    print("🌐 Starting Frontend Server...")
    print("📍 Frontend will run at: http://localhost:8080")
    print("-" * 50)
    
    try:
        # Try Python 3
        subprocess.run([sys.executable, "-m", "http.server", "8080"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Frontend server stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run local development servers")
    parser.add_argument("--backend", action="store_true", help="Run only backend")
    parser.add_argument("--frontend", action="store_true", help="Run only frontend")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    
    args = parser.parse_args()
    
    if args.backend:
        run_backend()
    elif args.frontend:
        run_frontend()
    else:
        print("=" * 50)
        print("🤖 AI Legal Assistant - Local Development")
        print("=" * 50)
        print("\nChọn option:")
        print("1. Chạy Backend (http://localhost:8000)")
        print("2. Chạy Frontend (http://localhost:8080)")
        print("3. Chạy cả hai (cần 2 terminal)")
        print("\nHoặc dùng:")
        print("  python run_local.py --backend   # Chỉ backend")
        print("  python run_local.py --frontend  # Chỉ frontend")
        print("\n💡 Tip: Chạy backend và frontend ở 2 terminal riêng!")

