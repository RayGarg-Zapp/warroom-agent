#!/bin/bash
# =============================================================================
# WarRoom Agent — Add HTTPS via Nginx + self-signed cert
#
# Run this AFTER ec2-setup.sh to enable HTTPS (required by Auth0 SPA SDK).
#
# Usage:
#   sudo ./ec2-setup-ssl.sh
#
# After running, access the app at:
#   https://<EC2_PUBLIC_IP>
# =============================================================================

set -euo pipefail

EC2_PUBLIC_IP="52.0.233.16"
echo "============================================"
echo "  WarRoom Agent — SSL Setup"
echo "  EC2 Public IP: ${EC2_PUBLIC_IP}"
echo "============================================"

# ── Install nginx (support both yum and dnf) ─────────────────────────────────
echo ""
echo "=== Installing Nginx ==="
if command -v yum &>/dev/null; then
  yum install -y nginx openssl
elif command -v dnf &>/dev/null; then
  dnf install -y nginx openssl
elif command -v apt-get &>/dev/null; then
  apt-get update && apt-get install -y nginx openssl
else
  echo "ERROR: No supported package manager found"
  exit 1
fi

# ── Generate self-signed certificate ─────────────────────────────────────────
echo ""
echo "=== Generating self-signed SSL certificate ==="
mkdir -p /etc/nginx/ssl

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/warroom.key \
  -out /etc/nginx/ssl/warroom.crt \
  -subj "/C=US/ST=State/L=City/O=WarRoom/CN=${EC2_PUBLIC_IP}"

# ── Nginx config ─────────────────────────────────────────────────────────────
echo ""
echo "=== Configuring Nginx ==="
cat > /etc/nginx/conf.d/warroom.conf << 'NGINXEOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS — serves frontend + proxies API to backend
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/warroom.crt;
    ssl_certificate_key /etc/nginx/ssl/warroom.key;

    # Frontend (Vite build output)
    root /home/ec2-user/warroom/dist;
    index index.html;

    # API proxy to uvicorn backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Health check proxy
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # SPA fallback — all non-file routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

# Remove default nginx config if it conflicts
rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Test nginx config
nginx -t

# ── Update backend CORS ─────────────────────────────────────────────────────
echo ""
echo "=== Updating backend CORS for HTTPS ==="
ENV_FILE="/home/ec2-user/warroom/backend/.env"
if [ -f "${ENV_FILE}" ]; then
  # Update CORS to include HTTPS origin
  sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://${EC2_PUBLIC_IP}\",\"http://localhost:8080\"]|" "${ENV_FILE}"
  echo "Updated CORS_ORIGINS in ${ENV_FILE}"
fi

# ── Fix permissions so nginx can read frontend files ─────────────────────────
echo ""
echo "=== Fixing file permissions for Nginx ==="
chmod 711 /home/ec2-user
chmod -R 755 /home/ec2-user/warroom/dist

# ── Stop the standalone frontend serve (nginx takes over) ────────────────────
echo ""
echo "=== Stopping standalone frontend service (nginx handles it now) ==="
systemctl stop warroom-frontend 2>/dev/null || true
systemctl disable warroom-frontend 2>/dev/null || true

# ── Start services ──────────────────────────────────────────────────────────
echo ""
echo "=== Starting Nginx ==="
systemctl enable nginx
systemctl restart nginx
systemctl restart warroom-backend

# ── Open port 443 ───────────────────────────────────────────────────────────
echo ""
echo "=== Opening HTTPS port ==="
if command -v firewall-cmd &>/dev/null; then
  firewall-cmd --permanent --add-service=https
  firewall-cmd --permanent --add-service=http
  firewall-cmd --reload
else
  iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  SSL Setup Complete!"
echo "============================================"
echo ""
echo "Access your app at:"
echo "  https://${EC2_PUBLIC_IP}"
echo ""
echo "IMPORTANT — Update Auth0 settings:"
echo ""
echo "1. Auth0 Dashboard > Applications > Your App > Settings:"
echo "   - Allowed Callback URLs:      https://${EC2_PUBLIC_IP}/integrations"
echo "   - Allowed Logout URLs:         https://${EC2_PUBLIC_IP}"
echo "   - Allowed Web Origins:         https://${EC2_PUBLIC_IP}"
echo ""
echo "2. Your browser will show a security warning (self-signed cert)."
echo "   Click 'Advanced' > 'Proceed' to continue."
echo ""
echo "3. Update your frontend .env VITE vars if needed."
echo ""