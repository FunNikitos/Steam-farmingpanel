# ASF Config Directory

This directory contains ArchiSteamFarm configuration files.

**⚠️ Important:** These files are NOT tracked by git (contain credentials).

## Setup

### 1. ASF.json

Copy the example and edit:

```bash
cp ASF.json.example ASF.json
nano ASF.json
```

Set `IPCPassword` to the same value as `ASF_IPC_PASSWORD` in `.env`.

### 2. Bot configs

Bot config files are created automatically when you add accounts through the Telegram bot.

Example structure after adding accounts:

```
asf-config/
├── ASF.json              # Main ASF config
├── bot1.json             # First account config
├── bot1.maFile           # Steam Guard file for bot1
├── bot2.json             # Second account config
└── bot2.maFile           # Steam Guard file for bot2
```

## Manual bot config

If you want to create bot config manually:

```json
{
  "SteamLogin": "your_steam_login",
  "SteamPassword": "your_steam_password",
  "Enabled": true,
  "GamesPlayedWhileIdle": [730]
}
```

Save as `bot1.json` and place corresponding `.maFile` in the same directory.

## Security

- Never commit `.json` or `.maFile` files to git
- Backup `.maFile` files separately (needed for 2FA recovery)
- Use strong `IPCPassword`
