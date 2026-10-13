from __future__ import annotations

import logging

import discord
from discord.ext import commands

from quadton.config import Config
from quadton.db.database import Database
from quadton.db.migrations import run_migrations
from quadton.services.achievements import AchievementService
from quadton.services.cooldowns import CooldownService
from quadton.services.currency import CurrencyService
from quadton.services.effects import EffectService
from quadton.services.inventory import InventoryService
from quadton.services.networth import NetWorthService

log = logging.getLogger(__name__)

INITIAL_COGS = (
    "quadton.cogs.economy",
    "quadton.cogs.daily",
    "quadton.cogs.jobs",
    "quadton.cogs.items",
    "quadton.cogs.minigames",
    "quadton.cogs.profile",
    "quadton.cogs.leaderboard",
    "quadton.cogs.admin",
    "quadton.cogs.help",
)


class Quadton(commands.Bot):
    def __init__(self, config: Config, db: Database) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.config = config
        self.db = db
        self.currency = CurrencyService(db)
        self.inventory = InventoryService(db)
        self.cooldowns = CooldownService(db)
        self.effects = EffectService(db)
        self.networth = NetWorthService(db)
        self.achievements = AchievementService(db)

    async def setup_hook(self) -> None:
        await run_migrations(self.db)
        await self.inventory.ensure_seed()
        for ext in INITIAL_COGS:
            await self.load_extension(ext)
        try:
            synced = await self.tree.sync()
            log.info("Synced %d slash commands", len(synced))
        except Exception as exc:  # noqa: BLE001
            log.exception("Slash command sync failed: %s", exc)

    async def on_ready(self) -> None:
        log.info("Quadton online as %s (%s)", self.user, self.user.id if self.user else "?")

    async def close(self) -> None:
        try:
            await super().close()
        finally:
            await self.db.close()
