from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.data.shop import CATEGORIES, by_item, in_category
from quadton.services.inventory import InsufficientItems
from quadton.services.currency import InsufficientFunds
from quadton.services.shop import NotInShop, NotSellable
from quadton.ui.base import SelectView
from quadton.ui.embeds import (
    COLOR_MARKET,
    empty_state,
    error,
    info,
    qc,
    success,
)


def _cat_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=c.title(), value=c, description=f"Browse {c}")
        for c in CATEGORIES
    ]


class Shop(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="shop",
        description="Buy and sell items with the NPC vendor.",
    )
    async def shop(self, interaction: discord.Interaction) -> None:
        view = SelectView(
            interaction.user.id,
            placeholder="Choose a shop category...",
            options=_cat_options(),
            on_select=self._on_category,
        )
        embed = info(
            "🛒 Quadton Shop",
            "Pick a category to browse. Buy prices are fixed; "
            "sell prices are lower than buy prices.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _on_category(
        self, interaction: discord.Interaction, category: str
    ) -> None:
        entries = in_category(category)
        if not entries:
            await interaction.response.edit_message(
                embed=empty_state(f"No items in category **{category}**."),
                view=None,
            )
            return

        options: list[discord.SelectOption] = []
        for e in entries[:25]:
            from quadton.data.items import by_id as item_by_id

            it = item_by_id(e.item_id)
            name = it.name if it else e.item_id
            sell_text = f" · sells for {e.sell_price} QC" if e.sell_price > 0 else ""
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=e.item_id,
                    description=f"Buy: {e.buy_price} QC{sell_text}"[:100],
                )
            )

        async def on_item(inter2: discord.Interaction, item_id: str) -> None:
            await self._show_item(inter2, item_id, category)

        view = SelectView(
            interaction.user.id,
            placeholder=f"Choose an item from {category}...",
            options=options,
            on_select=on_item,
        )
        embed = info(
            f"🛒 {category.title()}",
            "Select an item to view its prices and actions.",
        )
        embed.color = COLOR_MARKET
        await interaction.response.edit_message(embed=embed, view=view)

    async def _show_item(
        self, interaction: discord.Interaction, item_id: str, category: str
    ) -> None:
        from quadton.data.items import by_id as item_by_id

        entry = by_item(item_id)
        definition = item_by_id(item_id)
        if entry is None or definition is None:
            await interaction.response.edit_message(
                embed=error("Item not found"), view=None
            )
            return

        owned = await self.bot.inventory.get_quantity(interaction.user.id, item_id)
        wallet = await self.bot.currency.get_balance(interaction.user.id, "wallet")

        embed = discord.Embed(
            title=definition.name,
            description=definition.description,
            color=COLOR_MARKET,
        )
        embed.add_field(name="Buy price", value=qc(entry.buy_price), inline=True)
        embed.add_field(
            name="Sell price",
            value=qc(entry.sell_price) if entry.sell_price > 0 else "—",
            inline=True,
        )
        embed.add_field(name="You own", value=str(owned), inline=True)
        embed.add_field(name="Your wallet", value=qc(wallet), inline=True)

        actions: list[discord.SelectOption] = [
            discord.SelectOption(label="Buy 1", value=f"buy:1:{item_id}"),
            discord.SelectOption(label="Buy 5", value=f"buy:5:{item_id}"),
            discord.SelectOption(
                label="Buy custom amount...", value=f"buymodal:{item_id}"
            ),
        ]
        if entry.sell_price > 0 and owned > 0:
            actions.append(
                discord.SelectOption(label="Sell 1", value=f"sell:1:{item_id}")
            )
            actions.append(
                discord.SelectOption(
                    label="Sell custom amount...", value=f"sellmodal:{item_id}"
                )
            )
        actions.append(discord.SelectOption(label="← Back", value=f"back:{category}"))

        async def on_action(inter2: discord.Interaction, value: str) -> None:
            parts = value.split(":", 2)
            action = parts[0]
            if action == "back":
                await self._on_category(inter2, parts[1])
                return
            if action == "buy":
                await self._do_buy(inter2, parts[2], int(parts[1]))
            elif action == "sell":
                await self._do_sell(inter2, parts[2], int(parts[1]))
            elif action == "buymodal":
                await inter2.response.send_modal(_BuyModal(self.bot, parts[1]))
            elif action == "sellmodal":
                await inter2.response.send_modal(
                    _SellModal(self.bot, parts[1], owned)
                )

        view = SelectView(
            interaction.user.id,
            placeholder="Choose an action...",
            options=actions,
            on_select=on_action,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _do_buy(
        self, interaction: discord.Interaction, item_id: str, quantity: int
    ) -> None:
        try:
            total, _ = await self.bot.shop.buy(interaction.user.id, item_id, quantity)
        except (NotInShop, InsufficientFunds, ValueError) as exc:
            await interaction.response.send_message(
                embed=error("Purchase failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Purchase complete",
                f"Bought **{quantity}× {item_id}** for **{qc(total)}**.",
            ),
            ephemeral=True,
        )

    async def _do_sell(
        self, interaction: discord.Interaction, item_id: str, quantity: int
    ) -> None:
        try:
            total, _ = await self.bot.shop.sell(
                interaction.user.id, item_id, quantity
            )
        except (NotInShop, NotSellable, InsufficientItems, ValueError) as exc:
            await interaction.response.send_message(
                embed=error("Sale failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Sale complete",
                f"Sold **{quantity}× {item_id}** for **{qc(total)}**.",
            ),
            ephemeral=True,
        )


class _BuyModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Quantity", min_length=1, max_length=6)

    def __init__(self, bot, item_id: str) -> None:
        super().__init__(title=f"Buy {item_id}"[:45])
        self.bot = bot
        self.item_id = item_id
        self.quantity.default = "1"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error("Invalid quantity"), ephemeral=True
            )
            return
        if qty <= 0:
            await interaction.response.send_message(
                embed=error("Quantity must be positive"), ephemeral=True
            )
            return
        try:
            total, _ = await self.bot.shop.buy(interaction.user.id, self.item_id, qty)
        except (NotInShop, InsufficientFunds, ValueError) as exc:
            await interaction.response.send_message(
                embed=error("Purchase failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Purchase complete",
                f"Bought **{qty}× {self.item_id}** for **{qc(total)}**.",
            ),
            ephemeral=True,
        )


class _SellModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Quantity", min_length=1, max_length=6)

    def __init__(self, bot, item_id: str, owned: int) -> None:
        super().__init__(title=f"Sell {item_id}"[:45])
        self.bot = bot
        self.item_id = item_id
        self.quantity.default = "1"
        self.quantity.placeholder = f"You own {owned}"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error("Invalid quantity"), ephemeral=True
            )
            return
        if qty <= 0:
            await interaction.response.send_message(
                embed=error("Quantity must be positive"), ephemeral=True
            )
            return
        try:
            total, _ = await self.bot.shop.sell(
                interaction.user.id, self.item_id, qty
            )
        except (NotInShop, NotSellable, InsufficientItems, ValueError) as exc:
            await interaction.response.send_message(
                embed=error("Sale failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Sale complete",
                f"Sold **{qty}× {self.item_id}** for **{qc(total)}**.",
            ),
            ephemeral=True,
        )


async def setup(bot) -> None:
    await bot.add_cog(Shop(bot))
