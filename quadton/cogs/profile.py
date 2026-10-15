from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services import ranks as rank_service
from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_MARKET, info, qc


TABS = (
    ("overview", "Overview"),
    ("economy", "Economy"),
    ("career", "Career"),
    ("achievements", "Achievements"),
    ("effects", "Active Effects"),
    ("market", "Market Activity"),
)


class Profile(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="profile", description="Your player profile (tabbed)."
    )
    async def profile(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user

        async def on_select(inter2: discord.Interaction, tab: str) -> None:
            embed = await self._render(target, tab)
            await inter2.response.edit_message(embed=embed)

        options = [
            discord.SelectOption(label=label, value=key, description=f"View {label}")
            for key, label in TABS
        ]
        view = SelectView(
            interaction.user.id,
            placeholder="Choose a profile section...",
            options=options,
            on_select=on_select,
        )
        embed = await self._render(target, "overview")
        await view.start(interaction, embed=embed)

    async def _render(
        self, target: discord.abc.User, tab: str
    ) -> discord.Embed:
        if tab == "overview":
            return await self._overview(target)
        if tab == "economy":
            return await self._economy(target)
        if tab == "career":
            return await self._career(target)
        if tab == "achievements":
            return await self._achievements(target)
        if tab == "effects":
            return await self._effects(target)
        if tab == "market":
            return await self._market(target)
        return info("Profile", "Unknown tab.")

    async def _overview(self, target: discord.abc.User) -> discord.Embed:
        b = await self.bot.networth.breakdown(target.id)
        earned, spent = await self.bot.currency.get_lifetime(target.id)
        achievements = await self.bot.achievements.count_unlocked(target.id)
        score = rank_service.score(b["total"], achievements, 0)
        info_ = rank_service.rank_for(score)

        embed = discord.Embed(
            title=f"{target.display_name}",
            color=COLOR_MARKET,
        )
        embed.add_field(name="Rank", value=info_["rank"], inline=True)
        embed.add_field(name="Net Worth", value=qc(b["total"]), inline=True)
        embed.add_field(name="Achievements", value=str(achievements), inline=True)
        embed.add_field(name="Lifetime Earned", value=qc(earned), inline=True)
        embed.add_field(name="Lifetime Spent", value=qc(spent), inline=True)
        if info_["next"]:
            embed.add_field(
                name="Next Rank",
                value=f"{info_['next']} — {info_['points_to_next']:,} pts",
                inline=True,
            )
        return embed

    async def _economy(self, target: discord.abc.User) -> discord.Embed:
        b = await self.bot.networth.breakdown(target.id)
        embed = discord.Embed(
            title=f"{target.display_name} — Economy",
            color=COLOR_MARKET,
        )
        embed.add_field(name="Wallet", value=qc(b["wallet"]))
        embed.add_field(name="Bank", value=qc(b["bank"]))
        embed.add_field(name="Inventory", value=qc(b["inventory"]))
        embed.add_field(name="Net Worth", value=f"**{qc(b['total'])}**")
        return embed

    async def _career(self, target: discord.abc.User) -> discord.Embed:
        row = await self.bot.db.fetchone(
            "SELECT job_id, level, xp, promotions FROM user_jobs WHERE user_id=?",
            (target.id,),
        )
        embed = discord.Embed(
            title=f"{target.display_name} — Career",
            color=COLOR_MARKET,
        )
        if row is None:
            embed.description = "*No career. Use `/job-change` to start one.*"
            return embed
        from quadton.data.jobs import by_id, pay_for, xp_needed

        job = by_id(row["job_id"])
        if job is None:
            embed.description = "*Career invalid — pick a new one.*"
            return embed
        embed.add_field(name="Career", value=job.name)
        embed.add_field(name="Level", value=str(row["level"]))
        embed.add_field(
            name="XP",
            value=f"{row['xp']} / {xp_needed(int(row['level']))}",
        )
        embed.add_field(name="Pay per shift", value=qc(pay_for(job, int(row["level"]))))
        embed.add_field(name="Promotions", value=str(row["promotions"]))
        return embed

    async def _achievements(self, target: discord.abc.User) -> discord.Embed:
        data = await self.bot.achievements.progress(target.id)
        lines = []
        for _, info_ in data.items():
            mark = "✅" if info_["unlocked_at"] else "⬜"
            lines.append(
                f"{mark} **{info_['name']}** — {info_['progress']}/{info_['target']}"
            )
        embed = info(
            f"{target.display_name} — Achievements",
            "\n".join(lines) or "None.",
        )
        return embed

    async def _effects(self, target: discord.abc.User) -> discord.Embed:
        active = await self.bot.effects.active_effects(target.id)
        if not active:
            return info(
                f"{target.display_name} — Effects", "*No active effects.*"
            )
        lines = [
            f"**{e['effect_type']}** ({e['perk_class']}) "
            f"+{int(e['strength'] * 100)}% — <t:{e['expires_at']}:R>"
            for e in active
        ]
        return info(f"{target.display_name} — Effects", "\n".join(lines))

    async def _market(self, target: discord.abc.User) -> discord.Embed:
        orders = await self.bot.market.user_orders(target.id)
        embed = discord.Embed(
            title=f"{target.display_name} — Market Activity",
            color=COLOR_MARKET,
        )
        if not orders:
            embed.description = "*No open orders.*"
            return embed
        lines = []
        for o in orders[:10]:
            side = o["side"].upper()
            lines.append(
                f"`#{o['order_id']}` {side} {o['item_id']} "
                f"×{o['remaining']} @ {o['price']:,} QC"
            )
        embed.description = "\n".join(lines)
        return embed

    @app_commands.command(name="networth", description="Net-worth breakdown.")
    async def networth(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        b = await self.bot.networth.breakdown(target.id)
        embed = info(
            f"{target.display_name} — Net Worth",
            f"**Wallet** · {qc(b['wallet'])}\n"
            f"**Bank** · {qc(b['bank'])}\n"
            f"**Inventory** · {qc(b['inventory'])}\n"
            f"**Total** · **{qc(b['total'])}**",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rank", description="Rank and progression.")
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
        info_ = rank_service.rank_for(score)
        embed = info(f"{target.display_name} — Rank")
        embed.add_field(name="Rank", value=info_["rank"])
        embed.add_field(name="Score", value=f"{score:,}")
        if info_["next"]:
            embed.add_field(
                name="Next",
                value=f"{info_['next']} — {info_['points_to_next']:,} pts",
            )
        embed.add_field(name="Achievements", value=str(achievements))
        embed.add_field(name="Job levels", value=str(total_levels))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="achievements", description="Your achievements.")
    async def achievements(self, interaction: discord.Interaction) -> None:
        embed = await self._achievements(interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Profile(bot))
