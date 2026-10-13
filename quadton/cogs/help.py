from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_PRIMARY, info


SECTIONS: dict[str, dict[str, str]] = {
    "economy": {
        "label": "💰 Economy",
        "commands": {
            "/balance [member]": "Wallet, bank, and total balances.",
            "/deposit <amount>": "Move QC from wallet → bank.",
            "/withdraw <amount>": "Move QC from bank → wallet.",
            "/pay <member> <amount>": "Send QC to another member.",
            "/history": "Your last 10 transactions.",
            "/daily": "Claim your daily Quad Coins (22h cooldown).",
        },
    },
    "market": {
        "label": "🛒 Market",
        "commands": {
            "/market": "Browse items with an interactive market view.",
            "/my-orders": "View and cancel your open orders.",
        },
    },
    "career": {
        "label": "💼 Careers",
        "commands": {
            "/jobs": "List all available careers.",
            "/job-change <job_id>": "Choose a career (resets level & XP).",
            "/career": "Your career summary.",
            "/work": "Work a shift and earn QC + XP.",
        },
    },
    "activities": {
        "label": "🎣 Activities",
        "commands": {
            "/fish": "Go fishing (45s cooldown).",
            "/mine": "Go mining (45s cooldown).",
            "/treasure": "Search for treasure (60s cooldown).",
        },
    },
    "items": {
        "label": "🧪 Items & Effects",
        "commands": {
            "/inventory": "List your items.",
            "/use <item_id> [quantity]": "Consume a usable item.",
            "/effects": "Your active buffs.",
        },
    },
    "profile": {
        "label": "👤 Profile",
        "commands": {
            "/profile [member]": "Full player summary.",
            "/networth [member]": "Net-worth breakdown.",
            "/rank [member]": "Rank and progression.",
            "/achievements": "Your achievement progress.",
        },
    },
    "leaderboard": {
        "label": "🏆 Leaderboards",
        "commands": {
            "/leaderboard": "Global top 10 by net worth.",
        },
    },
    "admin": {
        "label": "🛡️ Admin",
        "commands": {
            "/admin-give <member> <amount> [reason]": "Audited adjustment.",
            "/admin-integrity": "SQLite integrity check.",
            "/admin-backup": "Snapshot and verify backup.",
            "/admin-purge-effects": "Purge expired effects.",
        },
    },
}


class Help(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Show Quadton commands with a dropdown category selector.",
    )
    async def help(self, interaction: discord.Interaction) -> None:
        options = [
            discord.SelectOption(
                label=s["label"][:100],
                value=key,
                description=f"Show {key} commands",
            )
            for key, s in SECTIONS.items()
        ]

        async def on_select(inter2: discord.Interaction, key: str) -> None:
            section = SECTIONS.get(key)
            if section is None:
                return
            embed = info(section["label"], "Commands in this category:")
            for cmd, desc in section["commands"].items():
                embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
            embed.set_footer(text="Quadton is a game. QC has no monetary value.")
            await inter2.response.edit_message(embed=embed)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a category...",
            options=options,
            on_select=on_select,
        )

        overview = info(
            "⬢ Quadton — Command Reference",
            "A persistent, **gambling-free** Discord economy bot.\n\n"
            "Use the dropdown below to jump to a command category.",
        )
        overview.color = COLOR_PRIMARY
        overview.set_footer(text="Quadton is a game. QC has no monetary value.")
        await view.start(interaction, embed=overview)


async def setup(bot) -> None:
    await bot.add_cog(Help(bot))
