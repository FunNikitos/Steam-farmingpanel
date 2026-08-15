"""Deals (cheap games) handler."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from backend.bot.keyboards import get_deals_buttons
from backend.bot.messages import format_deals_list
from backend.db import get_deals
from backend.config import settings

router = Router()


@router.message(F.text == "💎 Игры")
@router.callback_query(F.data == "deals")
async def show_deals(event: Message | CallbackQuery):
    """Show list of cheap games with cards."""
    deals = await get_deals(settings.db_path)
    text = format_deals_list(deals)
    keyboard = get_deals_buttons()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data == "deals_refresh")
async def refresh_deals(callback: CallbackQuery):
    """Refresh deals list."""
    await callback.answer("🔄 Обновляем...")

    # Trigger manual scan
    from backend.scheduler import job_scan_deals
    await job_scan_deals()

    # Show updated list
    await show_deals(callback)
