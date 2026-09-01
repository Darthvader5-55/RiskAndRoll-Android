"""
ui/over_under_ui.py
-------------------
OVER / UNDER — bet on the TOTAL of all six dice.

Deliberately built to look and feel like Color Royale, because a player who
has already used that screen should not have to learn a new one. The only
real difference is that there are three big choices instead of a colour and
a number, and the screen shows the real chance of each.

Phases: BETTING -> COUNTDOWN -> ROLLING -> RESULT
"""

import pygame

from config import settings
from game.over_under import (OverUnderGame, CHOICES, CHANCE, PAYOUT, MIDDLE,
                             describe, UNDER, OVER, EXACT)
from ui import ui
from ui.mode_screen import ModeScreen
from ui.particles import Confetti
from ui.result_ui import ResultPanel

BETTING = "BETTING"
COUNTDOWN = "COUNTDOWN"
ROLLING = "ROLLING"
RESULT = "RESULT"

MAX_ROLL_SECONDS = 6.0

CHOICE_COLORS = {
    UNDER: settings.NEON_CYAN,
    EXACT: settings.GOLD,
    OVER: settings.NEON_PINK,
}


class OverUnderUI(ModeScreen):

    title = "OVER / UNDER"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.game = OverUnderGame(credits=manager.credits)
        self.phase = BETTING
        self.timer = 0.0
        self.confetti = Confetti()
        self.shown_credits = float(manager.credits)

        self._build_buttons()

        card = pygame.Rect(0, 0, 580, 516)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card, primary_label="PLAY AGAIN")
        self.result_panel.primary.on_click = self.play_again
        self.result_panel.secondary.on_click = self.go_to_menu

        self._refresh()

    # ================================================================ building
    def _build_buttons(self):
        panel = self.panel_rect
        left, width = panel.left + 16, panel.width - 32

        self.choice_buttons = []
        y = panel.top + 104
        for choice in CHOICES:
            rect = pygame.Rect(left, y, width, 54)
            button = ui.Button(rect, choice, font_size=22,
                               accent=CHOICE_COLORS[choice],
                               on_click=lambda c=choice: self.pick_choice(c))
            button.label_dy = -13      # make room for the two lines below it
            self.choice_buttons.append(button)
            y += 62

        self.bet_buttons = []
        y = panel.top + 322
        for index, amount in enumerate(settings.BET_AMOUNTS):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4), y + row * 36,
                               width // 2 - 4, 32)
            self.bet_buttons.append(
                ui.Button(rect, str(amount), font_size=18, accent=settings.GOLD,
                          on_click=lambda a=amount: self.pick_amount(a)))

        self.place_button = ui.Button(
            pygame.Rect(left, panel.bottom - 146, width, 50),
            "PLACE BET", accent=settings.WIN_GREEN, font_size=24,
            on_click=self.place_bet)

    def buttons(self):
        return (self.choice_buttons + self.bet_buttons
                + [self.place_button, self.back_button]
                + self.result_panel.buttons())

    def _refresh(self):
        for button in self.choice_buttons:
            button.selected = (button.label == self.game.choice)
        for button in self.bet_buttons:
            button.selected = (int(button.label) == (self.game.amount or -1))
        ok, message = self.game.validate()
        self.set_message(message,
                         settings.WIN_GREEN if ok else settings.TEXT_DIM)

    # ================================================================= actions
    def pick_choice(self, choice):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.game.select_choice(choice)
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
        self.game.clear()
        self.phase = BETTING
        self._refresh()

    # ================================================================== update
    def update_mode(self, dt):
        self.result_panel.update(dt)
        self.confetti.update(dt)

        target = float(self.game.credits)
        gap = target - self.shown_credits
        self.shown_credits = target if abs(gap) < 0.6 else self.shown_credits + gap * min(1.0, dt * 7)

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

        # Button states are worked out AFTER the phase may have changed above.
        # Doing it first leaves them one frame behind, so the very first click
        # on a newly-live button gets ignored.
        live = (self.phase == BETTING)
        for button in self.choice_buttons + self.bet_buttons:
            button.enabled = live
        self.place_button.enabled = live and self.game.is_complete

    def _show_result(self):
        result = self.game.settle(self.dice.results())
        self.manager.credits = self.game.credits
        self.phase = RESULT

        if result["won"]:
            self.confetti.burst((self.play_rect.centerx, self.play_rect.centery))
            self.audio.play("win")
            title, color = "YOU WIN!", settings.WIN_GREEN
            note = f"+{result['change']} CREDITS"
        else:
            self.audio.play("lose")
            title, color = "YOU LOSE", settings.LOSE_RED
            note = f"-{result['bet']} CREDITS"

        lines = [
            ("TOTAL ROLLED", str(result["total"]), settings.TEXT_BRIGHT),
            ("THAT COUNTS AS", result["landed"], CHOICE_COLORS[result["landed"]]),
            ("YOUR PICK", result["choice"], CHOICE_COLORS[result["choice"]]),
            ("BET", str(result["bet"]), settings.GOLD),
            ("RETURNED", str(result["payout"]), settings.GOLD),
            ("CREDITS NOW", str(result["credits"]), settings.GOLD),
        ]
        chips = [(name, result["results"][name]) for name in settings.COLOR_ORDER]
        self.result_panel.show(title, lines, title_color=color,
                               big_note=note, big_note_color=color, chips=chips)
        self.set_message("")

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  OVER / UNDER",
            "summary": "Forget the colours - bet on the TOTAL of all six dice.",
            "steps": [
                f"Six dice add up to between 6 and 36. The middle is {MIDDLE}.",
                f"UNDER means {MIDDLE - 1} or less. OVER means {MIDDLE + 1} or more.",
                "EXACT means the total lands right on the middle.",
                "Pick one, pick your bet, then press PLACE BET.",
            ],
            "payouts": [("UNDER  45%", f"{PAYOUT[UNDER]}x"),
                        ("OVER  45%", f"{PAYOUT[OVER]}x"),
                        ("EXACT  9%", f"{PAYOUT[EXACT]}x")],
            "controls": "U  under     O  over     E  exact     SPACE  roll     R  new player",
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
            if self.phase == BETTING:
                if event.key == pygame.K_u:
                    self.pick_choice(UNDER)
                    return
                if event.key == pygame.K_o:
                    self.pick_choice(OVER)
                    return
                if event.key == pygame.K_e:
                    self.pick_choice(EXACT)
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

        ui.draw_text(surface, "TOTAL OF SIX DICE", (panel.centerx, panel.top + 12),
                     size=18, color=settings.NEON_CYAN, bold=True, align="midtop")

        chip = pygame.Rect(0, 0, panel.width - 32, 34)
        chip.midtop = (panel.centerx, panel.top + 38)
        pygame.draw.rect(surface, (12, 14, 34), chip, border_radius=17)
        pygame.draw.rect(surface, settings.GOLD, chip, width=2, border_radius=17)
        counting = abs(self.shown_credits - self.game.credits) > 0.6
        ui.draw_text(surface, f"CREDITS  {int(round(self.shown_credits))}",
                     chip.center, size=19, bold=True, align="center",
                     color=settings.WIN_GREEN if counting else settings.GOLD)

        # each choice shows what it means, its real chance and what it pays
        for button, choice in zip(self.choice_buttons, CHOICES):
            button.draw(surface)
            face = button.rect.move(0, -ui.Button.DEPTH)
            ui.draw_text(surface, describe(choice),
                         (face.centerx, face.top + 30), size=13,
                         color=settings.TEXT_DIM, bold=True, align="midtop")
            odds = f"{CHANCE[choice] * 100:.0f}%  ·  PAYS {PAYOUT[choice]}x"
            ui.draw_text(surface, odds, (face.centerx, face.top + 44), size=12,
                         color=CHOICE_COLORS[choice], bold=True, align="midtop")

        ui.draw_text(surface, "BET", (panel.left + 18, panel.top + 302), size=15,
                     color=settings.TEXT_DIM, bold=True)
        for button in self.bet_buttons:
            button.draw(surface)

        self.place_button.draw(surface)

        if self.game.can_afford_anything(settings.BET_AMOUNTS):
            self.draw_message(surface, panel.bottom - 92)
        else:
            ui.draw_text(surface, "OUT OF CREDITS - PRESS R",
                         (panel.centerx, panel.bottom - 92), size=15,
                         color=settings.LOSE_RED, bold=True, align="midtop")

    def draw_overlay(self, surface):
        if self.phase == COUNTDOWN:
            number = max(1, int(self.timer) + 1)
            fraction = self.timer - int(self.timer)
            ui.draw_glow_text(surface, str(number),
                              (self.play_rect.centerx, self.play_rect.centery),
                              size=int(90 + 60 * fraction), color=settings.GOLD,
                              align="center", glow=10)
        elif self.phase == ROLLING:
            ui.draw_glow_text(surface, "ROLLING...",
                              (self.play_rect.centerx, self.play_rect.top + 118),
                              size=32, color=settings.NEON_CYAN, align="center")
        elif self.phase == BETTING:
            ui.draw_text(surface, f"SIX DICE ADD UP TO BETWEEN 6 AND 36  ·  "
                                  f"THE MIDDLE IS {MIDDLE}",
                         (self.play_rect.centerx, self.play_rect.top + 118),
                         size=17, color=settings.TEXT_DIM, bold=True,
                         align="center")

        # the running total, big, while the dice settle
        if self.phase in (ROLLING, RESULT):
            total = sum(self.dice.results().values())
            ui.draw_glow_text(surface, str(total),
                              (self.play_rect.centerx, self.play_rect.top + 164),
                              size=44, color=settings.GOLD, align="center")

        self.result_panel.draw(surface)
        self.confetti.draw(surface)
