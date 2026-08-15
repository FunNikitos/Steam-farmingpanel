# backend/scheduler.py
import logging
from datetime import datetime, timezone
import pytz
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .db import (
    get_accounts, insert_giveaway, upsert_claim, get_claim,
    expire_giveaways, upsert_session, update_account,
    upsert_deal, delete_stale_deals
)
from .scanner import scan_giveaways, scan_deals
from .asf_client import send_command, get_bot_status

logger = logging.getLogger(__name__)
TZ = "Asia/Tokyo"


async def job_scan_giveaways() -> None:
    logger.info("job_scan_giveaways: starting")
    now = datetime.now(timezone.utc).isoformat()
    await expire_giveaways(settings.db_path, now)
    items = await scan_giveaways()
    accounts = [a for a in await get_accounts(settings.db_path) if a["enabled"]]
    for item in items:
        gw_id = await insert_giveaway(
            settings.db_path,
            appid=item["appid"],
            license_type=item["license_type"],
            name=item["name"],
            found_at=now,
        )
        claimed, failed = 0, 0
        for acc in accounts:
            existing = await get_claim(
                settings.db_path, giveaway_id=gw_id, steamid=acc["steamid"]
            )
            if existing and existing["status"] == "claimed":
                claimed += 1
                continue
            bot = acc["asf_bot_name"]
            cmd = f"addlicense {bot} {item['license_type']}/{item['appid']}"
            try:
                result = await send_command(
                    bot, cmd,
                    ipc_url=settings.asf_ipc_url,
                    ipc_password=settings.asf_ipc_password,
                )
                status = "claimed" if ("Activated" in result or "OK" in result) else "failed"
            except Exception as e:
                logger.error("addlicense failed for %s: %s", bot, e)
                status = "failed"
            await upsert_claim(
                settings.db_path,
                giveaway_id=gw_id,
                steamid=acc["steamid"],
                status=status,
                claimed_at=now,
            )
            if status == "claimed":
                claimed += 1
            else:
                failed += 1
        if settings.telegram_token:
            from .bot import send_alert
            await send_alert(
                f"🎮 {item['name']} — бесплатно! "
                f"Выдано на {claimed}/{len(accounts)} аккаунтов"
            )
    logger.info("job_scan_giveaways: done, %d items processed", len(items))


async def job_sync_hours() -> None:
    logger.info("job_sync_hours: starting")
    jst = pytz.timezone("Asia/Tokyo")
    today = datetime.now(jst).strftime("%Y-%m-%d")
    now_str = datetime.now(timezone.utc).isoformat()
    accounts = await get_accounts(settings.db_path)
    for acc in accounts:
        steamid = acc["steamid"]
        bot = acc["asf_bot_name"]
        # --- Steam Web API: CS2 playtime ---
        try:
            url = (
                f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
                f"?key={settings.steam_api_key}&steamid={steamid}"
                f"&include_played_free_games=1&include_appinfo=1"
            )
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    data = await r.json()
            games = data.get("response", {}).get("games", [])
            cs2 = next((g for g in games if g["appid"] == 730), None)
            if cs2:
                total_h = cs2["playtime_forever"] / 60.0
                prev_total = acc.get("total_hours") or 0.0
                delta = min(max(total_h - prev_total, 0.0), 2.0)
                await upsert_session(
                    settings.db_path, steamid=steamid, date=today, hours_delta=delta
                )
                await update_account(
                    settings.db_path, steamid, total_hours=total_h, updated_at=now_str
                )
        except Exception as e:
            logger.warning("Steam API hours sync failed for %s: %s", steamid, e)
        # --- Steam Level ---
        try:
            url = (
                f"https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/"
                f"?key={settings.steam_api_key}&steamid={steamid}"
            )
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    data = await r.json()
            level = data.get("response", {}).get("player_level", 0)
            await update_account(settings.db_path, steamid, level=level)
        except Exception as e:
            logger.warning("Steam level sync failed for %s: %s", steamid, e)
        # --- ASF IPC: wallet balance + status ---
        try:
            bot_data = await get_bot_status(
                bot,
                ipc_url=settings.asf_ipc_url,
                ipc_password=settings.asf_ipc_password,
            )
            wallet = str(bot_data.get("WalletBalance", "0.00"))
            status = "farming" if bot_data.get("IsPlayingPossible") else "online"
            await update_account(
                settings.db_path, steamid,
                wallet_balance=wallet, status=status
            )
        except Exception as e:
            logger.warning("ASF status sync failed for %s: %s", bot, e)
            await update_account(settings.db_path, steamid, status="error")
    logger.info("job_sync_hours: done")


async def job_scan_deals() -> None:
    logger.info("job_scan_deals: starting")
    now = datetime.now(timezone.utc).isoformat()
    items = await scan_deals(max_price_rub=100.0, min_discount=50)
    current_appids = [i["appid"] for i in items]
    await delete_stale_deals(settings.db_path, current_appids)
    for item in items:
        await upsert_deal(settings.db_path, found_at=now, **item)
    logger.info("job_scan_deals: %d deals saved", len(items))


def start_scheduler(app) -> None:
    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(
        job_scan_giveaways,
        CronTrigger.from_crontab(settings.scan_cron, timezone=TZ),
        id="scan_giveaways",
    )
    scheduler.add_job(
        job_sync_hours,
        CronTrigger.from_crontab(settings.sync_cron, timezone=TZ),
        id="sync_hours",
    )
    scheduler.add_job(
        job_scan_deals,
        CronTrigger.from_crontab(settings.deals_cron, timezone=TZ),
        id="scan_deals",
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started (TZ=%s)", TZ)
