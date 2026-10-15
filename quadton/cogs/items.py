from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services.effects import ACTIVITY, ECONOMIC
from quadton.ui.base import SelectView
from quadton.ui.embeds import (
    COLOR_MARKET,
    empty_state,
    error,
    info,
    qc,
    success,
)

EFFECT_CLASS = {
    "heal": None,
    "xp_boost": ACTIVITY,
    "focus": ACTIVITY,
    "prosperity": ECONOMIC,
    "pet_training": ACTIVITY,
}


class Items(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="inventory",
        description="Browse your items with dropdown navigation.",
    )
    async def inventory(self, interaction: discord.Interaction) -> None:
        entries = await self.bot.inventory.list_inventory(interaction.user.id)
        if not entries:
            await interaction.response.send_message(
                embed=empty_state("Your inventory is empty."), ephemeral=True
            )
            return

        options = []
        for item_id, qty in entries[:25]:
            d = self.bot.inventory.item_def(item_id)
            name = d.name if d else item_id
            options.append(
                discord.SelectOption(
                    label=f"{name} ×{qty}"[:100],
                    value=item_id,
                    description=(d.rarity.title() if d else "?")[:100],
                )
            )

        async def on_select(inter2: discord.Interaction, item_id: str) -> None:
            await self._show_item(inter2, item_id)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose an item to inspect...",
            options=options,
            on_select=on_select,
        )
        embed = info(
            "🎒 Inventory",
            f"You own **{len(entries)}** distinct items. "
            "Select one to inspect and act on it.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _show_item(
        self, interaction: discord.Interaction, item_id: str
    ) -> None:
        definition = self.bot.inventory.item_def(item_id)
        if definition is None:
            await interaction.response.edit_message(
                embed=error("Unknown item"), view=None
            )
            return
        qty = await self.bot.inventory.get_quantity(interaction.user.id, item_id)
        embed = discord.Embed(
            title=definition.name,
            description=definition.description,
            color=COLOR_MARKET,
        )
        embed.add_field(name="Rarity", value=definition.rarity.title(), inline=True)
        embed.add_field(name="Category", value=definition.category.title(), inline=True)
        embed.add_field(name="Owned", value=str(qty), inline=True)
        embed.add_field(name="Base value", value=qc(definition.base_value), inline=True)

        actions: list[discord.SelectOption] = [
            discord.SelectOption(label="← Back to inventory", value="back"),
        ]
        if definition.usable:
            actions.append(
                discord.SelectOption(label="Use 1", value=f"use:1:{item_id}")
            )
            if qty >= 5:
                actions.append(
                    discord.SelectOption(label="Use 5", value=f"use:5:{item_id}")
                )

        async def on_action(inter2: discord.Interaction, value: str) -> None:
            if value == "back":
                await self.inventory(inter2)  # reopen
                return
            parts = value.split(":", 2)
            await self._do_use(inter2, parts[2], int(parts[1]))

        view = SelectView(
            interaction.user.id,
            placeholder="Choose an action...",
            options=actions,
            on_select=on_action,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _do_use(
        self, interaction: discord.Interaction, item_id: str, quantity: int
    ) -> None:
        definition = self.bot.inventory.item_def(item_id)
        if definition is None or not definition.usable:
            await interaction.response.send_message(
                embed=error("Item is not usable"), ephemeral=True
            )
            return
        effect_type = definition.effect or ""
        try:
            async with self.bot.db.transaction() as conn:
                await self.bot.inventory.consume(
                    conn, interaction.user.id, item_id, quantity
                )
                perk_class = EFFECT_CLASS.get(effect_type)
                if perk_class is not None:
                    await self.bot.effects.apply(
                        conn,
                        interaction.user.id,
                        effect_type=effect_type,
                        perk_class=perk_class,
                        strength=definition.strength,
                        source=item_id,
                        duration=definition.duration,
                    )
        except Exception as exc:  # noqa: BLE001
            await interaction.response.send_message(
                embed=error("Use failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Item used",
                f"Consumed **{quantity}× {definition.name}**.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="use", description="Consume a usable item.")
    @app_commands.describe(item_id="Item ID", quantity="How many to use")
    async def use(
        self,
        interaction: discord.Interaction,
        item_id: str,
        quantity: int = 1,
    ) -> None:
        if quantity <= 0:
            await interaction.response.send_message(
                embed=error("Quantity must be positive"), ephemeral=True
            )
            return
        await self._do_use(interaction, item_id, quantity)

    @app_commands.command(name="effects", description="Show active effects.")
    async def effects(self, interaction: discord.Interaction) -> None:
        active = await self.bot.effects.active_effects(interaction.user.id)
        if not active:
            await interaction.response.send_message(
                embed=empty_state("No active effects."), ephemeral=True
            )
            return
        lines = [
            f"**{e['effect_type']}** ({e['perk_class']}) "
            f"+{int(e['strength'] * 100)}% — expires <t:{e['expires_at']}:R>"
            for e in active
        ]
        embed = info("Active Effects", "\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Items(bot))
