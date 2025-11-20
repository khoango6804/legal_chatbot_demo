#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: setup_server.sh [options]

Automates deployment of the Legal Chatbot backend (FastAPI) and static frontend on a Linux server.
Run as root (sudo) from anywhere; by default the script assumes the repository lives at /root/legal_chatbot_demo.

Options:
  -d, --domain DOMAIN          Primary domain for the site (default: example.com)
      --www-domain DOMAIN      www-domain alias (default: www.<DOMAIN>)
  -a, --app-root PATH          Absolute path to repository root (default: autodetected)
  -u, --user USER              System user to run the service (default: legalbot)
  -g, --group GROUP            System group for the service (default: same as user)
  -p, --api-prefix PREFIX      URL prefix that proxies to the API (default: /api/)
      --env-file PATH          Path to .env file (default: <app-root>/.env)
      --systemd-unit NAME      systemd service name (default: legal-backend)
      --nginx-conf NAME        Nginx conf name under sites-available (default: legal-chatbot.conf)
      --skip-packages          Skip apt-get update && apt-get install step
      --certbot                Install certbot and request certificates (requires --certbot-email)
      --certbot-email EMAIL    Email for Let's Encrypt registration
  -h, --help                   Show this help

Environment variables can override the same names (DOMAIN, APP_ROOT, APP_USER, etc.).
EOF
}

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        echo "This script must be run as root (use sudo)." >&2
        exit 1
    fi
}

parse_args() {
    DOMAIN="${DOMAIN:-example.com}"
    WWW_DOMAIN=""
    APP_USER="${APP_USER:-legalbot}"
    APP_GROUP="${APP_GROUP:-}"
    API_PREFIX="${API_PREFIX:-/api/}"
    STATIC_ROOT="${STATIC_ROOT:-}"
    SYSTEMD_UNIT="${SYSTEMD_UNIT:-legal-backend}"
    NGINX_CONF_NAME="${NGINX_CONF_NAME:-legal-chatbot.conf}"
    SKIP_PACKAGES=0
    ENABLE_CERTBOT="${ENABLE_CERTBOT:-0}"
    CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
    ENV_FILE="${ENV_FILE:-}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -d|--domain)
                DOMAIN="$2"; shift 2;;
            --www-domain)
                WWW_DOMAIN="$2"; shift 2;;
            -a|--app-root)
                APP_ROOT="$2"; shift 2;;
            -u|--user)
                APP_USER="$2"; shift 2;;
            -g|--group)
                APP_GROUP="$2"; shift 2;;
            -p|--api-prefix)
                API_PREFIX="$2"; shift 2;;
            --static-root)
                STATIC_ROOT="$2"; shift 2;;
            --env-file)
                ENV_FILE="$2"; shift 2;;
            --systemd-unit)
                SYSTEMD_UNIT="$2"; shift 2;;
            --nginx-conf)
                NGINX_CONF_NAME="$2"; shift 2;;
            --skip-packages)
                SKIP_PACKAGES=1; shift;;
            --certbot)
                ENABLE_CERTBOT=1; shift;;
            --certbot-email)
                CERTBOT_EMAIL="$2"; shift 2;;
            -h|--help)
                usage; exit 0;;
            *)
                echo "Unknown option: $1" >&2
                usage
                exit 1;;
        esac
    done

    # Compute defaults that depend on arguments
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT_DEFAULT="$(dirname "$(dirname "$SCRIPT_DIR")")"
    APP_ROOT="${APP_ROOT:-$REPO_ROOT_DEFAULT}"
    ENV_FILE="${ENV_FILE:-$APP_ROOT/.env}"
    APP_GROUP="${APP_GROUP:-$APP_USER}"
    WWW_DOMAIN="${WWW_DOMAIN:-www.${DOMAIN}}"
    STATIC_ROOT="${STATIC_ROOT:-$APP_ROOT/frontend}"
}

install_packages() {
    if [[ "$SKIP_PACKAGES" -eq 1 ]]; then
        echo "[SKIP] Package installation skipped."
        return
    fi

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    local packages=(python3-venv python3-pip nginx git curl rsync)
    if [[ "$ENABLE_CERTBOT" -eq 1 ]]; then
        packages+=(certbot python3-certbot-nginx)
    fi
    apt-get install -y "${packages[@]}"
}

ensure_service_user() {
    if ! id "$APP_USER" &>/dev/null; then
        echo "[INFO] Creating system user '$APP_USER'"
        adduser --system --group --no-create-home "$APP_USER"
    fi
    if ! getent group "$APP_GROUP" &>/dev/null; then
        echo "[INFO] Creating system group '$APP_GROUP'"
        addgroup --system "$APP_GROUP"
    fi
}

prepare_repo_permissions() {
    mkdir -p "$APP_ROOT"
    chown -R "$APP_USER:$APP_GROUP" "$APP_ROOT"
}

verify_repo_structure() {
    local required_paths=(
        "$APP_ROOT/backend/requirements.txt"
        "$APP_ROOT/backend/app.py"
        "$APP_ROOT/deploy/systemd/legal-backend.service"
        "$APP_ROOT/deploy/nginx/legal-chatbot.conf"
    )
    for path in "${required_paths[@]}"; do
        if [[ ! -e "$path" ]]; then
            echo "[ERROR] Required path missing: $path" >&2
            echo "Ensure APP_ROOT points at the cloned repository." >&2
            exit 1
        fi
    done
}

ensure_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "[INFO] Creating environment file at $ENV_FILE"
        cat <<EOF > "$ENV_FILE"
MODEL_HF_REPO=sigmaloop/qwen3-0.6B-instruct-trafficlaws
MODEL_HF_SUBFOLDER=model
HF_TOKEN=__REPLACE_WITH_YOUR_TOKEN__
DATABASE_URL=sqlite:///./feedback.db
CORS_ORIGINS=https://${DOMAIN}
HEALTH_RELOAD_INFERENCE=0
USE_GENERATIVE_MODEL=true
# Point to an external generator (optional)
REMOTE_GENERATOR_URL=
REMOTE_GENERATOR_TIMEOUT=45
REMOTE_GENERATOR_TOKEN=
EOF
        chmod 640 "$ENV_FILE"
        chown "$APP_USER:$APP_GROUP" "$ENV_FILE"
    else
        ensure_env_var() {
            local key="$1"
            local value="$2"
            if ! grep -q "^${key}=" "$ENV_FILE"; then
                echo "${key}=${value}" >> "$ENV_FILE"
            fi
        }
        ensure_env_var "HEALTH_RELOAD_INFERENCE" "0"
        ensure_env_var "USE_GENERATIVE_MODEL" "true"
        ensure_env_var "REMOTE_GENERATOR_URL" ""
        ensure_env_var "REMOTE_GENERATOR_TIMEOUT" "45"
        ensure_env_var "REMOTE_GENERATOR_TOKEN" ""
    fi
}

setup_python_env() {
prepare_static_assets() {
    mkdir -p "$STATIC_ROOT"
    if command -v rsync >/dev/null 2>&1; then
        if [[ "$STATIC_ROOT" != "$APP_ROOT/frontend" ]]; then
            echo "[INFO] Syncing frontend assets to $STATIC_ROOT"
            rsync -a --delete "$APP_ROOT/frontend/" "$STATIC_ROOT/"
        else
            echo "[INFO] STATIC_ROOT matches repo frontend; skipping sync"
        fi
    else
        echo "[WARN] rsync not available; static assets not synced automatically."
    fi

    local static_owner="www-data"
    if ! id "$static_owner" &>/dev/null; then
        static_owner="root"
    fi
    chown -R "$static_owner:$static_owner" "$STATIC_ROOT"
}
    if [[ ! -d "$APP_ROOT/.venv" ]]; then
        echo "[INFO] Creating Python virtual environment"
        python3 -m venv "$APP_ROOT/.venv"
    fi
    source "$APP_ROOT/.venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$APP_ROOT/backend/requirements.txt"
    deactivate
    chown -R "$APP_USER:$APP_GROUP" "$APP_ROOT/.venv"
}

render_template() {
    local template_path="$1"
    local output_path="$2"
    shift 2
    local cmd=(sed)
    for pair in "$@"; do
        local search="${pair%%=*}"
        local replace="${pair#*=}"
        cmd+=(-e "s|${search}|${replace}|g")
    done
    "${cmd[@]}" "$template_path" > "$output_path"
}

install_systemd_unit() {
    local template="$APP_ROOT/deploy/systemd/legal-backend.service"
    local target="/etc/systemd/system/${SYSTEMD_UNIT}.service"
    echo "[INFO] Installing systemd unit to $target"
    render_template "$template" "$target" \
        "__APP_USER__=$APP_USER" \
        "__APP_GROUP__=$APP_GROUP" \
        "__APP_ROOT__=$APP_ROOT" \
        "__ENV_FILE__=$ENV_FILE"
    chmod 644 "$target"
    systemctl daemon-reload
    systemctl enable "$SYSTEMD_UNIT".service
    systemctl restart "$SYSTEMD_UNIT".service
}

install_nginx_conf() {
    local template="$APP_ROOT/deploy/nginx/legal-chatbot.conf"
    local target="/etc/nginx/sites-available/${NGINX_CONF_NAME}"
    echo "[INFO] Installing Nginx configuration to $target"
    render_template "$template" "$target" \
        "__SERVER_NAME__=$DOMAIN" \
        "__SERVER_NAME_WWW__=$WWW_DOMAIN" \
        "__STATIC_ROOT__=$STATIC_ROOT" \
        "__API_PREFIX__=$API_PREFIX"
    ln -sf "$target" "/etc/nginx/sites-enabled/${NGINX_CONF_NAME}"
    if [[ -e /etc/nginx/sites-enabled/default ]]; then
        rm -f /etc/nginx/sites-enabled/default
    fi
    nginx -t
    systemctl reload nginx
}

request_certificates() {
    if [[ "$ENABLE_CERTBOT" -ne 1 ]]; then
        return
    fi
    if [[ -z "$CERTBOT_EMAIL" ]]; then
        echo "[WARN] --certbot specified but no --certbot-email provided; skipping certificate issuance."
        return
    fi
    echo "[INFO] Requesting Let's Encrypt certificates for $DOMAIN and $WWW_DOMAIN"
    certbot --nginx -d "$DOMAIN" -d "$WWW_DOMAIN" \
        --non-interactive --agree-tos --email "$CERTBOT_EMAIL" || {
        echo "[WARN] Certbot failed. Please run certbot manually."
    }
}

main() {
    parse_args "$@"
    require_root
    install_packages
    ensure_service_user
    prepare_repo_permissions
    verify_repo_structure
    ensure_env_file
    setup_python_env
    prepare_static_assets
    install_systemd_unit
    install_nginx_conf
    request_certificates

    cat <<EOF

Deployment complete!
- Backend service: systemctl status ${SYSTEMD_UNIT}.service
- Backend logs: journalctl -u ${SYSTEMD_UNIT}.service -f
- Env file: ${ENV_FILE} (update secrets and restart with systemctl restart ${SYSTEMD_UNIT}.service)
- Nginx conf: /etc/nginx/sites-available/${NGINX_CONF_NAME}

Remember to replace the placeholder HF_TOKEN in your .env file.
EOF
}

main "$@"

