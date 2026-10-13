from __future__ import annotations

from quadton.db.database import Database
from quadton.services.currency import BANK, WALLET


class NetWorthService:
    """Defensible net-worth calculation.

    net_worth = wallet + bank + inventory_value.

    Wallet→bank transfers never change net worth because both sides are the
    same user's accounts. Inventory is valued at the item's base_value, which
    is a documented fallback. Market-based valuation will be layered on in
    Phase 2 when a price history is available.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    async def breakdown(self, user_id: int) -> dict[str, int]:
        wallet = await self._balance(user_id, WALLET)
        bank = await self._balance(user_id, BANK)
        inventory = await self._inventory_value(user_id)
        return {
            "wallet": wallet,
            "bank": bank,
            "inventory": inventory,
            "total": wallet + bank + inventory,
        }

    async def _balance(self, user_id: int, kind: str) -> int:
        row = await self.db.fetchone(
            "SELECT balance FROM accounts WHERE user_id=? AND kind=?",
            (user_id, kind),
        )
        return int(row[0]) if row else 0

    async def _inventory_value(self, user_id: int) -> int:
        row = await self.db.fetchone(
            """
            SELECT COALESCE(SUM(i.quantity * it.base_value), 0)
            FROM inventory i
            JOIN items it ON it.item_id = i.item_id
            WHERE i.user_id=? AND i.quantity > 0
            """,
            (user_id,),
        )
        return int(row[0]) if row else 0

    async def top_by_networth(self, limit: int = 10) -> list[dict]:
        rows = await self.db.fetchall(
            """
            SELECT u.user_id,
                   COALESCE(SUM(CASE WHEN a.kind='wallet' THEN a.balance ELSE 0 END), 0) AS wallet,
                   COALESCE(SUM(CASE WHEN a.kind='bank'   THEN a.balance ELSE 0 END), 0) AS bank,
                   COALESCE((
                     SELECT SUM(i.quantity * it.base_value)
                     FROM inventory i
                     JOIN items it ON it.item_id = i.item_id
                     WHERE i.user_id = u.user_id
                   ), 0) AS inventory
            FROM users u
            LEFT JOIN accounts a ON a.user_id = u.user_id
            GROUP BY u.user_id
            """,
        )
        result = []
        for r in rows:
            total = int(r["wallet"]) + int(r["bank"]) + int(r["inventory"])
            result.append(
                {
                    "user_id": int(r["user_id"]),
                    "total": total,
                    "wallet": int(r["wallet"]),
                    "bank": int(r["bank"]),
                    "inventory": int(r["inventory"]),
                }
            )
        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:limit]
