# Steam Panel Bot

🎮 Telegram-бот для управления Steam аккаунтами: автофарм карточек, мониторинг часов, раздачи игр.

## ✨ Возможности

- 📊 **Управление аккаунтами** — старт/стоп, выбор игр, статус онлайн
- 🔑 **Steam Guard** — TOTP коды с автообновлением, подтверждение трейдов
- 🎁 **Раздачи** — автопоиск халявных игр в Steam Store
- 💎 **Дешёвые игры** — поиск игр с карточками (<300₽, >20% скидка)
- 📈 **Статистика** — график часов CS2 за 7 дней
- 👥 **Система доступов** — выдача прав другим пользователям (менеджер/наблюдатель)
- 🤖 **Автофарм карточек** — через ArchiSteamFarm (ASF)

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/steam-panel-bot.git
cd steam-panel-bot
```

### 2. Настройка окружения

```bash
cp .env.example .env
nano .env  # Заполни свои данные
```

**Обязательные переменные:**
- `TELEGRAM_BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather)
- `TELEGRAM_USER_ID` — твой Telegram ID (узнай через [@userinfobot](https://t.me/userinfobot))
- `STEAM_API_KEY` — ключ Steam Web API ([получить](https://steamcommunity.com/dev/apikey))
- `ASF_IPC_PASSWORD` — пароль для ASF IPC (любой, например `261183`)

### 3. Запуск через Docker Compose

```bash
docker compose up -d
```

Готово! Бот запущен. Открой Telegram и напиши `/start` своему боту.

---

## 📦 Установка вручную (без Docker)

### Требования:
- Python 3.11+
- ArchiSteamFarm (скачай [здесь](https://github.com/JustArchiNET/ArchiSteamFarm/releases))

### Шаги:

```bash
# 1. Создай виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Инициализируй БД
python -m backend.db

# 4. Запусти бота
python -m backend.telegram_bot
```

---

## 🐳 Docker Compose (рекомендуется)

### Структура:
- **bot** — Telegram-бот на Python
- **asf** — ArchiSteamFarm для фарма карточек

### Команды:

```bash
# Запуск
docker compose up -d

# Логи
docker compose logs -f bot
docker compose logs -f asf

# Остановка
docker compose down

# Перезапуск
docker compose restart bot
```

---

## 📁 Структура проекта

```
steam-panel-bot/
├── backend/
│   ├── bot/
│   │   ├── handlers/          # Обработчики команд и callback
│   │   ├── keyboards.py       # Inline и Reply клавиатуры
│   │   ├── messages.py        # Шаблоны сообщений
│   │   └── middleware/        # Проверка доступов
│   ├── telegram_bot.py        # Главный файл бота
│   ├── db.py                  # База данных (SQLite)
│   ├── account_mgr.py         # Управление аккаунтами Steam
│   ├── scheduler.py           # Фоновые задачи (синхронизация)
│   ├── scanner.py             # Парсинг Steam Store
│   └── config.py              # Конфигурация
├── asf-config/                # Конфиги ASF (не в git)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Конфигурация

### `.env` файл:

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_USER_ID=1209417350

# Steam Web API
STEAM_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ASF
ASF_IPC_URL=http://asf:1242
ASF_IPC_PASSWORD=261183

# База данных
DB_PATH=/app/data/panel.db

# Планировщик (cron)
SCAN_CRON=0 10 * * *      # Раздачи — каждый день в 10:00
SYNC_CRON=0 * * * *        # Часы — каждый час
DEALS_CRON=0 11 * * *      # Дешёвые игры — каждый день в 11:00
```

---

## 🔐 Безопасность

### Что НЕ попадает в Git:
- `.env` — секреты (токены, ключи)
- `*.db` — база данных с аккаунтами
- `asf-config/*.json` — конфиги ботов ASF
- `asf-config/*.maFile` — Steam Guard файлы

### Рекомендации:
- Используй `.env` для всех секретов
- Не коммить `panel.db` (содержит логины Steam)
- Бэкапь `asf-config/*.maFile` отдельно (восстановление 2FA)

---

## 📊 Система доступов

Выдавай доступ к аккаунтам другим пользователям:

- **👤 Менеджер** — может управлять (старт/стоп, выбор игр, SteamGuard)
- **👁 Наблюдатель** — только просмотр статистики

**Как выдать:**
1. Открой аккаунт в боте
2. Нажми `👥 Доступы`
3. Введи Telegram ID пользователя
4. Выбери роль

---

## 🛠 Разработка

### Запуск в dev режиме:

```bash
# Бот (с автоперезагрузкой)
python -m backend.telegram_bot

# Форматирование кода
black backend/
ruff check backend/

# Тесты
pytest tests/ -v
```

### Структура handlers:

```python
# backend/bot/handlers/accounts.py
from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith("stop:"))
async def stop_account(callback: CallbackQuery):
    steamid = callback.data.split(":")[1]
    # Логика остановки
    await callback.answer("✅ Остановлено")
```

---

## 🚢 Деплой на VPS

### 1. Подготовка сервера (Ubuntu 22.04+)

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose-plugin

# Создание директории
mkdir -p /opt/steam-panel-bot
cd /opt/steam-panel-bot
```

### 2. Загрузка проекта

```bash
git clone https://github.com/yourusername/steam-panel-bot.git .
cp .env.example .env
nano .env  # Заполни данные
```

### 3. Запуск

```bash
docker compose up -d

# Проверка логов
docker compose logs -f
```

### 4. Автозапуск (systemd)

Создай `/etc/systemd/system/steam-panel-bot.service`:

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

Включи автозапуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable steam-panel-bot
sudo systemctl start steam-panel-bot
```

### 5. Обновление

```bash
cd /opt/steam-panel-bot
git pull
docker compose down
docker compose up -d --build
```

---

## 📝 Changelog

### v1.0.0 (2026-08-12)
- ✅ Telegram-бот с полным функционалом
- ✅ Управление аккаунтами (старт/стоп/игры)
- ✅ SteamGuard коды + SDA подтверждение
- ✅ Система доступов (owner/manager/viewer)
- ✅ Мониторинг часов CS2
- ✅ Парсинг дешёвых игр и раздач
- ✅ Docker Compose для деплоя

---

## 🤝 Contributing

Pull requests приветствуются! Для крупных изменений сначала открой issue.

1. Fork проекта
2. Создай feature branch (`git checkout -b feature/amazing`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Открой Pull Request

---

## 📄 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

## 💬 Поддержка

- 🐛 **Баги**: открой [issue](https://github.com/yourusername/steam-panel-bot/issues)
- 💡 **Идеи**: [discussions](https://github.com/yourusername/steam-panel-bot/discussions)
- 📧 **Email**: your@email.com

---

## 🙏 Благодарности

- [ArchiSteamFarm](https://github.com/JustArchiNET/ArchiSteamFarm) — фарм карточек
- [aiogram](https://github.com/aiogram/aiogram) — Telegram Bot framework
- [Steam Web API](https://steamcommunity.com/dev) — данные Steam

---

**Сделано с ❤️ для Steam фармеров**
