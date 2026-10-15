from __future__ import annotations

from quadton.data.recipes import RecipeDef, by_id
from quadton.db.database import Database
from quadton.services.currency import CurrencyService
from quadton.services.inventory import InventoryService


class CraftingError(Exception):
    pass


class UnknownRecipe(CraftingError):
    pass


class MissingIngredients(CraftingError):
    pass


class CraftingService:
    """Atomic crafting. All inputs consumed and output granted in one tx."""

    def __init__(
        self,
        db: Database,
        currency: CurrencyService,
        inventory: InventoryService,
    ) -> None:
        self.db = db
        self.currency = currency
        self.inventory = inventory

    async def craft(
        self, user_id: int, recipe_id: str, quantity: int = 1
    ) -> tuple[RecipeDef, int]:
        """Craft `quantity` batches. Return (recipe, total_fee)."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        recipe = by_id(recipe_id)
        if recipe is None:
            raise UnknownRecipe(recipe_id)

        total_fee = recipe.fee * quantity

        async with self.db.transaction() as conn:
            await self.currency.ensure_user(conn, user_id)

            # Verify all inputs first (fail fast, no partial state).
            for item_id, need_per_batch in recipe.inputs:
                need = need_per_batch * quantity
                cur = await conn.execute(
                    "SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",
                    (user_id, item_id),
                )
                row = await cur.fetchone()
                have = int(row[0]) if row else 0
                if have < need:
                    raise MissingIngredients(
                        f"need {need}× {item_id}, have {have}"
                    )

            # Consume inputs.
            for item_id, need_per_batch in recipe.inputs:
                await self.inventory.consume(
                    conn, user_id, item_id, need_per_batch * quantity
                )

            # Take the fee (sink).
            if total_fee > 0:
                await self.currency.debit_in_tx(
                    conn, user_id, total_fee, "CRAFTING_FEE",
                    count_as_spent=True,
                    meta={"recipe_id": recipe_id, "quantity": quantity},
                )

            # Grant output.
            await self.inventory.grant(
                conn, user_id, recipe.output_item, recipe.output_qty * quantity
            )

        return recipe, total_fee
