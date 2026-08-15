import aiosqlite
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    steamid TEXT PRIMARY KEY, login TEXT NOT NULL, asf_bot_name TEXT NOT NULL,
    status TEXT DEFAULT 'offline', total_hours REAL DEFAULT 0,
    level INTEGER DEFAULT 0, xp INTEGER DEFAULT 0,
    wallet_balance TEXT DEFAULT '0.00', enabled INTEGER DEFAULT 1,
    owner_id INTEGER, has_mafile INTEGER DEFAULT 0,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS account_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steamid TEXT NOT NULL,
    telegram_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('manager', 'viewer')),
    granted_by INTEGER NOT NULL,
    granted_at TEXT NOT NULL,
    FOREIGN KEY (steamid) REFERENCES accounts(steamid),
    UNIQUE(steamid, telegram_id)
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, steamid TEXT NOT NULL,
    date TEXT NOT NULL, hours_delta REAL DEFAULT 0, UNIQUE(steamid, date)
);
CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT, appid TEXT NOT NULL,
    license_type TEXT NOT NULL, name TEXT, found_at TEXT,
    deadline TEXT, status TEXT DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS claims (
    giveaway_id INTEGER NOT NULL, steamid TEXT NOT NULL,
    status TEXT DEFAULT 'pending', claimed_at TEXT,
    PRIMARY KEY (giveaway_id, steamid)
);
CREATE TABLE IF NOT EXISTS deals (
    appid TEXT PRIMARY KEY, name TEXT NOT NULL,
    price_rub REAL NOT NULL, original_rub REAL NOT NULL,
    discount_pct INTEGER NOT NULL, card_count INTEGER DEFAULT 0,
    found_at TEXT NOT NULL, expires_at TEXT, notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
"""

async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(SCHEMA)
        await conn.commit()

async def upsert_account(db_path: str, *, steamid: str, login: str, asf_bot_name: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT INTO accounts(steamid,login,asf_bot_name) VALUES(?,?,?) "
            "ON CONFLICT(steamid) DO UPDATE SET login=excluded.login, asf_bot_name=excluded.asf_bot_name",
            (steamid, login, asf_bot_name)
        )
        await conn.commit()

async def get_accounts(db_path: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM accounts")
        return [dict(r) for r in await cur.fetchall()]

_ACCOUNT_UPDATABLE = frozenset({
    "login", "asf_bot_name", "status", "total_hours",
    "level", "xp", "wallet_balance", "enabled", "updated_at",
})

async def update_account(db_path: str, steamid: str, **fields) -> None:
    if not fields:
        return
    unknown = set(fields) - _ACCOUNT_UPDATABLE
    if unknown:
        raise ValueError(f"update_account: unknown column(s): {unknown}")
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [steamid]
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(f"UPDATE accounts SET {cols} WHERE steamid=?", vals)
        await conn.commit()

async def upsert_session(db_path: str, *, steamid: str, date: str, hours_delta: float) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT INTO sessions(steamid,date,hours_delta) VALUES(?,?,?) "
            "ON CONFLICT(steamid,date) DO UPDATE SET hours_delta=excluded.hours_delta",
            (steamid, date, hours_delta)
        )
        await conn.commit()

async def get_sessions(db_path: str, *, steamid: str, days: int) -> list[dict]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM sessions WHERE steamid=? ORDER BY date DESC LIMIT ?",
            (steamid, days)
        )
        return [dict(r) for r in await cur.fetchall()]

async def get_all_sessions(db_path: str, days: int) -> list[dict]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT s.*, a.login FROM sessions s JOIN accounts a USING(steamid) "
            "WHERE s.date >= date('now', ? || ' days') "
            "ORDER BY s.date DESC",
            (f"-{days}",)
        )
        return [dict(r) for r in await cur.fetchall()]

async def insert_giveaway(db_path: str, *, appid: str, license_type: str,
                          name: str, found_at: str, deadline: str | None = None) -> int:
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            "INSERT INTO giveaways(appid,license_type,name,found_at,deadline) VALUES(?,?,?,?,?)",
            (appid, license_type, name, found_at, deadline)
        )
        await conn.commit()
        return cur.lastrowid

async def get_active_giveaways(db_path: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT g.*, COUNT(CASE WHEN c.status='claimed' THEN 1 END) as claimed_count, "
            "COUNT(CASE WHEN c.status='failed' THEN 1 END) as failed_count "
            "FROM giveaways g LEFT JOIN claims c ON g.id=c.giveaway_id "
            "WHERE g.status='active' GROUP BY g.id ORDER BY g.found_at DESC LIMIT 10"
        )
        return [dict(r) for r in await cur.fetchall()]

async def expire_giveaways(db_path: str, now: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE giveaways SET status='expired' WHERE deadline IS NOT NULL AND deadline < ? AND status='active'",
            (now,)
        )
        await conn.commit()

async def upsert_claim(db_path: str, *, giveaway_id: int, steamid: str,
                        status: str, claimed_at: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT INTO claims(giveaway_id,steamid,status,claimed_at) VALUES(?,?,?,?) "
            "ON CONFLICT(giveaway_id,steamid) DO UPDATE SET status=excluded.status, claimed_at=excluded.claimed_at",
            (giveaway_id, steamid, status, claimed_at)
        )
        await conn.commit()

async def get_claim(db_path: str, *, giveaway_id: int, steamid: str) -> dict | None:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM claims WHERE giveaway_id=? AND steamid=?", (giveaway_id, steamid)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

async def upsert_deal(db_path: str, *, appid: str, name: str, price_rub: float,
                       original_rub: float, discount_pct: int, card_count: int,
                       found_at: str, expires_at: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT INTO deals(appid,name,price_rub,original_rub,discount_pct,card_count,found_at,expires_at,notified) "
            "VALUES(?,?,?,?,?,?,?,?,0) ON CONFLICT(appid) DO UPDATE SET "
            "price_rub=excluded.price_rub, discount_pct=excluded.discount_pct, "
            "card_count=excluded.card_count, name=excluded.name",
            (appid, name, price_rub, original_rub, discount_pct, card_count, found_at, expires_at)
        )
        await conn.commit()

async def delete_stale_deals(db_path: str, current_appids: list[str]) -> None:
    if not current_appids:
        return
    placeholders = ",".join("?" * len(current_appids))
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(f"DELETE FROM deals WHERE appid NOT IN ({placeholders})", current_appids)
        await conn.commit()

async def get_deals(db_path: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM deals ORDER BY price_rub ASC")
        return [dict(r) for r in await cur.fetchall()]

async def create_auth_session(db_path: str, token: str, expires_at: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT INTO auth_sessions(token,created_at,expires_at) VALUES(?,?,?)",
            (token, now, expires_at)
        )
        await conn.commit()

async def validate_auth_session(db_path: str, token: str, now: str) -> bool:
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            "SELECT 1 FROM auth_sessions WHERE token=? AND expires_at > ?", (token, now)
        )
        return await cur.fetchone() is not None

async def delete_auth_session(db_path: str, token: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
        await conn.commit()


# ============================================
# Access Control Functions
# ============================================

async def add_account(
    db_path: str,
    *,
    steamid: str,
    login: str,
    asf_bot_name: str,
    owner_id: int,
    has_mafile: bool = False
) -> None:
    """Add new account with owner."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT INTO accounts(steamid, login, asf_bot_name, owner_id, has_mafile)
               VALUES(?, ?, ?, ?, ?)""",
            (steamid, login, asf_bot_name, owner_id, int(has_mafile))
        )
        await conn.commit()


async def delete_account(db_path: str, steamid: str) -> None:
    """Delete account and all related data."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("DELETE FROM accounts WHERE steamid=?", (steamid,))
        await conn.execute("DELETE FROM account_access WHERE steamid=?", (steamid,))
        await conn.execute("DELETE FROM sessions WHERE steamid=?", (steamid,))
        await conn.commit()


async def grant_access(
    db_path: str,
    steamid: str,
    telegram_id: int,
    role: str,
    granted_by: int
) -> None:
    """Grant access to account."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT OR REPLACE INTO account_access
               (steamid, telegram_id, role, granted_by, granted_at)
               VALUES (?, ?, ?, ?, ?)""",
            (steamid, telegram_id, role, granted_by, now)
        )
        await conn.commit()


async def revoke_access(db_path: str, steamid: str, telegram_id: int) -> None:
    """Revoke user access to account."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "DELETE FROM account_access WHERE steamid=? AND telegram_id=?",
            (steamid, telegram_id)
        )
        await conn.commit()


async def get_user_role(db_path: str, steamid: str, telegram_id: int) -> str | None:
    """Get user role for account (owner/manager/viewer/None)."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row

        # Check if owner
        cur = await conn.execute(
            "SELECT owner_id FROM accounts WHERE steamid=?",
            (steamid,)
        )
        row = await cur.fetchone()
        if row and row[0] == telegram_id:
            return "owner"

        # Check granted access
        cur = await conn.execute(
            "SELECT role FROM account_access WHERE steamid=? AND telegram_id=?",
            (steamid, telegram_id)
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def get_account_accesses(db_path: str, steamid: str) -> list[dict]:
    """Get all users with access to account."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """SELECT telegram_id, role, granted_by, granted_at
               FROM account_access
               WHERE steamid=?
               ORDER BY granted_at DESC""",
            (steamid,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_user_accounts(db_path: str, telegram_id: int) -> list[dict]:
    """Get all accounts accessible to user."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """SELECT DISTINCT a.*, aa.role
               FROM accounts a
               LEFT JOIN account_access aa ON a.steamid = aa.steamid
               WHERE a.owner_id = ? OR aa.telegram_id = ?
               ORDER BY a.login""",
            (telegram_id, telegram_id)
        )
        return [dict(r) for r in await cur.fetchall()]

