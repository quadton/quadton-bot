from __future__ import annotations

import time

from quadton.db.database import Database

SCHEMA_V1 = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    created_at INTEGER NOT NULL,
    lifetime_earned INTEGER NOT NULL DEFAULT 0,
    lifetime_spent INTEGER NOT NULL DEFAULT 0,
    trading_profit INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('wallet','bank')),
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    UNIQUE (user_id, kind),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE transactions (
    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT UNIQUE,
    tx_type TEXT NOT NULL,
    from_account INTEGER,
    to_account INTEGER,
    amount INTEGER NOT NULL CHECK (amount >= 0),
    meta TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (from_account) REFERENCES accounts(account_id),
    FOREIGN KEY (to_account) REFERENCES accounts(account_id)
);
CREATE INDEX idx_tx_from ON transactions(from_account);
CREATE INDEX idx_tx_to ON transactions(to_account);
CREATE INDEX idx_tx_created ON transactions(created_at);

CREATE TABLE cooldowns (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    ready_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE items (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    rarity TEXT NOT NULL,
    category TEXT NOT NULL,
    base_value INTEGER NOT NULL,
    stackable INTEGER NOT NULL DEFAULT 1,
    usable INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE inventory (
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE effects (
    effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    effect_type TEXT NOT NULL,
    perk_class TEXT NOT NULL CHECK (perk_class IN ('economic','activity')),
    strength REAL NOT NULL,
    source TEXT NOT NULL,
    activated_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX idx_effects_user ON effects(user_id, expires_at);

CREATE TABLE user_jobs (
    user_id INTEGER NOT NULL PRIMARY KEY,
    job_id TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    promotions INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE user_stats (
    user_id INTEGER PRIMARY KEY,
    jobs_completed INTEGER NOT NULL DEFAULT 0,
    minigames_played INTEGER NOT NULL DEFAULT 0,
    fish_caught INTEGER NOT NULL DEFAULT 0,
    ores_mined INTEGER NOT NULL DEFAULT 0,
    treasures_found INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE user_achievements (
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    unlocked_at INTEGER,
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE market_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    price INTEGER NOT NULL CHECK (price > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    remaining INTEGER NOT NULL CHECK (remaining >= 0),
    status TEXT NOT NULL DEFAULT 'open',
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);
CREATE INDEX idx_market_item_side ON market_orders(item_id, side, price);

CREATE TABLE price_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_id INTEGER,
    details TEXT,
    created_at INTEGER NOT NULL
);
"""

MIGRATIONS: tuple[tuple[int, str], ...] = ((1, SCHEMA_V1),)


async def run_migrations(db: Database) -> None:
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)"
    )
    await db.conn.commit()
    row = await db.fetchone(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    )
    current = int(row[0]) if row else 0
    for version, sql in MIGRATIONS:
        if version <= current:
            continue
        await db.conn.executescript(sql)
        await db.conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, int(time.time())),
        )
        await db.conn.commit()
