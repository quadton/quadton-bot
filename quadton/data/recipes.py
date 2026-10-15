from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeDef:
    recipe_id: str
    output_item: str
    output_qty: int
    inputs: tuple[tuple[str, int], ...]
    fee: int = 0
    category: str = "crafting"


RECIPES: tuple[RecipeDef, ...] = (
    # Basic
    RecipeDef(
        "bread_from_fiber",
        "bread", 1,
        (("fiber", 3), ("apple", 1)),
        fee=5,
        category="food",
    ),
    RecipeDef(
        "soup_hearty",
        "soup", 1,
        (("apple", 2), ("bread", 1), ("fiber", 2)),
        fee=15,
        category="food",
    ),
    # Potions
    RecipeDef(
        "health_potion_brew",
        "health_potion", 1,
        (("apple", 2), ("fiber", 1)),
        fee=20,
        category="potions",
    ),
    RecipeDef(
        "focus_potion_brew",
        "focus_potion", 1,
        (("soup", 1), ("silver_ore", 1)),
        fee=60,
        category="potions",
    ),
    RecipeDef(
        "xp_potion_brew",
        "xp_potion", 1,
        (("gold_ore", 1), ("soup", 1)),
        fee=75,
        category="potions",
    ),
    RecipeDef(
        "prosperity_potion_brew",
        "prosperity_potion", 1,
        (("gold_ore", 2), ("silver_ore", 2), ("soup", 2)),
        fee=180,
        category="potions",
    ),
    # Tools
    RecipeDef(
        "pickaxe_forge",
        "pickaxe", 1,
        (("iron_ore", 2), ("wood", 3)),
        fee=30,
        category="tools",
    ),
    RecipeDef(
        "fishing_rod_craft",
        "fishing_rod", 1,
        (("fiber", 5), ("wood", 2)),
        fee=25,
        category="tools",
    ),
    # Weapons & armor
    RecipeDef(
        "rusty_sword_forge",
        "rusty_sword", 1,
        (("iron_ore", 1), ("wood", 1)),
        fee=25,
        category="equipment",
    ),
    RecipeDef(
        "iron_sword_forge",
        "iron_sword", 1,
        (("iron_ore", 3), ("wood", 2)),
        fee=75,
        category="equipment",
    ),
    RecipeDef(
        "steel_armor_forge",
        "steel_armor", 1,
        (("iron_ore", 5), ("mithril_ore", 1), ("silver_ore", 2)),
        fee=200,
        category="equipment",
    ),
    # Cards (conversion)
    RecipeDef(
        "common_to_rare_card",
        "card_rare", 1,
        (("card_common", 5), ("fiber", 3)),
        fee=100,
        category="collectibles",
    ),
)


CATEGORIES = ("food", "potions", "tools", "equipment", "collectibles")


def by_id(recipe_id: str) -> RecipeDef | None:
    for r in RECIPES:
        if r.recipe_id == recipe_id:
            return r
    return None


def in_category(category: str) -> tuple[RecipeDef, ...]:
    return tuple(r for r in RECIPES if r.category == category)
