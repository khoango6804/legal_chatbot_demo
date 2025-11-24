# Legal Chatbot Demo

This project wires a retrieval-augmented (RAG) pipeline with a local large language model to answer Vietnamese traffic-law questions. The FastAPI backend serves both the API and the single-page frontend so the entire experience can run on a single Windows machine.

## Prerequisites
- Windows 10/11 x64 (tested with PowerShell 5)
- [Anaconda](https://www.anaconda.com/download) or Miniconda
- Python 3.10 (the `llama_env` conda environment uses this)
- NVIDIA GPU drivers (optional but recommended). Install CUDA-capable PyTorch as shown below.

## 1. Create the Python environment
```powershell
conda create -n llama_env python=3.10 -y
conda activate llama_env
pip install --upgrade pip
pip install -r requirements.txt
```

If you want GPU acceleration, install the CUDA build of PyTorch that matches your driver. Example (CUDA 12.1):
```powershell
pip install --upgrade --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 2. Prepare the local model
Download the model into `models/qwen3-0.6B-instruct-trafficlaws/model`. You can use the Hugging Face CLI:
```powershell
huggingface-cli login          # paste your HF token
huggingface-cli download sigmaloop/qwen3-0.6B-instruct-trafficlaws `
  --local-dir models/qwen3-0.6B-instruct-trafficlaws/model `
  --local-dir-use-symlinks False
```

> The backend now defaults to this local path. If the folder is missing, it will fall back to Hugging Face Hub (requires `MODEL_HF_REPO`, `MODEL_HF_SUBFOLDER`, `HF_TOKEN`).

## 3. Run the backend
Use the helper script:
```powershell
cd K:\wwebdemodoan\legal_chatbot_demo
conda activate llama_env
.\restart_backend.ps1
```

The script:
- Kills any previous backend listening on port 8100.
- Points `MODEL_PATH` to `models/qwen3-0.6B-instruct-trafficlaws/model`.
- Starts `uvicorn backend.app:app --host 0.0.0.0 --port 8000`.

If you prefer manual control:
```powershell
conda activate llama_env
cd K:\wwebdemodoan\legal_chatbot_demo
Set-Item Env:MODEL_PATH "K:\wwebdemodoan\legal_chatbot_demo\models\qwen3-0.6B-instruct-trafficlaws\model"
uvicorn backend.app:app --host 0.0.0.0 --port 8100
```

The API will be available at `http://localhost:8100/chat` and the frontend at `http://localhost:8100/`.

## 4. Optional: expose publicly with ngrok
```powershell
ngrok http 8100
```
Keep both the backend and ngrok terminals running. Share the HTTPS URL that ngrok prints.

## Useful commands
- Health check: `curl http://localhost:8100/health`
- Verify GPU usage: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`
- View logs: check the backend terminal where `uvicorn` runs.

## Project layout
- `backend/` – FastAPI app, RAG pipeline, database models.
- `frontend/` – SPA assets served by FastAPI (`/static`).
- `models/` – local Hugging Face model files.
- `restart_backend.ps1` – helper script to restart the backend with correct environment variables.
- `nd168_metadata_clean.json` – processed legal corpus for RAG.

Enjoy testing and feel free to adapt the instructions for your own deployment scripts.***

