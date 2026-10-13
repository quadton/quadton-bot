from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services import ranks as rank_service


def fmt(n: int) -> str:
    return f"{n:,} QC"


class Profile(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="Show your net worth breakdown.")
    async def networth(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        b = await self.bot.networth.breakdown(target.id)
        embed = discord.Embed(title=f"{target.display_name} — Net Worth", color=0xF1C40F)
        embed.add_field(name="Wallet", value=fmt(b["wallet"]))
        embed.add_field(name="Bank", value=fmt(b["bank"]))
        embed.add_field(name="Inventory", value=fmt(b["inventory"]))
        embed.add_field(name="Total", value=f"**{fmt(b['total'])}**")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Show your rank and progression.")
    async def rank(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        b = await self.bot.networth.breakdown(target.id)
        achievements = await self.bot.achievements.count_unlocked(target.id)
        row = await self.bot.db.fetchone(
            "SELECT COALESCE(SUM(level), 0) AS total FROM user_jobs WHERE user_id=?",
            (target.id,),
        )
        total_levels = int(row["total"]) if row else 0
        score = rank_service.score(b["total"], achievements, total_levels)
        info = rank_service.rank_for(score)
        embed = discord.Embed(title=f"{target.display_name} — Rank", color=0x9B59B6)
        embed.add_field(name="Rank", value=info["rank"])
        embed.add_field(name="Score", value=f"{score:,}")
        if info["next"]:
            embed.add_field(
                name="Next",
                value=f"{info['next']} — {info['points_to_next']:,} pts to go",
            )
        embed.add_field(name="Achievements", value=str(achievements))
        embed.add_field(name="Total job levels", value=str(total_levels))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Show a player profile summary.")
    async def profile(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        b = await self.bot.networth.breakdown(target.id)
        earned, spent = await self.bot.currency.get_lifetime(target.id)
        achievements = await self.bot.achievements.count_unlocked(target.id)
        job_row = await self.bot.db.fetchone(
            "SELECT job_id, level FROM user_jobs WHERE user_id=?", (target.id,)
        )
        effects = await self.bot.effects.active_effects(target.id)

        score = rank_service.score(b["total"], achievements, 0)
        info = rank_service.rank_for(score)

        embed = discord.Embed(title=f"{target.display_name}", color=0x3498DB)
        embed.add_field(name="Rank", value=info["rank"])
        embed.add_field(name="Net Worth", value=fmt(b["total"]))
        embed.add_field(name="Wallet", value=fmt(b["wallet"]))
        embed.add_field(name="Bank", value=fmt(b["bank"]))
        embed.add_field(name="Lifetime Earned", value=fmt(earned))
        embed.add_field(name="Lifetime Spent", value=fmt(spent))
        embed.add_field(name="Achievements", value=str(achievements))
        if job_row:
            embed.add_field(
                name="Career",
                value=f"{job_row['job_id']} lv {job_row['level']}",
            )
        if effects:
            embed.add_field(
                name="Active effects",
                value=", ".join(e["effect_type"] for e in effects),
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Show your achievements.")
    async def achievements(self, interaction: discord.Interaction) -> None:
        data = await self.bot.achievements.progress(interaction.user.id)
        lines = []
        for aid, info in data.items():
            check = "✅" if info["unlocked_at"] else "⬜"
            lines.append(
                f"{check} **{info['name']}** — {info['progress']}/{info['target']} "
                f"(+{info['reward_qc']} QC)"
            )
        embed = discord.Embed(
            title="Achievements", description="\n".join(lines) or "None",
            color=0xF39C12,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Profile(bot))
