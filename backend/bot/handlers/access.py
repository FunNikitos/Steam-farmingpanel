"""Access control handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.bot.keyboards import (
    get_access_list_buttons,
    get_access_user_buttons,
    get_access_role_buttons,
    get_confirm_buttons,
)
from backend.bot.messages import format_access_list
from backend.db import (
    get_user_role,
    get_accounts,
    grant_access,
    revoke_access,
    get_account_accesses,
)
from backend.config import settings

router = Router()


class AccessStates(StatesGroup):
    """States for access management."""
    enter_telegram_id = State()


@router.callback_query(F.data.startswith("access:"))
async def show_access_list(callback: CallbackQuery):
    """Show list of users with access to account."""
    steamid = callback.data.split(":")[1]

    # Check access (owner only)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role != "owner":
        await callback.answer("❌ Только владелец может управлять доступами", show_alert=True)
        return

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    # Get accesses
    accesses = await get_account_accesses(settings.db_path, steamid)

    # Format message
    owner_name = "Ты"
    owner_id = account.get("owner_id", callback.from_user.id)
    text = format_access_list(accesses, owner_name, owner_id)
    text = f"👥 Доступы — {account['login']}\n\n" + text

    # Build keyboard with user buttons
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    for acc in accesses:
        role_emoji = {"manager": "👤", "viewer": "👁"}
        emoji = role_emoji.get(acc["role"], "👤")
        builder.button(
            text=f"{emoji} {acc['telegram_id']}",
            callback_data=f"access_user:{steamid}:{acc['telegram_id']}"
        )

    builder.button(
        text="➕ Добавить пользователя",
        callback_data=f"access_add:{steamid}"
    )
    builder.button(
        text="◀️ К аккаунту",
        callback_data=f"account:{steamid}"
    )

    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("access_add:"))
async def access_add_start(callback: CallbackQuery, state: FSMContext):
    """Start adding user access."""
    steamid = callback.data.split(":")[1]

    await state.update_data(steamid=steamid)
    await state.set_state(AccessStates.enter_telegram_id)

    await callback.message.edit_text(
        "➕ Выдать доступ\n\n"
        "Отправь Telegram ID пользователя\n\n"
        "💡 Как узнать ID:\n"
        "1. Попроси пользователя написать @userinfobot\n"
        "2. Скопируй его ID (число)\n\n"
        "Отправь ID сообщением ⬇️"
    )
    await callback.answer()


@router.message(AccessStates.enter_telegram_id)
async def access_add_get_id(message: Message, state: FSMContext):
    """Receive telegram ID."""
    telegram_id_str = message.text.strip()

    if not telegram_id_str.isdigit():
        await message.answer(
            "⚠️ ID должен быть числом\n\n"
            "Попробуй ещё раз или нажми /cancel"
        )
        return

    telegram_id = int(telegram_id_str)
    data = await state.get_data()
    steamid = data["steamid"]

    # Check if user already has access
    accesses = await get_account_accesses(settings.db_path, steamid)
    if any(a["telegram_id"] == telegram_id for a in accesses):
        await message.answer(
            f"⚠️ Пользователь {telegram_id} уже имеет доступ\n\n"
            f"Используй «Изменить роль» в списке доступов"
        )
        await state.clear()
        return

    await state.update_data(telegram_id=telegram_id)

    # Show role selection
    text = (
        f"✅ ID получен: {telegram_id}\n\n"
        f"Выбери уровень доступа:\n\n"
        f"👤 **Менеджер**\n"
        f"├─ Может: запускать/останавливать, менять игры, SteamGuard\n"
        f"└─ Не может: удалять, управлять доступами\n\n"
        f"👁 **Наблюдатель**\n"
        f"└─ Может: только смотреть статистику"
    )
    keyboard = get_access_role_buttons(steamid, telegram_id)

    await message.answer(text, reply_markup=keyboard)
    await state.clear()


@router.callback_query(F.data.startswith("access_role:"))
async def access_add_select_role(callback: CallbackQuery):
    """Grant access with selected role."""
    parts = callback.data.split(":")
    steamid = parts[1]
    telegram_id = int(parts[2])
    role = parts[3]  # manager or viewer

    # Grant access
    await grant_access(
        db_path=settings.db_path,
        steamid=steamid,
        telegram_id=telegram_id,
        role=role,
        granted_by=callback.from_user.id,
    )

    role_name = {"manager": "Менеджер", "viewer": "Наблюдатель"}[role]

    await callback.message.edit_text(
        f"✅ Доступ выдан!\n\n"
        f"Пользователь: {telegram_id}\n"
        f"Роль: {role_name}\n\n"
        f"Он получит уведомление при следующем запуске бота."
    )
    await callback.answer()

    # TODO: Send notification to user (if bot knows their chat_id)


@router.callback_query(F.data.startswith("access_user:"))
async def access_show_user(callback: CallbackQuery):
    """Show single user access details."""
    parts = callback.data.split(":")
    steamid = parts[1]
    telegram_id = int(parts[2])

    # Get access details
    accesses = await get_account_accesses(settings.db_path, steamid)
    user_access = next((a for a in accesses if a["telegram_id"] == telegram_id), None)

    if not user_access:
        await callback.answer("❌ Доступ не найден", show_alert=True)
        return

    role_name = {"manager": "Менеджер", "viewer": "Наблюдатель"}[user_access["role"]]
    role_perms = {
        "manager": "управлять, смотреть",
        "viewer": "только смотреть",
    }[user_access["role"]]

    text = (
        f"👤 Доступ пользователя\n\n"
        f"ID: {telegram_id}\n"
        f"Роль: {role_name}\n"
        f"Может: {role_perms}\n"
        f"Выдан: {user_access['granted_at'][:10]}"
    )
    keyboard = get_access_user_buttons(steamid, telegram_id)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("access_edit:"))
async def access_edit_role(callback: CallbackQuery):
    """Edit user role."""
    parts = callback.data.split(":")
    steamid = parts[1]
    telegram_id = int(parts[2])

    text = (
        f"📝 Изменить роль\n\n"
        f"Пользователь: {telegram_id}\n\n"
        f"Выбери новую роль:"
    )
    keyboard = get_access_role_buttons(steamid, telegram_id)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("access_revoke:"))
async def access_revoke_confirm(callback: CallbackQuery):
    """Confirm access revocation."""
    parts = callback.data.split(":")
    steamid = parts[1]
    telegram_id = int(parts[2])

    # Get access details
    accesses = await get_account_accesses(settings.db_path, steamid)
    user_access = next((a for a in accesses if a["telegram_id"] == telegram_id), None)

    if not user_access:
        await callback.answer("❌ Доступ не найден", show_alert=True)
        return

    role_name = {"manager": "Менеджер", "viewer": "Наблюдатель"}[user_access["role"]]

    text = (
        f"⚠️ Удалить доступ?\n\n"
        f"Пользователь: {telegram_id}\n"
        f"Роль: {role_name}\n\n"
        f"Он больше не сможет управлять этим аккаунтом."
    )
    keyboard = get_confirm_buttons("access_revoke_exec", f"{steamid}:{telegram_id}")

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("access_revoke_exec_confirm:"))
async def access_revoke_execute(callback: CallbackQuery):
    """Execute access revocation."""
    parts = callback.data.split(":")[1:]  # Remove action prefix
    steamid = parts[0]
    telegram_id = int(parts[1])

    # Revoke access
    await revoke_access(
        db_path=settings.db_path,
        steamid=steamid,
        telegram_id=telegram_id,
    )

    await callback.message.edit_text(
        f"✅ Доступ удалён\n\n"
        f"Пользователь {telegram_id} больше не имеет доступа к аккаунту."
    )
    await callback.answer()

    # TODO: Send notification to user


@router.callback_query(F.data.startswith("access_revoke_exec_cancel:"))
async def access_revoke_cancel(callback: CallbackQuery):
    """Cancel access revocation."""
    parts = callback.data.split(":")[1:]
    steamid = parts[0]
    telegram_id = int(parts[1])

    await callback.answer("❌ Отменено")

    # Return to user details
    callback.data = f"access_user:{steamid}:{telegram_id}"
    await access_show_user(callback)
