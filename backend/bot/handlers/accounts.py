"""Accounts management handler."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from backend.bot.keyboards import (
    get_accounts_list_buttons,
    get_account_buttons,
    get_confirm_buttons,
)
from backend.bot.messages import format_accounts_list, format_account_card
from backend.db import get_accounts, delete_account, get_user_role
from backend.account_mgr import send_command
from backend.config import settings

router = Router()


@router.message(F.text == "📊 Аккаунты")
@router.callback_query(F.data == "accounts")
async def show_accounts(event: Message | CallbackQuery):
    """Show list of all accounts with buttons."""
    user_id = event.from_user.id
    accounts = await get_accounts(settings.db_path)

    # Get roles for current user
    roles = {}
    for acc in accounts:
        role = await get_user_role(settings.db_path, acc["steamid"], user_id)
        if role:
            roles[acc["steamid"]] = role

    accessible = [a for a in accounts if a["steamid"] in roles]

    if not accessible:
        text = "📊 Аккаунты\n\nУ тебя нет аккаунтов.\nНажми ➕ Добавить чтобы добавить первый."
        keyboard = get_accounts_list_buttons()
        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        else:
            await event.message.edit_text(text, reply_markup=keyboard)
            await event.answer()
        return

    # Header message with per-account buttons
    header = f"📊 Аккаунты ({len(accessible)})\n\nВыбери аккаунт для управления:"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for acc in accessible:
        status_emoji = {"farming": "🟢", "online": "🟡", "offline": "🔴", "error": "⚠️"}.get(acc.get("status", "offline"), "⚪")
        hours = acc.get("total_hours", 0)
        builder.button(
            text=f"{status_emoji} {acc['login']} — {hours:.1f}ч",
            callback_data=f"account:{acc['steamid']}"
        )
    builder.button(text="➕ Добавить аккаунт", callback_data="add_account")
    builder.button(text="🔄 Обновить", callback_data="accounts_refresh")
    builder.button(text="◀️ Главная", callback_data="main")
    builder.adjust(1)

    if isinstance(event, Message):
        await event.answer(header, reply_markup=builder.as_markup())
    else:
        await event.message.edit_text(header, reply_markup=builder.as_markup())
        await event.answer()


@router.callback_query(F.data.startswith("account:"))
async def show_account_detail(callback: CallbackQuery, steamid: str = None):
    """Show single account details with all action buttons."""
    if steamid is None:
        steamid = callback.data.split(":")[1]

    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if not role:
        await callback.answer("❌ У тебя нет доступа к этому аккаунту", show_alert=True)
        return

    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)
    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    # Format account info
    status = account.get("status", "offline")
    status_emoji = {"farming": "🟢", "online": "🟡", "offline": "🔴", "error": "⚠️"}.get(status, "⚪")
    status_text = {"farming": "Фармит", "online": "Онлайн", "offline": "Офлайн", "error": "Ошибка"}.get(status, status)

    try:
        balance = float(str(account.get("wallet_balance", "0")).replace(",", ".") or "0")
    except (ValueError, TypeError):
        balance = 0.0

    role_badge = {"owner": "👤 Владелец", "manager": "🔧 Менеджер", "viewer": "👁 Наблюдатель"}.get(role, role)

    text = (
        f"{status_emoji} <b>{account['login']}</b> [{role_badge}]\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"├─ Уровень: {account.get('level', 0)} | Баланс: {balance:.0f}₽\n"
        f"├─ CS2: {account.get('total_hours', 0):.1f}ч\n"
        f"├─ Статус: {status_text}\n"
        f"└─ SteamID: <code>{steamid}</code>\n"
    )

    # Build buttons based on role
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    if role in ("owner", "manager"):
        if status in ("farming", "online"):
            builder.button(text="◼️ Стоп", callback_data=f"stop:{steamid}")
        else:
            builder.button(text="▶️ Старт", callback_data=f"start:{steamid}")
        builder.button(text="🎮 Игры", callback_data=f"games:{steamid}")

    # SteamGuard — show if has_mafile
    has_mafile = account.get("has_mafile", 0)
    if has_mafile:
        builder.button(text="🔑 Guard", callback_data=f"guard:{steamid}")

    if role == "owner":
        builder.button(text="👥 Доступы", callback_data=f"access:{steamid}")
        builder.button(text="🗑 Удалить", callback_data=f"delete:{steamid}")

    builder.button(text="🔄 Обновить", callback_data=f"refresh:{steamid}")
    builder.button(text="◀️ К списку", callback_data="accounts")
    builder.adjust(2)

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("stop:"))
async def stop_account(callback: CallbackQuery):
    """Stop account farming."""
    steamid = callback.data.split(":")[1]

    # Check access (manager or owner)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role not in ("owner", "manager"):
        await callback.answer("❌ У тебя нет прав на управление", show_alert=True)
        return

    # Get bot name
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    bot_name = account.get("asf_bot_name")

    # Send stop command to ASF
    try:
        await send_command(
            bot_name,
            f"stop {bot_name}",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )
        await callback.answer("✅ Остановлено")
    except Exception as e:
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)

    # Refresh account display
    await show_account_detail(callback, steamid)


@router.callback_query(F.data.startswith("start:"))
async def start_account(callback: CallbackQuery):
    """Start account farming."""
    steamid = callback.data.split(":")[1]

    # Check access (manager or owner)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role not in ("owner", "manager"):
        await callback.answer("❌ У тебя нет прав на управление", show_alert=True)
        return

    # Get bot name
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    bot_name = account.get("asf_bot_name")

    # Send start command to ASF
    try:
        await send_command(
            bot_name,
            f"start {bot_name}",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )
        await callback.answer("✅ Запущено")
    except Exception as e:
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)

    # Refresh account display
    await show_account_detail(callback, steamid)


@router.callback_query(F.data.startswith("delete:"))
async def delete_account_confirm(callback: CallbackQuery):
    """Confirm account deletion (only owner)."""
    steamid = callback.data.split(":")[1]

    # Check access (owner only)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role != "owner":
        await callback.answer("❌ Только владелец может удалить аккаунт", show_alert=True)
        return

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    text = (
        f"⚠️ Удалить аккаунт?\n\n"
        f"Аккаунт: {account['login']}\n"
        f"SteamID: {steamid}\n\n"
        f"Это действие нельзя отменить."
    )
    keyboard = get_confirm_buttons("delete", steamid)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def delete_account_execute(callback: CallbackQuery):
    """Execute account deletion."""
    steamid = callback.data.split(":")[1]

    # Check access (owner only)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role != "owner":
        await callback.answer("❌ Только владелец может удалить аккаунт", show_alert=True)
        return

    # Delete from DB
    await delete_account(settings.db_path, steamid)

    await callback.answer("✅ Аккаунт удалён")

    # Return to accounts list
    await show_accounts(callback)


@router.callback_query(F.data.startswith("delete_cancel:"))
async def delete_account_cancel(callback: CallbackQuery):
    """Cancel account deletion."""
    steamid = callback.data.split(":")[1]
    await callback.answer("❌ Отменено")

    # Return to account detail
    await show_account_detail(callback, steamid)


@router.callback_query(F.data.startswith("refresh:"))
async def refresh_account(callback: CallbackQuery):
    """Refresh account display."""
    steamid = callback.data.split(":")[1]
    await show_account_detail(callback, steamid)


@router.callback_query(F.data == "accounts_refresh")
async def refresh_accounts_list(callback: CallbackQuery):
    """Refresh accounts list."""
    await show_accounts(callback)
