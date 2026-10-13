
## `docs/COMMANDS.md`

```markdown
# Quadton Command Reference (Phase 1)

### Currency
- `/balance [member]` — wallet, bank, total.
- `/deposit amount` — move QC wallet → bank.
- `/withdraw amount` — move QC bank → wallet.
- `/pay member amount` — player-to-player transfer.
- `/history` — last 10 transactions.

### Rewards
- `/daily` — daily QC. 22h cooldown.

### Careers
- `/jobs` — list careers.
- `/job-change job_id` — pick a career (resets level/xp).
- `/career` — current job summary.
- `/work` — work one shift. Pays based on level & effects.

### Items & effects
- `/inventory` — your items.
- `/use item_id [quantity]` — consume a usable item.
- `/effects` — active buffs.

### Gathering
- `/fish`, `/mine`, `/treasure` — 45–60s cooldown per activity.

### Profile
- `/networth [member]` — wallet, bank, inventory, total.
- `/rank [member]` — rank + progression.
- `/profile [member]` — full summary.
- `/achievements` — your achievement progress.

### Leaderboards
- `/leaderboard` — global top 10 by net worth.

### Admin (requires user ID in `QUADTON_ADMIN_IDS`)
- `/admin-give member amount [reason]` — audit-logged adjustment.
- `/admin-integrity` — SQLite integrity check.
- `/admin-backup` — snapshot backup with verification.
- `/admin-purge-effects` — purge expired effects.
