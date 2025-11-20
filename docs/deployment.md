# Server Deployment Guide

This project ships with both a FastAPI backend (`backend/`) and a static frontend (`frontend/`). The following steps describe how to deploy everything on a single Linux server (Ubuntu/Debian family). They assume you have root or sudo access.

> **Tip:** A ready-to-use `render.yaml` is included if you prefer to deploy on Render. Likewise, you can adapt the existing `docker-compose.yml` when containerising the stack.

## 0. Quick Automation (Recommended)

Most steps below can be automated using the helper script:

```bash
sudo /root/legal_chatbot_demo/deploy/scripts/setup_server.sh \
  --domain your-domain.com \
  --app-root /root/legal_chatbot_demo \
  --static-root /var/www/legal_chatbot/frontend \
  --certbot \
  --certbot-email you@example.com
```

Export environment variables (`APP_ROOT`, `DOMAIN`, etc.) hoặc dùng tham số dòng lệnh để tùy biến. Script sẽ cài gói hệ thống, tạo user dịch vụ, thiết lập virtualenv, đồng bộ frontend sang `--static-root`, cài systemd unit, cấu hình Nginx và (tuỳ chọn) xin chứng chỉ TLS.

## 1. Prepare the Server

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-pip nginx git
```

Clone (or update) the repository under `/root/legal_chatbot_demo` or another directory of your choice:

```bash
git clone https://<your repo url> /root/legal_chatbot_demo
cd /root/legal_chatbot_demo
```

## 2. Configure Environment Variables

Create `/root/legal_chatbot_demo/.env` with the values needed by the backend:

```
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=<huggingface token>
DATABASE_URL=sqlite:///./feedback.db
CORS_ORIGINS=https://your-frontend-domain
HEALTH_RELOAD_INFERENCE=0
USE_GENERATIVE_MODEL=true
# Only set REMOTE_GENERATOR_URL if you want to offload the heavy model elsewhere
REMOTE_GENERATOR_URL=http://<remote-machine>:9000/generate
REMOTE_GENERATOR_TIMEOUT=45
# Matches REMOTE_GENERATOR_TOKEN on the remote machine (optional but recommended)
REMOTE_GENERATOR_TOKEN=<shared-secret>
```

- Set `HEALTH_RELOAD_INFERENCE=0` to skip the expensive Torch reload the health check attempted in development.
- Update `CORS_ORIGINS` to match your deployed frontend or keep `*` for testing only.
- Switch `DATABASE_URL` to PostgreSQL or another RDBMS when required.
- `USE_GENERATIVE_MODEL=true` keeps the previous behaviour (model-generated answers). Set to `false` if you only want deterministic RAG responses.
- When `REMOTE_GENERATOR_URL` is present the backend will *not* load a local LLM. Instead it sends prompts to the specified endpoint, which lets you keep the heavy model on a laptop or workstation with more CPU/GPU resources.

### 2.1 Offload the Generative Model to Another Machine

1. **Prepare the remote/laptop host**
   - Install system packages: `sudo apt-get update && sudo apt-get install -y python3.12-venv python3-pip git`
   - Clone the repo (or copy only `backend/` + `nd168_metadata_clean.json` if you prefer a lighter footprint).
   - Create a virtualenv and install dependencies:
     ```
     python3 -m venv /opt/legalbot/.venv
     source /opt/legalbot/.venv/bin/activate
     pip install --upgrade pip
     pip install -r backend/requirements.txt
     ```
   - Export or place in `.env` (same directory) the following variables:
     ```
     HF_TOKEN=<huggingface token>          # needed to download model weights
     USE_GENERATIVE_MODEL=true             # ensure model actually loads
     REMOTE_GENERATOR_TOKEN=<shared-secret>
     MODEL_PATH=/data/models/qwen          # optional, if you already cached the model
     ```
   - Start the microservice that hosts the model:
     ```
     uvicorn backend.remote_generator_server:app \
       --host 0.0.0.0 --port 9000
     ```
     The first start downloads + loads the model. Subsequent runs reuse the cache in `~/.cache/huggingface` or `MODEL_PATH`.
2. **Connect the remote machine to your server**
   - Recommended options:
     - VPN mesh (Tailscale / ZeroTier): both machines join the same private network; use the VPN IP in `REMOTE_GENERATOR_URL`.
     - SSH reverse tunnel from the remote/laptop to the server: `ssh -N -R 9000:localhost:9000 user@server-ip`. Then point `REMOTE_GENERATOR_URL` to `http://127.0.0.1:9000/generate`.
     - Port-forwarding / reverse proxy with HTTPS if exposing over the internet (pair it with the bearer token for security).
3. **Update the server `.env`**
   - Set `REMOTE_GENERATOR_URL` to the reachable address (VPN IP, tunnel endpoint, etc.).
   - Ensure `REMOTE_GENERATOR_TOKEN` matches the remote machine.
   - Restart the backend (`systemctl restart legal-backend`).
4. **Smoke test**
   - From the server: `curl -H "Authorization: Bearer <secret>" http://<remote>:9000/health`
   - From the server: `curl -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{"question":"...", "chat_history":[]}'`
   - Check the remote `uvicorn` logs to confirm requests are flowing.

## 3. Create a Virtual Environment

```bash
python3 -m venv /root/legal_chatbot_demo/.venv
source /root/legal_chatbot_demo/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate
```

## 4. Install the systemd Unit

A template unit file is provided at `deploy/systemd/legal-backend.service` (placeholders wrapped in `__LIKE_THIS__`). Copy it to `/etc/systemd/system/` and replace them or render via `envsubst`:

```bash
sudo adduser --system --group --no-create-home legalbot   # optional but recommended
sudo chown -R legalbot:legalbot /root/legal_chatbot_demo  # match the user set in the unit file
```

```bash
APP_ROOT=/root/legal_chatbot_demo
APP_USER=legalbot
APP_GROUP=legalbot
ENV_FILE=/root/legal_chatbot_demo/.env
sudo sed \
  -e "s|__APP_ROOT__|${APP_ROOT}|g" \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__ENV_FILE__|${ENV_FILE}|g" \
  deploy/systemd/legal-backend.service | sudo tee /etc/systemd/system/legal-backend.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now legal-backend
```

Check the logs:

```bash
sudo journalctl -u legal-backend -f
```

## 5. Configure Nginx

1. (Optional) Edit `frontend/index.html` and set the API base URL:

   ```html
   <script>
     window.API_BASE_URL = 'https://your-domain.com/api';
   </script>
   ```

2. Nếu `STATIC_ROOT` khác với thư mục frontend gốc, đồng bộ nội dung (script `setup_server.sh` đã thực hiện bước này khi chạy):

   ```bash
   sudo rsync -a --delete /root/legal_chatbot_demo/frontend/ /var/www/legal_chatbot/frontend/
   ```

3. Copy the provided Nginx example (`deploy/nginx/legal-chatbot.conf`) into `/etc/nginx/sites-available/`, replacing placeholders as you go:

```bash
APP_ROOT=/root/legal_chatbot_demo
STATIC_ROOT=/var/www/legal_chatbot/frontend
DOMAIN=your-domain.com
WWW_DOMAIN=www.your-domain.com
API_PREFIX=/api/
sudo sed \
  -e "s|__STATIC_ROOT__|${STATIC_ROOT:-${APP_ROOT}/frontend}|g" \
  -e "s|__SERVER_NAME__|${DOMAIN}|g" \
  -e "s|__SERVER_NAME_WWW__|${WWW_DOMAIN}|g" \
  -e "s|__API_PREFIX__|${API_PREFIX}|g" \
  deploy/nginx/legal-chatbot.conf | sudo tee /etc/nginx/sites-available/legal-chatbot.conf > /dev/null
sudo ln -sf /etc/nginx/sites-available/legal-chatbot.conf /etc/nginx/sites-enabled/legal-chatbot.conf
sudo nginx -t
sudo systemctl reload nginx
```

4. Issue HTTPS certificates with Let’s Encrypt (Certbot):

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 6. Updating the Deployment

```bash
cd /root/legal_chatbot_demo
sudo systemctl stop legal-backend
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
deactivate
sudo systemctl start legal-backend
sudo systemctl reload nginx
```

## 7. Optional: Docker/Render

- **Render**: The `render.yaml` in the repository defines both a backend web service (Python environment) and a static frontend. Update secrets (`HF_TOKEN`, etc.) through the Render dashboard.
- **Docker Compose**: Adapt `docker-compose.yml` to mount your model checkpoints and serve the frontend either from the container or via a dedicated static host.

## 8. Health Check Endpoint

The `/health` endpoint returns `{"status": "healthy", "model_loaded": <bool>}`. When `HEALTH_RELOAD_INFERENCE=0`, it skips reloading the inference module to avoid Torch thread configuration errors. This makes the endpoint safe for load balancer probes.

---

You should now have the backend running as a service behind Nginx with the static frontend served from the same server. Let me know if you need deployment automation (Ansible, GitHub Actions, etc.) or containerisation help.


