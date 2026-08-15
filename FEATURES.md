# Features Overview

## ✅ Implemented Features

### 🎮 Account Management
- ✅ List all accounts with status (farming/online/offline/error)
- ✅ Start/Stop farming
- ✅ Add account via login/password
- ✅ Add account via maFile upload
- ✅ Delete account
- ✅ Real-time status updates

### 🔑 SteamGuard
- ✅ TOTP code generation from maFile
- ✅ Auto-refresh every 5 seconds
- ✅ Visual countdown timer
- ✅ SDA confirmations (trades, market)

### 🎯 Game Selection
- ✅ Load games from Steam API
- ✅ Toggle multiple games
- ✅ Apply selection to ASF
- ✅ Shows playtime per game

### 💎 Cheap Games Scanner
- ✅ Finds games <300₽ with >20% discount
- ✅ Shows card count
- ✅ Links to Steam Store
- ✅ Manual refresh

### 🎁 Giveaways
- ✅ Scans Steam Store for free-to-keep games
- ✅ Add to all accounts with one click
- ✅ Manual refresh

### 👥 Access Control System
- ✅ Owner role (full access)
- ✅ Manager role (can manage, no delete/access control)
- ✅ Viewer role (read-only)
- ✅ Grant/revoke access by Telegram ID
- ✅ Change user roles

### 📈 Statistics
- ✅ Summary (online, hours, levels, balance)
- ✅ Per-account breakdown
- ✅ Weekly hours tracking
- ✅ Graph generation (matplotlib)
- ✅ Send graph as image

### 🔄 Automation
- ✅ Hourly hours synchronization
- ✅ Daily giveaways scan (10:00)
- ✅ Daily deals scan (11:00)
- ✅ Background scheduler (APScheduler)

### 🐳 Deployment
- ✅ Docker Compose setup
- ✅ Separate bot and ASF containers
- ✅ Volume mounts for data persistence
- ✅ Environment variables for secrets
- ✅ Deploy script for VPS

---

## 📋 Command Reference

### Main Menu Buttons
- 📊 Аккаунты — list all accounts
- 💎 Игры — cheap games with cards
- 🎁 Раздачи — free giveaways
- 📈 Статистика — statistics + graph
- ➕ Добавить — add new account
- ⚙️ Настройки — bot settings (planned)

### Account Card Buttons
- ◼️ Стоп / ▶️ Старт — stop/start farming
- 🎮 Игры — select games to farm
- 🔑 Guard — SteamGuard code + SDA confirm
- 👥 Доступы — manage user access (owner only)
- 🗑 Удалить — delete account (owner only)

### Commands
- `/start` — show main menu
- `/help` — show help
- `/cancel` — cancel current operation

---

## 🚀 How It Works

### Account Addition Flow

**Via Login/Password:**
1. User clicks "➕ Добавить"
2. Selects "🔑 Логин и пароль"
3. Enters login → password → SteamID (optional)
4. Bot creates ASF config file
5. ASF attempts login (may need 2FA code)

**Via maFile:**
1. User clicks "➕ Добавить"
2. Selects "📁 Загрузить maFile"
3. Uploads .maFile document
4. Enters password
5. Bot creates config + saves maFile
6. ASF logs in automatically

### SteamGuard Code Generation
1. Bot reads `botX.maFile`
2. Extracts `shared_secret`
3. Generates TOTP code (time-based, 30s window)
4. Auto-refreshes every 5 seconds
5. Shows countdown timer

### Access Control
1. Owner adds user by Telegram ID
2. Selects role (manager/viewer)
3. User sees account in their bot
4. Middleware checks permissions on every action
5. Owner can revoke anytime

### Automation
- **Scheduler** runs in background
- **job_sync_hours**: fetches playtime from Steam API every hour
- **job_scan_giveaways**: checks Steam Store for free games daily
- **job_scan_deals**: finds cheap games with cards daily

---

## 🔧 Technical Stack

- **Bot Framework**: aiogram 3.13
- **Database**: SQLite (aiosqlite)
- **ASF Integration**: HTTP IPC API
- **Steam API**: GetOwnedGames, Store Search
- **Scheduler**: APScheduler
- **Graphs**: matplotlib
- **Deployment**: Docker Compose

---

## 📊 Database Schema

```sql
accounts (steamid, login, asf_bot_name, status, total_hours, 
          level, xp, wallet_balance, enabled, owner_id, has_mafile)

account_access (steamid, telegram_id, role, granted_by, granted_at)

sessions (steamid, date, hours_delta)

giveaways (appid, name, license_type, found_at, status)

deals (appid, name, price_rub, original_rub, discount_pct, 
       card_count, found_at, notified)
```

---

## 🎯 Future Enhancements (Not Implemented)

- [ ] Settings menu (notification preferences)
- [ ] Push notifications (new giveaway, errors)
- [ ] Multiple game stores (Epic Games, GOG)
- [ ] Card crafting automation
- [ ] Market price tracking
- [ ] Trade confirmations log
- [ ] Backup/restore functionality
- [ ] Multi-language support

---

## 🐛 Known Limitations

1. **ASF IPC instability** — sometimes ASF doesn't respond, commands may fail
2. **Steam API rate limits** — GetOwnedGames limited to 100,000 calls/day
3. **maFile validation** — basic JSON check, doesn't verify signature
4. **No 2FA prompt** — login/password accounts need manual 2FA input via ASF logs
5. **Graph requires data** — needs at least 1 day of sessions to generate

---

## 📖 See Also

- [README.md](README.md) — full documentation
- [SETUP.md](SETUP.md) — quick setup guide
- [CHANGELOG.md](CHANGELOG.md) — version history
