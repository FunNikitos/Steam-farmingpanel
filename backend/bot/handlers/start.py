"""Start handler and main menu."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from backend.bot.keyboards import get_main_menu, get_back_to_main
from backend.bot.messages import format_summary
from backend.db import get_accounts
from backend.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    # Check if user is authorized
    if message.from_user.id != settings.telegram_user_id:
        await message.answer(
            "⚠️ У тебя нет доступа к этому боту.\n\n"
            "Это приватный бот для управления Steam аккаунтами."
        )
        return

    # Get accounts summary
    accounts = await get_accounts(settings.db_path)
    online = sum(1 for a in accounts if a["status"] in ("farming", "online"))

    summary = format_summary({
        "online": online,
        "total": len(accounts),
        "hours_week": sum(a.get("total_hours", 0) for a in accounts),
        "avg_level": sum(a.get("level", 0) for a in accounts) / len(accounts) if accounts else 0,
    })

    await message.answer(
        summary,
        reply_markup=get_main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
🎮 **Steam Panel Bot**

**Основные команды:**
• /start — главное меню
• /accounts — список аккаунтов
• /add — добавить аккаунт
• /deals — дешёвые игры
• /giveaways — раздачи
• /stats — статистика
• /help — эта справка

**Кнопки:**
Используй кнопки меню для быстрого доступа ко всем функциям.

**Управление аккаунтами:**
• ◼️ Стоп / ▶️ Старт — остановить/запустить фарм
• 🎮 Игры — выбрать игры для фарма
• 🔑 Guard — SteamGuard код + подтверждение SDA
• 👥 Доступы — выдать доступ другим пользователям

**Система доступов:**
• 👤 Менеджер — может управлять аккаунтом
• 👁 Наблюдатель — только просмотр

**Поддержка:**
GitHub: https://github.com/yourusername/steam-panel-bot
"""
    await message.answer(help_text)


@router.callback_query(F.data == "main")
async def callback_main(callback: CallbackQuery):
    """Handle back to main menu."""
    accounts = await get_accounts(settings.db_path)
    online = sum(1 for a in accounts if a["status"] in ("farming", "online"))

    summary = format_summary({
        "online": online,
        "total": len(accounts),
        "hours_week": sum(a.get("total_hours", 0) for a in accounts),
        "avg_level": sum(a.get("level", 0) for a in accounts) / len(accounts) if accounts else 0,
    })

    await callback.message.edit_text(
        summary,
        reply_markup=get_back_to_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """No-op callback (for disabled buttons)."""
    await callback.answer()
