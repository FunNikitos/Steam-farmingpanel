"""Add account handler with FSM."""
import json
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.bot.keyboards import get_add_account_method, get_back_to_main
from backend.db import add_account, get_accounts
from backend.config import settings
from backend.account_mgr import create_bot_config

router = Router()


class AddAccountStates(StatesGroup):
    """States for adding account."""
    choose_method = State()
    # Login/password flow
    enter_login = State()
    enter_password = State()
    enter_steamid = State()
    # maFile flow
    upload_mafile = State()
    mafile_password = State()


@router.message(F.text == "➕ Добавить")
@router.callback_query(F.data == "add_account")
async def add_account_start(event: Message | CallbackQuery, state: FSMContext):
    """Start add account flow."""
    text = (
        "➕ Добавить аккаунт\n\n"
        "Выбери способ:\n\n"
        "🔑 **Логин и пароль**\n"
        "├─ Нужен Steam Guard код при входе\n"
        "└─ Рекомендуется если нет maFile\n\n"
        "📁 **maFile**\n"
        "├─ Автоматический вход без кодов\n"
        "└─ Скачай с LZT или экспортируй из SDA"
    )
    keyboard = get_add_account_method()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()

    await state.set_state(AddAccountStates.choose_method)


@router.callback_query(F.data == "add_login", AddAccountStates.choose_method)
async def add_via_login_start(callback: CallbackQuery, state: FSMContext):
    """Start login/password flow."""
    await callback.message.edit_text(
        "🔑 Добавление через логин\n\n"
        "**Шаг 1/4:** Введи логин Steam\n\n"
        "Отправь сообщением ниже ⬇️"
    )
    await callback.answer()
    await state.set_state(AddAccountStates.enter_login)


@router.message(AddAccountStates.enter_login)
async def add_via_login_get_login(message: Message, state: FSMContext):
    """Receive login."""
    login = message.text.strip()

    # Check if already exists
    accounts = await get_accounts(settings.db_path)
    if any(a["login"] == login for a in accounts):
        await message.answer(
            f"⚠️ Аккаунт {login} уже добавлен\n\n"
            "Попробуй другой логин или нажми /start"
        )
        await state.clear()
        return

    await state.update_data(login=login)
    await message.answer(
        f"✅ Логин: {login}\n\n"
        f"**Шаг 2/4:** Введи пароль Steam"
    )
    await state.set_state(AddAccountStates.enter_password)


@router.message(AddAccountStates.enter_password)
async def add_via_login_get_password(message: Message, state: FSMContext):
    """Receive password."""
    password = message.text.strip()

    # Delete user's message with password
    try:
        await message.delete()
    except Exception:
        pass

    await state.update_data(password=password)

    data = await state.get_data()
    login = data["login"]

    await message.answer(
        f"✅ Пароль сохранён\n\n"
        f"**Шаг 3/4:** Введи SteamID64\n\n"
        f"💡 Как узнать SteamID:\n"
        f"1. Открой профиль в Steam\n"
        f"2. Скопируй ссылку (steamcommunity.com/profiles/XXXXXX)\n"
        f"3. Числа после /profiles/ — это SteamID\n\n"
        f"Или нажми /skip если не знаешь\n"
        f"(SteamID нужен только для статистики)"
    )
    await state.set_state(AddAccountStates.enter_steamid)


@router.message(AddAccountStates.enter_steamid)
async def add_via_login_get_steamid(message: Message, state: FSMContext):
    """Receive SteamID or skip."""
    steamid_input = message.text.strip()

    # Allow skip
    if steamid_input.lower() in ("/skip", "skip", "пропустить"):
        steamid = None
    else:
        # Validate SteamID format
        if not steamid_input.isdigit() or len(steamid_input) != 17:
            await message.answer(
                "⚠️ Неверный формат SteamID\n\n"
                "Должно быть 17 цифр, например:\n"
                "76561199563609590\n\n"
                "Попробуй ещё раз или нажми /skip"
            )
            return
        steamid = steamid_input

    data = await state.get_data()
    login = data["login"]
    password = data["password"]

    # Get next bot number
    accounts = await get_accounts(settings.db_path)
    bot_num = len(accounts) + 1
    bot_name = f"bot{bot_num}"

    await message.answer(
        f"⏳ Создаю конфиг для {login}...\n\n"
        f"Bot name: {bot_name}"
    )

    # Create ASF bot config (without maFile)
    try:
        config_path = Path(settings.asf_config_path) / f"{bot_name}.json"
        config = {
            "SteamLogin": login,
            "SteamPassword": password,
            "Enabled": True,
            "GamesPlayedWhileIdle": [730],  # CS2 by default
        }

        config_path.write_text(json.dumps(config, indent=2))

        # Add to database
        await add_account(
            db_path=settings.db_path,
            steamid=steamid or f"temp_{bot_num}",
            login=login,
            asf_bot_name=bot_name,
            owner_id=message.from_user.id,
            has_mafile=False,
        )

        await message.answer(
            f"✅ Аккаунт добавлен!\n\n"
            f"Логин: {login}\n"
            f"Bot: {bot_name}\n"
            f"Статус: Ожидает первого входа\n\n"
            f"⚠️ **Важно:**\n"
            f"При первом входе ASF запросит Steam Guard код.\n"
            f"Следи за логами ASF и введи код когда потребуется:\n\n"
            f"<code>docker compose logs -f asf</code>\n\n"
            f"Затем используй команду:\n"
            f"<code>docker exec steam-panel-asf asf 2fa {bot_name} CODE</code>",
            reply_markup=get_back_to_main(),
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка создания конфига:\n{e}",
            reply_markup=get_back_to_main(),
        )

    await state.clear()


@router.callback_query(F.data == "add_mafile", AddAccountStates.choose_method)
async def add_via_mafile_start(callback: CallbackQuery, state: FSMContext):
    """Start maFile upload flow."""
    await callback.message.edit_text(
        "📁 Добавление через maFile\n\n"
        "**Шаг 1/2:** Загрузи .maFile файл\n\n"
        "💡 Где взять maFile:\n"
        "• Скачать с LZT при покупке аккаунта\n"
        "• Экспортировать из SDA (Steam Desktop Authenticator)\n"
        "• Извлечь из WinAuth или других 2FA приложений\n\n"
        "Отправь файл документом ⬇️"
    )
    await callback.answer()
    await state.set_state(AddAccountStates.upload_mafile)


@router.message(AddAccountStates.upload_mafile, F.document)
async def add_via_mafile_receive_file(message: Message, state: FSMContext):
    """Receive maFile document."""
    document = message.document

    # Check file extension (case-insensitive)
    if not document.file_name.lower().endswith(".mafile"):
        await message.answer(
            "⚠️ Файл должен иметь расширение .maFile\n\n"
            "Попробуй ещё раз или нажми /start для отмены"
        )
        return

    # Download file
    try:
        file = await message.bot.download(document)
        content = file.read().decode("utf-8")
        mafile_data = json.loads(content)

        # Validate maFile structure
        required_fields = ["shared_secret", "identity_secret", "account_name"]
        if not all(field in mafile_data for field in required_fields):
            await message.answer(
                "⚠️ Неверный формат maFile\n\n"
                "Файл должен содержать: shared_secret, identity_secret, account_name"
            )
            return

        login = mafile_data.get("account_name")
        steamid = mafile_data.get("steamid")

        # Check if already exists
        accounts = await get_accounts(settings.db_path)
        if any(a["login"] == login for a in accounts):
            await message.answer(
                f"⚠️ Аккаунт {login} уже добавлен\n\n"
                "Удали старый или используй другой maFile"
            )
            await state.clear()
            return

        # Save maFile content and metadata
        await state.update_data(
            mafile_content=content,
            mafile_data=mafile_data,
            login=login,
            steamid=str(steamid) if steamid else None,
        )

        await message.answer(
            f"✅ maFile загружен\n\n"
            f"Логин: {login}\n"
            f"SteamID: {steamid or 'не указан'}\n\n"
            f"**Шаг 2/2:** Введи пароль Steam для этого аккаунта"
        )
        await state.set_state(AddAccountStates.mafile_password)

    except json.JSONDecodeError:
        await message.answer(
            "❌ Файл повреждён или не является JSON\n\n"
            "Проверь файл и попробуй ещё раз"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка обработки файла:\n{e}")


@router.message(AddAccountStates.mafile_password)
async def add_via_mafile_get_password(message: Message, state: FSMContext):
    """Receive password for maFile account."""
    password = message.text.strip()

    # Delete user's message with password
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    mafile_content = data["mafile_content"]
    mafile_data = data["mafile_data"]
    login = data["login"]
    steamid = data.get("steamid")

    # Get next bot number
    accounts = await get_accounts(settings.db_path)
    bot_num = len(accounts) + 1
    bot_name = f"bot{bot_num}"

    await message.answer(
        f"⏳ Создаю конфиг с maFile для {login}...\n\n"
        f"Bot name: {bot_name}"
    )

    try:
        config_dir = Path(settings.asf_config_path)
        config_dir.mkdir(exist_ok=True)

        # Save maFile
        mafile_path = config_dir / f"{bot_name}.maFile"
        mafile_path.write_text(mafile_content)

        # Create bot config with maFile
        config_path = config_dir / f"{bot_name}.json"
        config = {
            "SteamLogin": login,
            "SteamPassword": password,
            "Enabled": True,
            "GamesPlayedWhileIdle": [730],
        }
        config_path.write_text(json.dumps(config, indent=2))

        # Add to database
        await add_account(
            db_path=settings.db_path,
            steamid=steamid or f"temp_{bot_num}",
            login=login,
            asf_bot_name=bot_name,
            owner_id=message.from_user.id,
            has_mafile=True,
        )

        await message.answer(
            f"✅ Аккаунт добавлен через maFile!\n\n"
            f"Логин: {login}\n"
            f"Bot: {bot_name}\n"
            f"SteamID: {steamid or 'авто'}\n"
            f"🔑 SteamGuard: доступен\n\n"
            f"ASF залогинится автоматически.\n"
            f"Проверь статус через несколько секунд.",
            reply_markup=get_back_to_main(),
        )

        # Trigger ASF reload (send via IPC or restart container)
        # TODO: implement ASF bot reload via IPC

    except Exception as e:
        await message.answer(
            f"❌ Ошибка создания конфига:\n{e}",
            reply_markup=get_back_to_main(),
        )

    await state.clear()


@router.message(F.text == "/start", ~F.state(None))
@router.message(F.text == "/cancel", ~F.state(None))
async def cancel_add_account(message: Message, state: FSMContext):
    """Cancel add account flow."""
    await state.clear()
    await message.answer(
        "❌ Добавление аккаунта отменено",
        reply_markup=get_back_to_main(),
    )
