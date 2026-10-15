from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_MARKET, empty_state, info, qc


CATEGORIES = (
    ("net_worth", "Net Worth"),
    ("wallet", "Wallet"),
    ("bank", "Bank"),
    ("lifetime_earned", "Lifetime Earned"),
    ("jobs", "Job Levels"),
)


class Leaderboard(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="Leaderboards with dropdown selectors.",
    )
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        scopes = [
            discord.SelectOption(label="Global", value="global", description="Across all servers"),
        ]
        if interaction.guild is not None:
            scopes.append(
                discord.SelectOption(
                    label=f"Server: {interaction.guild.name}"[:100],
                    value="server",
                    description="Members of this server only",
                )
            )

        async def on_scope(inter2: discord.Interaction, scope: str) -> None:
            await self._pick_category(inter2, scope)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a scope...",
            options=scopes,
            on_select=on_scope,
        )
        embed = info(
            "🏆 Leaderboards",
            "Choose a scope, then a category.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _pick_category(
        self, interaction: discord.Interaction, scope: str
    ) -> None:
        options = [
            discord.SelectOption(label=label, value=key, description=f"Rank by {label}")
            for key, label in CATEGORIES
        ]

        async def on_cat(inter2: discord.Interaction, category: str) -> None:
            await self._render(inter2, scope, category)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a category...",
            options=options,
            on_select=on_cat,
        )
        embed = info(
            "🏆 Leaderboard",
            f"Scope: **{scope}** — pick a category.",
        )
        embed.color = COLOR_MARKET
        await interaction.response.edit_message(embed=embed, view=view)

    async def _render(
        self,
        interaction: discord.Interaction,
        scope: str,
        category: str,
    ) -> None:
        if category == "net_worth":
            embed = await self._net_worth(scope, interaction)
        elif category in ("wallet", "bank"):
            embed = await self._balance_rank(scope, category, interaction)
        elif category == "lifetime_earned":
            embed = await self._lifetime_earned(scope, interaction)
        elif category == "jobs":
            embed = await self._job_levels(scope, interaction)
        else:
            embed = empty_state("Unknown category.")

        # Add a dropdown to switch category without re-running the command.
        options = [
            discord.SelectOption(label=label, value=key, description=f"Rank by {label}")
            for key, label in CATEGORIES
        ] + [discord.SelectOption(label="← Change scope", value="__scope__")]

        async def on_cat(inter2: discord.Interaction, value: str) -> None:
            if value == "__scope__":
                await self.leaderboard(inter2)
                return
            await self._render(inter2, scope, value)

        view = SelectView(
            interaction.user.id,
            placeholder="Switch category...",
            options=options,
            on_select=on_cat,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _guild_member_ids(self, interaction: discord.Interaction) -> list[int]:
        if interaction.guild is None:
            return []
        return [m.id for m in interaction.guild.members if not m.bot]

    async def _net_worth(
        self, scope: str, interaction: discord.Interaction
    ) -> discord.Embed:
        rows = await self.bot.networth.top_by_networth(limit=100)
        if scope == "server":
            members = set(await self._guild_member_ids(interaction))
            rows = [r for r in rows if r["user_id"] in members]
        rows = rows[:10]
        return self._list_embed(
            f"🏆 Net Worth — {scope.title()}", rows, "total", interaction
        )

    async def _balance_rank(
        self, scope: str, kind: str, interaction: discord.Interaction
    ) -> discord.Embed:
        members_clause = ""
        params: list = [kind]
        if scope == "server":
            ids = await self._guild_member_ids(interaction)
            if not ids:
                return empty_state("No members to rank.")
            placeholders = ",".join("?" * len(ids))
            members_clause = f" AND a.user_id IN ({placeholders})"
            params.extend(ids)
        rows = await self.bot.db.fetchall(
            f"""
            SELECT a.user_id, a.balance AS total
            FROM accounts a
            WHERE a.kind=?{members_clause}
            ORDER BY a.balance DESC LIMIT 10
            """,
            params,
        )
        return self._list_embed(
            f"🏆 {kind.title()} — {scope.title()}",
            [{"user_id": r["user_id"], "total": int(r["total"])} for r in rows],
            "total",
            interaction,
        )

    async def _lifetime_earned(
        self, scope: str, interaction: discord.Interaction
    ) -> discord.Embed:
        members_clause = ""
        params: list = []
        if scope == "server":
            ids = await self._guild_member_ids(interaction)
            if not ids:
                return empty_state("No members to rank.")
            placeholders = ",".join("?" * len(ids))
            members_clause = f" WHERE user_id IN ({placeholders})"
            params.extend(ids)
        rows = await self.bot.db.fetchall(
            f"""
            SELECT user_id, lifetime_earned AS total FROM users{members_clause}
            ORDER BY lifetime_earned DESC LIMIT 10
            """,
            params,
        )
        return self._list_embed(
            f"🏆 Lifetime Earned — {scope.title()}",
            [{"user_id": r["user_id"], "total": int(r["total"])} for r in rows],
            "total",
            interaction,
        )

    async def _job_levels(
        self, scope: str, interaction: discord.Interaction
    ) -> discord.Embed:
        members_clause = ""
        params: list = []
        if scope == "server":
            ids = await self._guild_member_ids(interaction)
            if not ids:
                return empty_state("No members to rank.")
            placeholders = ",".join("?" * len(ids))
            members_clause = f" WHERE user_id IN ({placeholders})"
            params.extend(ids)
        rows = await self.bot.db.fetchall(
            f"""
            SELECT user_id, COALESCE(SUM(level), 0) AS total FROM user_jobs
            {members_clause}
            GROUP BY user_id ORDER BY total DESC LIMIT 10
            """,
            params,
        )
        embed = discord.Embed(
            title=f"🏆 Job Levels — {scope.title()}",
            color=COLOR_MARKET,
        )
        if not rows:
            embed.description = "*No data.*"
            return embed
        lines = []
        for i, r in enumerate(rows, start=1):
            member = interaction.guild.get_member(int(r["user_id"])) if interaction.guild else None
            name = member.display_name if member else f"<@{r['user_id']}>"
            lines.append(f"`{i:>2}.` {name} — {int(r['total'])} levels")
        embed.description = "\n".join(lines)
        return embed

    def _list_embed(
        self,
        title: str,
        rows: list[dict],
        value_key: str,
        interaction: discord.Interaction,
    ) -> discord.Embed:
        embed = discord.Embed(title=title, color=COLOR_MARKET)
        if not rows:
            embed.description = "*No data.*"
            return embed
        lines = []
        for i, r in enumerate(rows, start=1):
            member = (
                interaction.guild.get_member(r["user_id"])
                if interaction.guild
                else None
            )
            name = member.display_name if member else f"<@{r['user_id']}>"
            lines.append(f"`{i:>2}.` {name} — {qc(r[value_key])}")
        embed.description = "\n".join(lines)
        return embed


async def setup(bot) -> None:
    await bot.add_cog(Leaderboard(bot))
