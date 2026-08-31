#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$APP_DIR/backend-node"
FRONTEND_DIR="$APP_DIR/frontend"
DB_URL="postgresql://postgres:postgres@localhost:5432/employees"

echo "============================================"
echo "  Employee App — Node.js Backend"
echo "============================================"

# ─── PHASE 1: BUILD ──────────────────────────────
echo ""
echo ">>> PHASE 1: BUILD"
echo "Installing Node.js dependencies..."
cd "$BACKEND_DIR"
npm install
echo "Build complete."

# ─── PHASE 2: TEST ───────────────────────────────
echo ""
echo ">>> PHASE 2: TEST"
echo "Running tests (requires Postgres)..."
cd "$BACKEND_DIR"
DATABASE_URL=$DB_URL npm test
echo "Tests passed."

# ─── PHASE 3: START ──────────────────────────────
echo ""
echo ">>> PHASE 3: START"

echo "Configuring Nginx..."
sudo tee /etc/nginx/conf.d/employee-app.conf > /dev/null <<EOF
server {
    listen 80;

    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
    }

    location / {
        root $FRONTEND_DIR;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "Fixing home directory permissions for Nginx..."
chmod o+x /home/ec2-user

echo "Starting Node.js backend on port 5000..."
cd "$BACKEND_DIR"
DATABASE_URL=$DB_URL nohup node app.js > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

echo "Waiting for backend to be ready..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "Backend is up."
        break
    fi
    sleep 1
done

TOKEN=$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
PUBLIC_IP=$(curl -sf -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -sf http://checkip.amazonaws.com 2>/dev/null || echo "<EC2_PUBLIC_IP>")

echo ""
echo "============================================"
echo "  App is running!"
echo "  Open: http://$PUBLIC_IP"
echo "  Logs: tail -f /tmp/backend.log"
echo "  Stop: kill $BACKEND_PID"
echo "============================================"
