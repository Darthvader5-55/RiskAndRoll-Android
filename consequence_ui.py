"""
ui/consequence_ui.py
--------------------
CONSEQUENCE POOL — 1 to 6 players, lowest roll does the dare.

Each player is given a colour. Everyone rolls at once. The lowest number
loses. If two or more tie for lowest, ONLY those players reroll — that is
sudden death — and it repeats until one player is left standing at the bottom.

Phases:

    SETUP        choose how many players
    ROLLING      dice in the air
    SUDDEN       a tie was found, tied players are about to reroll
    RESULT       the loser and their dare
"""

import pygame

from config import settings
from game.consequences import ConsequenceBook, lowest_rollers, player_colors
from ui import ui
from ui.mode_screen import ModeScreen
from ui.result_ui import ResultPanel

SETUP = "SETUP"
ROLLING = "ROLLING"
SUDDEN = "SUDDEN"
RESULT = "RESULT"

MAX_ROLL_SECONDS = 6.0
MAX_NAME_LENGTH = 10
LEVEL_COLORS = [settings.NEON_LIME, settings.NEON_CYAN, settings.GOLD,
                settings.NEON_PINK, settings.LOSE_RED]

SUDDEN_PAUSE = 1.4      # seconds to show "SUDDEN DEATH" before the reroll


class ConsequenceUI(ModeScreen):

    title = "CONSEQUENCE POOL"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.book = ConsequenceBook()
        self.player_count = 4

        # Player names. The booth types real names in; if a slot is left blank
        # it just shows PLAYER 1, PLAYER 2 and so on.
        self.names = {color: "" for color in settings.COLOR_ORDER}
        self.editing_color = None       # which name is being typed right now
        self._name_before_edit = ""
        self.name_rows = {}             # colour -> clickable rect
        self.active_colors = player_colors(self.player_count)
        self.tied_colors = []
        self.loser = None
        self.round_number = 0

        self.phase = SETUP
        self.timer = 0.0

        self._build_buttons()

        card = pygame.Rect(0, 0, 600, 400)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="NEXT ROUND")
        self.result_panel.primary.on_click = self.new_round
        self.result_panel.secondary.on_click = self.go_to_menu

        if self.book.load_error:
            self.set_message(self.book.load_error, settings.LOSE_RED)
        else:
            self.set_message("CHOOSE PLAYERS, THEN ROLL")

    # ================================================================= building
    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        self.count_buttons = []
        y = panel.top + 76
        for index in range(settings.MIN_PLAYERS, settings.MAX_PLAYERS + 1):
            column, row = (index - 1) % 3, (index - 1) // 3
            rect = pygame.Rect(left + column * (width // 3 + 2), y + row * 40,
                               width // 3 - 4, 34)
            self.count_buttons.append(
                ui.Button(rect, str(index), font_size=20,
                          on_click=lambda c=index: self.set_players(c)))

        # one on/off button per difficulty level
        self.level_buttons = []
        y = panel.bottom - 232
        for index, name in enumerate(self.book.category_names()):
            column, row = index % 3, index // 3
            rect = pygame.Rect(left + column * (width // 3 + 2),
                               y + row * 34, width // 3 - 4, 30)
            self.level_buttons.append(
                ui.Button(rect, name[:7], font_size=13,
                          accent=LEVEL_COLORS[min(index, len(LEVEL_COLORS) - 1)],
                          on_click=lambda n=name: self.toggle_level(n)))

        roll = pygame.Rect(left, panel.bottom - 150, width, 54)
        self.roll_button = ui.Button(roll, "ROLL", accent=settings.NEON_PINK,
                                     font_size=24, on_click=self.start_roll)
        self._refresh_counts()
        self._refresh_levels()

    def buttons(self):
        return (self.count_buttons + self.level_buttons
                + [self.roll_button, self.back_button]
                + self.result_panel.buttons())

    # =============================================================== difficulty
    def toggle_level(self, name):
        """Switch a difficulty level on or off for this booth session."""
        if self.phase not in (SETUP, RESULT):
            return
        self.audio.play("click")
        self.book.toggle(name)
        self._refresh_levels()
        on = len(self.book.enabled_names())
        total = len(self.book.category_names())
        self.set_message(f"{on} OF {total} LEVELS ON", settings.NEON_LIME)

    def _refresh_levels(self):
        for button, name in zip(self.level_buttons, self.book.category_names()):
            button.selected = self.book.is_enabled(name)

    # ============================================================ player names
    def start_editing(self, color_name):
        if self.phase not in (SETUP, RESULT):
            return
        self.audio.play("click")
        self.editing_color = color_name
        self._name_before_edit = self.names[color_name]
        self.set_message("TYPE A NAME, THEN ENTER", settings.GOLD)

    def stop_editing(self, keep=True):
        if self.editing_color and not keep:
            self.names[self.editing_color] = self._name_before_edit
        self.editing_color = None
        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    def _type_into_name(self, event):
        """Handle one key press while a name is being typed."""
        color = self.editing_color
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.stop_editing()
        elif event.key == pygame.K_ESCAPE:
            # cancel: put back whatever the name was before typing started
            self.names[color] = self._name_before_edit
            self.editing_color = None
            self.set_message("CHOOSE PLAYERS, THEN ROLL")
        elif event.key == pygame.K_BACKSPACE:
            self.names[color] = self.names[color][:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.names[color]) < MAX_NAME_LENGTH:
                self.names[color] += event.unicode.upper()

    def player_label(self, color_name):
        """The typed name, or PLAYER n if nobody typed one."""
        typed = self.names.get(color_name, "").strip()
        if typed:
            return typed
        if color_name in self.active_colors:
            return f"PLAYER {self.active_colors.index(color_name) + 1}"
        return f"PLAYER {settings.COLOR_ORDER.index(color_name) + 1}"

    def _refresh_counts(self):
        for button in self.count_buttons:
            button.selected = (button.label == str(self.player_count))

    # =================================================================== actions
    def set_players(self, count):
        if self.phase not in (SETUP, RESULT):
            return
        self.audio.play("click")
        self.player_count = count
        self.active_colors = player_colors(count)
        self._refresh_counts()
        self.set_message(f"{count} PLAYER{'S' if count > 1 else ''} READY")

    def start_roll(self):
        if self.phase != SETUP:
            return
        self.audio.play("place")
        self.editing_color = None
        self.round_number += 1
        self.tied_colors = []
        self.loser = None
        self.dice.roll()
        self.phase = ROLLING
        self.timer = 0.0
        self.set_message("ROLLING...", settings.NEON_CYAN)

    def new_round(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.loser = None
        self.tied_colors = []
        self.phase = SETUP
        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    # ==================================================================== update
    def update_mode(self, dt):
        self.result_panel.update(dt)

        self.roll_button.enabled = (self.phase == SETUP)
        for button in self.count_buttons:
            button.enabled = self.phase in (SETUP, RESULT)
        for button in self.level_buttons:
            button.enabled = self.phase in (SETUP, RESULT)

        if self.phase == ROLLING:
            self.timer += dt
            if self.timer > MAX_ROLL_SECONDS:
                self.dice.force_settle_all()
            if self.dice_settled(dt):
                self._judge()

        elif self.phase == SUDDEN:
            self.timer -= dt
            if self.timer <= 0:
                self.audio.play("beep")
                self.dice.roll(only_colors=self.tied_colors)
                self.phase = ROLLING
                self.timer = 0.0
                self.set_message("SUDDEN DEATH ROLL", settings.NEON_PINK)

    def _judge(self):
        """Find the lowest roll among the players still in play."""
        # In sudden death only the tied players count, not the whole set.
        contenders = self.tied_colors or self.active_colors
        lowest = lowest_rollers(self.dice.results(), contenders)

        if len(lowest) > 1:
            # still tied: those players go again
            self.tied_colors = lowest
            self.phase = SUDDEN
            self.timer = SUDDEN_PAUSE
            names = ", ".join(self._player_name(c) for c in lowest)
            self.set_message(f"TIE: {names}", settings.NEON_PINK)
            return

        self.loser = lowest[0]
        self.tied_colors = []
        self._show_result()

    def _show_result(self):
        category, dare = self.book.random_consequence()
        self.audio.play("lose")
        self.phase = RESULT

        results = self.dice.results()
        lines = [("PLAYER", self._player_name(self.loser), settings.TEXT_BRIGHT),
                 ("COLOUR", self.loser, settings.DICE_COLORS[self.loser]),
                 ("ROLLED", str(results[self.loser]), settings.LOSE_RED),
                 ("CATEGORY", category, settings.NEON_PINK)]

        self.result_panel.show("CONSEQUENCE!", lines,
                               title_color=settings.NEON_PINK,
                               big_note=dare, big_note_color=settings.TEXT_BRIGHT)
        self.set_message("")

    def _player_name(self, color_name):
        return self.player_label(color_name)

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  CONSEQUENCE POOL",
            "summary": "Lowest roll does the dare. No credits, just nerve.",
            "steps": [
                "Choose how many players, 1 to 6. Each gets a colour.",
                "Click any name to type a real one over it.",
                "Switch difficulty levels on or off - dares only come "
                "from the levels that are ON.",
                "Press ROLL. Lowest number loses. A tie rolls again "
                "between the tied players only.",
            ],
            "payouts": [],
            "controls": "SPACE  roll     ESC  back to the menu",
        }

    # ==================================================================== input
    def is_typing(self):
        """A name box is open, so the keyboard belongs to it."""
        return self.editing_color is not None

    def handle_event(self, event):
        if self.handle_help_event(event):
            return

        # While a name is being typed, the keyboard belongs to the text box.
        # Without this, pressing S or ESC would fire the normal shortcuts.
        if self.editing_color is not None:
            if event.type == pygame.KEYDOWN:
                self._type_into_name(event)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                clicked_row = any(row.collidepoint(event.pos)
                                  for row in self.name_rows.values())
                if not clicked_row:
                    self.stop_editing()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_to_menu()
                return
            if event.key == pygame.K_SPACE:
                if self.phase == SETUP:
                    self.start_roll()
                elif self.phase == RESULT:
                    self.new_round()
                return

        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and not self.result_panel.visible):
            for color_name, row in self.name_rows.items():
                if row.collidepoint(event.pos):
                    self.start_editing(color_name)
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

        ui.draw_text(surface, "PLAYERS", (panel.centerx, panel.top + 14),
                     size=22, color=settings.NEON_PINK, bold=True, align="midtop")
        ui.draw_text(surface, "HOW MANY PLAYERS?", (panel.left + 18, panel.top + 56),
                     size=15, color=settings.TEXT_DIM, bold=True)
        for button in self.count_buttons:
            button.draw(surface)

        y = panel.top + 172
        ui.draw_text(surface, "NAMES  (CLICK TO TYPE)", (panel.left + 18, y),
                     size=13, color=settings.TEXT_DIM, bold=True)
        y += 22

        results = self.dice.results()
        show_values = self.phase in (RESULT, SUDDEN)
        mouse = pygame.mouse.get_pos()
        self.name_rows = {}

        for index, color_name in enumerate(self.active_colors):
            row = pygame.Rect(panel.left + 16, y - 3, panel.width - 32, 24)
            self.name_rows[color_name] = row

            editing = (self.editing_color == color_name)
            hovered = (row.collidepoint(mouse) and not self.result_panel.visible
                       and self.phase in (SETUP, RESULT))
            if editing:
                pygame.draw.rect(surface, settings.GOLD, row, width=2,
                                 border_radius=6)
            elif hovered:
                pygame.draw.rect(surface, settings.PANEL_EDGE, row, width=1,
                                 border_radius=6)

            swatch = pygame.Rect(panel.left + 22, y, 16, 16)
            pygame.draw.rect(surface, settings.DICE_COLORS[color_name], swatch,
                             border_radius=4)

            in_play = (not self.tied_colors) or (color_name in self.tied_colors)
            text_color = settings.TEXT_BRIGHT if in_play else settings.TEXT_DIM
            if self.loser == color_name:
                text_color = settings.LOSE_RED
            if editing:
                text_color = settings.GOLD

            label = self.player_label(color_name)
            if editing:
                # a blinking cursor, so it is obvious the keyboard is live
                label = self.names[color_name] + ("|" if ui.pulse(1.4) > 0.5 else "")
                if not self.names[color_name] and ui.pulse(1.4) <= 0.5:
                    label = ""
            ui.draw_text(surface, label, (swatch.right + 10, y - 2),
                         size=16, color=text_color, bold=True)

            if show_values:
                ui.draw_text(surface, str(results[color_name]),
                             (panel.right - 20, y - 2), size=18, color=text_color,
                             bold=True, align="topright")
            y += 24

        ui.draw_text(surface, "DIFFICULTY  (TAP TO SWITCH ON / OFF)",
                     (panel.left + 18, panel.bottom - 252), size=12,
                     color=settings.TEXT_DIM, bold=True)
        for button, name in zip(self.level_buttons, self.book.category_names()):
            button.draw(surface)
            if not self.book.is_enabled(name):
                # a dark sheet over the button so OFF is unmistakable
                off = pygame.Surface(button.rect.size, pygame.SRCALPHA)
                off.fill((0, 0, 0, 150))
                surface.blit(off, button.rect.topleft)
                pygame.draw.line(surface, settings.LOSE_RED,
                                 (button.rect.left + 8, button.rect.centery),
                                 (button.rect.right - 8, button.rect.centery), 2)

        self.roll_button.draw(surface)
        self.draw_message(surface, panel.bottom - 90)

    def draw_overlay(self, surface):
        if self.phase == ROLLING:
            # low down, clear of the machine's own lit sign at the top
            ui.draw_glow_text(surface, "ROLLING...",
                              (self.play_rect.centerx, self.play_rect.top + 118),
                              size=32, color=settings.NEON_CYAN, align="center")
        elif self.phase == SUDDEN:
            ui.draw_glow_text(surface, "SUDDEN DEATH",
                              (self.play_rect.centerx, self.play_rect.centery - 40),
                              size=56, color=settings.NEON_PINK, align="center",
                              glow=10)
            names = "  vs  ".join(self._player_name(c) for c in self.tied_colors)
            ui.draw_text(surface, names,
                         (self.play_rect.centerx, self.play_rect.centery + 16),
                         size=24, color=settings.TEXT_BRIGHT, bold=True,
                         align="midtop")
        self.result_panel.draw(surface)
