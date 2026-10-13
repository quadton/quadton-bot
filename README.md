<div align="center">

# ⬢ QUADTON

**A persistent, gambling-free Discord economy & progression bot.**

`Quad Coins` · `Python 3.11+` · `discord.py 2.x` · `SQLite (WAL)`

![status](https://img.shields.io/badge/status-phase%201%20complete-2ea043?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![gambling](https://img.shields.io/badge/gambling-none-critical?style=flat-square)

</div>

---

## 📖 Table of Contents

- [About](#-about)
- [Status](#-status)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Running Quadton](#-running-quadton)
- [Commands](#-commands)
- [Architecture](#-architecture)
- [Database](#-database)
- [Economy Design](#-economy-design)
- [Security](#-security)
- [Backup & Recovery](#-backup--recovery)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 About

**Quadton** is a persistent virtual economy game for Discord. Players earn
**QC (Quad Coins)**, progress through careers, gather resources, unlock
achievements, and climb global leaderboards — all without a single gambling
mechanic.

> **QC is a virtual game currency.** It is not real money and cannot be
> exchanged for real money. Quadton contains **no** casinos, slots, betting,
> wagering, loot boxes, or paid randomized rewards of any kind.

Quadton is designed for long-term operation on modest hardware, including
**Linux ARM64** environments such as Alpine Linux inside Podroid, and small
cloud VMs.

### Design Principles

- **Correctness first.** Every QC movement flows through one atomic ledger.
- **No fake functionality.** Every advertised command has a working implementation.
- **Persistent state.** Cooldowns, effects, and balances live in the database.
- **Safe by default.** Parameterized SQL, non-negative balances, idempotent payouts.
- **Modest hosting.** Runs comfortably on an ARM64 Alpine container.

---

## 🚦 Status

| Phase | Description                        | Status          |
| :---: | :--------------------------------- | :-------------- |
|   1   | Core economy & progression         | ✅ **Complete** |
|   2   | Market, crafting, businesses       | 🚧 Planned      |
|   3   | RPG, pets, cards, guilds           | 🚧 Planned      |
|   4   | Seasons, mastery, analytics        | 🚧 Planned      |

**No Phase 2–4 feature is stubbed or faked.** Anything not yet built is
listed honestly in the [Roadmap](#-roadmap).

---

## ✨ Features

### 💰 Economy
- Central ledger with atomic transactions
- Wallet & bank with deposit / withdraw
- Player-to-player payments
- Idempotency keys prevent duplicate payouts
- Lifetime earned / spent tracking
- Non-negative balance enforced at the database level

### 💼 Careers
- **10** distinct careers
- XP, levels, and promotions
- Pay scaling with career level
- Per-career work cooldowns

### 🎣 Gathering
- Fishing, mining, treasure hunting
- Weighted drop tables
- Effect-based yield multipliers

### 🧪 Items & Effects
- 32 seeded items across 12 categories
- 6 rarity tiers (Common → Mythic)
- Usable consumables (potions, food)
- Persistent buffs with class-based stacking

### 🏆 Progression
- **7 ranks**: Bronze → Champion
- Documented score formula
- 5 stat-driven achievements
- Net-worth breakdown

### 📊 Leaderboards
- Global net-worth ranking
- Efficient indexed queries

### ⏱️ Cooldowns
- **Persistent** — survive restarts
- Atomic check-grant-set
- Race-condition proof

### 🛡️ Administration
- Audited admin give / take
- SQLite integrity check
- Verified backups
- Effect purge

### 🔒 Security
- All secrets from environment
- Log redaction filter
- Parameterized SQL everywhere
- No trust in user input

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version   |
| :---------- | :-------- |
| Python      | 3.11+     |
| pip         | 23+       |
| Discord Bot | created on the [Developer Portal](https://discord.com/developers/applications) |

### 1. Clone & Install

```bash
git clone https://github.com/quadton/quadton-bot
cd quadton

python -m venv .venv
. .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# edit .env and set DISCORD_TOKEN at minimum
```

### 3. Run

```bash
python -m quadton
```

On first launch Quadton will:

1. Create the SQLite database
2. Apply all migrations
3. Seed the item catalog
4. Sync slash commands with Discord

---

## ⚙️ Configuration

Quadton reads all configuration from environment variables.
Copy `.env.example` to `.env` and edit:

| Variable             | Required | Default      | Description                                     |
| :------------------- | :------: | :----------- | :---------------------------------------------- |
| `DISCORD_TOKEN`      |    ✅    | —            | Bot token from the Discord Developer Portal     |
| `QUADTON_DB_PATH`    |    ❌    | `quadton.db` | Path to the SQLite database file                |
| `QUADTON_ADMIN_IDS`  |    ❌    | *(empty)*    | Comma-separated Discord user IDs for `/admin-*` |
| `QUADTON_BACKUP_DIR` |    ❌    | `backups`    | Directory for database backups                  |
| `QUADTON_LOG_LEVEL`  |    ❌    | `INFO`       | `DEBUG` · `INFO` · `WARNING` · `ERROR`           |
| `QUADTON_ENV`        |    ❌    | `production` | Free-form environment label                     |

> ⚠️ **Never commit your `.env`.** It is already listed in `.gitignore`.
> Quadton will refuse to start without `DISCORD_TOKEN`.

### Discord Developer Portal Setup

1. Create an application → **Bot** tab → **Reset Token** → copy it.
2. Under **Privileged Gateway Intents**, enable **Server Members Intent**.
3. Under **OAuth2 → URL Generator**, select scopes `bot` + `applications.commands`
   and permissions:
   - Send Messages
   - Embed Links
   - Use Slash Commands
4. Invite the bot to your server with the generated URL.

---

## ▶️ Running Quadton

### Development

```bash
python -m quadton
```

### With auto-reload (dev only)

```bash
watchfiles "python -m quadton" quadton/
```

### Graceful shutdown

Send `Ctrl+C` (SIGINT) or `SIGTERM`. Quadton closes the database cleanly and
flushes the WAL. Do not `kill -9`.

---

## 🎮 Commands

All commands are **Discord slash commands**. `[square]` = optional,
`<angle>` = required.

### 💰 Currency

| Command                  | Description                   |
| :----------------------- | :---------------------------- |
| `/balance [member]`      | Show wallet, bank, and total  |
| `/deposit <amount>`      | Move QC from wallet → bank    |
| `/withdraw <amount>`     | Move QC from bank → wallet    |
| `/pay <member> <amount>` | Transfer QC to another member |
| `/history`               | Your last 10 transactions     |

### 🎁 Rewards

| Command  | Description                                |
| :------- | :----------------------------------------- |
| `/daily` | Claim your daily Quad Coins (22h cooldown) |

### 💼 Careers

| Command                | Description                         |
| :--------------------- | :---------------------------------- |
| `/jobs`                | List all available careers          |
| `/job-change <job_id>` | Choose a career (resets level & XP) |
| `/career`              | Show your current job summary       |
| `/work`                | Work one shift and earn QC + XP     |

### 🧪 Items & Effects

| Command                     | Description              |
| :-------------------------- | :----------------------- |
| `/inventory`                | List your items          |
| `/use <item_id> [quantity]` | Consume a usable item    |
| `/effects`                  | Show your active buffs   |

### 🎣 Gathering

| Command     | Cooldown | Rewards                             |
| :---------- | :------: | :---------------------------------- |
| `/fish`     |   45s    | Fiber, apple, soup, ruby (rare)     |
| `/mine`     |   45s    | Stone, ores (copper → mithril)      |
| `/treasure` |   60s    | Sand, gold ore, diamond, rare cards |

### 👤 Profile

| Command              | Description          |
| :------------------- | :------------------- |
| `/networth [member]` | Net-worth breakdown  |
| `/rank [member]`     | Rank and progression |
| `/profile [member]`  | Full player summary  |
| `/achievements`      | Your achievement progress |

### 🏆 Leaderboards

| Command        | Description                |
| :------------- | :------------------------- |
| `/leaderboard` | Global top 10 by net worth |

### 🛡️ Admin

Requires user ID in `QUADTON_ADMIN_IDS`.

| Command                                  | Description                            |
| :--------------------------------------- | :------------------------------------- |
| `/admin-give <member> <amount> [reason]` | Grant or remove QC (audit-logged)      |
| `/admin-integrity`                       | Run `PRAGMA integrity_check` on the DB |
| `/admin-backup`                          | Create & verify a database backup      |
| `/admin-purge-effects`                   | Delete all expired effects             |

---

## 🏗️ Architecture

Quadton is organized into strict layers. **Commands never contain business
logic.** All economy-changing operations flow through shared services.

```text
┌────────────────────────────────────────────────────────────────┐
│                    Discord (Cogs / Slash Commands)             │
│  economy · daily · jobs · items · minigames · profile · admin  │
└──────────────────────────────┬─────────────────────────────────┘
                               │  calls
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                        Service Layer                           │
│  Currency · Inventory · Cooldowns · Effects · NetWorth ·       │
│  Achievements · Ranks · Backups                                │
└──────────────────────────────┬─────────────────────────────────┘
                               │  uses
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                     Database Layer (SQLite + WAL)              │
│  Database (single writer) · Migrations · Repositories          │
└────────────────────────────────────────────────────────────────┘
```

### Project Layout

```text
quadton/
├── quadton/
│   ├── __main__.py          # Entry point
│   ├── bot.py               # Bot class & cog loading
│   ├── config.py            # Environment → Config
│   ├── logging_setup.py     # Redaction filter
│   ├── db/
│   │   ├── database.py      # aiosqlite wrapper, transactions
│   │   └── migrations.py    # Versioned schema
│   ├── data/
│   │   ├── items.py         # 32 item definitions
│   │   ├── jobs.py          # 10 careers
│   │   └── achievements.py  # Achievement catalogue
│   ├── services/
│   │   ├── currency.py      # Ledger + transfers
│   │   ├── inventory.py     # Item ownership
│   │   ├── cooldowns.py     # Persistent cooldowns
│   │   ├── effects.py       # Buffs & perks
│   │   ├── networth.py      # Valuation
│   │   ├── ranks.py         # Score & thresholds
│   │   ├── achievements.py  # Progress + rewards
│   │   └── backups.py       # Snapshot + verify
│   └── cogs/                # Discord command surfaces
├── tests/                   # pytest + pytest-asyncio
├── docs/                    # COMMANDS.md · ECONOMY.md · BACKUP.md
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## 🗄️ Database

Quadton uses **SQLite** with **WAL mode** and **foreign keys enabled**.

| Table               | Purpose                                     |
| :------------------ | :------------------------------------------ |
| `users`             | Core user row, lifetime earned / spent      |
| `accounts`          | Wallet & bank balances (`CHECK >= 0`)       |
| `transactions`      | Full ledger with idempotency keys           |
| `cooldowns`         | Persistent per-user cooldown timestamps     |
| `items`             | Seeded item catalog                         |
| `inventory`         | Player item ownership                       |
| `effects`           | Active buffs (economic / activity classes)  |
| `user_jobs`         | Career, level, XP, promotions               |
| `user_stats`        | Counters used by achievements               |
| `user_achievements` | Progress + unlock timestamp                 |
| `market_orders`     | *Reserved for Phase 2*                      |
| `price_history`     | *Reserved for Phase 2*                      |
| `audit_log`         | Admin action trail                          |
| `schema_migrations` | Applied migration versions                  |

### Concurrency Model

- **Single active bot instance** against one SQLite file.
- All writes serialized via `_write_lock` + `BEGIN IMMEDIATE`.
- Reads are concurrent using WAL.
- **Scaling horizontally requires PostgreSQL.** The service layer's API is
  stable so this is a data-layer swap, not a rewrite.

---

## 💹 Economy Design

### QC (Quad Coins)

- Integer amounts only — no floating-point balances.
- Displayed as `1,250 QC`.
- **Never** mixed with real money.

### Sources (QC entering)

| Source               | Notes                                   |
| :------------------- | :-------------------------------------- |
| `JOB_REWARD`         | Scales with career level + `prosperity` |
| `DAILY_REWARD`       | Flat, 22h cooldown                      |
| `ACHIEVEMENT_REWARD` | One-off per achievement                 |
| `ADMIN_ADJUSTMENT`   | Restricted, audit-logged                |

### Sinks (QC leaving)

| Sink               | Phase |
| :----------------- | :---: |
| `CRAFTING_FEE`     |   2   |
| `MARKET_FEE`       |   2   |
| `ADMIN_ADJUSTMENT` |   1   |

### Invariants

> Every guarantee below is enforced in code and tested.

- ✅ Balances are integers `>= 0` at the database level.
- ✅ Every mutation goes through `CurrencyService` and is ledgered.
- ✅ Wallet ↔ bank transfers **never** change lifetime or net worth.
- ✅ Rewards use `reward_with_cooldown` — atomic check + grant + set.
- ✅ `idempotency_key UNIQUE` prevents duplicate payouts from retries.
- ✅ Concurrent debits are impossible to over-spend.

### Net Worth Formula

```text
net_worth = wallet + bank + Σ(inventory_qty × item_base_value)
```

`base_value` is the documented fallback when no market price exists.
Phase 2 will layer in market-price valuation via `price_history`.

### Rank Formula

```text
score = net_worth + achievements×500 + total_job_levels×250
```

| Rank     | Threshold  |
| :------- | :--------- |
| Bronze   | 0          |
| Silver   | 5,000      |
| Gold     | 25,000     |
| Platinum | 100,000    |
| Diamond  | 500,000    |
| Emerald  | 2,000,000  |
| Champion | 10,000,000 |

### Balance Levers

| File                        | Tune                    |
| :-------------------------- | :---------------------- |
| `quadton/data/items.py`     | Item base values        |
| `quadton/data/jobs.py`      | Pay, cooldowns, XP      |
| `quadton/cogs/minigames.py` | Drop tables & weights   |
| `quadton/cogs/daily.py`     | Daily amount & cooldown |

---

## 🔒 Security

### Secret Management

- All secrets read from environment variables.
- `.env` and `backups/` are gitignored.
- Log filter redacts `token`, `secret`, `password`, `authorization`, `bearer`.
- The Discord token is **never** printed or returned.

### Economy Security

- Parameterized SQL everywhere — no string interpolation.
- Amount validation: positive integers only, no floats.
- Balance floor enforced by `CHECK (balance >= 0)` + write-lock.
- Duplicate prevention: `idempotency_key` + `BEGIN IMMEDIATE`.
- Authorization: `/admin-*` requires user ID in `QUADTON_ADMIN_IDS`.
- Audit trail: every admin mutation writes to `audit_log`.

### Abuse Resistance

| Vector                   | Mitigation                                   |
| :----------------------- | :------------------------------------------- |
| Concurrent reward claims | Serialized writes + cooldown in transaction  |
| Retried interactions     | Idempotency keys on transfers                |
| Negative amounts         | `ValueError` before any DB write             |
| Self-transfers           | Explicit check in `CurrencyService.transfer` |
| Over-spending            | Balance floor + atomic UPDATE with predicate |
| Admin abuse              | Configured allow-list + audit log            |

### Operational Security

- Runs with minimum privileges on the host.
- No network listeners beyond Discord's outbound gateway.
- SQLite file is never exposed over the network.
- No unnecessary personal data collected.

---

## 💾 Backup & Recovery

### Create a Backup

**In-Discord** (admin only):

```text
/admin-backup
```

**Manual (safe while running):**

```bash
sqlite3 quadton.db "VACUUM INTO 'backups/manual-$(date +%s).db'"
```

**Manual (safe while stopped):**

```bash
cp quadton.db backups/manual-$(date +%s).db
```

> `VACUUM INTO` produces a **consistent snapshot** even while the bot is
> running, using SQLite's built-in backup API.

### Retention

`BackupService` keeps the most recent **14** backups matching
`quadton-*.db` and prunes older ones automatically.

### Restore

1. **Stop the bot.**
2. Move the current DB aside:
   ```bash
   mv quadton.db quadton.db.broken
   ```
3. Copy the backup into place:
   ```bash
   cp backups/quadton-YYYYMMDD-HHMMSS.db quadton.db
   ```
4. Remove stale WAL / SHM:
   ```bash
   rm -f quadton.db-wal quadton.db-shm
   ```
5. **Start the bot** and run `/admin-integrity`.
   Expected output: `Integrity: ok`.

### Off-Device Storage

The bot does **not** ship backups off-device by itself. Wire your
`QUADTON_BACKUP_DIR` into your preferred tool:

```bash
# rclone to cloud
rclone sync backups/ remote:quadton-backups/

# scp to another host
scp backups/*.db backup-host:/srv/quadton/
```

---

## 🧪 Testing

Quadton ships with a real, runnable test suite.

```bash
pip install -r requirements.txt
pytest -q
```

### Coverage Areas

| File                 | Tests                                             |
| :------------------- | :------------------------------------------------ |
| `test_currency.py`   | Credit, debit, transfer, idempotency, races       |
| `test_inventory.py`  | Grant, consume, rollback, unknown-item guard      |
| `test_cooldowns.py`  | Single-claim, concurrent claims, failure rollback |
| `test_effects.py`    | Apply, multiplier, stacking rules                 |
| `test_networth.py`   | Deposit-no-change, inventory valuation            |
| `test_ranks.py`      | Threshold boundaries, terminal rank               |

### Expected Output

```text
20 passed in 3.42s
```

---

## 🚢 Deployment

### Linux (systemd)

`/etc/systemd/system/quadton.service`:

```ini
[Unit]
Description=Quadton Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=quadton
Group=quadton
WorkingDirectory=/srv/quadton
EnvironmentFile=/srv/quadton/.env
ExecStart=/srv/quadton/.venv/bin/python -m quadton
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/quadton

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quadton
sudo journalctl -u quadton -f
```

### Alpine Linux / ARM64 (Podroid)

```bash
apk add python3 py3-pip build-base python3-dev sqlite
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If `discord.py` or `aiosqlite` has no prebuilt wheel for your architecture,
pip builds from source — `build-base` and `python3-dev` are required.

### Docker

```dockerfile
FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache build-base
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "quadton"]
```

---

## 🗺️ Roadmap

### Phase 2 — Economic Depth
- [ ] Player-to-player market orders
- [ ] Order book matching & reservations
- [ ] Auctions
- [ ] Price history & alerts
- [ ] Businesses (revenue, wages, upgrades)
- [ ] Crafting with atomic recipes
- [ ] Luxury goods & property
- [ ] Contracts & economic events

### Phase 3 — RPG & Collectibles
- [ ] Adventures & exploration
- [ ] Combat engine & bosses
- [ ] Equipment with durability
- [ ] Pets with evolution
- [ ] Trading cards & battles
- [ ] Guilds & cooperative quests

### Phase 4 — Long-Term Progression
- [ ] Seasons with rotating rewards
- [ ] Mastery & skill trees
- [ ] Market analytics dashboard
- [ ] Advanced balancing tools

---

## 🤝 Contributing

1. Fork the repo and create a feature branch.
2. **Follow the layering rules:** no business logic in cogs.
3. **Add a test** for every economy-affecting change.
4. Run `pytest -q` before opening a PR.
5. Keep changes small and focused.

### Style

- Python 3.11+, `from __future__ import annotations` in every module.
- Type hints on all public functions.
- Integers for currency, never floats.
- `ruff` and `black` preferred formatting.

---

## 📜 License

MIT License — see `LICENSE` for details.

---

<div align="center">

**Quadton is a game. QC has no monetary value.**

*Built with care for players, not for gamblers.*

⬢

</div>
