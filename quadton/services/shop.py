from __future__ import annotations

import aiosqlite

from quadton.data.shop import ShopEntry, by_item
from quadton.db.database import Database
from quadton.services.currency import CurrencyService
from quadton.services.inventory import InventoryService


class ShopError(Exception):
    pass


class NotInShop(ShopError):
    pass


class NotSellable(ShopError):
    pass


class ShopService:
    """NPC shop. Player ↔ NPC trades only.

    Prices are fixed. The shop is a QC sink: buy price is higher than
    sell price, and the spread is destroyed (not held by anyone).
    """

    def __init__(
        self,
        db: Database,
        currency: CurrencyService,
        inventory: InventoryService,
    ) -> None:
        self.db = db
        self.currency = currency
        self.inventory = inventory

    async def buy(
        self, user_id: int, item_id: str, quantity: int
    ) -> tuple[int, int]:
        """Return (total_cost, new_wallet_balance)."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        entry = by_item(item_id)
        if entry is None or entry.buy_price <= 0:
            raise NotInShop(item_id)
        total = entry.buy_price * quantity
        async with self.db.transaction() as conn:
            await self.currency.ensure_user(conn, user_id)
            await self.currency.debit_in_tx(
                conn, user_id, total, "SHOP_BUY",
                count_as_spent=True,
                meta={"item_id": item_id, "quantity": quantity},
            )
            await self.inventory.grant(conn, user_id, item_id, quantity)
            new_balance = await self._wallet_balance(conn, user_id)
        return total, new_balance

    async def sell(
        self, user_id: int, item_id: str, quantity: int
    ) -> tuple[int, int]:
        """Return (total_earned, new_wallet_balance)."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        entry = by_item(item_id)
        if entry is None:
            raise NotInShop(item_id)
        if entry.sell_price <= 0:
            raise NotSellable(item_id)
        total = entry.sell_price * quantity
        async with self.db.transaction() as conn:
            await self.currency.ensure_user(conn, user_id)
            await self.inventory.consume(conn, user_id, item_id, quantity)
            await self.currency.credit_in_tx(
                conn, user_id, total, "SHOP_SELL",
                count_as_earned=True,
                meta={"item_id": item_id, "quantity": quantity},
            )
            new_balance = await self._wallet_balance(conn, user_id)
        return total, new_balance

    async def _wallet_balance(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> int:
        cur = await conn.execute(
            "SELECT balance FROM accounts WHERE user_id=? AND kind='wallet'",
            (user_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0
