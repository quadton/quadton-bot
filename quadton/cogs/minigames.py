from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands


FISH_TABLE = (
    ("fiber", 30, 1, 2),
    ("apple", 20, 1, 1),
    ("soup", 5, 1, 1),
    ("ruby", 1, 1, 1),
)

MINE_TABLE = (
    ("stone", 35, 1, 3),
    ("copper_ore", 25, 1, 2),
    ("iron_ore", 15, 1, 2),
    ("silver_ore", 5, 1, 1),
    ("gold_ore", 4, 1, 1),
    ("mithril_ore", 1, 1, 1),
)

TREASURE_TABLE = (
    ("sand", 40, 1, 3),
    ("gold_ore", 15, 1, 2),
    ("diamond", 2, 1, 1),
    ("card_rare", 3, 1, 1),
)


class Minigames(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="Go fishing.")
    async def fish(self, interaction: discord.Interaction) -> None:
        await self._gather(interaction, "fish", 45, FISH_TABLE, "fish_caught")

    @app_commands.command(description="Go mining.")
    async def mine(self, interaction: discord.Interaction) -> None:
        await self._gather(interaction, "mine", 45, MINE_TABLE, "ores_mined")

    @app_commands.command(description="Search for treasure.")
    async def treasure(self, interaction: discord.Interaction) -> None:
        await self._gather(
            interaction, "treasure", 60, TREASURE_TABLE, "treasures_found"
        )

    async def _gather(
        self,
        interaction: discord.Interaction,
        key: str,
        cooldown_seconds: int,
        table: tuple,
        stat_field: str,
    ) -> None:
        uid = interaction.user.id
        mult = await self.bot.effects.multiplier(uid, "focus")
        item_id, _, qmin, qmax = random.choices(
            table, weights=[t[1] for t in table], k=1
        )[0]
        qty = max(1, int(random.randint(qmin, qmax) * mult))

        async def grant(conn):
            await self.bot.inventory.grant(conn, uid, item_id, qty)
            await conn.execute(
                f"UPDATE user_stats SET {stat_field} = {stat_field} + 1, "
                f"minigames_played = minigames_played + 1 WHERE user_id=?",
                (uid,),
            )

        status = await self.bot.cooldowns.reward_with_cooldown(
            uid, f"mg:{key}", cooldown_seconds, grant
        )
        if not status.ready:
            m, s = divmod(status.remaining, 60)
            await interaction.response.send_message(
                f"Cooldown: {m}m {s}s remaining.", ephemeral=True
            )
            return

        definition = self.bot.inventory.item_def(item_id)
        name = definition.name if definition else item_id
        embed = discord.Embed(
            title=f"{key.title()} result",
            description=f"You obtained **{qty}x {name}**.",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed)
        unlocked = await self.bot.achievements.check_and_grant(uid)
        if unlocked:
            await interaction.followup.send(
                f"Unlocked achievements: {', '.join(unlocked)}", ephemeral=True
            )


async def setup(bot) -> None:
    await bot.add_cog(Minigames(bot))
