import logging
import aiohttp

logger = logging.getLogger(__name__)


async def send_command(bot_name: str, command: str, *,
                       ipc_url: str, ipc_password: str) -> str:
    """Send a command to ASF IPC. Returns Result text or raises on error."""
    url = f"{ipc_url}/Api/Command"
    headers = {"Authentication": ipc_password, "Content-Type": "application/json"}
    payload = {"Command": f"{bot_name} {command}" if bot_name else command}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 403:
                    raise PermissionError("ASF IPC auth failed (403) — check ASF_IPC_PASSWORD")
                if resp.status != 200:
                    logger.error("ASF returned status %d", resp.status)
                    return "Ошибка подключения к ASF"
                data = await resp.json()
                result = data.get("Result", "")
                logger.debug("ASF command %r → %s", command, result[:100])
                return result
    except (aiohttp.ClientError, TimeoutError, ConnectionError) as e:
        logger.error("ASF connection error: %s", e)
        return "⚠️ ASF недоступен. Проверь что контейнер steam-panel-asf запущен."


async def get_bot_status(bot_name: str, *,
                         ipc_url: str, ipc_password: str) -> dict:
    """Fetch bot status JSON from /Api/Bot/{botName}."""
    url = f"{ipc_url}/Api/Bot/{bot_name}"
    headers = {"Authentication": ipc_password}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 403:
                    raise PermissionError("ASF IPC auth failed (403)")
                if resp.status != 200:
                    return {}
                data = await resp.json()
                # ASF returns {"Result": {botName: {...}}}
                bots = data.get("Result", {})
                return bots.get(bot_name, {})
    except (aiohttp.ClientError, TimeoutError, ConnectionError) as e:
        logger.error("ASF status fetch error: %s", e)
        return {}
