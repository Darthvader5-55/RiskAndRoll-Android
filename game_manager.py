"""
game/game_manager.py
--------------------
The "traffic controller" of the game.

Only ONE screen is active at a time (main menu, Color Royale, ...).
The GameManager remembers which one it is, passes events to it, updates it
and draws it. To move somewhere else a screen just calls:

    self.manager.change_state(GameState.MAIN_MENU)

This keeps main.py tiny and makes each screen independent.
"""

import pygame

from config import settings


class GameState:
    """Just a list of state names. Using constants avoids typo bugs:
    GameState.MAIN_MENU fails loudly if misspelled, "man_menu" would not."""

    MAIN_MENU = "MAIN_MENU"

    # betting games - these use credits
    COLOR_ROYALE = "COLOR_ROYALE"
    OVER_UNDER = "OVER_UNDER"
    LUCKY_THREE = "LUCKY_THREE"
    BEAT_HOUSE = "BEAT_HOUSE"

    # party games - free play, for groups
    CONSEQUENCE_POOL = "CONSEQUENCE_POOL"
    BATTLE_ROYALE = "BATTLE_ROYALE"
    ARCADE_DUEL = "ARCADE_DUEL"

    SETTINGS = "SETTINGS"


class Screen:
    """Base class every screen inherits from.

    A screen only has to override the parts it needs. The four methods below
    are the contract the GameManager relies on.
    """

    def __init__(self, manager):
        self.manager = manager

    def on_enter(self):
        """Called once when this screen becomes active."""
        pass

    def handle_event(self, event):
        """Called for every pygame event (clicks, keys, quit...)."""
        pass

    def update(self, dt):
        """Called once per frame. dt = seconds since the last frame."""
        pass

    def draw(self, surface):
        """Called once per frame, after update."""
        pass


class GameManager:
    """Owns the player's credits and the currently active screen."""

    def __init__(self, surface):
        self.surface = surface
        self.running = True

        # Player data that must survive a screen change lives here.
        self.credits = settings.STARTING_CREDITS

        # One shared sound player for the whole game.
        from game.audio import Audio
        self.audio = Audio()

        self.state = None
        self.current_screen = None
        self.change_state(GameState.MAIN_MENU)

    # ------------------------------------------------------------ switching
    def change_state(self, new_state):
        """Build the screen for new_state and make it the active one."""
        # Imports are inside the method on purpose: the screens import
        # GameManager too, and importing at the top would loop forever.
        from ui.main_menu import MainMenu
        from ui.color_royale_ui import ColorRoyaleUI
        from ui.over_under_ui import OverUnderUI
        from ui.lucky_three_ui import LuckyThreeUI
        from ui.beat_house_ui import BeatHouseUI
        from ui.consequence_ui import ConsequenceUI
        from ui.battle_royale_ui import BattleRoyaleUI
        from ui.duel_ui import DuelUI
        from ui.settings_ui import SettingsUI

        screens = {
            GameState.MAIN_MENU: MainMenu,
            GameState.COLOR_ROYALE: ColorRoyaleUI,
            GameState.OVER_UNDER: OverUnderUI,
            GameState.LUCKY_THREE: LuckyThreeUI,
            GameState.BEAT_HOUSE: BeatHouseUI,
            GameState.CONSEQUENCE_POOL: ConsequenceUI,
            GameState.BATTLE_ROYALE: BattleRoyaleUI,
            GameState.ARCADE_DUEL: DuelUI,
            GameState.SETTINGS: SettingsUI,
        }
        screen = screens.get(new_state, MainMenu)(self)

        self.state = new_state
        self.current_screen = screen
        self.current_screen.on_enter()

    def quit_game(self):
        self.running = False

    # ------------------------------------------------- per-frame delegation
    def handle_event(self, event):
        if self.current_screen:
            self.current_screen.handle_event(event)

    def update(self, dt):
        if self.current_screen:
            self.current_screen.update(dt)

    def draw(self, surface):
        if self.current_screen:
            self.current_screen.draw(surface)
