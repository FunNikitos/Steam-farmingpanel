"""SteamGuard handler."""
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from backend.bot.keyboards import get_steamguard_buttons
from backend.bot.messages import format_steamguard_code
from backend.db import get_user_role, get_accounts
from backend.account_mgr import get_steamguard_code, confirm_all_trades
from backend.config import settings

router = Router()


@router.callback_query(F.data.startswith("guard:"))
async def show_steamguard(callback: CallbackQuery, bot: Bot):
    """Show SteamGuard code with auto-refresh."""
    steamid = callback.data.split(":")[1]

    # Check access (all roles can see guard)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if not role:
        await callback.answer("❌ У тебя нет доступа к этому аккаунту", show_alert=True)
        return

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    if not account.get("has_mafile"):
        await callback.answer("❌ У аккаунта нет maFile", show_alert=True)
        return

    login = account["login"]
    bot_name = account.get("asf_bot_name")

    # Initial code display
    try:
        code_data = get_steamguard_code(bot_name)
        text = f"🔑 Steam Guard — {login}\n\n" + format_steamguard_code(code_data)
        keyboard = get_steamguard_buttons(steamid)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

        # Start auto-refresh loop
        asyncio.create_task(
            steamguard_refresh_loop(
                bot=bot,
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                bot_name=bot_name,
                login=login,
                steamid=steamid,
            )
        )

    except Exception as e:
        await callback.answer(f"⚠️ Ошибка получения кода: {e}", show_alert=True)


async def steamguard_refresh_loop(
    bot: Bot,
    chat_id: int,
    message_id: int,
    bot_name: str,
    login: str,
    steamid: str,
):
    """Auto-refresh SteamGuard code every 5 seconds."""
    for _ in range(6):  # 30 seconds / 5 = 6 iterations
        await asyncio.sleep(5)

        try:
            code_data = get_steamguard_code(bot_name)
            text = f"🔑 Steam Guard — {login}\n\n" + format_steamguard_code(code_data)
            keyboard = get_steamguard_buttons(steamid)

            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard,
            )
        except Exception:
            # Message was deleted or edited by user
            break


@router.callback_query(F.data.startswith("sda:"))
async def confirm_sda(callback: CallbackQuery):
    """Confirm all SDA trades/market transactions."""
    steamid = callback.data.split(":")[1]

    # Check access (manager or owner)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role not in ("owner", "manager"):
        await callback.answer("❌ У тебя нет прав на управление", show_alert=True)
        return

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    bot_name = account.get("asf_bot_name")

    # Send confirmation command
    try:
        result = await confirm_all_trades(
            bot_name,
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )

        if result and "success" in result.lower():
            await callback.answer("✅ Подтверждения отправлены", show_alert=True)
        elif result and ("no" in result.lower() or "nothing" in result.lower()):
            await callback.answer("ℹ️ Нет ожидающих подтверждений", show_alert=True)
        else:
            await callback.answer("✅ Команда отправлена в ASF", show_alert=True)

    except Exception as e:
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)
