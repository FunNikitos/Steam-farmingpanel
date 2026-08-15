"""Statistics handler."""
import io
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from backend.db import get_accounts, get_all_sessions
from backend.config import settings

router = Router()


@router.message(F.text == "📈 Статистика")
@router.callback_query(F.data == "stats")
async def show_statistics(event: Message | CallbackQuery):
    """Show statistics summary."""
    accounts = await get_accounts(settings.db_path)
    sessions = await get_all_sessions(settings.db_path, days=7)

    online = sum(1 for a in accounts if a["status"] in ("farming", "online"))
    total_hours = sum(a.get("total_hours", 0) for a in accounts)
    avg_level = sum(a.get("level", 0) for a in accounts) / len(accounts) if accounts else 0
    total_balance = sum(float(str(a.get("wallet_balance", "0")).replace(",", ".") or "0") for a in accounts)

    # Calculate weekly hours per account
    weekly_hours = {}
    for session in sessions:
        login = session.get("login", "unknown")
        if login not in weekly_hours:
            weekly_hours[login] = 0
        weekly_hours[login] += session.get("hours_delta", 0)

    text = (
        "📈 Статистика за 7 дней\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🟢 Онлайн: {online}/{len(accounts)}\n"
        f"⏱ Всего часов: {total_hours:.1f}ч\n"
        f"📊 Средний уровень: {avg_level:.1f}\n"
        f"💰 Баланс: {total_balance:.0f}₽\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📊 По аккаунтам:\n\n"
    )

    for account in accounts:
        login = account["login"]
        hours = account.get("total_hours", 0)
        week_hours = weekly_hours.get(login, 0)
        text += f"{login}: {hours:.1f}ч (+{week_hours:.1f}ч)\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 График часов", callback_data="graph")
    builder.button(text="◀️ Главная", callback_data="main")
    builder.adjust(1)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=builder.as_markup())
    else:
        await event.message.edit_text(text, reply_markup=builder.as_markup())
        await event.answer()


@router.callback_query(F.data == "graph")
async def show_graph(callback: CallbackQuery):
    """Generate and send hours graph."""
    await callback.answer("📊 Генерирую график...")

    try:
        # Get sessions data
        sessions = await get_all_sessions(settings.db_path, days=7)
        accounts = await get_accounts(settings.db_path)

        if not sessions:
            await callback.message.answer(
                "⚠️ Недостаточно данных для графика\n\n"
                "График будет доступен после первой синхронизации часов."
            )
            return

        # Prepare data for plotting
        dates = []
        data_by_account = {}

        # Initialize data structure
        for account in accounts:
            login = account["login"]
            data_by_account[login] = {}

        # Fill data
        for session in sessions:
            date = session["date"]
            login = session.get("login", "unknown")
            hours = session.get("hours_delta", 0)

            if login in data_by_account:
                data_by_account[login][date] = hours

            if date not in dates:
                dates.append(date)

        dates = sorted(dates)

        # Create plot
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')

        for login, data in data_by_account.items():
            hours_list = [data.get(date, 0) for date in dates]
            plt.plot(dates, hours_list, marker='o', label=login, linewidth=2)

        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Часы CS2', fontsize=12)
        plt.title('Часы CS2 за 7 дней', fontsize=14, fontweight='bold')
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#1a1a1a')
        buf.seek(0)
        plt.close()

        # Send image
        photo = BufferedInputFile(buf.read(), filename="hours_graph.png")

        summary = f"📈 График часов за 7 дней\n\n"
        for login, data in data_by_account.items():
            total = sum(data.values())
            summary += f"{login}: {total:.1f}ч\n"

        await callback.message.answer_photo(
            photo=photo,
            caption=summary
        )

    except Exception as e:
        await callback.message.answer(
            f"❌ Ошибка генерации графика:\n{e}"
        )
