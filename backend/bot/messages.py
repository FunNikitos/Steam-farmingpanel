"""Message templates for bot."""


def format_account_card(account: dict, role: str = "owner") -> str:
    """Format account info card."""
    status_emoji = {
        "farming": "🟢",
        "online": "🟡",
        "offline": "🔴",
        "error": "⚠️",
    }

    status = account.get("status", "offline")
    emoji = status_emoji.get(status, "⚪")

    role_badges = {
        "owner": "[👤 Владелец]",
        "manager": "[🔧 Менеджер]",
        "viewer": "[👁 Наблюдатель]",
    }
    role_badge = role_badges.get(role, "")

    # XP progress bar
    xp = account.get("xp_progress", 0)
    bar_length = 10
    filled = int(xp / 100 * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)

    msg = f"{emoji} {account['login']} {role_badge}\n"
    msg += "━━━━━━━━━━━━━━━━\n"
    msg += f"├─ Уровень: {account.get('level', 0)} | "
    # wallet_balance stored as string, convert safely
    try:
        balance = float(str(account.get('wallet_balance', 0)).replace(',', '.'))
    except (ValueError, TypeError):
        balance = 0.0
    msg += f"Баланс: {balance:.0f}₽\n"
    msg += f"├─ CS2: {account.get('total_hours', 0):.1f}ч | "
    msg += f"XP: [{bar}] {xp:.0f}%\n"

    if status == "farming":
        current_game = account.get("current_game_name", "неизвестно")
        cards_left = account.get("cards_remaining", 0)
        msg += f"└─ Фармит: {current_game}"
        if cards_left > 0:
            msg += f" ({cards_left}🃏)"
    elif status == "error":
        msg += f"└─ Ошибка: {account.get('error_message', 'неизвестно')}"
    else:
        msg += f"└─ Статус: {status}"

    msg += "\n\n"

    if role == "viewer":
        msg += "⚠️ Только просмотр\n"

    return msg


def format_accounts_list(accounts: list[dict], roles: dict[str, str]) -> str:
    """Format list of all accounts."""
    if not accounts:
        return (
            "📊 Аккаунты\n\n"
            "У тебя ещё нет аккаунтов.\n"
            "Добавь первый через кнопку ниже."
        )

    msg = f"📊 Аккаунты ({len(accounts)})\n\n"

    for acc in accounts:
        role = roles.get(acc["steamid"], "owner")
        msg += format_account_card(acc, role)

    return msg


def format_steamguard_code(data: dict) -> str:
    """Format SteamGuard code with timer."""
    code = data.get("code", "?????")
    seconds = data.get("seconds_remaining", 30)

    # Format code with spaces
    spaced_code = " ".join(code)

    # Progress bar
    progress = seconds / 30
    bar_length = 14
    filled = int(progress * bar_length)

    if seconds < 10:
        bar = "🔴" * filled + "░" * (bar_length - filled)
    else:
        bar = "█" * filled + "░" * (bar_length - filled)

    msg = f"🔑 Steam Guard\n\n"
    msg += "╔═══════════════╗\n"
    msg += f"║ {spaced_code} ║\n"
    msg += "╚═══════════════╝\n\n"
    msg += f"⏱ Обновится через {seconds} сек\n"
    msg += f"[{bar}]\n"

    return msg


def format_deals_list(deals: list[dict]) -> str:
    """Format list of cheap games."""
    if not deals:
        return (
            "💎 Дешёвые игры\n\n"
            "Сейчас нет выгодных предложений.\n"
            "Попробуй обновить позже."
        )

    msg = f"💎 Игры для фарма (<300₽)\n\n"
    msg += f"Найдено: {len(deals)} игр\n"
    msg += "━━━━━━━━━━━━━━━━\n\n"

    for i, deal in enumerate(deals[:10], 1):
        name = deal["name"]
        price = deal["price_rub"]
        original = deal["original_rub"]
        discount = deal["discount_pct"]
        cards = deal.get("card_count", 0)

        msg += f"{i}. {name}\n"
        msg += f"   ├─ {price:.0f}₽ → было {original:.0f}₽ (-{discount}%)\n"

        if cards > 0:
            msg += f"   └─ 🃏 {cards} карточек (~{price/cards:.0f}₽/шт)\n"
        else:
            msg += f"   └─ Карточки: уточняется\n"

        msg += "\n"

    if len(deals) > 10:
        msg += f"... и ещё {len(deals) - 10} игр\n"

    return msg


def format_giveaways_list(giveaways: list[dict]) -> str:
    """Format list of giveaways."""
    if not giveaways:
        return (
            "🎁 Раздачи\n\n"
            "Сейчас нет активных раздач.\n"
            "Проверяем каждый день в 10:00."
        )

    msg = f"🎁 Раздачи ({len(giveaways)} активные)\n\n"

    for giveaway in giveaways:
        name = giveaway["name"]
        appid = giveaway["appid"]

        msg += "━━━━━━━━━━━━━━━━\n"
        msg += f"🎮 {name}\n"
        msg += f"├─ AppID: {appid}\n"
        msg += f"├─ Тип: Free to Keep\n"
        msg += f"└─ Статус: Активна\n\n"

    return msg


def format_summary(data: dict) -> str:
    """Format main menu summary."""
    msg = "🎮 Steam Panel\n\n"
    msg += f"Твои аккаунты онлайн: {data.get('online', 0)}/{data.get('total', 0)}\n"
    msg += f"Часов за неделю: {data.get('hours_week', 0):.1f}ч\n"
    msg += f"Средний уровень: {data.get('avg_level', 0):.0f}\n"

    return msg


def format_access_list(accesses: list[dict], owner_name: str, owner_id: int) -> str:
    """Format list of accesses for account."""
    msg = "👥 Доступы к аккаунту\n\n"
    msg += "Владелец:\n"
    msg += f"└─ {owner_name} (ID: {owner_id})\n\n"

    if not accesses:
        msg += "Доступ не выдан никому.\n"
        msg += "Добавь пользователей через кнопку ниже."
        return msg

    msg += f"Доступ выдан ({len(accesses)}):\n"
    msg += "━━━━━━━━━━━━━━━━\n\n"

    role_emoji = {"manager": "👤", "viewer": "👁"}
    role_names = {"manager": "Менеджер", "viewer": "Наблюдатель"}
    role_perms = {
        "manager": "управлять, смотреть",
        "viewer": "только смотреть",
    }

    for acc in accesses:
        role = acc["role"]
        emoji = role_emoji.get(role, "👤")
        role_name = role_names.get(role, role)
        perms = role_perms.get(role, "")

        msg += f"{emoji} {role_name}\n"
        msg += f"├─ ID: {acc['telegram_id']}\n"
        msg += f"├─ Может: {perms}\n"
        msg += f"└─ Выдан: {acc['granted_at'][:10]}\n\n"

    return msg
