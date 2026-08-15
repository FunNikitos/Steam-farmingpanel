"""Games selection handler."""
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.db import get_user_role, get_accounts
from backend.account_mgr import send_command
from backend.config import settings

router = Router()


@router.callback_query(F.data.startswith("games:"))
async def show_games_list(callback: CallbackQuery):
    """Show games list for account."""
    steamid = callback.data.split(":")[1]

    # Check access (manager or owner)
    role = await get_user_role(settings.db_path, steamid, callback.from_user.id)
    if role not in ("owner", "manager"):
        await callback.answer("❌ У тебя нет прав на управление", show_alert=True)
        return

    await callback.answer("⏳ Загружаю игры...")

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    login = account["login"]

    # Fetch games from Steam API
    try:
        games = await fetch_owned_games(steamid)

        if not games:
            await callback.message.edit_text(
                f"🎮 {login} — Игры\n\n"
                f"⚠️ Не удалось загрузить список игр\n\n"
                f"Возможные причины:\n"
                f"• Профиль приватный\n"
                f"• Неверный SteamID\n"
                f"• Steam API недоступен",
            )
            return

        # Get currently playing games (from account state)
        current_games = account.get("games_playing", [730])  # Default CS2

        # Build keyboard with toggle buttons
        builder = InlineKeyboardBuilder()

        # Show first 10 games
        for game in games[:10]:
            appid = game["appid"]
            name = game["name"]
            hours = game.get("playtime_forever", 0) / 60

            # Check if selected
            is_selected = appid in current_games
            emoji = "✅" if is_selected else "⬜"

            builder.button(
                text=f"{emoji} {name} ({hours:.1f}ч)",
                callback_data=f"toggle_game:{steamid}:{appid}"
            )

        # Add "show more" if >10 games
        if len(games) > 10:
            builder.button(
                text=f"⬇️ Показать ещё {len(games) - 10}",
                callback_data=f"games_more:{steamid}"
            )

        # Action buttons
        builder.button(
            text="💾 Сохранить",
            callback_data=f"save_games:{steamid}"
        )
        builder.button(
            text="◀️ К аккаунту",
            callback_data=f"account:{steamid}"
        )

        builder.adjust(1)  # 1 button per row

        text = (
            f"🎮 {login} — Выбери игры\n\n"
            f"Текущие ({len(current_games)}):\n"
        )

        for appid in current_games:
            game = next((g for g in games if g["appid"] == appid), None)
            if game:
                text += f"✅ {game['name']}\n"

        text += f"\nДоступные ({len(games)}):\n"
        text += "Нажми на игру чтобы добавить/убрать"

        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка загрузки игр:\n{e}"
        )


@router.callback_query(F.data.startswith("toggle_game:"))
async def toggle_game_selection(callback: CallbackQuery):
    """Toggle game selection."""
    parts = callback.data.split(":")
    steamid = parts[1]
    appid = int(parts[2])

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    # Toggle game in selection
    current_games = account.get("games_playing", [730])

    if appid in current_games:
        current_games.remove(appid)
        await callback.answer("⬜ Убрано")
    else:
        current_games.append(appid)
        await callback.answer("✅ Добавлено")

    # Save to account state (in memory for now, will save on "save_games")
    account["games_playing"] = current_games

    # Refresh display
    callback.data = f"games:{steamid}"
    await show_games_list(callback)


@router.callback_query(F.data.startswith("save_games:"))
async def save_games_selection(callback: CallbackQuery):
    """Save and apply games selection."""
    steamid = callback.data.split(":")[1]

    # Get account
    accounts = await get_accounts(settings.db_path)
    account = next((a for a in accounts if a["steamid"] == steamid), None)

    if not account:
        await callback.answer("❌ Аккаунт не найден", show_alert=True)
        return

    bot_name = account.get("asf_bot_name")
    selected_games = account.get("games_playing", [730])

    await callback.answer("⏳ Применяю...")

    try:
        # Send play command to ASF
        games_str = ",".join(map(str, selected_games))
        await send_command(
            bot_name,
            f"play {bot_name} {games_str}",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )

        # Get game names for display
        games = await fetch_owned_games(steamid)
        game_names = []
        for appid in selected_games:
            game = next((g for g in games if g["appid"] == appid), None)
            if game:
                game_names.append(game["name"])

        await callback.message.edit_text(
            f"✅ Игры обновлены!\n\n"
            f"Теперь фармит:\n" +
            "\n".join(f"• {name}" for name in game_names[:5]) +
            (f"\n... и ещё {len(game_names) - 5}" if len(game_names) > 5 else "")
        )

        # TODO: Save to database (update account.games_playing field)

    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ Ошибка применения:\n{e}\n\n"
            f"Игры выбраны, но ASF не ответил.\n"
            f"Проверь что ASF запущен."
        )


async def fetch_owned_games(steamid: str) -> list[dict]:
    """Fetch owned games from Steam API."""
    url = (
        f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        f"?key={settings.steam_api_key}&steamid={steamid}"
        f"&include_played_free_games=1&include_appinfo=1"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
                games = data.get("response", {}).get("games", [])
                return games
    except Exception:
        return []
