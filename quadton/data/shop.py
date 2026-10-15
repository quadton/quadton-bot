from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopEntry:
    item_id: str
    buy_price: int    # what the player pays to buy from the shop
    sell_price: int   # what the shop pays the player when selling back
    category: str
    stock: int | None = None  # None = unlimited


# NPC shop catalog.
#
# Only raw resources and basic consumables are sold back to the NPC shop.
# Equipment, gems, cards, and luxury goods must be crafted, found, or traded
# between players — they are not buyable from the shop and cannot be sold to it.
SHOP_ENTRIES: tuple[ShopEntry, ...] = (
    # Resources — buyable, sellable
    ShopEntry("wood", 12, 3, "resources"),
    ShopEntry("stone", 10, 2, "resources"),
    ShopEntry("fiber", 8, 2, "resources"),
    ShopEntry("sand", 6, 1, "resources"),
    ShopEntry("copper_ore", 20, 5, "resources"),
    ShopEntry("iron_ore", 45, 12, "resources"),
    ShopEntry("silver_ore", 120, 30, "resources"),
    ShopEntry("gold_ore", 180, 45, "resources"),
    # Food & potions — buyable, sellable
    ShopEntry("apple", 15, 4, "consumables"),
    ShopEntry("bread", 22, 6, "consumables"),
    ShopEntry("soup", 55, 14, "consumables"),
    ShopEntry("health_potion", 90, 25, "consumables"),
    ShopEntry("xp_potion", 260, 70, "consumables"),
    ShopEntry("prosperity_potion", 650, 175, "consumables"),
    ShopEntry("focus_potion", 220, 60, "consumables"),
    ShopEntry("pet_treat", 100, 28, "consumables"),
    # Tools — buyable only
    ShopEntry("pickaxe", 130, 0, "tools"),
    ShopEntry("fishing_rod", 120, 0, "tools"),
)


CATEGORIES = ("resources", "consumables", "tools")


def by_item(item_id: str) -> ShopEntry | None:
    for e in SHOP_ENTRIES:
        if e.item_id == item_id:
            return e
    return None


def in_category(category: str) -> tuple[ShopEntry, ...]:
    return tuple(e for e in SHOP_ENTRIES if e.category == category)
