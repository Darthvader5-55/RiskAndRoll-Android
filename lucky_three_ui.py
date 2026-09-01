"""
ui/lucky_three_ui.py
--------------------
LUCKY THREE — pick a number, pick three colours, get paid per hit.

Replaces HIGHER OR LOWER, which could be beaten and never felt generous.
Here the player makes three real choices, all six dice roll, and any of their
three showing their number is a hit.

Phases: BETTING -> COUNTDOWN -> ROLLING -> RESULT
"""

import pygame

from config import settings
from game.lucky_three import (LuckyThreeGame, PAYOUT, CHANCE, WIN_CHANCE,
                              TEAM_SIZE)
from ui import ui
from ui.mode_screen import ModeScreen
from ui.particles import Confetti
from ui.result_ui import ResultPanel

BETTING = "BETTING"
COUNTDOWN = "COUNTDOWN"
ROLLING = "ROLLING"
RESULT = "RESULT"

MAX_ROLL_SECONDS = 6.0


class LuckyThreeUI(ModeScreen):

    title = "LUCKY THREE"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.game = LuckyThreeGame(credits=manager.credits,
                                   all_colors=settings.COLOR_ORDER)
        self.game.random_colors()          # start with three, so it is playable
        self.phase = BETTING
        self.timer = 0.0
        self.confetti = Confetti()
        self.shown_credits = float(manager.credits)

        self._build_buttons()

        card = pygame.Rect(0, 0, 580, 540)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="PLAY AGAIN")
        self.result_panel.primary.on_click = self.play_again
        self.result_panel.secondary.on_click = self.go_to_menu

        self._refresh()

    # ================================================================ building
    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        # your three colours
        self.color_buttons = []
        for index, name in enumerate(settings.COLOR_ORDER):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4),
                               panel.top + 74 + row * 34,
                               width // 2 - 4, 30)
            self.color_buttons.append(
                ui.Button(rect, name, font_size=14,
                          accent=settings.DICE_COLORS[name],
                          on_click=lambda n=name: self.tap_color(n)))

        self.random_button = ui.Button(
            pygame.Rect(left, panel.top + 178, width, 26),
            "RANDOM THREE", accent=settings.NEON_PINK, font_size=13,
            on_click=self.random_colors)

        # your number
        self.number_buttons = []
        for index, value in enumerate(settings.DICE_FACES):
            column, row = index % 3, index // 3
            rect = pygame.Rect(left + column * (width // 3 + 2),
                               panel.top + 226 + row * 40,
                               width // 3 - 4, 34)
            button = ui.Button(rect, str(value), font_size=18,
                               on_click=lambda v=value: self.pick_number(v))
            button.pip_value = value
            self.number_buttons.append(button)

        # your bet
        self.bet_buttons = []
        for index, amount in enumerate(settings.BET_AMOUNTS):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4),
                               panel.top + 328 + row * 34,
                               width // 2 - 4, 30)
            self.bet_buttons.append(
                ui.Button(rect, str(amount), font_size=17, accent=settings.GOLD,
                          on_click=lambda a=amount: self.pick_amount(a)))

        self.place_button = ui.Button(
            pygame.Rect(left, panel.bottom - 146, width, 50),
            "PLACE BET", accent=settings.WIN_GREEN, font_size=24,
            on_click=self.place_bet)

    def buttons(self):
        return (self.color_buttons + self.number_buttons + self.bet_buttons
                + [self.random_button, self.place_button, self.back_button]
                + self.result_panel.buttons())

    def _refresh(self):
        for button in self.color_buttons:
            button.selected = (button.label in self.game.colors)
        for button in self.number_buttons:
            button.selected = (int(button.label) == (self.game.number or -1))
        for button in self.bet_buttons:
            button.selected = (int(button.label) == (self.game.amount or -1))
        ok, message = self.game.validate()
        self.set_message(message,
                         settings.WIN_GREEN if ok else settings.TEXT_DIM)

    # ================================================================= actions
    def tap_color(self, name):
        if self.phase != BETTING:
            return
        if self.game.tap_color(name) or name not in self.game.colors:
            self.audio.play("click")
        else:
            self.audio.play("beep")
        self._refresh()

    def random_colors(self):
        if self.phase != BETTING:
            return
        self.audio.play("place")
        self.game.random_colors()
        self._refresh()

    def pick_number(self, value):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.select_number(value)
        self._refresh()

    def pick_amount(self, amount):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.select_amount(amount)
        self._refresh()

    def place_bet(self):
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
        self.phase = COUNTDOWN
        self.timer = settings.COUNTDOWN_SECONDS
        self.set_message("GET READY", settings.NEON_CYAN)

    def play_again(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.game.clear()          # keeps the three colours, clears the rest
        self.phase = BETTING
        self._refresh()

    # ================================================================== update
    def update_mode(self, dt):
        self.result_panel.update(dt)
        self.confetti.update(dt)

        target = float(self.game.credits)
        gap = target - self.shown_credits
        if abs(gap) < 0.6:
            self.shown_credits = target
        else:
            self.shown_credits += gap * min(1.0, dt * 7)

        if self.phase == COUNTDOWN:
            self.timer -= dt
            if self.timer <= 0:
                self.dice.roll()
                self.phase = ROLLING
                self.timer = 0.0
                self.set_message("ROLLING...", settings.NEON_CYAN)

        elif self.phase == ROLLING:
            self.timer += dt
            if self.timer > MAX_ROLL_SECONDS:
                self.dice.force_settle_all()
            if self.dice_settled(dt):
                self._show_result()

        # button states come after the phase may have changed, so a newly
        # live button accepts a click on the same frame
        live = (self.phase == BETTING)
        for button in (self.color_buttons + self.number_buttons
                       + self.bet_buttons):
            button.enabled = live
        self.random_button.enabled = live
        self.place_button.enabled = live and self.game.is_complete

    def _show_result(self):
        result = self.game.settle(self.dice.results())
        self.manager.credits = self.game.credits
        self.phase = RESULT

        if result["jackpot"]:
            self.confetti.burst((self.play_rect.centerx,
                                 self.play_rect.centery), 130)
            self.audio.play("win")
            title, color = "JACKPOT!", settings.GOLD
            note = f"ALL THREE HIT  ·  +{result['change']} CREDITS"
        elif result["won"]:
            self.confetti.burst((self.play_rect.centerx, self.play_rect.centery))
            self.audio.play("win")
            title, color = "YOU WIN!", settings.WIN_GREEN
            hit_word = "HIT" if result["hits"] == 1 else "HITS"
            note = f"{result['hits']} {hit_word}  ·  +{result['change']} CREDITS"
        else:
            self.audio.play("lose")
            title, color = "NO HITS", settings.LOSE_RED
            note = f"-{result['bet']} CREDITS"

        lines = [
            ("YOUR NUMBER", str(result["number"]), settings.NEON_CYAN),
            ("YOUR DICE", "  ".join(result["colors"]), settings.TEXT_BRIGHT),
            ("HITS", f"{result['hits']} of {TEAM_SIZE}", color),
            ("BET", str(result["bet"]), settings.GOLD),
            ("RETURNED", str(result["payout"]), settings.GOLD),
            ("CREDITS NOW", str(result["credits"]), settings.GOLD),
        ]
        chips = [(name, result["results"][name]) for name in result["colors"]]
        self.result_panel.show(title, lines, title_color=color,
                               big_note=note, big_note_color=color,
                               chips=chips)
        self.set_message("")

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  LUCKY THREE",
            "summary": "Three of the dice are YOURS. Every one on your number pays.",
            "steps": [
                "Pick THREE colours - those three dice belong to you.",
                "Pick ONE number from 1 to 6.",
                "Pick your bet, then press PLACE BET.",
                "All six roll, but only your three count. Each one showing "
                "your number is a hit.",
            ],
            "payouts": [("1 HIT", f"{PAYOUT[1]}x"),
                        ("2 HITS", f"{PAYOUT[2]}x"),
                        ("3 HITS", f"{PAYOUT[3]}x")],
            "controls": ("1-6  number     L  random three     "
                         f"SPACE  roll     R  new player    "
                         f"·  you win something {WIN_CHANCE * 100:.0f}% of rounds"),
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
                    self.place_bet()
                elif self.phase == RESULT:
                    self.play_again()
                return
            if self.phase == BETTING and pygame.K_1 <= event.key <= pygame.K_6:
                self.pick_number(event.key - pygame.K_0)
                return
            if event.key == pygame.K_l:
                self.random_colors()
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
        counting = abs(self.shown_credits - self.game.credits) > 0.6
        ui.draw_text(surface, f"CREDITS  {int(round(self.shown_credits))}",
                     chip.center, size=18, bold=True, align="center",
                     color=settings.WIN_GREEN if counting else settings.GOLD)

        ui.draw_text(surface, f"YOUR THREE DICE  ({len(self.game.colors)}/{TEAM_SIZE})",
                     (panel.left + 18, panel.top + 54), size=12,
                     color=settings.TEXT_DIM, bold=True)
        self._draw_color_buttons(surface)
        self.random_button.draw(surface)

        ui.draw_text(surface, "YOUR NUMBER", (panel.left + 18, panel.top + 210),
                     size=12, color=settings.TEXT_DIM, bold=True)
        for button in self.number_buttons:
            button.draw(surface)

        ui.draw_text(surface, "BET", (panel.left + 18, panel.top + 312),
                     size=12, color=settings.TEXT_DIM, bold=True)
        for button in self.bet_buttons:
            button.draw(surface)

        self._draw_payout_table(surface, panel.top + 400)
        self.place_button.draw(surface)

        if self.game.can_afford_anything(settings.BET_AMOUNTS):
            self.draw_message(surface, panel.bottom - 90)
        else:
            ui.draw_text(surface, "OUT OF CREDITS - PRESS R",
                         (panel.centerx, panel.bottom - 90), size=15,
                         color=settings.LOSE_RED, bold=True, align="midtop")

    def _draw_color_buttons(self, surface):
        """A tick on the colours the player has taken."""
        for button in self.color_buttons:
            button.draw(surface)
            if button.label not in self.game.colors:
                continue
            face = button.rect.move(0, -ui.Button.DEPTH)
            badge = pygame.Rect(0, 0, 18, 18)
            badge.midright = (face.right - 7, face.centery)
            pygame.draw.rect(surface, settings.DICE_COLORS[button.label], badge,
                             border_radius=5)
            ui.draw_text(surface, "✓", badge.center, size=14, color=(10, 12, 30),
                         bold=True, align="center")

    def _draw_payout_table(self, surface, y):
        """What each number of hits pays. Players check this constantly."""
        panel = self.panel_rect
        ui.draw_text(surface, "PAYS", (panel.left + 18, y - 16), size=12,
                     color=settings.TEXT_DIM, bold=True)

        width = (panel.width - 40) // 3
        for index, hits in enumerate((1, 2, 3)):
            box = pygame.Rect(panel.left + 18 + index * width, y, width - 6, 34)
            accent = settings.GOLD if hits == 3 else settings.NEON_CYAN
            pygame.draw.rect(surface, (14, 17, 40), box, border_radius=7)
            pygame.draw.rect(surface, accent, box, width=1, border_radius=7)
            ui.draw_text(surface, f"{hits} HIT" + ("S" if hits > 1 else ""),
                         (box.centerx, box.top + 3), size=11,
                         color=settings.TEXT_DIM, bold=True, align="midtop")
            ui.draw_text(surface, f"{PAYOUT[hits]}x", (box.centerx, box.top + 15),
                         size=17, color=accent, bold=True, align="midtop")

    def draw_overlay(self, surface):
        centre = (self.play_rect.centerx, self.play_rect.top + 118)

        if self.phase == COUNTDOWN:
            number = max(1, int(self.timer) + 1)
            fraction = self.timer - int(self.timer)
            ui.draw_glow_text(surface, str(number),
                              (self.play_rect.centerx, self.play_rect.centery),
                              size=int(90 + 60 * fraction), color=settings.GOLD,
                              align="center", glow=10)
        elif self.phase == ROLLING:
            ui.draw_glow_text(surface, "ROLLING...", centre, size=32,
                              color=settings.NEON_CYAN, align="center")
        elif self.phase == BETTING:
            ui.draw_text(surface,
                         "THREE DICE ARE YOURS  ·  EVERY ONE ON YOUR NUMBER PAYS",
                         centre, size=17, color=settings.TEXT_DIM, bold=True,
                         align="center")
            ui.draw_text(surface,
                         f"YOU WIN SOMETHING {WIN_CHANCE * 100:.0f}% OF ROUNDS",
                         (self.play_rect.centerx, self.play_rect.top + 150),
                         size=15, color=settings.NEON_LIME, bold=True,
                         align="center")

        # while the dice settle, show the hits climbing
        if self.phase in (ROLLING, RESULT) and self.game.has_colors:
            results = self.dice.results()
            hits = sum(1 for name in self.game.colors
                       if results.get(name) == self.game.number)
            color = settings.WIN_GREEN if hits else settings.TEXT_DIM
            ui.draw_glow_text(surface, f"{hits} / {TEAM_SIZE}",
                              (self.play_rect.centerx, self.play_rect.top + 164),
                              size=38, color=color, align="center")

        self.result_panel.draw(surface)
        self.confetti.draw(surface)
