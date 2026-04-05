#!/bin/bash
# =============================================================================
# WarRoom Agent — EC2 Setup Script (Amazon Linux 2023)
#
# Run this ONCE on a fresh EC2 instance to install all dependencies and
# configure the app to run as systemd services.
#
# Usage:
#   chmod +x ec2-setup.sh
#   sudo ./ec2-setup.sh
# =============================================================================

set -euo pipefail

APP_USER="${1:-ec2-user}"
APP_DIR="/home/${APP_USER}/warroom"
BACKEND_PORT=8000
FRONTEND_PORT=8080

echo "============================================"
echo "  WarRoom Agent — EC2 Setup"
echo "  User: ${APP_USER}"
echo "  App dir: ${APP_DIR}"
echo "============================================"

# ── System packages ─────────────────────────────────────────────────────────
echo ""
echo "=== Installing system packages ==="
if command -v yum &>/dev/null; then
  PKG="yum"
elif command -v dnf &>/dev/null; then
  PKG="dnf"
else
  echo "ERROR: No supported package manager found"; exit 1
fi

$PKG update -y
$PKG install -y \
  python3 \
  python3-pip \
  python3-devel \
  nodejs \
  npm \
  git \
  gcc \
  make \
  openssl-devel \
  libffi-devel \
  sqlite \
  sqlite-devel \
  rsync \
  htop 2>/dev/null || true

# Install python3.12 but do NOT override system python3 (breaks dnf)
$PKG install -y python3.12 python3.12-pip python3.12-devel 2>/dev/null || true

# Use python3.12 if available, otherwise fall back to system python3
PYTHON_BIN=$(command -v python3.12 || command -v python3)
echo "App Python: $($PYTHON_BIN --version)"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"

# ── Create app directory ────────────────────────────────────────────────────
echo ""
echo "=== Setting up app directory ==="
mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# ── Python virtual environment ──────────────────────────────────────────────
echo ""
echo "=== Setting up Python virtual environment ==="
sudo -u "${APP_USER}" bash -c "
  cd ${APP_DIR}/backend 2>/dev/null || { echo 'Backend dir not found yet — will be created on first deploy'; exit 0; }
  ${PYTHON_BIN} -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  deactivate
"

# ── Frontend dependencies ───────────────────────────────────────────────────
echo ""
echo "=== Installing frontend dependencies ==="
sudo -u "${APP_USER}" bash -c "
  cd ${APP_DIR} 2>/dev/null || { echo 'App dir not found yet — will be created on first deploy'; exit 0; }
  if [ -f package.json ]; then
    npm ci
  fi
"

# ── Backend .env file ───────────────────────────────────────────────────────
echo ""
echo "=== Setting up backend .env ==="
ENV_FILE="${APP_DIR}/backend/.env"
if [ ! -f "${ENV_FILE}" ]; then
  mkdir -p "${APP_DIR}/backend"
  cat > "${ENV_FILE}" << 'ENVEOF'
# Database
DATABASE_URL=sqlite:///./warroom.db

# App
APP_ENV=production
LOG_LEVEL=INFO
JWT_SECRET=CHANGE_ME_TO_A_RANDOM_SECRET

# ── LLM / Anthropic Claude ─────────────────────────────────────────
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

# Slack
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_CHANNEL_ID=
SLACK_POLL_INTERVAL=10

# Zoom
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
ZOOM_ACCOUNT_ID=

# Google Calendar
GOOGLE_SERVICE_ACCOUNT_KEY=

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=

# Auth0 core
AUTH0_DOMAIN=
AUTH0_AUDIENCE=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=

# Token Vault / Custom API Client
AUTH0_CUSTOM_API_CLIENT_ID=
AUTH0_CUSTOM_API_CLIENT_SECRET=
AUTH0_TOKEN_ENDPOINT=

# Connection names
AUTH0_SLACK_CONNECTION_NAME=sign-in-with-slack
AUTH0_GOOGLE_CONNECTION_NAME=google-oauth2
AUTH0_GITHUB_CONNECTION_NAME=github

# CORS (update with your EC2 public IP or domain)
CORS_ORIGINS=["http://localhost:8080"]
ENVEOF

  chown "${APP_USER}:${APP_USER}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE} — EDIT THIS FILE with your actual secrets!"
else
  echo ".env already exists, skipping"
fi

# ── Frontend .env file ──────────────────────────────────────────────────────
echo ""
echo "=== Setting up frontend .env ==="
FRONTEND_ENV="${APP_DIR}/.env"
if [ ! -f "${FRONTEND_ENV}" ]; then
  cat > "${FRONTEND_ENV}" << 'ENVEOF'
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_AUDIENCE=
ENVEOF

  chown "${APP_USER}:${APP_USER}" "${FRONTEND_ENV}"
  chmod 600 "${FRONTEND_ENV}"
  echo "Created ${FRONTEND_ENV} — EDIT THIS FILE with your Auth0 frontend config!"
else
  echo ".env already exists, skipping"
fi

# ── Systemd service: Backend (uvicorn) ──────────────────────────────────────
echo ""
echo "=== Creating systemd service: warroom-backend ==="
cat > /etc/systemd/system/warroom-backend.service << EOF
[Unit]
Description=WarRoom Agent Backend (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/backend
Environment=PATH=${APP_DIR}/backend/venv/bin:/usr/local/bin:/usr/bin
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── Systemd service: Frontend (serve static build) ──────────────────────────
echo ""
echo "=== Installing serve for static frontend hosting ==="
npm install -g serve

cat > /etc/systemd/system/warroom-frontend.service << EOF
[Unit]
Description=WarRoom Agent Frontend (Static)
After=network.target warroom-backend.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/serve -s dist -l ${FRONTEND_PORT}
Environment=PORT=${FRONTEND_PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── Enable and start services ───────────────────────────────────────────────
echo ""
echo "=== Enabling systemd services ==="
systemctl daemon-reload
systemctl enable warroom-backend
systemctl enable warroom-frontend

# ── Firewall (open ports) ──────────────────────────────────────────────────
echo ""
echo "=== Opening firewall ports ==="
# Amazon Linux uses firewalld if installed, otherwise iptables
if command -v firewall-cmd &>/dev/null; then
  firewall-cmd --permanent --add-port=${BACKEND_PORT}/tcp
  firewall-cmd --permanent --add-port=${FRONTEND_PORT}/tcp
  firewall-cmd --reload
else
  iptables -I INPUT -p tcp --dport ${BACKEND_PORT} -j ACCEPT 2>/dev/null || true
  iptables -I INPUT -p tcp --dport ${FRONTEND_PORT} -j ACCEPT 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Edit backend secrets:"
echo "   nano ${APP_DIR}/backend/.env"
echo ""
echo "2. Edit frontend Auth0 config:"
echo "   nano ${APP_DIR}/.env"
echo ""
echo "3. Update CORS_ORIGINS in backend .env with your EC2 public IP:"
echo "   CORS_ORIGINS=[\"http://<EC2_PUBLIC_IP>:${FRONTEND_PORT}\"]"
echo ""
echo "4. Update Auth0 callback URLs to include:"
echo "   http://<EC2_PUBLIC_IP>:${FRONTEND_PORT}/integrations"
echo ""
echo "5. Deploy code (push to main) or manually start:"
echo "   sudo systemctl start warroom-backend"
echo "   sudo systemctl start warroom-frontend"
echo ""
echo "6. Check logs:"
echo "   journalctl -u warroom-backend -f"
echo "   journalctl -u warroom-frontend -f"
echo ""
echo "7. Make sure your EC2 Security Group allows inbound:"
echo "   - Port ${BACKEND_PORT} (backend API)"
echo "   - Port ${FRONTEND_PORT} (frontend UI)"
echo "   - Port 22 (SSH)"
echo ""