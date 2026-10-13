from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Sequence

import aiosqlite

from quadton.db.database import Database

WALLET = "wallet"
BANK = "bank"


class InsufficientFunds(Exception):
    pass


class DuplicateTransaction(Exception):
    pass


@dataclass
class TransferResult:
    tx_id: int
    amount: int
    from_account: int | None
    to_account: int | None
    tx_type: str


class CurrencyService:
    """Central ledger. All QC movements must go through this service."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_user(self, conn: aiosqlite.Connection, user_id: int) -> None:
        now = int(time.time())
        await conn.execute(
            "INSERT OR IGNORE INTO users(user_id, created_at) VALUES (?, ?)",
            (user_id, now),
        )
        for kind in (WALLET, BANK):
            await conn.execute(
                "INSERT OR IGNORE INTO accounts(user_id, kind, balance) VALUES (?, ?, 0)",
                (user_id, kind),
            )
        await conn.execute(
            "INSERT OR IGNORE INTO user_stats(user_id) VALUES (?)", (user_id,)
        )

    async def _account_id(self, conn, user_id: int, kind: str) -> int:
        cur = await conn.execute(
            "SELECT account_id FROM accounts WHERE user_id=? AND kind=?",
            (user_id, kind),
        )
        row = await cur.fetchone()
        if row is None:
            raise RuntimeError(f"account missing: {user_id}/{kind}")
        return int(row[0])

    async def get_balance(self, user_id: int, kind: str = WALLET) -> int:
        row = await self.db.fetchone(
            "SELECT balance FROM accounts WHERE user_id=? AND kind=?",
            (user_id, kind),
        )
        return int(row[0]) if row else 0

    async def get_lifetime(self, user_id: int) -> tuple[int, int]:
        row = await self.db.fetchone(
            "SELECT lifetime_earned, lifetime_spent FROM users WHERE user_id=?",
            (user_id,),
        )
        if row is None:
            return 0, 0
        return int(row[0]), int(row[1])

    async def _record_tx(
        self,
        conn,
        tx_type: str,
        amount: int,
        from_account: int | None,
        to_account: int | None,
        idempotency_key: str | None,
        meta: dict[str, Any] | None,
        now: int,
    ) -> int:
        if idempotency_key is not None:
            cur = await conn.execute(
                "SELECT tx_id FROM transactions WHERE idempotency_key=?",
                (idempotency_key,),
            )
            if await cur.fetchone() is not None:
                raise DuplicateTransaction(idempotency_key)
        cur = await conn.execute(
            """
            INSERT INTO transactions
              (idempotency_key, tx_type, from_account, to_account, amount, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                tx_type,
                from_account,
                to_account,
                amount,
                json.dumps(meta) if meta else None,
                now,
            ),
        )
        return int(cur.lastrowid)

    async def _adjust(self, conn, account_id: int, delta: int) -> int:
        cur = await conn.execute(
            "UPDATE accounts SET balance = balance + ? "
            "WHERE account_id=? AND balance + ? >= 0",
            (delta, account_id, delta),
        )
        if cur.rowcount == 0:
            raise InsufficientFunds()
        cur = await conn.execute(
            "SELECT balance FROM accounts WHERE account_id=?", (account_id,)
        )
        row = await cur.fetchone()
        return int(row[0])

    # --- in-transaction API (call only within db.transaction) ---

    async def credit_in_tx(
        self,
        conn,
        user_id: int,
        amount: int,
        tx_type: str,
        *,
        kind: str = WALLET,
        idempotency_key: str | None = None,
        meta: dict | None = None,
        count_as_earned: bool = False,
    ) -> TransferResult:
        if amount <= 0:
            raise ValueError("amount must be positive")
        now = int(time.time())
        await self.ensure_user(conn, user_id)
        to_acct = await self._account_id(conn, user_id, kind)
        tx_id = await self._record_tx(
            conn, tx_type, amount, None, to_acct, idempotency_key, meta, now
        )
        await self._adjust(conn, to_acct, amount)
        if count_as_earned:
            await conn.execute(
                "UPDATE users SET lifetime_earned = lifetime_earned + ? WHERE user_id=?",
                (amount, user_id),
            )
        return TransferResult(tx_id, amount, None, to_acct, tx_type)

    async def debit_in_tx(
        self,
        conn,
        user_id: int,
        amount: int,
        tx_type: str,
        *,
        kind: str = WALLET,
        idempotency_key: str | None = None,
        meta: dict | None = None,
        count_as_spent: bool = False,
    ) -> TransferResult:
        if amount <= 0:
            raise ValueError("amount must be positive")
        now = int(time.time())
        await self.ensure_user(conn, user_id)
        from_acct = await self._account_id(conn, user_id, kind)
        tx_id = await self._record_tx(
            conn, tx_type, amount, from_acct, None, idempotency_key, meta, now
        )
        await self._adjust(conn, from_acct, -amount)
        if count_as_spent:
            await conn.execute(
                "UPDATE users SET lifetime_spent = lifetime_spent + ? WHERE user_id=?",
                (amount, user_id),
            )
        return TransferResult(tx_id, amount, from_acct, None, tx_type)

    # --- public wrappers (own transaction) ---

    async def credit(self, user_id: int, amount: int, tx_type: str, **kw) -> TransferResult:
        async with self.db.transaction() as conn:
            return await self.credit_in_tx(conn, user_id, amount, tx_type, **kw)

    async def debit(self, user_id: int, amount: int, tx_type: str, **kw) -> TransferResult:
        async with self.db.transaction() as conn:
            return await self.debit_in_tx(conn, user_id, amount, tx_type, **kw)

    async def transfer(
        self,
        from_user: int,
        to_user: int,
        amount: int,
        tx_type: str,
        *,
        from_kind: str = WALLET,
        to_kind: str = WALLET,
        idempotency_key: str | None = None,
        meta: dict | None = None,
    ) -> TransferResult:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if from_user == to_user:
            raise ValueError("cannot transfer to self")
        now = int(time.time())
        async with self.db.transaction() as conn:
            await self.ensure_user(conn, from_user)
            await self.ensure_user(conn, to_user)
            from_acct = await self._account_id(conn, from_user, from_kind)
            to_acct = await self._account_id(conn, to_user, to_kind)
            tx_id = await self._record_tx(
                conn, tx_type, amount, from_acct, to_acct,
                idempotency_key, meta, now,
            )
            await self._adjust(conn, from_acct, -amount)
            await self._adjust(conn, to_acct, amount)
        return TransferResult(tx_id, amount, from_acct, to_acct, tx_type)

    async def deposit(self, user_id: int, amount: int) -> TransferResult:
        return await self._internal(user_id, WALLET, BANK, amount, "BANK_DEPOSIT")

    async def withdraw(self, user_id: int, amount: int) -> TransferResult:
        return await self._internal(user_id, BANK, WALLET, amount, "BANK_WITHDRAWAL")

    async def _internal(
        self, user_id: int, from_kind: str, to_kind: str, amount: int, tx_type: str
    ) -> TransferResult:
        if amount <= 0:
            raise ValueError("amount must be positive")
        now = int(time.time())
        async with self.db.transaction() as conn:
            await self.ensure_user(conn, user_id)
            from_acct = await self._account_id(conn, user_id, from_kind)
            to_acct = await self._account_id(conn, user_id, to_kind)
            tx_id = await self._record_tx(
                conn, tx_type, amount, from_acct, to_acct, None, None, now
            )
            await self._adjust(conn, from_acct, -amount)
            await self._adjust(conn, to_acct, amount)
        return TransferResult(tx_id, amount, from_acct, to_acct, tx_type)

    async def history(self, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        return await self.db.fetchall(
            """
            SELECT t.tx_id, t.tx_type, t.amount, t.created_at, t.meta,
                   t.from_account, t.to_account,
                   fa.user_id AS from_user, ta.user_id AS to_user
            FROM transactions t
            LEFT JOIN accounts fa ON fa.account_id = t.from_account
            LEFT JOIN accounts ta ON ta.account_id = t.to_account
            WHERE fa.user_id = ? OR ta.user_id = ?
            ORDER BY t.tx_id DESC LIMIT ?
            """,
            (user_id, user_id, limit),
        )
