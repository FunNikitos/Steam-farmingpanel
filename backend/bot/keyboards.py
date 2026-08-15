"""Keyboards for Telegram bot."""
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Main persistent menu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Аккаунты"), KeyboardButton(text="💎 Игры")],
            [KeyboardButton(text="🎁 Раздачи"), KeyboardButton(text="📈 Статистика")],
            [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def get_back_to_main() -> InlineKeyboardMarkup:
    """Back to main menu button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Главная", callback_data="main")]]
    )


def get_account_buttons(steamid: str, role: str = "owner") -> InlineKeyboardMarkup:
    """Buttons for account card."""
    buttons = []

    # First row: Start/Stop, Games, Guard
    if role in ("owner", "manager"):
        buttons.append([
            InlineKeyboardButton(text="◼️ Стоп", callback_data=f"stop:{steamid}"),
            InlineKeyboardButton(text="🎮 Игры", callback_data=f"games:{steamid}"),
            InlineKeyboardButton(text="🔑 Guard", callback_data=f"guard:{steamid}"),
        ])
    else:  # viewer
        buttons.append([
            InlineKeyboardButton(text="🔑 Guard", callback_data=f"guard:{steamid}"),
        ])

    # Second row: Access, Delete (only owner)
    if role == "owner":
        buttons.append([
            InlineKeyboardButton(text="👥 Доступы", callback_data=f"access:{steamid}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{steamid}"),
        ])

    # Third row: Refresh, Back
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh:{steamid}"),
        InlineKeyboardButton(text="◀️ К списку", callback_data="accounts"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_accounts_list_buttons() -> InlineKeyboardMarkup:
    """Buttons for accounts list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_account"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="accounts_refresh"),
            ],
            [InlineKeyboardButton(text="◀️ Главная", callback_data="main")],
        ]
    )


def get_steamguard_buttons(steamid: str) -> InlineKeyboardMarkup:
    """Buttons for SteamGuard modal."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить SDA", callback_data=f"sda:{steamid}")],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"guard:{steamid}"),
                InlineKeyboardButton(text="◀️ К аккаунтам", callback_data="accounts"),
            ],
        ]
    )


def get_add_account_method() -> InlineKeyboardMarkup:
    """Choose add account method."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Логин и пароль", callback_data="add_login")],
            [InlineKeyboardButton(text="📁 Загрузить maFile", callback_data="add_mafile")],
            [InlineKeyboardButton(text="◀️ Главная", callback_data="main")],
        ]
    )


def get_deals_buttons() -> InlineKeyboardMarkup:
    """Buttons for deals list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="deals_refresh"),
            ],
            [InlineKeyboardButton(text="◀️ Главная", callback_data="main")],
        ]
    )


def get_deal_buttons(appid: str) -> InlineKeyboardMarkup:
    """Buttons for single deal."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Открыть в Steam", url=f"https://store.steampowered.com/app/{appid}")],
            [InlineKeyboardButton(text="◀️ К играм", callback_data="deals")],
        ]
    )


def get_giveaways_buttons() -> InlineKeyboardMarkup:
    """Buttons for giveaways list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="giveaways_refresh")],
            [InlineKeyboardButton(text="◀️ Главная", callback_data="main")],
        ]
    )


def get_giveaway_buttons(appid: str, already_claimed: bool = False) -> InlineKeyboardMarkup:
    """Buttons for single giveaway."""
    buttons = []

    if not already_claimed:
        buttons.append([
            InlineKeyboardButton(text="📥 Добавить на все аккаунты", callback_data=f"claim_all:{appid}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="✅ Уже добавлено", callback_data="noop")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔗 Открыть в Steam", url=f"https://store.steampowered.com/app/{appid}")
    ])
    buttons.append([
        InlineKeyboardButton(text="◀️ К раздачам", callback_data="giveaways")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_access_list_buttons(steamid: str) -> InlineKeyboardMarkup:
    """Buttons for access management."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data=f"access_add:{steamid}")],
            [InlineKeyboardButton(text="◀️ К аккаунту", callback_data=f"account:{steamid}")],
        ]
    )


def get_access_user_buttons(steamid: str, telegram_id: int) -> InlineKeyboardMarkup:
    """Buttons for single user access."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Изменить роль", callback_data=f"access_edit:{steamid}:{telegram_id}")],
            [InlineKeyboardButton(text="🗑 Удалить доступ", callback_data=f"access_revoke:{steamid}:{telegram_id}")],
            [InlineKeyboardButton(text="◀️ К доступам", callback_data=f"access:{steamid}")],
        ]
    )


def get_access_role_buttons(steamid: str, telegram_id: int) -> InlineKeyboardMarkup:
    """Choose role for user."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Менеджер", callback_data=f"access_role:{steamid}:{telegram_id}:manager")],
            [InlineKeyboardButton(text="👁 Наблюдатель", callback_data=f"access_role:{steamid}:{telegram_id}:viewer")],
            [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"access:{steamid}")],
        ]
    )


def get_confirm_buttons(action: str, param: str) -> InlineKeyboardMarkup:
    """Confirmation buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{action}_confirm:{param}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"{action}_cancel:{param}"),
            ]
        ]
    )
