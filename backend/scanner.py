"""Steam Store scanners: giveaways and cheap card-farming deals."""
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

GIVEAWAY_URL = (
    "https://store.steampowered.com/search/results/"
    "?filter=free_to_keep&json=1&count=50"
)
# featuredcategories returns real RUB prices with discount info
FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/?cc=ru&l=russian"
# appdetails endpoint for checking trading cards (category 29)
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails/?appids={appid}&cc=ru&filters=price_overview,categories"

# Known games with trading cards (appid set) — used as fallback
KNOWN_CARD_GAMES = {
    440, 730, 570, 578080, 252950, 105600, 1172470, 1551360,
    359550, 413150, 292030, 271590, 548430, 374320, 227300,
    8930, 32440, 4000, 49520, 72850, 220, 380, 550, 620,
    40800, 400, 17520, 24240, 22380, 237110, 304930,
}


def parse_giveaway_items(items: list[dict]) -> list[dict]:
    """Return games that were paid (initial > 0) and are now free (final == 0)."""
    result = []
    for item in items:
        price = item.get("price_overview") or {}
        initial = price.get("initial", 0)
        final = price.get("final", 0)
        if initial > 0 and final == 0:
            result.append({
                "appid": str(item["appid"]),
                "name": item["name"],
                "license_type": "app",
            })
    return result


def parse_deal_items(items: list[dict], *, max_price_rub: float,
                     min_discount: int) -> list[dict]:
    """Parse featured/specials items for cheap card-farming deals."""
    result = []
    for item in items:
        if item.get("type") != 0:  # 0 = app
            continue
        final_price = (item.get("final_price") or 0) / 100.0
        original_price = (item.get("original_price") or 0) / 100.0
        discount = item.get("discount_percent") or 0
        appid = item.get("id", 0)

        if final_price <= max_price_rub and discount >= min_discount and appid:
            result.append({
                "appid": str(appid),
                "name": item.get("name", str(appid)),
                "price_rub": final_price,
                "original_rub": original_price,
                "discount_pct": discount,
                # Mark as having cards if in known list; appdetails check is expensive
                "card_count": 1 if appid in KNOWN_CARD_GAMES else 0,
            })
    return result


async def _fetch_json(url: str) -> dict:
    for attempt in range(2):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    r.raise_for_status()
                    return await r.json()
        except Exception as e:
            if attempt == 0:
                logger.warning("Scanner fetch failed (%s), retrying in 5s...", e)
                await asyncio.sleep(5)
            else:
                logger.error("Scanner fetch failed after retry: %s", e)
    return {}


async def _check_has_cards(appid: int) -> bool:
    """Check if a game has trading cards via appdetails API."""
    try:
        data = await _fetch_json(APPDETAILS_URL.format(appid=appid))
        info = data.get(str(appid), {}).get("data", {})
        cats = [c.get("id") for c in info.get("categories", [])]
        return 29 in cats
    except Exception:
        return False


async def scan_giveaways() -> list[dict]:
    """Fetch and parse free-to-keep games from Steam Store."""
    data = await _fetch_json(GIVEAWAY_URL)
    raw = data.get("items") or data.get("results") or []
    return parse_giveaway_items(raw)


async def scan_deals(*, max_price_rub: float = 300.0,
                     min_discount: int = 20) -> list[dict]:
    """
    Fetch cheap games on sale from Steam featuredcategories (RUB prices).
    Uses higher price cap and lower discount threshold to return more results.
    """
    data = await _fetch_json(FEATURED_URL)

    # Collect items from all sections
    items: list[dict] = []
    for section_key in ("specials", "top_sellers", "new_releases", "coming_soon"):
        section = data.get(section_key, {})
        items.extend(section.get("items", []))

    # Deduplicate by appid
    seen: set[int] = set()
    unique: list[dict] = []
    for it in items:
        aid = it.get("id", 0)
        if aid and aid not in seen:
            seen.add(aid)
            unique.append(it)

    # Parse with wider filters
    deals = parse_deal_items(unique, max_price_rub=max_price_rub,
                             min_discount=min_discount)

    # For games not in known list, check top 15 cheapest for trading cards
    unknown = [d for d in deals if d["card_count"] == 0][:15]
    for deal in unknown:
        has = await _check_has_cards(int(deal["appid"]))
        deal["card_count"] = 1 if has else 0

    # Return all discounted games (show everything, let user decide)
    return sorted(deals, key=lambda x: x["price_rub"])
