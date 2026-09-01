"""
ui/battle_royale_ui.py
----------------------
BATTLE ROYALE — last player standing.

Every round the surviving players roll, and the lowest is knocked out. Ties
for lowest go to sudden death between just those players. Keep going until
one is left.

Players can type their own names over the colours, so the screen says
"MIKE IS OUT" instead of "BLUE IS OUT". Click a name to edit it.

Players can type their own names over the colours, so the screen says MIKE IS
OUT instead of BLUE IS OUT. Click any name in the list to type it.

Free play: no credits, no betting. This is the mode for a crowd.

Phases: SETUP -> ROLLING -> SUDDEN -> ROUND -> FINISHED
"""

import pygame

from config import settings
from game.battle import BattleRoyale
from ui import ui
from ui.mode_screen import ModeScreen
from ui.particles import Confetti
from ui.result_ui import ResultPanel

SETUP = "SETUP"
ROLLING = "ROLLING"
SUDDEN = "SUDDEN"
ROUND = "ROUND"          # showing who just went out
FINISHED = "FINISHED"

MAX_NAME_LENGTH = 10
MAX_NAME_LENGTH = 10
MAX_ROLL_SECONDS = 6.0
SUDDEN_PAUSE = 1.4
ROUND_PAUSE = 1.8


class BattleRoyaleUI(ModeScreen):

    title = "BATTLE ROYALE"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.battle = BattleRoyale(player_count=4)
        self.phase = SETUP
        self.timer = 0.0
        self.tied = []
        self.just_out = None
        self.confetti = Confetti()

        # Real names typed over the colours. Blank means just use the colour.
        self.names = {color: "" for color in settings.COLOR_ORDER}
        self.editing_color = None
        self._name_before_edit = ""
        self.name_rows = {}

        # Real names, typed in by the players. A blank one falls back to the
        # colour, so the mode works fine if nobody bothers.
        self.names = {color: "" for color in settings.COLOR_ORDER}
        self.editing_color = None
        self._name_before_edit = ""
        self.name_rows = {}

        self._build_buttons()
        self._sync_dice()

        card = pygame.Rect(0, 0, 560, 400)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="PLAY AGAIN")
        self.result_panel.primary.on_click = self.restart
        self.result_panel.secondary.on_click = self.go_to_menu

        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        self.count_buttons = []
        y = panel.top + 62
        for index, count in enumerate(range(2, settings.MAX_PLAYERS + 1)):
            column, row = index % 3, index // 3
            rect = pygame.Rect(left + column * (width // 3 + 2), y + row * 38,
                               width // 3 - 4, 32)
            self.count_buttons.append(
                ui.Button(rect, str(count), font_size=19,
                          accent=settings.NEON_PINK,
                          on_click=lambda c=count: self.set_players(c)))

        self.roll_button = ui.Button(
            pygame.Rect(left, panel.bottom - 150, width, 52),
            "ROLL ROUND", accent=settings.NEON_LIME, font_size=22,
            on_click=self.start_round)
        self._refresh()

    def buttons(self):
        return (self.count_buttons + [self.roll_button, self.back_button]
                + self.result_panel.buttons())

    def _refresh(self):
        for button in self.count_buttons:
            button.selected = (button.label == str(self.battle.player_count))

    # ============================================================ player names
    def player_name(self, color_name):
        """The typed name, or the colour if nobody typed one."""
        return self.names.get(color_name, "").strip() or color_name

    def start_editing(self, color_name):
        if self.phase not in (SETUP, FINISHED):
            return
        self.audio.play("click")
        self.editing_color = color_name
        self._name_before_edit = self.names[color_name]
        self.set_message("TYPE A NAME, THEN ENTER", settings.GOLD)

    def stop_editing(self):
        self.editing_color = None
        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    def _type_into_name(self, event):
        color = self.editing_color
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.stop_editing()
        elif event.key == pygame.K_ESCAPE:
            self.names[color] = self._name_before_edit
            self.stop_editing()
        elif event.key == pygame.K_BACKSPACE:
            self.names[color] = self.names[color][:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.names[color]) < MAX_NAME_LENGTH:
                self.names[color] += event.unicode.upper()

    # ============================================================ player names
    def label_for(self, color_name):
        """The typed name, or the colour if nobody typed one."""
        return self.names.get(color_name, "").strip() or color_name

    def start_editing(self, color_name):
        if self.phase not in (SETUP, FINISHED):
            return
        self.audio.play("click")
        self.editing_color = color_name
        self._name_before_edit = self.names[color_name]
        self.set_message("TYPE A NAME, THEN ENTER", settings.GOLD)

    def stop_editing(self):
        self.editing_color = None
        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    def _type_into_name(self, event):
        color = self.editing_color
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.stop_editing()
        elif event.key == pygame.K_ESCAPE:
            self.names[color] = self._name_before_edit
            self.stop_editing()
        elif event.key == pygame.K_BACKSPACE:
            self.names[color] = self.names[color][:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.names[color]) < MAX_NAME_LENGTH:
                self.names[color] += event.unicode.upper()

    def _sync_dice(self):
        """Only the players still in the battle appear in the machine."""
        self.dice.set_in_play(self.battle.alive)

    # ================================================================= actions
    def set_players(self, count):
        if self.phase not in (SETUP, FINISHED):
            return
        self.audio.play("click")
        self.result_panel.hide()
        self.battle.set_players(count)
        self.phase = SETUP
        self._refresh()
        self._sync_dice()
        self.set_message(f"{count} PLAYERS - LAST ONE STANDING WINS")

    def start_round(self):
        if self.phase != SETUP:
            return
        self.audio.play("place")
        self.editing_color = None
        self.tied = []
        self.just_out = None
        self.battle.begin_round()
        self.dice.roll(only_colors=self.battle.alive)
        self.phase = ROLLING
        self.timer = 0.0
        self.set_message("ROLLING...", settings.NEON_CYAN)

    def restart(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.battle.restart()
        self.phase = SETUP
        self._sync_dice()
        self.set_message("CHOOSE PLAYERS, THEN ROLL")

    # ================================================================== update
    def update_mode(self, dt):
        self.result_panel.update(dt)
        self.confetti.update(dt)

        if self.phase == ROLLING:
            self.timer += dt
            if self.timer > MAX_ROLL_SECONDS:
                self.dice.force_settle_all()
            if self.dice_settled(dt):
                self._judge()

        elif self.phase == SUDDEN:
            self.timer -= dt
            if self.timer <= 0:
                self.dice.roll(only_colors=self.tied)
                self.phase = ROLLING
                self.timer = 0.0
                self.set_message("SUDDEN DEATH ROLL", settings.NEON_PINK)

        elif self.phase == ROUND:
            self.timer -= dt
            if self.timer <= 0:
                if self.battle.finished:
                    self._show_winner()
                else:
                    self.phase = SETUP
                    self._sync_dice()
                    self.set_message(f"{len(self.battle.alive)} LEFT - ROLL AGAIN",
                                     settings.NEON_CYAN)

        # Button states are worked out AFTER the phase may have changed above.
        # Doing it first leaves them one frame behind, so the very first click
        # on a newly-live button gets ignored.
        for button in self.count_buttons:
            button.enabled = self.phase in (SETUP, FINISHED)
        self.roll_button.enabled = (self.phase == SETUP)

    def _judge(self):
        """Find the lowest roll among whoever just rolled."""
        among = self.tied if self.tied else self.battle.alive
        lowest = self.battle.lowest(self.dice.results(), among)

        if len(lowest) > 1:
            # a tie for lowest: only those players roll again
            self.tied = lowest
            self.phase = SUDDEN
            self.timer = SUDDEN_PAUSE
            self.audio.play("beep")
            self.set_message("TIE - SUDDEN DEATH", settings.NEON_PINK)
            return

        self.just_out = lowest[0]
        self.battle.knock_out(self.just_out)
        self.tied = []
        self.audio.play("lose")
        self.phase = ROUND
        self.timer = ROUND_PAUSE
        self.set_message(f"{self.player_name(self.just_out)} IS OUT",
                         settings.LOSE_RED)

    def _show_winner(self):
        winner = self.battle.winner
        self.confetti.burst((self.play_rect.centerx, self.play_rect.centery), 110)
        self.audio.play("win")
        self.phase = FINISHED

        lines = [("WINNER", self.player_name(winner), settings.DICE_COLORS[winner]),
                 ("PLAYERS", str(self.battle.player_count), settings.TEXT_BRIGHT),
                 ("ROUNDS", str(self.battle.round_number), settings.TEXT_BRIGHT)]
        for color_name in reversed(self.battle.knocked_out[-3:]):
            lines.append((f"{_ordinal(self.battle.placement(color_name))} PLACE",
                          self.player_name(color_name),
                          settings.DICE_COLORS[color_name]))

        self.result_panel.show("LAST ONE STANDING", lines,
                               title_color=settings.DICE_COLORS[winner],
                               big_note=f"{self.player_name(winner)} WINS",
                               big_note_color=settings.DICE_COLORS[winner])
        self.set_message("")

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  BATTLE ROYALE",
            "summary": "Last player standing. Free to play, best with a crowd.",
            "steps": [
                "Choose 2 to 6 players. Each one gets a colour.",
                "Click any name to type a real one over it.",
                "Every round, everyone still in rolls.",
                "The lowest roll is knocked out. Ties roll again. "
                "Keep going until one is left.",
            ],
            "payouts": [],
            "controls": "SPACE  roll the next round     ESC  back to the menu",
        }

    # =================================================================== input
    def is_typing(self):
        """A name box is open, so the keyboard belongs to it."""
        return self.editing_color is not None

    def handle_event(self, event):
        if self.handle_help_event(event):
            return

        # While a name is being typed the keyboard belongs to the text box,
        # or pressing S would fire a shortcut instead of typing an S.
        if self.editing_color is not None:
            if event.type == pygame.KEYDOWN:
                self._type_into_name(event)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not any(row.collidepoint(event.pos)
                           for row in self.name_rows.values()):
                    self.stop_editing()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_to_menu()
                return
            if event.key == pygame.K_SPACE:
                if self.phase == SETUP:
                    self.start_round()
                elif self.phase == FINISHED:
                    self.restart()
                return

        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and not self.result_panel.visible):
            for color_name, row in self.name_rows.items():
                if row.collidepoint(event.pos):
                    self.start_editing(color_name)
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

    # ==================================================================== draw
    def draw_panel(self, surface):
        panel = self.panel_rect

        ui.draw_text(surface, "BATTLE", (panel.centerx, panel.top + 12), size=22,
                     color=settings.NEON_PINK, bold=True, align="midtop")
        ui.draw_text(surface, "HOW MANY PLAYERS?", (panel.left + 18, panel.top + 44),
                     size=13, color=settings.TEXT_DIM, bold=True)
        for button in self.count_buttons:
            button.draw(surface)

        results = self.dice.results()
        show_values = self.phase in (ROUND, SUDDEN, FINISHED)

        y = panel.top + 152
        ui.draw_text(surface, "STILL IN  (CLICK A NAME TO TYPE)",
                     (panel.left + 18, y), size=12,
                     color=settings.NEON_LIME, bold=True)
        y += 22
        mouse = pygame.mouse.get_pos()
        self.name_rows = {}

        for color_name in self.battle.alive:
            row = pygame.Rect(panel.left + 16, y - 4, panel.width - 32, 23)
            self.name_rows[color_name] = row

            editing = (self.editing_color == color_name)
            hovered = (row.collidepoint(mouse) and not self.result_panel.visible
                       and self.phase in (SETUP, FINISHED))
            if editing:
                pygame.draw.rect(surface, settings.GOLD, row, width=2,
                                 border_radius=6)
            elif hovered:
                pygame.draw.rect(surface, settings.PANEL_EDGE, row, width=1,
                                 border_radius=6)

            swatch = pygame.Rect(panel.left + 22, y, 15, 15)
            pygame.draw.rect(surface, settings.DICE_COLORS[color_name], swatch,
                             border_radius=4)

            in_tie = color_name in self.tied
            text_color = settings.NEON_PINK if in_tie else settings.TEXT_BRIGHT
            if editing:
                text_color = settings.GOLD

            label = self.player_name(color_name)
            if editing:
                label = self.names[color_name] + ("|" if ui.pulse(1.4) > 0.5 else "")
            ui.draw_text(surface, label, (swatch.right + 10, y - 2),
                         size=15, color=text_color, bold=True)
            if show_values:
                ui.draw_text(surface, str(results[color_name]),
                             (panel.right - 20, y - 2), size=16,
                             color=text_color, bold=True, align="topright")
            y += 23

        if self.battle.knocked_out:
            y += 10
            ui.draw_text(surface, "KNOCKED OUT", (panel.left + 18, y), size=13,
                         color=settings.LOSE_RED, bold=True)
            y += 20
            for color_name in self.battle.knocked_out:
                swatch = pygame.Rect(panel.left + 22, y + 2, 11, 11)
                pygame.draw.rect(surface, ui.shade(settings.DICE_COLORS[color_name], 0.5),
                                 swatch, border_radius=3)
                ui.draw_text(surface, self.player_name(color_name),
                             (swatch.right + 10, y - 2),
                             size=13, color=settings.TEXT_DIM, bold=True)
                ui.draw_text(surface, _ordinal(self.battle.placement(color_name)),
                             (panel.right - 20, y - 2), size=13,
                             color=settings.TEXT_DIM, bold=True, align="topright")
                y += 19

        self.roll_button.draw(surface)
        self.draw_message(surface, panel.bottom - 92)

    def draw_overlay(self, surface):
        centre = (self.play_rect.centerx, self.play_rect.top + 118)
        if self.phase == ROLLING:
            ui.draw_glow_text(surface, "ROLLING...", centre, size=32,
                              color=settings.NEON_CYAN, align="center")
        elif self.phase == SUDDEN:
            ui.draw_glow_text(surface, "SUDDEN DEATH", centre, size=44,
                              color=settings.NEON_PINK, align="center", glow=10)
            ui.draw_text(surface,
                         "  vs  ".join(self.player_name(c) for c in self.tied),
                         (self.play_rect.centerx, self.play_rect.top + 156),
                         size=20, color=settings.TEXT_BRIGHT, bold=True,
                         align="center")
        elif self.phase == ROUND and self.just_out:
            ui.draw_glow_text(surface, f"{self.player_name(self.just_out)} IS OUT",
                              centre, size=40,
                              color=settings.LOSE_RED, align="center")
            ui.draw_text(surface, f"{len(self.battle.alive)} STILL IN",
                         (self.play_rect.centerx, self.play_rect.top + 156),
                         size=20, color=settings.TEXT_DIM, bold=True,
                         align="center")
        elif self.phase == SETUP:
            ui.draw_text(surface, "LOWEST ROLL IS KNOCKED OUT EACH ROUND",
                         centre, size=18, color=settings.TEXT_DIM, bold=True,
                         align="center")

        self.result_panel.draw(surface)
        self.confetti.draw(surface)


def _ordinal(number):
    """1 -> 1ST, 2 -> 2ND, 3 -> 3RD, 4 -> 4TH ...

    The 11th to 13th are the awkward ones: they take TH even though they end
    in 1, 2 and 3.
    """
    if 11 <= (number % 100) <= 13:
        return f"{number}TH"
    return f"{number}{ {1: 'ST', 2: 'ND', 3: 'RD'}.get(number % 10, 'TH') }".replace(" ", "")
