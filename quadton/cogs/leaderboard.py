from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


def fmt(n: int) -> str:
    return f"{n:,} QC"


class Leaderboard(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="Global net-worth leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.networth.top_by_networth(limit=10)
        lines = []
        for i, r in enumerate(rows, start=1):
            member = interaction.guild.get_member(r["user_id"]) if interaction.guild else None
            name = member.display_name if member else f"<@{r['user_id']}>"
            lines.append(f"`{i:>2}.` {name} — {fmt(r['total'])}")
        embed = discord.Embed(
            title="Global Net Worth Leaderboard",
            description="\n".join(lines) or "No data.",
            color=0xF1C40F,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Leaderboard(bot))
