"""Giveaways handler."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from backend.bot.keyboards import get_giveaways_buttons
from backend.bot.messages import format_giveaways_list
from backend.db import get_active_giveaways, get_accounts
from backend.account_mgr import send_command
from backend.config import settings

router = Router()


@router.message(F.text == "🎁 Раздачи")
@router.callback_query(F.data == "giveaways")
async def show_giveaways(event: Message | CallbackQuery):
    """Show list of active giveaways."""
    giveaways = await get_active_giveaways(settings.db_path)
    text = format_giveaways_list(giveaways)
    keyboard = get_giveaways_buttons()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data == "giveaways_refresh")
async def refresh_giveaways(callback: CallbackQuery):
    """Refresh giveaways list."""
    await callback.answer("🔄 Обновляем...")

    # Trigger manual scan
    from backend.scheduler import job_scan_giveaways
    await job_scan_giveaways()

    # Show updated list
    await show_giveaways(callback)


@router.callback_query(F.data.startswith("claim_all:"))
async def claim_giveaway_all(callback: CallbackQuery):
    """Claim giveaway on all accounts."""
    appid = callback.data.split(":")[1]

    await callback.answer("⏳ Добавляем на все аккаунты...")

    # Get all accounts
    accounts = await get_accounts(settings.db_path)

    success_count = 0
    for account in accounts:
        bot_name = account.get("asf_bot_name")
        if not bot_name:
            continue

        try:
            # Send addlicense command to ASF
            await send_command(
                bot_name,
                f"addlicense {bot_name} a/{appid}",
                ipc_url=settings.asf_ipc_url,
                ipc_password=settings.asf_ipc_password,
            )
            success_count += 1
        except Exception:
            continue

    if success_count > 0:
        await callback.message.edit_text(
            f"✅ Раздача добавлена!\n\n"
            f"Активировано на {success_count}/{len(accounts)} аккаунтов\n"
            f"AppID: {appid}",
            reply_markup=get_giveaways_buttons(),
        )
    else:
        await callback.message.edit_text(
            f"⚠️ Не удалось добавить раздачу\n\n"
            f"Проверь что ASF работает",
            reply_markup=get_giveaways_buttons(),
        )
