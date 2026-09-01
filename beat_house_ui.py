"""
ui/beat_house_ui.py
-------------------
BEAT THE HOUSE — one player against the machine.

You choose how many dice to roll (1, 2 or 3) and which colours you want. The
machine takes the same number from whatever is left. Highest total wins, and a
draw gives your stake back.

This mode exists because Arcade Duel needs two people, and at a real booth
most of the queue is one person on their own.

Phases: BETTING -> ROLLING -> RESULT
"""

import pygame

from config import settings
from game.beat_house import (BeatTheHouse, COLOR_POOL, MAX_DICE,
                             CHANCE_WIN, CHANCE_DRAW)
from game.duel import PLAYER_A, PLAYER_B, TIE
from ui import ui
from ui.mode_screen import ModeScreen
from ui.particles import Confetti
from ui.result_ui import ResultPanel

BETTING = "BETTING"
ROLLING = "ROLLING"
RESULT = "RESULT"

MAX_ROLL_SECONDS = 6.0


class BeatHouseUI(ModeScreen):

    title = "BEAT THE HOUSE"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.game = BeatTheHouse(credits=manager.credits)
        self.phase = BETTING
        self.timer = 0.0
        self.confetti = Confetti()

        self._build_buttons()
        self._sync_dice()

        card = pygame.Rect(0, 0, 580, 516)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="PLAY AGAIN")
        self.result_panel.primary.on_click = self.play_again
        self.result_panel.secondary.on_click = self.go_to_menu

        self._refresh()

    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        # how many dice each side rolls
        self.count_buttons = []
        for index, count in enumerate(range(1, MAX_DICE + 1)):
            rect = pygame.Rect(left + index * (width // 3 + 2), panel.top + 68,
                               width // 3 - 4, 30)
            self.count_buttons.append(
                ui.Button(rect, str(count), font_size=18, accent=settings.GOLD,
                          on_click=lambda c=count: self.set_dice_count(c)))

        # which colours are yours
        self.color_buttons = []
        for index, name in enumerate(COLOR_POOL):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4),
                               panel.top + 126 + row * 34,
                               width // 2 - 4, 30)
            self.color_buttons.append(
                ui.Button(rect, name, font_size=14,
                          accent=settings.DICE_COLORS[name],
                          on_click=lambda n=name: self.tap_color(n)))

        self.random_button = ui.Button(
            pygame.Rect(left, panel.top + 230, width, 28),
            "RANDOM COLOURS", accent=settings.NEON_PINK, font_size=14,
            on_click=self.randomise)

        self.bet_buttons = []
        y = panel.top + 290
        for index, amount in enumerate(settings.BET_AMOUNTS):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4), y + row * 36,
                               width // 2 - 4, 32)
            self.bet_buttons.append(
                ui.Button(rect, str(amount), font_size=18, accent=settings.GOLD,
                          on_click=lambda a=amount: self.pick_amount(a)))

        self.roll_button = ui.Button(
            pygame.Rect(left, panel.bottom - 148, width, 48),
            "ROLL", accent=settings.WIN_GREEN, font_size=24,
            on_click=self.start_roll)

    def buttons(self):
        return (self.count_buttons + self.color_buttons + self.bet_buttons
                + [self.random_button, self.roll_button, self.back_button]
                + self.result_panel.buttons())

    # ================================================================ choosing
    def set_dice_count(self, count):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.set_dice_count(count)
        self._sync_dice()
        self._refresh()

    def tap_color(self, name):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.tap(name)
        self._sync_dice()
        self._refresh()

    def randomise(self):
        if self.phase != BETTING:
            return
        self.audio.play("place")
        self.game.randomise()
        self._sync_dice()
        self._refresh()

    def _sync_dice(self):
        """Only the chosen dice appear inside the machine."""
        self.dice.set_in_play(self.game.in_play())

    def _refresh(self):
        for button in self.count_buttons:
            button.selected = (button.label == str(self.game.dice_count))
        for button in self.color_buttons:
            button.selected = (self.game.owner(button.label) is not None)
        for button in self.bet_buttons:
            button.selected = (int(button.label) == (self.game.amount or -1))
        for button in self.count_buttons:
            button.selected = (button.label == str(self.game.dice_count))
        for button in self.color_buttons:
            button.selected = (self.game.owner(button.label) == "YOU")
        ok, message = self.game.validate()
        self.set_message(message, settings.WIN_GREEN if ok else settings.TEXT_DIM)

    # ================================================================= actions
    def pick_amount(self, amount):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.select_amount(amount)
        self._refresh()

    def start_roll(self):
        if self.phase != BETTING:
            return
        ok, message = self.game.validate()
        if not ok:
            self.audio.play("beep")
            self.set_message(message, settings.LOSE_RED)
            return

        self.game.place()
        self.manager.credits = self.game.credits
        self.audio.play("place")
        self.dice.roll(only_colors=self.game.in_play())
        self.phase = ROLLING
        self.timer = 0.0
        self.set_message("ROLLING...", settings.NEON_CYAN)

    def play_again(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.phase = BETTING
        self._refresh()

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

        # Button states are worked out AFTER the phase may have changed above.
        # Doing it first leaves them one frame behind, so the very first click
        # on a newly-live button gets ignored.
        live = (self.phase == BETTING)
        for button in self.bet_buttons + self.count_buttons + self.color_buttons:
            button.enabled = live
        self.random_button.enabled = live
        self.roll_button.enabled = live and self.game.amount is not None

    def _judge(self):
        result = self.game.judge(self.dice.results())
        self.manager.credits = self.game.credits
        self.phase = RESULT

        if result["winner"] == PLAYER_A:
            self.confetti.burst((self.play_rect.centerx, self.play_rect.centery))
            self.audio.play("win")
            title, color = "YOU WIN!", settings.WIN_GREEN
            note = f"+{result['change']} CREDITS"
        elif result["winner"] == TIE:
            self.audio.play("beep")
            title, color = "DRAW", settings.GOLD
            note = "STAKE RETURNED"
        else:
            self.audio.play("lose")
            title, color = "HOUSE WINS", settings.LOSE_RED
            note = f"-{result['bet']} CREDITS"

        wins, losses, draws = result["score"]
        lines = [
            ("YOUR TOTAL", str(result["player_total"]), settings.NEON_CYAN),
            ("HOUSE TOTAL", str(result["house_total"]), settings.NEON_PINK),
            ("BET", str(result["bet"]), settings.GOLD),
            ("RETURNED", str(result["payout"]), settings.GOLD),
            ("CREDITS NOW", str(result["credits"]), settings.GOLD),
            ("RECORD", f"{wins}W  {losses}L  {draws}D", settings.TEXT_BRIGHT),
        ]
        chips = [(name, result["results"][name])
                 for name in result["player_colors"] + result["house_colors"]]
        self.result_panel.show(title, lines, title_color=color,
                               big_note=note, big_note_color=color, chips=chips)
        self.set_message("")

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  BEAT THE HOUSE",
            "summary": "You against the machine. Highest total wins.",
            "steps": [
                "Choose how many dice each side rolls: 1, 2 or 3.",
                "Tap the colours you want. The machine takes the same "
                "number from what is left.",
                "Pick your bet, then press ROLL.",
                "Add up your dice against the machine's.",
            ],
            "payouts": [("YOU WIN  45%", "2x"), ("DRAW  9%", "STAKE BACK")],
            "controls": ("SPACE  roll     R  new player     "
                         "·  a draw returns your stake, so this mode is exactly fair"),
        }

    # =================================================================== input
    def handle_event(self, event):
        if self.handle_help_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.phase in (BETTING, RESULT):
                    self.go_to_menu()
                return
            if event.key == pygame.K_SPACE:
                if self.phase == BETTING:
                    self.start_roll()
                elif self.phase == RESULT:
                    self.play_again()
                return
            if event.key == pygame.K_r:
                self.game.reset_credits()
                self.manager.credits = self.game.credits
                self._refresh()
                self.set_message("CREDITS RESET", settings.GOLD)
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

        chip = pygame.Rect(0, 0, panel.width - 32, 32)
        chip.midtop = (panel.centerx, panel.top + 10)
        pygame.draw.rect(surface, (12, 14, 34), chip, border_radius=16)
        pygame.draw.rect(surface, settings.GOLD, chip, width=2, border_radius=16)
        ui.draw_text(surface, f"CREDITS  {self.game.credits}", chip.center,
                     size=18, color=settings.GOLD, bold=True, align="center")

        wins, losses, draws = (self.game.player_wins, self.game.house_wins,
                               self.game.draws)
        ui.draw_text(surface, "DICE EACH SIDE", (panel.left + 18, panel.top + 50),
                     size=12, color=settings.TEXT_DIM, bold=True)
        ui.draw_text(surface, f"{wins}W  {losses}L  {draws}D",
                     (panel.right - 18, panel.top + 50), size=12,
                     color=settings.GOLD, bold=True, align="topright")
        for button in self.count_buttons:
            button.draw(surface)

        ui.draw_text(surface, "YOUR COLOURS  (TAP TO SWAP)",
                     (panel.left + 18, panel.top + 108), size=12,
                     color=settings.TEXT_DIM, bold=True)
        self._draw_color_buttons(surface)
        self.random_button.draw(surface)

        ui.draw_text(surface, "BET", (panel.left + 18, panel.top + 272), size=13,
                     color=settings.TEXT_DIM, bold=True)
        for button in self.bet_buttons:
            button.draw(surface)

        self._draw_teams(surface, panel.top + 358)

        self.roll_button.draw(surface)
        self.draw_message(surface, panel.bottom - 92)

    def _draw_color_buttons(self, surface):
        """Each colour is badged with who is rolling it."""
        for button in self.color_buttons:
            button.draw(surface)
            owner = self.game.owner(button.label)
            if owner is None:
                continue
            mine = (owner == "YOU")
            color = settings.NEON_CYAN if mine else settings.NEON_PINK
            badge = pygame.Rect(0, 0, 34, 18)
            badge.midright = (button.rect.right - 6,
                              button.rect.centery - ui.Button.DEPTH)
            pygame.draw.rect(surface, color, badge, border_radius=5)
            ui.draw_text(surface, "YOU" if mine else "CPU", badge.center,
                         size=11, color=(10, 12, 30), bold=True, align="center")

    def _draw_teams(self, surface, y):
        """Both line-ups, with the dice values once the roll is done."""
        panel = self.panel_rect
        results = self.dice.results()
        show = (self.phase == RESULT)

        for name, colors, accent in (("YOU", self.game.player_colors, settings.NEON_CYAN),
                                     ("HOUSE", self.game.house_colors, settings.NEON_PINK)):
            ui.draw_text(surface, name, (panel.left + 18, y), size=16,
                         color=accent, bold=True)
            if show:
                total = sum(results[color] for color in colors)
                ui.draw_text(surface, str(total), (panel.right - 20, y - 3),
                             size=21, color=accent, bold=True, align="topright")
            y += 21
            for index, color_name in enumerate(colors):
                tile = pygame.Rect(panel.left + 24 + index * 62, y, 56, 22)
                die_color = settings.DICE_COLORS[color_name]
                pygame.draw.rect(surface, ui.shade(die_color, 0.35), tile,
                                 border_radius=6)
                pygame.draw.rect(surface, die_color, tile, width=1, border_radius=6)
                label = str(results[color_name]) if show else color_name[:3]
                ui.draw_text(surface, label, tile.center, size=15 if show else 12,
                             color=settings.TEXT_BRIGHT, bold=True, align="center")
            y += 30

    def draw_overlay(self, surface):
        centre = (self.play_rect.centerx, self.play_rect.top + 118)
        if self.phase == ROLLING:
            ui.draw_glow_text(surface, "ROLLING...", centre, size=32,
                              color=settings.NEON_CYAN, align="center")
        elif self.phase == BETTING:
            count = self.game.dice_count
            word = {1: "ONE DIE", 2: "TWO DICE", 3: "THREE DICE"}[count]
            ui.draw_text(surface, f"{word} EACH  ·  HIGHEST TOTAL WINS",
                         centre, size=18, color=settings.TEXT_DIM, bold=True,
                         align="center")
            ui.draw_text(surface,
                         "EVEN ODDS BOTH WAYS  ·  A DRAW RETURNS YOUR STAKE",
                         (self.play_rect.centerx, self.play_rect.top + 150),
                         size=15, color=settings.TEXT_DIM, bold=True,
                         align="center")

        self.result_panel.draw(surface)
        self.confetti.draw(surface)
