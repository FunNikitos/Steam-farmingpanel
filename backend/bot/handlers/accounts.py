"""Accounts management handler."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

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
    """Show list of all accounts."""
    # Get user's accounts
    accounts = await get_accounts(settings.db_path)

    # Get roles for current user
    user_id = event.from_user.id
    roles = {}
    for acc in accounts:
        role = await get_user_role(settings.db_path, acc["steamid"], user_id)
        if role:
            roles[acc["steamid"]] = role

    # Filter only accessible accounts
    accessible = [a for a in accounts if a["steamid"] in roles]

    text = format_accounts_list(accessible, roles)
    keyboard = get_accounts_list_buttons()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data.startswith("account:"))
async def show_account_detail(callback: CallbackQuery):
    """Show single account details."""
    steamid = callback.data.split(":")[1]

    # Check access
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if not role:
        await callback.answer("❌ У тебя нет доступа к этому аккаунту", show_alert=True)
        return

    # Get account data
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    text = format_account_card(account, role)
    keyboard = get_account_buttons(steamid, role)

    await callback.message.edit_text(text, reply_markup=keyboard)
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
    await show_account_detail(callback)


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
    await show_account_detail(callback)


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
    callback.data = f"account:{steamid}"
    await show_account_detail(callback)


@router.callback_query(F.data.startswith("refresh:"))
async def refresh_account(callback: CallbackQuery):
    """Refresh account display."""
    steamid = callback.data.split(":")[1]
    callback.data = f"account:{steamid}"
    await show_account_detail(callback)


@router.callback_query(F.data == "accounts_refresh")
async def refresh_accounts_list(callback: CallbackQuery):
    """Refresh accounts list."""
    await show_accounts(callback)
