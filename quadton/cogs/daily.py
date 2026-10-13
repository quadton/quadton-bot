from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

DAILY_SECONDS = 22 * 3600
BASE_DAILY = 500


class Daily(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="Claim your daily Quad Coins reward.")
    async def daily(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id

        async def grant(conn):
            await self.bot.currency.credit_in_tx(
                conn, uid, BASE_DAILY, "DAILY_REWARD", count_as_earned=True
            )

        status = await self.bot.cooldowns.reward_with_cooldown(
            uid, "daily", DAILY_SECONDS, grant
        )
        if not status.ready:
            h, rem = divmod(status.remaining, 3600)
            m, s = divmod(rem, 60)
            await interaction.response.send_message(
                f"Daily available in {h}h {m}m {s}s.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Claimed **{BASE_DAILY:,} QC** daily reward!"
        )


async def setup(bot) -> None:
    await bot.add_cog(Daily(bot))
