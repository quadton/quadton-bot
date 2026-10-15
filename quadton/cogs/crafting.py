from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.data.recipes import CATEGORIES, RECIPES, by_id, in_category
from quadton.services.crafting import (
    CraftingError,
    MissingIngredients,
    UnknownRecipe,
)
from quadton.services.currency import InsufficientFunds
from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_MARKET, empty_state, error, info, qc, success


class Crafting(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="recipes",
        description="Browse all craftable recipes.",
    )
    async def recipes(self, interaction: discord.Interaction) -> None:
        options = [
            discord.SelectOption(label=c.title(), value=c, description=f"{c} recipes")
            for c in CATEGORIES
        ]

        async def on_cat(inter2: discord.Interaction, category: str) -> None:
            await self._show_recipes(inter2, category)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a recipe category...",
            options=options,
            on_select=on_cat,
        )
        embed = info(
            "🛠️ Recipes",
            "Browse the recipe book by category. Recipes are consumed "
            "atomically: ingredients and fees are taken only if the craft succeeds.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _show_recipes(
        self, interaction: discord.Interaction, category: str
    ) -> None:
        recipes = in_category(category)
        if not recipes:
            await interaction.response.edit_message(
                embed=empty_state(f"No recipes in **{category}**."), view=None
            )
            return
        options: list[discord.SelectOption] = []
        for r in recipes[:25]:
            from quadton.data.items import by_id as item_by_id

            out = item_by_id(r.output_item)
            name = out.name if out else r.output_item
            inputs_text = ", ".join(f"{q}× {i}" for i, q in r.inputs)
            options.append(
                discord.SelectOption(
                    label=f"{name} ×{r.output_qty}"[:100],
                    value=r.recipe_id,
                    description=f"{inputs_text} · fee {r.fee} QC"[:100],
                )
            )

        async def on_recipe(inter2: discord.Interaction, recipe_id: str) -> None:
            await self._show_recipe(inter2, recipe_id, category)

        view = SelectView(
            interaction.user.id,
            placeholder=f"Choose a {category} recipe...",
            options=options,
            on_select=on_recipe,
        )
        embed = info(f"🛠️ {category.title()} Recipes", "Pick one to inspect.")
        embed.color = COLOR_MARKET
        await interaction.response.edit_message(embed=embed, view=view)

    async def _show_recipe(
        self, interaction: discord.Interaction, recipe_id: str, category: str
    ) -> None:
        from quadton.data.items import by_id as item_by_id

        recipe = by_id(recipe_id)
        if recipe is None:
            await interaction.response.edit_message(
                embed=error("Recipe not found"), view=None
            )
            return
        output = item_by_id(recipe.output_item)
        embed = discord.Embed(
            title=f"Craft: {output.name if output else recipe.output_item}",
            color=COLOR_MARKET,
        )
        lines = []
        for item_id, qty in recipe.inputs:
            have = await self.bot.inventory.get_quantity(interaction.user.id, item_id)
            mark = "✅" if have >= qty else "❌"
            lines.append(f"{mark} {qty}× {item_id} (you have {have})")
        embed.add_field(name="Ingredients", value="\n".join(lines), inline=False)
        embed.add_field(name="Produces", value=f"{recipe.output_qty}× {recipe.output_item}")
        embed.add_field(name="Fee", value=qc(recipe.fee))

        actions = [
            discord.SelectOption(label="Craft 1", value=f"craft:1:{recipe_id}"),
            discord.SelectOption(label="Craft 5", value=f"craft:5:{recipe_id}"),
            discord.SelectOption(label="← Back", value=f"back:{category}"),
        ]

        async def on_action(inter2: discord.Interaction, value: str) -> None:
            parts = value.split(":", 2)
            if parts[0] == "back":
                await self._show_recipes(inter2, parts[1])
                return
            await self._do_craft(inter2, parts[2], int(parts[1]))

        view = SelectView(
            interaction.user.id,
            placeholder="Choose an action...",
            options=actions,
            on_select=on_action,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @app_commands.command(name="craft", description="Craft an item from a recipe.")
    @app_commands.describe(recipe_id="Recipe ID (see /recipes)", quantity="Batches to craft")
    async def craft(
        self,
        interaction: discord.Interaction,
        recipe_id: str,
        quantity: int = 1,
    ) -> None:
        if quantity <= 0:
            await interaction.response.send_message(
                embed=error("Quantity must be positive"), ephemeral=True
            )
            return
        try:
            recipe, fee = await self.bot.crafting.craft(
                interaction.user.id, recipe_id, quantity
            )
        except UnknownRecipe:
            await interaction.response.send_message(
                embed=error("Unknown recipe", f"No recipe `{recipe_id}`."),
                ephemeral=True,
            )
            return
        except MissingIngredients as exc:
            await interaction.response.send_message(
                embed=error("Missing ingredients", str(exc)), ephemeral=True
            )
            return
        except InsufficientFunds:
            await interaction.response.send_message(
                embed=error("Not enough QC for the crafting fee"), ephemeral=True
            )
            return
        except CraftingError as exc:
            await interaction.response.send_message(
                embed=error("Craft failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success(
                "Crafted",
                f"Made **{recipe.output_qty * quantity}× {recipe.output_item}** "
                f"for a fee of **{qc(fee)}**.",
            ),
            ephemeral=True,
        )

    async def _do_craft(
        self, interaction: discord.Interaction, recipe_id: str, quantity: int
    ) -> None:
        try:
            recipe, fee = await self.bot.crafting.craft(
                interaction.user.id, recipe_id, quantity
            )
        except MissingIngredients as exc:
            await interaction.response.send_message(
                embed=error("Missing ingredients", str(exc)), ephemeral=True
            )
            return
        except InsufficientFunds:
            await interaction.response.send_message(
                embed=error("Not enough QC for the crafting fee"), ephemeral=True
            )
            return
        except CraftingError as exc:
            await interaction.response.send_message(
                embed=error("Craft failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success(
                "Crafted",
                f"Made **{recipe.output_qty * quantity}× {recipe.output_item}** "
                f"for a fee of **{qc(fee)}**.",
            ),
            ephemeral=True,
        )


async def setup(bot) -> None:
    await bot.add_cog(Crafting(bot))
