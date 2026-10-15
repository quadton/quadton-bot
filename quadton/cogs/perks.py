from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from quadton.data.perks import PERKS, by_id
from quadton.services.effects import ACTIVITY, ECONOMIC
from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_MARKET, error, info, success


class Perks(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="perks",
        description="View activatable perks and their cooldowns.",
    )
    async def perks(self, interaction: discord.Interaction) -> None:
        embed = info(
            "⚡ Perks",
            "Perks grant temporary buffs. One economic perk and one "
            "activity perk may be active at the same time.",
        )
        embed.color = COLOR_MARKET
        for p in PERKS:
            status = await self.bot.cooldowns.check(
                interaction.user.id, f"perk:{p.perk_id}"
            )
            if status.ready:
                cd = "Ready"
            else:
                h, rem = divmod(status.remaining, 3600)
                m = rem // 60
                cd = f"{h}h {m}m"
            embed.add_field(
                name=f"{p.name} ({p.perk_class})",
                value=f"{p.description}\nCooldown: **{cd}**",
                inline=False,
            )
        embed.set_footer(text="Use /activate-perk to activate one.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="activate-perk", description="Activate a perk."
    )
    async def activate_perk(self, interaction: discord.Interaction) -> None:
        options = [
            discord.SelectOption(
                label=p.name[:100],
                value=p.perk_id,
                description=p.description[:100],
            )
            for p in PERKS
        ]

        async def on_select(inter2: discord.Interaction, perk_id: str) -> None:
            await self._activate(inter2, perk_id)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a perk to activate...",
            options=options,
            on_select=on_select,
        )
        embed = info(
            "⚡ Activate a Perk",
            "Perks have long cooldowns. Activating one replaces any active "
            "effect in the same class (economic / activity).",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _activate(
        self, interaction: discord.Interaction, perk_id: str
    ) -> None:
        perk = by_id(perk_id)
        if perk is None:
            await interaction.response.edit_message(
                embed=error("Unknown perk"), view=None
            )
            return
        status = await self.bot.cooldowns.check(
            interaction.user.id, f"perk:{perk.perk_id}"
        )
        if not status.ready:
            h, rem = divmod(status.remaining, 3600)
            m = rem // 60
            await interaction.response.edit_message(
                embed=error(
                    "Perk on cooldown",
                    f"**{perk.name}** available in {h}h {m}m.",
                ),
                view=None,
            )
            return

        # Apply effect and set cooldown atomically.
        async def grant(conn):
            await self.bot.effects.apply(
                conn,
                interaction.user.id,
                effect_type=perk.effect_type,
                perk_class=perk.perk_class,
                strength=perk.strength,
                source=f"perk:{perk.perk_id}",
                duration=perk.duration,
            )

        await self.bot.cooldowns.reward_with_cooldown(
            interaction.user.id, f"perk:{perk.perk_id}", perk.cooldown, grant
        )
        mins = perk.duration // 60
        await interaction.response.edit_message(
            embed=success(
                f"Activated: {perk.name}",
                f"**{perk.effect_type}** +{int(perk.strength * 100)}% "
                f"for {mins} minutes.",
            ),
            view=None,
        )


async def setup(bot) -> None:
    await bot.add_cog(Perks(bot))
