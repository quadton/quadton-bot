from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.ui.base import ConfirmView, SelectView
from quadton.ui.embeds import (
    COLOR_MARKET,
    empty_state,
    error,
    info,
    qc,
    success,
)


def _item_choices() -> list[discord.SelectOption]:
    """Top 25 items by name for the primary dropdown."""
    from quadton.data.items import ITEMS

    options: list[discord.SelectOption] = []
    for it in sorted(ITEMS, key=lambda i: i.name)[:25]:
        options.append(
            discord.SelectOption(
                label=it.name[:100],
                value=it.item_id,
                description=f"{it.rarity.title()} · {it.category}"[:100],
            )
        )
    return options


class Market(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="market",
        description="Browse the Quadton market with dropdown navigation.",
    )
    async def market(self, interaction: discord.Interaction) -> None:
        view = SelectView(
            interaction.user.id,
            placeholder="Select an item to inspect...",
            options=_item_choices(),
            on_select=self._on_item_selected,
        )
        embed = info(
            "Quadton Market",
            "Choose an item from the dropdown to view its order book, "
            "recent trades, and reference price.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _on_item_selected(
        self, interaction: discord.Interaction, item_id: str
    ) -> None:
        embed = await self._build_item_embed(item_id)

        options = [
            discord.SelectOption(label="Buy from market", value=f"buy:{item_id}"),
            discord.SelectOption(label="Sell to market", value=f"sell:{item_id}"),
            discord.SelectOption(label="View price history", value=f"hist:{item_id}"),
            discord.SelectOption(label="Back to item list", value="back"),
        ]

        async def on_action(inter2: discord.Interaction, value: str) -> None:
            if value == "back":
                await inter2.response.edit_message(
                    embed=info(
                        "Quadton Market",
                        "Choose an item from the dropdown to inspect it.",
                    ),
                    view=SelectView(
                        inter2.user.id,
                        placeholder="Select an item to inspect...",
                        options=_item_choices(),
                        on_select=self._on_item_selected,
                    ),
                )
                return
            action, target = value.split(":", 1)
            if action == "buy":
                await self._start_buy(inter2, target)
            elif action == "sell":
                await self._start_sell(inter2, target)
            elif action == "hist":
                await self._show_history(inter2, target)

        action_view = SelectView(
            interaction.user.id,
            placeholder="Choose an action...",
            options=options,
            on_select=on_action,
        )
        await interaction.response.edit_message(embed=embed, view=action_view)

    async def _build_item_embed(self, item_id: str) -> discord.Embed:
        from quadton.data.items import by_id

        definition = by_id(item_id)
        if definition is None:
            return error("Unknown item", f"No item with ID `{item_id}`.")

        bids = await self.bot.market.order_book(item_id, "buy", limit=5)
        asks = await self.bot.market.order_book(item_id, "sell", limit=5)
        reference = await self.bot.market.reference_price(
            item_id, definition.base_value
        )

        embed = discord.Embed(
            title=definition.name,
            description=definition.description,
            color=COLOR_MARKET,
        )
        embed.add_field(name="Rarity", value=definition.rarity.title(), inline=True)
        embed.add_field(name="Category", value=definition.category.title(), inline=True)
        embed.add_field(name="Reference price", value=qc(reference), inline=True)

        bid_text = (
            "\n".join(f"`{r['price']:>7,} QC` × {r['remaining']}" for r in bids)
            or "*No buy orders.*"
        )
        ask_text = (
            "\n".join(f"`{r['price']:>7,} QC` × {r['remaining']}" for r in asks)
            or "*No sell orders.*"
        )
        embed.add_field(name="Bids (buy orders)", value=bid_text, inline=True)
        embed.add_field(name="Asks (sell orders)", value=ask_text, inline=True)
        return embed

    async def _start_buy(self, interaction: discord.Interaction, item_id: str) -> None:
        from quadton.data.items import by_id

        definition = by_id(item_id)
        if definition is None:
            await interaction.response.send_message(
                embed=error("Unknown item"), ephemeral=True
            )
            return
        best_ask = await self.bot.market.best_price(item_id, "sell")
        suggestion = best_ask or definition.base_value
        await interaction.response.send_modal(
            _BuyModal(self.bot, item_id, definition.name, suggestion)
        )

    async def _start_sell(self, interaction: discord.Interaction, item_id: str) -> None:
        from quadton.data.items import by_id

        definition = by_id(item_id)
        if definition is None:
            await interaction.response.send_message(
                embed=error("Unknown item"), ephemeral=True
            )
            return
        owned = await self.bot.inventory.get_quantity(interaction.user.id, item_id)
        if owned <= 0:
            await interaction.response.send_message(
                embed=error(
                    "You don't own this item",
                    f"You have 0 × {definition.name}.",
                ),
                ephemeral=True,
            )
            return
        best_bid = await self.bot.market.best_price(item_id, "buy")
        suggestion = best_bid or definition.base_value
        await interaction.response.send_modal(
            _SellModal(self.bot, item_id, definition.name, suggestion, owned)
        )

    async def _show_history(
        self, interaction: discord.Interaction, item_id: str
    ) -> None:
        from quadton.data.items import by_id

        definition = by_id(item_id)
        rows = await self.bot.market.recent_trades(item_id, limit=10)
        if not rows:
            embed = empty_state(f"No trades recorded yet for {item_id}.")
            await interaction.response.edit_message(embed=embed, view=None)
            return
        lines = [
            f"<t:{r['created_at']}:R> — **{r['price']:,} QC** × {r['quantity']}"
            for r in rows
        ]
        embed = discord.Embed(
            title=f"Price History — {definition.name if definition else item_id}",
            description="\n".join(lines),
            color=COLOR_MARKET,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @app_commands.command(
        name="my-orders",
        description="View your open market orders and cancel one with a dropdown.",
    )
    async def my_orders(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.market.user_orders(interaction.user.id)
        if not rows:
            await interaction.response.send_message(
                embed=empty_state("You have no open market orders."),
                ephemeral=True,
            )
            return

        options: list[discord.SelectOption] = []
        for r in rows[:25]:
            side = r["side"].upper()
            label = f"{side} {r['item_id']} ×{r['remaining']} @ {r['price']:,} QC"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=str(r["order_id"]),
                    description=f"Order #{r['order_id']}",
                )
            )

        embed = info(
            "Your Open Orders",
            "Pick an order to cancel. Cancelling returns escrowed assets.",
        )
        embed.color = COLOR_MARKET

        async def on_cancel(inter2: discord.Interaction, order_id: str) -> None:
            try:
                order_int = int(order_id)
            except ValueError:
                await inter2.response.edit_message(
                    embed=error("Invalid order"), view=None
                )
                return

            async def do_cancel(confirm_inter: discord.Interaction) -> None:
                try:
                    await self.bot.market.cancel_order(
                        confirm_inter.user.id, order_int
                    )
                except Exception as exc:  # noqa: BLE001
                    await confirm_inter.response.edit_message(
                        embed=error("Cancel failed", str(exc)), view=None
                    )
                    return
                await confirm_inter.response.edit_message(
                    embed=success(
                        "Order cancelled",
                        "Escrowed assets have been returned to you.",
                    ),
                    view=None,
                )

            confirm = ConfirmView(inter2.user.id, on_confirm=do_cancel)
            await inter2.response.edit_message(
                embed=error(
                    "Confirm cancellation",
                    f"Cancel order #{order_int}? Escrowed assets will be returned.",
                ),
                view=confirm,
            )

        view = SelectView(
            interaction.user.id,
            placeholder="Select an order to cancel...",
            options=options,
            on_select=on_cancel,
        )
        await view.start(interaction, embed=embed)


class _BuyModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Quantity", min_length=1, max_length=6)
    price = discord.ui.TextInput(
        label="Max price per unit (QC)", min_length=1, max_length=12
    )

    def __init__(self, bot, item_id: str, item_name: str, suggested: int) -> None:
        super().__init__(title=f"Buy {item_name}"[:45])
        self.bot = bot
        self.item_id = item_id
        self.price.default = str(suggested)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.quantity.value)
            price = int(self.price.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error("Invalid input", "Quantity and price must be integers."),
                ephemeral=True,
            )
            return
        if qty <= 0 or price <= 0:
            await interaction.response.send_message(
                embed=error("Invalid input", "Both values must be positive."),
                ephemeral=True,
            )
            return
        try:
            order_id = await self.bot.market.place_buy_order(
                interaction.user.id, self.item_id, qty, price
            )
        except Exception as exc:  # noqa: BLE001
            await interaction.response.send_message(
                embed=error("Order failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Buy order placed",
                f"Order **#{order_id}** for {qty} × {self.item_id} at "
                f"{qc(price)} max per unit.",
            ),
            ephemeral=True,
        )


class _SellModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Quantity", min_length=1, max_length=6)
    price = discord.ui.TextInput(
        label="Ask price per unit (QC)", min_length=1, max_length=12
    )

    def __init__(
        self, bot, item_id: str, item_name: str, suggested: int, owned: int
    ) -> None:
        super().__init__(title=f"Sell {item_name}"[:45])
        self.bot = bot
        self.item_id = item_id
        self.quantity.default = "1"
        self.quantity.placeholder = f"You own {owned}"
        self.price.default = str(suggested)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.quantity.value)
            price = int(self.price.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error("Invalid input", "Quantity and price must be integers."),
                ephemeral=True,
            )
            return
        if qty <= 0 or price <= 0:
            await interaction.response.send_message(
                embed=error("Invalid input", "Both values must be positive."),
                ephemeral=True,
            )
            return
        try:
            order_id = await self.bot.market.place_sell_order(
                interaction.user.id, self.item_id, qty, price
            )
        except Exception as exc:  # noqa: BLE001
            await interaction.response.send_message(
                embed=error("Order failed", str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success(
                "Sell order placed",
                f"Order **#{order_id}** for {qty} × {self.item_id} at "
                f"{qc(price)} per unit.",
            ),
            ephemeral=True,
        )


async def setup(bot) -> None:
    await bot.add_cog(Market(bot))
