# Economy Design Notes

## Currency
- **QC = Quad Coins**, integer amounts. Format `1,250 QC`.
- QC is a virtual game currency. Not real money.

## Sources (QC entering the economy)
- `JOB_REWARD` — work shifts, scaled by career level and `prosperity` effect.
- `DAILY_REWARD` — flat, 22h cooldown.
- `ACHIEVEMENT_REWARD` — one-off per achievement.
- `ADMIN_ADJUSTMENT` — restricted, audited.

## Sinks (QC leaving the economy)
- `CRAFTING_FEE` — planned (Phase 2).
- `MARKET_FEE` — planned (Phase 2).
- `ADMIN_ADJUSTMENT` — restricted, audited.

## Invariants enforced by the code
- Balances are integers and constrained `>= 0` at the DB level.
- Every mutation goes through `CurrencyService` and is recorded in
  `transactions` with a `tx_type`.
- Wallet ↔ bank moves are internal transfers and do **not** change lifetime
  earned/spent and do **not** change net worth.
- Every reward path uses `reward_with_cooldown` which atomically: checks the
  cooldown, runs the grant, and writes the new cooldown in one transaction.
- `idempotency_key` on `transactions` prevents duplicate payout from retried
  interactions.
- Concurrent debits are serialized by `Database._write_lock` + `BEGIN IMMEDIATE`.

## Net worth
`net_worth = wallet + bank + Σ(inventory_qty × item_base_value)`

`base_value` is the documented fallback used when no market price exists.
Phase 2 will add market-price valuation using `price_history`.

## Ranks
Score = `net_worth + achievements×500 + total_job_levels×250`.
Thresholds (cumulative): Bronze 0, Silver 5k, Gold 25k, Platinum 100k,
Diamond 500k, Emerald 2M, Champion 10M.

## Balance levers
- `data/items.py` — item base values.
- `data/jobs.py` — pay, cooldowns, XP.
- `cogs/minigames.py` — drop tables & weights.
- `cogs/daily.py` — daily amount & cooldown.

All values are integers to avoid float drift; only effect multipliers use
floats and are applied at reward time.
