from __future__ import annotations

import time
from dataclasses import dataclass

import aiosqlite

from quadton.db.database import Database
from quadton.services.currency import CurrencyService
from quadton.services.inventory import InventoryService

SYSTEM_USER_ID = 0
MARKET_FEE_BPS = 200  # 2.00%


class OrderNotFound(Exception):
    pass


class NotYourOrder(Exception):
    pass


class OrderNotOpen(Exception):
    pass


@dataclass(frozen=True)
class TradeResult:
    buyer_id: int
    seller_id: int
    item_id: str
    quantity: int
    price: int
    fee: int


class MarketService:
    """Player-driven order-book market.

    Buy orders escrow QC into a system account.
    Sell orders escrow items (consumed from inventory).
    Matching is atomic and idempotent per call.
    Self-matching is skipped to prevent wash-trading price manipulation.
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

    # ---------- order placement ----------

    async def place_sell_order(
        self, user_id: int, item_id: str, quantity: int, price: int
    ) -> int:
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        async with self.db.transaction() as conn:
            await self.currency.ensure_user(conn, user_id)
            await self.inventory.consume(conn, user_id, item_id, quantity)
            cur = await conn.execute(
                """
                INSERT INTO market_orders
                    (user_id, item_id, side, price, quantity, remaining, status, created_at)
                VALUES (?, ?, 'sell', ?, ?, ?, 'open', ?)
                """,
                (user_id, item_id, price, quantity, quantity, int(time.time())),
            )
            order_id = int(cur.lastrowid)
        await self.match(item_id)
        return order_id

    async def place_buy_order(
        self, user_id: int, item_id: str, quantity: int, price: int
    ) -> int:
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        total = quantity * price
        async with self.db.transaction() as conn:
            await self.currency.ensure_user(conn, user_id)
            await self.currency.ensure_user(conn, SYSTEM_USER_ID)
            await self.currency.debit_in_tx(conn, user_id, total, "MARKET_BUY_RESERVE")
            await self.currency.credit_in_tx(
                conn, SYSTEM_USER_ID, total, "MARKET_BUY_RESERVE"
            )
            cur = await conn.execute(
                """
                INSERT INTO market_orders
                    (user_id, item_id, side, price, quantity, remaining, status, created_at)
                VALUES (?, ?, 'buy', ?, ?, ?, 'open', ?)
                """,
                (user_id, item_id, price, quantity, quantity, int(time.time())),
            )
            order_id = int(cur.lastrowid)
        await self.match(item_id)
        return order_id

    # ---------- order cancellation ----------

    async def cancel_order(self, user_id: int, order_id: int) -> None:
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                """
                SELECT order_id, user_id, item_id, side, price, remaining, status
                FROM market_orders WHERE order_id=?
                """,
                (order_id,),
            )
            row = await cur.fetchone()
            if row is None:
                raise OrderNotFound()
            if int(row["user_id"]) != user_id:
                raise NotYourOrder()
            if row["status"] != "open":
                raise OrderNotOpen()
            remaining = int(row["remaining"])
            if remaining <= 0:
                raise OrderNotOpen()

            if row["side"] == "sell":
                await self.inventory.grant(conn, user_id, row["item_id"], remaining)
            else:
                refund = remaining * int(row["price"])
                await self.currency.debit_in_tx(
                    conn, SYSTEM_USER_ID, refund, "MARKET_BUY_CANCEL"
                )
                await self.currency.credit_in_tx(
                    conn, user_id, refund, "MARKET_BUY_CANCEL"
                )

            await conn.execute(
                "UPDATE market_orders SET remaining=0, status='cancelled' WHERE order_id=?",
                (order_id,),
            )

    # ---------- matching engine ----------

    async def match(self, item_id: str) -> list[TradeResult]:
        """Cross the book for a single item until no further trades are possible."""
        trades: list[TradeResult] = []
        while True:
            trade = await self._match_one(item_id)
            if trade is None:
                break
            trades.append(trade)
        return trades

    async def _match_one(self, item_id: str) -> TradeResult | None:
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                """
                SELECT order_id, user_id, price, remaining, created_at
                FROM market_orders
                WHERE item_id=? AND side='buy' AND status='open' AND remaining>0
                ORDER BY price DESC, created_at ASC LIMIT 20
                """,
                (item_id,),
            )
            buys = await cur.fetchall()
            if not buys:
                return None

            cur = await conn.execute(
                """
                SELECT order_id, user_id, price, remaining, created_at
                FROM market_orders
                WHERE item_id=? AND side='sell' AND status='open' AND remaining>0
                ORDER BY price ASC, created_at ASC LIMIT 20
                """,
                (item_id,),
            )
            sells = await cur.fetchall()
            if not sells:
                return None

            pair: tuple[aiosqlite.Row, aiosqlite.Row] | None = None
            for b in buys:
                for s in sells:
                    if int(b["user_id"]) == int(s["user_id"]):
                        continue
                    if int(b["price"]) >= int(s["price"]):
                        pair = (b, s)
                        break
                if pair is not None:
                    break
            if pair is None:
                return None

            buy, sell = pair
            buy_price = int(buy["price"])
            sell_price = int(sell["price"])
            trade_price = sell_price
            qty = min(int(buy["remaining"]), int(sell["remaining"]))
            gross = trade_price * qty
            fee = (gross * MARKET_FEE_BPS) // 10_000
            net_to_seller = gross - fee

            buyer_id = int(buy["user_id"])
            seller_id = int(sell["user_id"])

            await self.currency.debit_in_tx(
                conn, SYSTEM_USER_ID, gross, "MARKET_TRADE"
            )
            await self.currency.credit_in_tx(
                conn, seller_id, net_to_seller, "MARKET_SALE", count_as_earned=True
            )

            if buy_price > trade_price:
                refund = (buy_price - trade_price) * qty
                await self.currency.debit_in_tx(
                    conn, SYSTEM_USER_ID, refund, "MARKET_PRICE_REFUND"
                )
                await self.currency.credit_in_tx(
                    conn, buyer_id, refund, "MARKET_PRICE_REFUND"
                )

            await self.inventory.grant(conn, buyer_id, item_id, qty)

            new_buy = int(buy["remaining"]) - qty
            new_sell = int(sell["remaining"]) - qty
            await conn.execute(
                "UPDATE market_orders SET remaining=? WHERE order_id=?",
                (new_buy, int(buy["order_id"])),
            )
            await conn.execute(
                "UPDATE market_orders SET remaining=? WHERE order_id=?",
                (new_sell, int(sell["order_id"])),
            )
            if new_buy == 0:
                await conn.execute(
                    "UPDATE market_orders SET status='filled' WHERE order_id=?",
                    (int(buy["order_id"]),),
                )
            if new_sell == 0:
                await conn.execute(
                    "UPDATE market_orders SET status='filled' WHERE order_id=?",
                    (int(sell["order_id"]),),
                )

            await conn.execute(
                """
                INSERT INTO price_history(item_id, price, quantity, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (item_id, trade_price, qty, int(time.time())),
            )

            return TradeResult(
                buyer_id=buyer_id,
                seller_id=seller_id,
                item_id=item_id,
                quantity=qty,
                price=trade_price,
                fee=fee,
            )

    # ---------- queries ----------

    async def order_book(
        self, item_id: str, side: str, limit: int = 10
    ) -> list[aiosqlite.Row]:
        direction = "DESC" if side == "buy" else "ASC"
        return await self.db.fetchall(
            f"""
            SELECT order_id, user_id, item_id, side, price, quantity, remaining, created_at
            FROM market_orders
            WHERE item_id=? AND side=? AND status='open' AND remaining>0
            ORDER BY price {direction}, created_at ASC
            LIMIT ?
            """,
            (item_id, side, limit),
        )

    async def best_price(self, item_id: str, side: str) -> int | None:
        direction = "DESC" if side == "buy" else "ASC"
        row = await self.db.fetchone(
            f"""
            SELECT price FROM market_orders
            WHERE item_id=? AND side=? AND status='open' AND remaining>0
            ORDER BY price {direction} LIMIT 1
            """,
            (item_id, side),
        )
        return int(row["price"]) if row else None

    async def reference_price(self, item_id: str, fallback: int) -> int:
        row = await self.db.fetchone(
            "SELECT price FROM price_history WHERE item_id=? ORDER BY history_id DESC LIMIT 1",
            (item_id,),
        )
        if row is not None:
            return int(row["price"])
        bid = await self.best_price(item_id, "buy")
        ask = await self.best_price(item_id, "sell")
        if bid is not None and ask is not None:
            return (bid + ask) // 2
        if bid is not None:
            return bid
        if ask is not None:
            return ask
        return fallback

    async def recent_trades(
        self, item_id: str, limit: int = 10
    ) -> list[aiosqlite.Row]:
        return await self.db.fetchall(
            """
            SELECT price, quantity, created_at FROM price_history
            WHERE item_id=? ORDER BY history_id DESC LIMIT ?
            """,
            (item_id, limit),
        )

    async def user_orders(self, user_id: int) -> list[aiosqlite.Row]:
        return await self.db.fetchall(
            """
            SELECT order_id, item_id, side, price, quantity, remaining, status, created_at
            FROM market_orders
            WHERE user_id=? AND status='open' AND remaining>0
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
