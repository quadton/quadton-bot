from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services.effects import ACTIVITY, ECONOMIC


def fmt(n: int) -> str:
    return f"{n:,} QC"


# effect_type -> perk_class. Determines the stacking bucket.
EFFECT_CLASS = {
    "heal": None,          # instant, no persistence
    "xp_boost": ACTIVITY,
    "focus": ACTIVITY,
    "prosperity": ECONOMIC,
    "pet_training": ACTIVITY,
}


class Items(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="List your inventory.")
    async def inventory(self, interaction: discord.Interaction) -> None:
        entries = await self.bot.inventory.list_inventory(interaction.user.id)
        if not entries:
            await interaction.response.send_message(
                "Your inventory is empty.", ephemeral=True
            )
            return
        lines = []
        for item_id, qty in entries:
            d = self.bot.inventory.item_def(item_id)
            name = d.name if d else item_id
            lines.append(f"`{item_id}` — {name} x{qty}")
        embed = discord.Embed(
            title="Inventory", description="\n".join(lines), color=0x3498DB
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Use an item from your inventory.")
    @app_commands.describe(item_id="Item ID", quantity="How many to consume")
    async def use(
        self,
        interaction: discord.Interaction,
        item_id: str,
        quantity: int = 1,
    ) -> None:
        if quantity <= 0:
            await interaction.response.send_message(
                "Quantity must be positive.", ephemeral=True
            )
            return
        uid = interaction.user.id
        definition = self.bot.inventory.item_def(item_id)
        if definition is None:
            await interaction.response.send_message("Unknown item.", ephemeral=True)
            return
        if not definition.usable:
            await interaction.response.send_message(
                "That item is not usable.", ephemeral=True
            )
            return
        effect_type = definition.effect or ""

        async def grant(conn):
            await self.bot.inventory.consume(conn, uid, item_id, quantity)
            perk_class = EFFECT_CLASS.get(effect_type)
            if perk_class is None:
                # Instant effect (e.g. heal). No persistent effect.
                return
            await self.bot.effects.apply(
                conn,
                uid,
                effect_type=effect_type,
                perk_class=perk_class,
                strength=definition.strength,
                source=item_id,
                duration=definition.duration,
            )

        try:
            async with self.bot.db.transaction() as conn:
                await grant(conn)
        except Exception as e:
            await interaction.response.send_message(
                f"Use failed: {e}", ephemeral=True
            )
            return
        if EFFECT_CLASS.get(effect_type) is None:
            await interaction.response.send_message(
                f"Used {quantity}x **{definition.name}** ({effect_type}).",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Used {quantity}x **{definition.name}**. "
                f"Effect `{effect_type}` active for {definition.duration}s.",
                ephemeral=True,
            )

    @app_commands.command(description="Show your active effects.")
    async def effects(self, interaction: discord.Interaction) -> None:
        active = await self.bot.effects.active_effects(interaction.user.id)
        if not active:
            await interaction.response.send_message(
                "No active effects.", ephemeral=True
            )
            return
        lines = []
        for e in active:
            lines.append(
                f"**{e['effect_type']}** ({e['perk_class']}) "
                f"+{int(e['strength'] * 100)}% until <t:{e['expires_at']}:R>"
            )
        embed = discord.Embed(
            title="Active Effects", description="\n".join(lines), color=0x1ABC9C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Items(bot))
