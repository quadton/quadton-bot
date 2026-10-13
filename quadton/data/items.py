from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


RARITIES = ("common", "uncommon", "rare", "epic", "legendary", "mythic")


@dataclass(frozen=True)
class ItemDef:
    item_id: str
    name: str
    description: str
    rarity: str
    category: str
    base_value: int
    stackable: bool = True
    usable: bool = False
    effect: str | None = None
    duration: int = 0
    strength: float = 0.0


ITEMS: tuple[ItemDef, ...] = (
    # Resources
    ItemDef("wood", "Wood", "Basic lumber.", "common", "resource", 5),
    ItemDef("stone", "Stone", "Common stone.", "common", "resource", 4),
    ItemDef("fiber", "Fiber", "Plant fiber.", "common", "resource", 3),
    ItemDef("sand", "Sand", "Fine sand.", "common", "resource", 2),
    # Food
    ItemDef("apple", "Apple", "A fresh apple.", "common", "food", 6, usable=True,
            effect="heal", strength=20.0),
    ItemDef("bread", "Bread", "A warm loaf.", "common", "food", 10, usable=True,
            effect="heal", strength=25.0),
    ItemDef("soup", "Soup", "Hot soup.", "uncommon", "food", 25, usable=True,
            effect="heal", strength=50.0),
    # Metals
    ItemDef("copper_ore", "Copper Ore", "Copper ore.", "common", "metal", 8),
    ItemDef("iron_ore", "Iron Ore", "Iron ore.", "uncommon", "metal", 20),
    ItemDef("silver_ore", "Silver Ore", "Silver ore.", "rare", "metal", 55),
    ItemDef("gold_ore", "Gold Ore", "Gold ore.", "rare", "metal", 80),
    ItemDef("mithril_ore", "Mithril Ore", "Mithril ore.", "epic", "metal", 220),
    # Gems
    ItemDef("ruby", "Ruby", "A red gem.", "epic", "gem", 400),
    ItemDef("sapphire", "Sapphire", "A blue gem.", "epic", "gem", 380),
    ItemDef("emerald", "Emerald", "A green gem.", "epic", "gem", 420),
    ItemDef("diamond", "Diamond", "A brilliant diamond.", "legendary", "gem", 1200),
    # Tools
    ItemDef("pickaxe", "Pickaxe", "For mining.", "uncommon", "tool", 60),
    ItemDef("fishing_rod", "Fishing Rod", "For fishing.", "uncommon", "tool", 55),
    # Weapons / armor
    ItemDef("rusty_sword", "Rusty Sword", "A worn blade.", "common", "weapon", 30),
    ItemDef("iron_sword", "Iron Sword", "A reliable blade.", "uncommon", "weapon", 150),
    ItemDef("steel_armor", "Steel Armor", "Sturdy plate.", "rare", "armor", 300),
    # Potions / boosters
    ItemDef("health_potion", "Health Potion", "Restores 50 HP.", "common", "potion",
            40, usable=True, effect="heal", strength=50.0),
    ItemDef("xp_potion", "XP Potion", "+50% XP for 30 min.", "uncommon", "potion", 120,
            usable=True, effect="xp_boost", duration=1800, strength=0.5),
    ItemDef("prosperity_potion", "Prosperity Potion", "+20% job pay for 1h.",
            "rare", "potion", 300, usable=True, effect="prosperity",
            duration=3600, strength=0.2),
    ItemDef("focus_potion", "Focus Potion", "+15% gathering yield for 30 min.",
            "uncommon", "potion", 100, usable=True, effect="focus",
            duration=1800, strength=0.15),
    # Pet
    ItemDef("pet_egg_common", "Common Pet Egg", "Hatches a common pet.",
            "common", "pet_egg", 200),
    ItemDef("pet_treat", "Pet Treat", "Boosts pet training.", "uncommon", "pet_item",
            45, usable=True, effect="pet_training", duration=900, strength=0.25),
    # Cards
    ItemDef("card_common", "Common Card", "Collectible card.", "common", "card", 50),
    ItemDef("card_rare", "Rare Card", "Rare collectible card.", "rare", "card", 350),
    # Luxury / vehicles / property
    ItemDef("watch_silver", "Silver Watch", "Elegant watch.", "rare", "luxury", 800),
    ItemDef("watch_gold", "Gold Watch", "Luxury watch.", "epic", "luxury", 2500),
    ItemDef("sports_car", "Sports Car", "A sleek sports car.", "legendary",
            "vehicle", 18000),
    ItemDef("yacht", "Yacht", "A luxury yacht.", "mythic", "vehicle", 65000),
    ItemDef("mansion", "Mansion", "A grand estate.", "mythic", "property", 90000),
    # Seasonal collectible
    ItemDef("season_badge_s1", "Season 1 Badge", "Commemorative badge.",
            "legendary", "collectible", 0),
)


def all_items() -> Iterable[ItemDef]:
    return ITEMS


def by_id(item_id: str) -> ItemDef | None:
    for it in ITEMS:
        if it.item_id == item_id:
            return it
    return None
