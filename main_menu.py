"""
ui/main_menu.py
---------------
The first screen the player sees.

Since Phase 2 the menu no longer draws its own background. It borrows the
same ArcadeScene the game modes use, so the whole game feels like one place.
The die artwork also comes from game/dice.py now instead of being duplicated
here.
"""

import random

import pygame

from config import settings
from game import cube
from game.game_manager import Screen, GameState
from ui import ui
from ui.scene import ArcadeScene


class FloatingDie:
    """One slowly drifting die used as menu decoration.

    'depth' fakes distance: far dice are small, dim and slow, near dice are
    big, bright and fast. That difference alone already sells the 2.5D look.
    """

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.reset(start_anywhere=True)

    def reset(self, start_anywhere=False):
        self.depth = random.uniform(0.35, 1.0)
        self.size = ui.lerp(13, 34, self.depth)
        self.alpha = int(ui.lerp(55, 165, self.depth))
        self.speed = ui.lerp(10, 34, self.depth)
        self.drift = random.uniform(-12, 12)
        # a slow tumble on all three axes, so the menu dice turn like the
        # real ones instead of spinning like flat stickers
        self.ax = random.uniform(0, 360)
        self.ay = random.uniform(0, 360)
        self.az = random.uniform(0, 360)
        self.wx = random.uniform(-22, 22)
        self.wy = random.uniform(-26, 26)
        self.wz = random.uniform(-16, 16)

        self.color = settings.DICE_COLORS[random.choice(settings.COLOR_ORDER)]
        self.value = random.choice(settings.DICE_FACES)

        self.x = random.uniform(0, self.screen_w)
        self.y = (random.uniform(0, self.screen_h) if start_anywhere
                  else self.screen_h + 60)

    def update(self, dt):
        self.y -= self.speed * dt        # drift upwards
        self.x += self.drift * dt
        self.ax = (self.ax + self.wx * dt) % 360
        self.ay = (self.ay + self.wy * dt) % 360
        self.az = (self.az + self.wz * dt) % 360

        if self.y < -80:
            self.reset()

    def draw(self, surface):
        image = cube.render_to_surface(self.size, self.color,
                                       self.ax, self.ay, self.az)
        image.set_alpha(self.alpha)
        surface.blit(image, image.get_rect(center=(int(self.x), int(self.y))))


class MainMenu(Screen):

    def __init__(self, manager):
        super().__init__(manager)

        self.scene = ArcadeScene()          # shared room, pillars included
        self.floaters = [FloatingDie(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
                         for _ in range(14)]
        self.time = 0.0

        # ---- menu buttons -------------------------------------------------
        # Seven modes no longer fit in one column, so they are grouped into
        # two: games you bet credits on, and free games for a crowd. Grouping
        # them also tells a player at a glance which is which.
        button_w, button_h, gap = 372, 50, 10
        left_x = settings.SCREEN_WIDTH // 2 - button_w - 20
        right_x = settings.SCREEN_WIDTH // 2 + 20
        start_y = 268

        betting = [
            ("COLOR ROYALE", settings.NEON_CYAN, GameState.COLOR_ROYALE),
            ("OVER / UNDER", settings.NEON_CYAN, GameState.OVER_UNDER),
            ("LUCKY THREE", settings.NEON_CYAN, GameState.LUCKY_THREE),
            ("BEAT THE HOUSE", settings.NEON_CYAN, GameState.BEAT_HOUSE),
        ]
        party = [
            ("CONSEQUENCE POOL", settings.NEON_PINK, GameState.CONSEQUENCE_POOL),
            ("BATTLE ROYALE", settings.NEON_PINK, GameState.BATTLE_ROYALE),
            ("ARCADE DUEL", settings.NEON_PINK, GameState.ARCADE_DUEL),
        ]

        self.buttons = []
        self.headings = [("BETTING GAMES", left_x, settings.NEON_CYAN),
                         ("PARTY GAMES", right_x, settings.NEON_PINK)]
        self.heading_y = start_y - 26

        for column_x, group in ((left_x, betting), (right_x, party)):
            for index, (label, accent, state) in enumerate(group):
                rect = pygame.Rect(column_x, start_y + index * (button_h + gap),
                                   button_w, button_h)
                self.buttons.append(
                    ui.Button(rect, label, accent=accent, font_size=21,
                              on_click=lambda s=state: manager.change_state(s)))

        # settings and exit sit underneath, smaller, side by side
        bottom_y = start_y + 4 * (button_h + gap) + 18
        small_w = 240
        self.buttons.append(ui.Button(
            pygame.Rect(settings.SCREEN_WIDTH // 2 - small_w - 10, bottom_y,
                        small_w, 44),
            "SETTINGS", accent=settings.TEXT_DIM, font_size=19,
            on_click=lambda: manager.change_state(GameState.SETTINGS)))
        self.buttons.append(ui.Button(
            pygame.Rect(settings.SCREEN_WIDTH // 2 + 10, bottom_y, small_w, 44),
            "EXIT", accent=settings.LOSE_RED, font_size=19,
            on_click=manager.quit_game))

    # ------------------------------------------------------------ input ---
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.quit_game()

        for button in self.buttons:
            button.handle_event(event)

    # ----------------------------------------------------------- update ---
    def update(self, dt):
        self.time += dt
        self.scene.update(dt)
        for floater in self.floaters:
            floater.update(dt)
        for button in self.buttons:
            button.update(dt)

    # ------------------------------------------------------------- draw ---
    def draw(self, surface):
        self.scene.draw_back(surface)

        for floater in self.floaters:
            floater.draw(surface)

        self.scene.draw_front(surface)
        self._draw_title(surface)

        # which column is which
        for text, x, color in self.headings:
            ui.draw_text(surface, text, (x + 8, self.heading_y), size=14,
                         color=color, bold=True)

        for button in self.buttons:
            button.draw(surface)

        ui.draw_credit_chip(surface, self.manager.credits,
                            topright=(settings.SCREEN_WIDTH - 24, 24))
        ui.draw_text(surface, "Click a mode to start  ·  ESC quits",
                     (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 26),
                     size=18, color=settings.TEXT_DIM, align="center")

    def _draw_title(self, surface):
        center_x = settings.SCREEN_WIDTH // 2
        ui.draw_glow_text(surface, settings.GAME_TITLE, (center_x, 118), size=88,
                          color=settings.NEON_CYAN, align="center", glow=10)
        ui.draw_text(surface, "2 . 5 D   A R C A D E   D I C E   M A C H I N E",
                     (center_x, 178), size=20, color=settings.TEXT_DIM,
                     bold=True, align="center")
        ui.draw_divider(surface, (center_x, 212), width=230)
