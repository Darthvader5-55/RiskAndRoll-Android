"""
ui/duel_ui.py
-------------
ARCADE DUEL — 1 vs 1.

The two players set up their own duel before rolling:

    1. HOW MANY DICE EACH   1, 2 or 3
    2. PICK YOUR COLOURS    they take turns tapping colours off the table.
                            Player A picks, then B, then A... Tapping a
                            colour you already own puts it back.

Then both sides roll their own dice at once, add them up, and the highest
total wins. Equal totals means a rematch.

Phases: SETUP -> READY -> ROLLING -> RESULT
"""

import pygame

from config import settings
from game.duel import Duel, PLAYER_A, PLAYER_B, TIE, COLOR_POOL
from ui import ui
from ui.mode_screen import ModeScreen
from ui.result_ui import ResultPanel

SETUP = "SETUP"        # choosing dice count and colours
READY = "READY"        # both teams picked, waiting for ROLL
ROLLING = "ROLLING"
RESULT = "RESULT"

MAX_ROLL_SECONDS = 6.0

DICE_COUNT_CHOICES = [1, 2, 3]


class DuelUI(ModeScreen):

    title = "ARCADE DUEL"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.duel = Duel(dice_count=3)
        self.phase = SETUP
        self.timer = 0.0
        self.was_tie = False

        self._build_buttons()
        self._sync_dice()
        self.set_message("PLAYER A, PICK A COLOUR", settings.NEON_CYAN)

        card = pygame.Rect(0, 0, 580, 440)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="ROLL AGAIN")
        self.result_panel.primary.on_click = self.next_duel
        self.result_panel.secondary.on_click = self.go_to_menu

    # ================================================================= building
    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        # how many dice each player rolls
        self.count_buttons = []
        for index, count in enumerate(DICE_COUNT_CHOICES):
            rect = pygame.Rect(left + index * (width // 3 + 2), panel.top + 62,
                               width // 3 - 4, 32)
            self.count_buttons.append(
                ui.Button(rect, str(count), font_size=20, accent=settings.GOLD,
                          on_click=lambda c=count: self.set_dice_count(c)))

        # the six colours on the table
        self.color_buttons = []
        for index, name in enumerate(COLOR_POOL):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4),
                               panel.top + 128 + row * 36,
                               width // 2 - 4, 32)
            self.color_buttons.append(
                ui.Button(rect, name, font_size=15,
                          accent=settings.DICE_COLORS[name],
                          on_click=lambda n=name: self.tap_color(n)))

        self.random_button = ui.Button(
            pygame.Rect(left, panel.top + 240, width // 2 - 4, 30),
            "RANDOM", accent=settings.NEON_PINK, font_size=15,
            on_click=self.random_colors)
        self.clear_button = ui.Button(
            pygame.Rect(left + width // 2 + 4, panel.top + 240,
                        width // 2 - 4, 30),
            "CLEAR", accent=settings.TEXT_DIM, font_size=15,
            on_click=self.clear_colors)

        self.roll_button = ui.Button(
            pygame.Rect(left, panel.bottom - 176, width, 50),
            "ROLL BOTH", accent=settings.NEON_LIME, font_size=24,
            on_click=self.start_roll)
        self.change_button = ui.Button(
            pygame.Rect(left, panel.bottom - 120, width, 32),
            "CHANGE COLOURS", accent=settings.TEXT_DIM, font_size=15,
            on_click=self.change_colors)

        self._refresh_buttons()

    def buttons(self):
        return (self.count_buttons + self.color_buttons
                + [self.random_button, self.clear_button, self.roll_button,
                   self.change_button, self.back_button]
                + self.result_panel.buttons())

    def _refresh_buttons(self):
        for button in self.count_buttons:
            button.selected = (button.label == str(self.duel.dice_count))
        for button in self.color_buttons:
            button.selected = (self.duel.owner(button.label) is not None)

    def _sync_dice(self):
        """Only the chosen colours appear inside the machine."""
        chosen = self.duel.in_play()
        self.dice.set_in_play(chosen if chosen else [])

    def _after_pick(self):
        self._refresh_buttons()
        self._sync_dice()

        if self.duel.teams_ready:
            self.phase = READY
            self.set_message("BOTH PLAYERS READY?", settings.NEON_LIME)
        else:
            self.phase = SETUP
            picker = self.duel.next_picker()
            who = "PLAYER A" if picker == PLAYER_A else "PLAYER B"
            color = settings.NEON_CYAN if picker == PLAYER_A else settings.NEON_LIME
            self.set_message(f"{who}, PICK A COLOUR", color)

    # ================================================================== actions
    def set_dice_count(self, count):
        if self.phase not in (SETUP, READY):
            return
        self.audio.play("click")
        self.duel.set_dice_count(count)
        self._after_pick()

    def tap_color(self, name):
        """Take a free colour, or hand back one you already own."""
        if self.phase not in (SETUP, READY):
            return
        if self.duel.owner(name) is None and self.duel.next_picker() is None:
            return                       # both teams already full
        self.audio.play("click")
        self.duel.tap(name)
        self._after_pick()

    def random_colors(self):
        if self.phase not in (SETUP, READY):
            return
        self.audio.play("place")
        self.duel.clear_teams()
        self.duel.auto_fill()
        self._after_pick()

    def clear_colors(self):
        if self.phase not in (SETUP, READY):
            return
        self.audio.play("click")
        self.duel.clear_teams()
        self._after_pick()

    def change_colors(self):
        """Go back to picking after a duel."""
        if self.phase not in (READY, RESULT):
            return
        self.audio.play("click")
        self.result_panel.hide()
        self.duel.clear_teams()
        self._after_pick()

    def start_roll(self):
        if self.phase != READY:
            return
        self.audio.play("place")
        self.dice.roll(only_colors=self.duel.in_play())
        self.phase = ROLLING
        self.timer = 0.0
        self.set_message("ROLLING...", settings.NEON_CYAN)

    def next_duel(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.phase = READY
        self.set_message("REMATCH!" if self.was_tie else "BOTH PLAYERS READY?",
                         settings.NEON_PINK if self.was_tie else settings.NEON_LIME)

    def reset_score(self):
        self.duel.reset_score()
        self.set_message("SCORE RESET", settings.GOLD)

    # =================================================================== update
    def update_mode(self, dt):
        self.result_panel.update(dt)

        picking = self.phase in (SETUP, READY)
        for button in self.count_buttons + self.color_buttons:
            button.enabled = picking
        self.random_button.enabled = picking
        self.clear_button.enabled = picking
        self.roll_button.enabled = (self.phase == READY)
        self.change_button.enabled = self.phase in (READY, RESULT)

        if self.phase == ROLLING:
            self.timer += dt
            if self.timer > MAX_ROLL_SECONDS:
                self.dice.force_settle_all()
            if self.dice_settled(dt):
                self._judge()

    def _judge(self):
        result = self.duel.judge(self.dice.results())
        self.phase = RESULT
        self.was_tie = (result["winner"] == TIE)

        if self.was_tie:
            self.audio.play("beep")
            title, color = "DRAW - REMATCH", settings.NEON_PINK
            note = f"BOTH ON {result['total_a']}"
        else:
            self.audio.play("win")
            winner = "PLAYER A" if result["winner"] == PLAYER_A else "PLAYER B"
            color = (settings.NEON_CYAN if result["winner"] == PLAYER_A
                     else settings.NEON_LIME)
            title = f"{winner} WINS"
            note = f"BY {result['difference']}"

        lines = [
            ("PLAYER A", self._team_text(self.duel.team_a, result["total_a"]),
             settings.NEON_CYAN),
            ("PLAYER B", self._team_text(self.duel.team_b, result["total_b"]),
             settings.NEON_LIME),
            ("SCORE", f"{result['wins'][PLAYER_A]} - {result['wins'][PLAYER_B]}",
             settings.GOLD),
        ]
        chips = [(name, result["results"][name]) for name in self.duel.in_play()]
        self.result_panel.show(title, lines, title_color=color,
                               big_note=note, big_note_color=color,
                               chips=chips)
        self.set_message("")

    def _team_text(self, colors, total):
        values = self.dice.results()
        parts = " + ".join(str(values[color]) for color in colors)
        return f"{parts}  =  {total}"

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  ARCADE DUEL",
            "summary": "Two players, one roll, highest total wins.",
            "steps": [
                "Choose how many dice each player rolls: 1, 2 or 3.",
                "Take turns tapping colours. Player A picks, then B, "
                "then A, and so on.",
                "Tap a colour you already own to put it back.",
                "Press ROLL BOTH. Highest total wins; a draw means "
                "a rematch.",
            ],
            "payouts": [],
            "controls": "1 2 3  dice each     SPACE  roll     ESC  back to the menu",
        }

    # ==================================================================== input
    def handle_event(self, event):
        if self.handle_help_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_to_menu()
                return
            if event.key == pygame.K_SPACE:
                if self.phase == READY:
                    self.start_roll()
                elif self.phase == RESULT:
                    self.next_duel()
                return
            if event.key == pygame.K_1 and self.phase in (SETUP, READY):
                self.set_dice_count(1)
                return
            if event.key == pygame.K_2 and self.phase in (SETUP, READY):
                self.set_dice_count(2)
                return
            if event.key == pygame.K_3 and self.phase in (SETUP, READY):
                self.set_dice_count(3)
                return

        self.result_panel.handle_event(event)
        if not self.result_panel.visible:
            for button in self.buttons():
                button.handle_event(event)
        else:
            self.back_button.handle_event(event)

    # ===================================================================== draw
    def draw_panel(self, surface):
        panel = self.panel_rect

        ui.draw_text(surface, "DUEL", (panel.centerx, panel.top + 12), size=22,
                     color=settings.NEON_LIME, bold=True, align="midtop")

        ui.draw_text(surface, "DICE EACH PLAYER", (panel.left + 18, panel.top + 44),
                     size=13, color=settings.TEXT_DIM, bold=True)
        for button in self.count_buttons:
            button.draw(surface)

        ui.draw_text(surface, "PICK YOUR COLOURS", (panel.left + 18, panel.top + 108),
                     size=13, color=settings.TEXT_DIM, bold=True)
        self._draw_color_buttons(surface)

        self._draw_teams(surface, panel.top + 284)

        self.random_button.draw(surface)
        self.clear_button.draw(surface)
        self.roll_button.draw(surface)
        self.change_button.draw(surface)
        self.draw_message(surface, panel.bottom - 82)

    def _draw_color_buttons(self, surface):
        """Each colour shows who owns it, or nothing while it is free."""
        for button in self.color_buttons:
            button.draw(surface)
            owner = self.duel.owner(button.label)
            if owner is None:
                continue
            tag = "A" if owner == PLAYER_A else "B"
            color = (settings.NEON_CYAN if owner == PLAYER_A
                     else settings.NEON_LIME)
            badge = pygame.Rect(0, 0, 22, 20)
            badge.midright = (button.rect.right - 8, button.rect.centery)
            pygame.draw.rect(surface, color, badge, border_radius=5)
            ui.draw_text(surface, tag, badge.center, size=15,
                         color=(10, 12, 30), bold=True, align="center")

    def _draw_teams(self, surface, y):
        """Both line-ups, with the dice values once the roll is done."""
        panel = self.panel_rect
        show = (self.phase == RESULT)
        results = self.dice.results()

        for name, colors, accent in (("PLAYER A", self.duel.team_a, settings.NEON_CYAN),
                                     ("PLAYER B", self.duel.team_b, settings.NEON_LIME)):
            ui.draw_text(surface, name, (panel.left + 18, y), size=17,
                         color=accent, bold=True)
            if show and colors:
                total = sum(results[color] for color in colors)
                ui.draw_text(surface, str(total), (panel.right - 20, y - 3),
                             size=22, color=accent, bold=True, align="topright")
            y += 24

            if not colors:
                ui.draw_text(surface, "no colours picked yet",
                             (panel.left + 26, y), size=13,
                             color=settings.TEXT_DIM)
            for index, color_name in enumerate(colors):
                tile = pygame.Rect(panel.left + 24 + index * 62, y, 56, 26)
                die_color = settings.DICE_COLORS[color_name]
                pygame.draw.rect(surface, ui.shade(die_color, 0.35), tile,
                                 border_radius=6)
                pygame.draw.rect(surface, die_color, tile, width=1, border_radius=6)
                label = (str(results[color_name]) if show else color_name[:3])
                ui.draw_text(surface, label, tile.center,
                             size=16 if show else 13,
                             color=settings.TEXT_BRIGHT, bold=True, align="center")
            y += 38

        wins = self.duel.wins
        ui.draw_text(surface, "SCORE", (panel.left + 18, y), size=14,
                     color=settings.TEXT_DIM, bold=True)
        ui.draw_text(surface, f"{wins[PLAYER_A]}  -  {wins[PLAYER_B]}",
                     (panel.right - 20, y - 5), size=20, color=settings.GOLD,
                     bold=True, align="topright")

    def draw_overlay(self, surface):
        if self.phase == ROLLING:
            ui.draw_glow_text(surface, "ROLLING...",
                              (self.play_rect.centerx, self.play_rect.top + 118),
                              size=32, color=settings.NEON_CYAN, align="center")
        elif self.phase == SETUP:
            # inside the machine's empty upper panel, where nothing else sits
            picker = self.duel.next_picker()
            who = "PLAYER A" if picker == PLAYER_A else "PLAYER B"
            color = settings.NEON_CYAN if picker == PLAYER_A else settings.NEON_LIME
            ui.draw_glow_text(surface, f"{who}, CHOOSE A COLOUR",
                              (self.play_rect.centerx, self.play_rect.top + 118),
                              size=28, color=color, align="center")
            ui.draw_text(surface,
                         f"{self.duel.dice_count} DICE EACH   -   "
                         f"TAP A COLOUR AGAIN TO PUT IT BACK",
                         (self.play_rect.centerx, self.play_rect.top + 150),
                         size=16, color=settings.TEXT_DIM, bold=True,
                         align="center")
        elif self.phase == READY:
            ui.draw_text(surface, "PRESS ROLL BOTH",
                         (self.play_rect.centerx, self.play_rect.top + 118),
                         size=22, color=settings.NEON_LIME, bold=True,
                         align="center")
        self.result_panel.draw(surface)
