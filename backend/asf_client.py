import logging
import asyncio
import subprocess

logger = logging.getLogger(__name__)


async def send_command(bot_name: str, command: str, *,
                       ipc_url: str, ipc_password: str) -> str:
    """Send a command to ASF via docker exec stdin pipe (IPC broken)."""
    # Use docker exec to send command via stdin
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", "-i", "steam-panel-asf", "sh", "-c",
            f"echo '{command}' > /tmp/asf_in",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

        if proc.returncode != 0:
            logger.error("ASF command failed: %s", stderr.decode())
            return ""

        # Wait a bit for ASF to process
        await asyncio.sleep(1)

        # Get logs to see result
        log_proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", "20", "steam-panel-asf",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logs, _ = await asyncio.wait_for(log_proc.communicate(), timeout=5)
        result = logs.decode()

        logger.debug("ASF command %r sent via stdin", command)
        return result
    except Exception as e:
        logger.error("ASF command error: %s", e)
        return ""


async def get_bot_status(bot_name: str, *,
                         ipc_url: str, ipc_password: str) -> dict:
    """Fetch bot status - returns mock data since IPC is broken."""
    # Return minimal mock data for now
    return {
        "Nickname": bot_name,
        "SteamID": 0,
        "WalletBalance": 0,
        "WalletCurrency": 0,
        "IsPlayingPossible": False,
    }
