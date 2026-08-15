"""Account management: add accounts with SteamGuard flow, game selection, maFile support."""
import base64
import hashlib
import hmac
import json
import logging
import shlex
import struct
import subprocess
import asyncio
import time
import re
from pathlib import Path

from .config import settings
from .asf_client import send_command

logger = logging.getLogger(__name__)

ASF_CONFIG_DIR = Path("/opt/steam-panel/asf-config")
ASF_CONTAINER  = "steam-panel-asf"
ASF_FIFO       = "/tmp/asf_in"


def _next_bot_name() -> str:
    existing = {f.stem for f in ASF_CONFIG_DIR.glob("bot*.json")}
    for i in range(1, 100):
        name = f"bot{i}"
        if name not in existing:
            return name
    raise RuntimeError("Too many bots")


def create_bot_config(botname: str, login: str, password: str,
                      games: list[int] | None = None) -> None:
    cfg = {
        "SteamLogin": login,
        "SteamPassword": password,
        "Enabled": True,
        "RemoteCommunication": 0,
        "GamesPlayedWhileIdle": games or [730],
    }
    path = ASF_CONFIG_DIR / f"{botname}.json"
    path.write_text(json.dumps(cfg, indent=2))
    logger.info("Created bot config: %s", path)


def create_bot_config_with_mafile(botname: str, login: str, password: str,
                                   mafile_content: bytes,
                                   games: list[int] | None = None) -> dict:
    """Save maFile and create bot config. Returns parsed maFile data."""
    try:
        mf = json.loads(mafile_content.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid maFile: not valid JSON")

    required = {"shared_secret", "identity_secret", "steamid", "account_name"}
    missing = required - set(mf.keys())
    if missing:
        raise ValueError(f"Invalid maFile: missing fields {missing}")

    # Write .maFile to asf-config (ASF will auto-import it)
    mafile_path = ASF_CONFIG_DIR / f"{botname}.maFile"
    mafile_path.write_bytes(mafile_content)

    cfg = {
        "SteamLogin": login,
        "SteamPassword": password,
        "Enabled": True,
        "RemoteCommunication": 0,
        "GamesPlayedWhileIdle": games or [730],
    }
    path = ASF_CONFIG_DIR / f"{botname}.json"
    path.write_text(json.dumps(cfg, indent=2))
    logger.info("Created bot config with maFile: %s", path)

    return {
        "steamid": str(mf.get("steamid", "")),
        "account_name": mf.get("account_name", login),
    }


def delete_bot_config(botname: str) -> None:
    path = ASF_CONFIG_DIR / f"{botname}.json"
    if path.exists():
        path.unlink()
    mafile_path = ASF_CONFIG_DIR / f"{botname}.maFile"
    if mafile_path.exists():
        mafile_path.unlink()


def get_steamguard_code(botname: str) -> dict:
    """Generate current Steam Guard TOTP code from maFile."""
    mafile_path = ASF_CONFIG_DIR / f"{botname}.maFile"
    if not mafile_path.exists():
        return {"error": "No maFile for this bot", "has_mafile": False}

    try:
        mf = json.loads(mafile_path.read_text())
        shared_secret = mf.get("shared_secret", "")
    except Exception as e:
        return {"error": str(e), "has_mafile": True}

    try:
        secret = base64.b64decode(shared_secret)
        timestamp = int(time.time())
        time_step = timestamp // 30
        msg = struct.pack(">Q", time_step)
        hmac_digest = hmac.new(secret, msg, hashlib.sha1).digest()
        offset = hmac_digest[-1] & 0x0F
        code_int = struct.unpack(">I", hmac_digest[offset:offset + 4])[0] & 0x7FFFFFFF

        chars = "23456789BCDFGHJKMNPQRTVWXY"
        code = ""
        for _ in range(5):
            code = chars[code_int % len(chars)] + code
            code_int //= len(chars)

        seconds_remaining = 30 - (timestamp % 30)
        return {"code": code, "seconds_remaining": seconds_remaining, "has_mafile": True}
    except Exception as e:
        return {"error": f"TOTP error: {e}", "has_mafile": True}


def inject_stdin(value: str) -> None:
    """Write value to ASF's named FIFO stdin pipe via docker exec."""
    safe = shlex.quote(value)
    try:
        subprocess.Popen(
            ["docker", "exec", ASF_CONTAINER, "sh", "-c",
             f"printf '%s\\n' {safe} > {ASF_FIFO}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Injected stdin: %r → %s", value, ASF_FIFO)
    except Exception as e:
        logger.error("inject_stdin failed: %s", e)


async def provide_2fa(botname: str, code: str) -> str:
    """Send 2FA/SteamGuard code to ASF via stdin FIFO (primary) or IPC (fallback)."""
    inject_stdin(code)
    try:
        return await send_command(
            botname,
            f"input TwoFactorAuthentication {botname} {code}",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )
    except Exception:
        return "sent via stdin"


async def switch_to_code(botname: str) -> str:
    """Tell ASF to use code instead of mobile push (send N to Y/N prompt)."""
    inject_stdin("N")
    try:
        return await send_command(
            botname, f"input Login {botname} N",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )
    except Exception:
        return "sent via stdin"


async def confirm_mobile_approval(botname: str) -> str:
    """Tell ASF the mobile approval was done (send Y)."""
    inject_stdin("Y")
    try:
        return await send_command(
            botname, f"input Login {botname} Y",
            ipc_url=settings.asf_ipc_url,
            ipc_password=settings.asf_ipc_password,
        )
    except Exception:
        return "sent via stdin"


async def set_games(botname: str, game_ids: list[int]) -> str:
    ids_str = " ".join(str(g) for g in game_ids)
    return await send_command(
        botname, f"play {botname} {ids_str}",
        ipc_url=settings.asf_ipc_url,
        ipc_password=settings.asf_ipc_password,
    )


def get_bot_login_status(botname: str) -> dict:
    """Parse recent Docker logs to determine bot login state."""
    try:
        result = subprocess.run(
            ["docker", "logs", "steam-panel-asf", "--tail", "120"],
            capture_output=True, text=True, timeout=5
        )
        raw = result.stdout + result.stderr
    except Exception as e:
        return {"status": "error", "message": str(e)}

    logs = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z=]', '', raw)
    logs = re.sub(r'\x1b[()][AB012]', '', logs)

    lines = [l for l in logs.splitlines() if botname in l]
    if not lines:
        return {"status": "connecting", "message": "Подключаемся..."}

    combined = "\n".join(lines).lower()
    recent   = "\n".join(lines[-6:]).lower()

    if "loggedon" in combined or "logged on" in combined or "idling" in combined:
        return {"status": "online", "message": "Вошли успешно!"}

    if "please check your steam mobile app" in combined or "login approval notification" in combined:
        return {"status": "need_mobile_approval",
                "message": "📱 Подтверди вход в приложении Steam или нажми «Ввести код»"}

    if any(kw in combined for kw in ("twofactorauthentication", "please enter", "steam guard",
                                     "two-factor", "enter the code", "provide code instead")):
        if "email" in combined and "code" in combined:
            return {"status": "need_email", "message": "📧 Введи код Steam Guard из email"}
        return {"status": "need_2fa", "message": "📱 Введи код из приложения Steam"}

    if "aborting" in combined or "3 times in a row" in combined:
        return {"status": "error", "message": "❌ Неверный логин или пароль"}
    if "ratelimitexceeded" in combined or "rate limit exceeded" in combined:
        return {"status": "error", "message": "⏳ Steam rate-limit — подожди ~25 минут и попробуй снова"}
    if "invalidpassword" in recent or "invalidcredentials" in recent:
        return {"status": "error", "message": "❌ Неверный пароль"}
    if "banned" in recent or "accountban" in recent:
        return {"status": "error", "message": "❌ Аккаунт заблокирован"}
    if "reconnecting" in recent:
        return {"status": "connecting", "message": "Переподключаемся..."}
    if "logging in" in recent or "loggingin" in recent:
        return {"status": "connecting", "message": "Входим..."}
    if "connected to steam" in recent:
        return {"status": "connecting", "message": "Подключились, проверяем пароль..."}

    return {"status": "connecting", "message": "Ожидаем ответа Steam..."}
