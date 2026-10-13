from __future__ import annotations

import aiosqlite

from quadton.data.items import ITEMS, ItemDef, by_id
from quadton.db.database import Database


class ItemNotFound(Exception):
    pass


class InsufficientItems(Exception):
    pass


class InventoryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_seed(self) -> None:
        async with self.db.transaction() as conn:
            for it in ITEMS:
                await conn.execute(
                    """
                    INSERT INTO items(item_id, name, description, rarity, category,
                                      base_value, stackable, usable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(item_id) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        rarity=excluded.rarity,
                        category=excluded.category,
                        base_value=excluded.base_value,
                        stackable=excluded.stackable,
                        usable=excluded.usable
                    """,
                    (
                        it.item_id, it.name, it.description, it.rarity,
                        it.category, it.base_value,
                        1 if it.stackable else 0,
                        1 if it.usable else 0,
                    ),
                )

    async def get_quantity(self, user_id: int, item_id: str) -> int:
        row = await self.db.fetchone(
            "SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",
            (user_id, item_id),
        )
        return int(row[0]) if row else 0

    async def list_inventory(self, user_id: int) -> list[tuple[str, int]]:
        rows = await self.db.fetchall(
            "SELECT item_id, quantity FROM inventory "
            "WHERE user_id=? AND quantity > 0 ORDER BY item_id",
            (user_id,),
        )
        return [(r[0], int(r[1])) for r in rows]

    async def grant(
        self,
        conn: aiosqlite.Connection,
        user_id: int,
        item_id: str,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if by_id(item_id) is None:
            raise ItemNotFound(item_id)
        await conn.execute(
            "INSERT INTO inventory(user_id, item_id, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, item_id) DO UPDATE SET "
            "quantity = quantity + excluded.quantity",
            (user_id, item_id, quantity),
        )

    async def consume(
        self,
        conn: aiosqlite.Connection,
        user_id: int,
        item_id: str,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        cur = await conn.execute(
            "UPDATE inventory SET quantity = quantity - ? "
            "WHERE user_id=? AND item_id=? AND quantity >= ?",
            (quantity, user_id, item_id, quantity),
        )
        if cur.rowcount == 0:
            raise InsufficientItems(f"{item_id} x{quantity}")

    @staticmethod
    def item_def(item_id: str) -> ItemDef | None:
        return by_id(item_id)
