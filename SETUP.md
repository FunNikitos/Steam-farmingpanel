# 🚀 Quick Setup Guide

## Local Development

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Clone & Setup

```bash
cd ~/Documents/steam-panel-bot
cp .env.example .env
nano .env  # Fill in your values
```

### 3. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python -c "import asyncio; from backend.db import init_db; asyncio.run(init_db('data/panel.db'))"
```

### 5. Run Bot

```bash
python -m backend.telegram_bot
```

---

## Production Deployment (VPS)

### 1. Prepare VPS (Ubuntu 22.04+)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y
```

### 2. Clone Project

```bash
mkdir -p /opt/steam-panel-bot
cd /opt/steam-panel-bot
git clone https://github.com/yourusername/steam-panel-bot.git .
```

### 3. Configure

```bash
# Copy and edit environment
cp .env.example .env
nano .env

# Copy and edit ASF config
cd asf-config
cp ASF.json.example ASF.json
nano ASF.json
```

**Important:** Set the same password in:
- `.env` → `ASF_IPC_PASSWORD`
- `asf-config/ASF.json` → `IPCPassword`

### 4. Deploy

```bash
cd /opt/steam-panel-bot
docker compose up -d
```

### 5. Check Status

```bash
# Check containers
docker compose ps

# View logs
docker compose logs -f bot
docker compose logs -f asf

# Restart if needed
docker compose restart bot
```

---

## Deploy Script (from local machine)

Edit `deploy.sh`:

```bash
VPS_HOST="your_vps_ip_here"
```

Then deploy:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Systemd Service (optional)

Create `/etc/systemd/system/steam-panel-bot.service`:

```ini
[Unit]
Description=Steam Panel Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/steam-panel-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable steam-panel-bot
sudo systemctl start steam-panel-bot
```

---

## Environment Variables

Required in `.env`:

```env
# Telegram (get from @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_USER_ID=1209417350

# Steam Web API (https://steamcommunity.com/dev/apikey)
STEAM_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ASF (same as in asf-config/ASF.json)
ASF_IPC_PASSWORD=your_password_here
```

---

## Troubleshooting

### Bot doesn't start

```bash
docker compose logs bot
```

Common issues:
- Missing `TELEGRAM_BOT_TOKEN`
- Invalid `TELEGRAM_USER_ID`
- Database permission errors

### ASF doesn't work

```bash
docker compose logs asf
```

Common issues:
- `IPCPassword` mismatch between `.env` and `ASF.json`
- Missing bot configs in `asf-config/`

### Bot responds but commands don't work

Check if your Telegram ID matches `TELEGRAM_USER_ID`:
1. Message [@userinfobot](https://t.me/userinfobot)
2. Copy your ID
3. Update `.env`
4. Restart: `docker compose restart bot`

---

## Backup

Important files to backup:
- `.env` — secrets
- `data/panel.db` — accounts database
- `asf-config/*.maFile` — Steam Guard files (CRITICAL for 2FA recovery)

```bash
# Backup script
tar -czf backup-$(date +%Y%m%d).tar.gz .env data/ asf-config/*.maFile
```

---

## Updates

```bash
cd /opt/steam-panel-bot
git pull
docker compose down
docker compose up -d --build
```

Or use deploy script from local machine:

```bash
./deploy.sh
```

---

## Support

- 📖 [Full README](README.md)
- 🐛 [Report Issues](https://github.com/yourusername/steam-panel-bot/issues)
- 💬 [Discussions](https://github.com/yourusername/steam-panel-bot/discussions)
