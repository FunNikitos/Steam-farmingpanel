#!/usr/bin/env bash
set -e

# Configuration
VPS_USER="root"
VPS_HOST="your_vps_ip_here"
DEPLOY_PATH="/opt/steam-panel-bot"

echo "🚀 Deploying Steam Panel Bot..."

# 1. Build locally (optional - for testing)
echo "→ Testing locally..."
# docker compose build

# 2. Sync files to VPS (excluding secrets and data)
echo "→ Syncing files to VPS..."
rsync -avz --delete \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='*.db' \
  --exclude='asf-config/*.json' \
  --exclude='asf-config/*.maFile' \
  --exclude='data/' \
  --exclude='__pycache__/' \
  --exclude='.venv/' \
  ./ ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}/

# 3. Deploy on VPS
echo "→ Deploying on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /opt/steam-panel-bot

# Pull latest changes if git repo
# git pull

# Rebuild and restart containers
docker compose down
docker compose up -d --build

# Show status
echo ""
echo "✅ Deploy complete!"
echo ""
docker compose ps
echo ""
echo "📋 Logs:"
docker compose logs --tail=20 bot

EOF

echo ""
echo "✅ Deployment finished!"
echo ""
echo "Commands:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'cd ${DEPLOY_PATH} && docker compose logs -f bot'"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'cd ${DEPLOY_PATH} && docker compose restart bot'"
