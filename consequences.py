"""
game/consequences.py
--------------------
Consequence Pool: who loses, and what they have to do.

Two separate jobs:

  1. READING THE DICE   find the lowest roll, and handle ties (sudden death)
  2. READING THE JSON   load config/consequences.json so the booth organiser
                        can edit the dares in Notepad without touching Python

If the JSON file is missing or broken the game does NOT crash. It falls back
to a small built-in list and carries on, because a crashed booth is worse than
a boring dare.
"""

import json
import os
import random

from config import settings


# Used only if config/consequences.json cannot be read.
FALLBACK = {
    "WARM UP": {"level": 1, "enabled": True,
                "items": ["Strike a funny pose for 5 seconds"]},
    "EASY": {"level": 2, "enabled": True, "items": ["Do 5 squats"]},
    "FUNNY": {"level": 3, "enabled": True,
              "items": ["Act like a chicken for 5 seconds"]},
    "HARD": {"level": 4, "enabled": True, "items": ["Do 10 jumping jacks"]},
    "EXTREME": {"level": 5, "enabled": True, "items": ["Do 20 squats"]},
}


class ConsequenceBook:
    """The list of dares, loaded from JSON."""

    def __init__(self, path=None):
        self.path = path or settings.CONSEQUENCES_FILE
        self.categories = {}
        self.load_error = None
        self.load()

    # ==================================================================== load
    def load(self):
        """Read the JSON file. Never raises — it reports instead."""
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            categories = data["categories"]

            # Keep every level that has items. Unlike before we KEEP the
            # switched-off ones too, because the operator can now turn levels
            # back on from the game screen without editing the file.
            cleaned = {}
            for index, (name, entry) in enumerate(categories.items()):
                items = [str(item) for item in entry.get("items", []) if item]
                if not items:
                    continue
                cleaned[name.upper()] = {
                    "enabled": bool(entry.get("enabled", True)),
                    "level": int(entry.get("level", index + 1)),
                    "items": items,
                }

            if not cleaned:
                raise ValueError("no categories with items")
            if not any(entry["enabled"] for entry in cleaned.values()):
                # everything switched off in the file: turn the first one back
                # on so a round can still be played
                first = sorted(cleaned, key=lambda n: cleaned[n]["level"])[0]
                cleaned[first]["enabled"] = True

            self.categories = cleaned
            self.load_error = None

        except FileNotFoundError:
            self.categories = dict(FALLBACK)
            self.load_error = "consequences.json not found - using defaults"
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
            self.categories = dict(FALLBACK)
            self.load_error = f"consequences.json problem ({error}) - using defaults"

    # ================================================================== picking
    def category_names(self):
        """Every level, easiest first."""
        return sorted(self.categories.keys(),
                      key=lambda name: (self.categories[name]["level"], name))

    def enabled_names(self):
        """Only the levels currently switched on."""
        return [name for name in self.category_names()
                if self.categories[name]["enabled"]]

    def level_of(self, name):
        return self.categories[name]["level"]

    def is_enabled(self, name):
        return bool(self.categories.get(name, {}).get("enabled", False))

    def toggle(self, name):
        """Switch a level on or off. Refuses to switch the last one off.

        Returns the new state. Leaving zero levels enabled would mean there is
        no dare to give the loser, so the last one always stays on.
        """
        if name not in self.categories:
            return False
        entry = self.categories[name]
        if entry["enabled"] and len(self.enabled_names()) <= 1:
            return True                       # keep the last level switched on
        entry["enabled"] = not entry["enabled"]
        return entry["enabled"]

    def random_consequence(self, category=None):
        """Return (level_name, dare_text).

        With no category given it picks from the levels that are switched on,
        so the operator controls how hard the booth is without editing a file.
        """
        names = self.enabled_names() or self.category_names()
        if not names:
            return "EASY", "Do 5 jumping jacks"

        if category is None or category.upper() not in self.categories:
            category = random.choice(names)
        else:
            category = category.upper()

        return category, random.choice(self.categories[category]["items"])


# ===========================================================================
# READING THE DICE
# ===========================================================================

def lowest_rollers(results, colors=None):
    """Return the list of colours that rolled the lowest number.

    One name in the list  -> that player loses.
    Two or more names     -> a tie, so those players go to sudden death.

        >>> lowest_rollers({"RED": 5, "BLUE": 2, "GREEN": 2})
        ['BLUE', 'GREEN']
    """
    if colors is None:
        colors = list(results.keys())
    if not colors:
        return []

    lowest = min(results[color] for color in colors)
    return [color for color in colors if results[color] == lowest]


def player_colors(player_count):
    """Give each player a colour, in the fixed order from the design doc."""
    count = max(settings.MIN_PLAYERS, min(settings.MAX_PLAYERS, player_count))
    return settings.COLOR_ORDER[:count]
