"""
ui/color_royale_ui.py
---------------------
COLOR ROYALE — the main booth mode.

Pick a colour, a number and a bet. Six dice roll. If your colour lands on your
number the stake comes back doubled, otherwise it is lost.

THE ROUND IS A STATE MACHINE. At any moment the screen is in exactly one of:

    BETTING     buttons live, waiting for the player
    COUNTDOWN   bet taken, 3... 2... 1...
    ROLLING     dice in the air, everything locked
    RESULT      the card is up, PLAY AGAIN or MAIN MENU

update_mode() is just "what happens in this state, and when do we leave it".
Written this way, it is impossible for the player to change their pick while
the dice are moving, which is the rule from section 12 of the design document.
"""

import random

import pygame

from config import settings
from game.betting import Betting
from game.history import RoundHistory, Streaks
from ui.particles import Confetti
from ui import ui
from ui.mode_screen import ModeScreen
from ui.result_ui import ResultPanel

# Keyboard shortcuts. A booth operator running a queue is much faster on the
# keyboard than with a mouse, and it costs nothing to support both.
COLOR_KEYS = {
    pygame.K_q: "RED",
    pygame.K_w: "BLUE",
    pygame.K_e: "GREEN",
    pygame.K_a: "YELLOW",
    pygame.K_s: "PURPLE",
    pygame.K_d: "ORANGE",
}

BETTING = "BETTING"
COUNTDOWN = "COUNTDOWN"
ROLLING = "ROLLING"
RESULT = "RESULT"

# If a die somehow keeps moving, stop the round anyway. A booth cannot wait.
MAX_ROLL_SECONDS = 6.0


class ColorRoyaleUI(ModeScreen):

    title = "COLOR ROYALE"

    def __init__(self, manager):
        super().__init__(manager, dice_size=26)

        self.betting = Betting(credits=manager.credits)
        self.phase = BETTING
        self.timer = 0.0

        # extras that make the booth feel livelier
        self.shown_credits = float(manager.credits)   # ticks towards the real
                                                      # number, never snaps
        self.history = RoundHistory()      # the strip along the bottom
        self.streaks = Streaks()           # wins/losses in a row
        self.confetti = Confetti()         # thrown on a win

        self._build_buttons()

        card = pygame.Rect(0, 0, 580, 470)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.result_panel = ResultPanel(card)
        self.result_panel.primary.on_click = self.play_again
        self.result_panel.secondary.on_click = self.go_to_menu

        self.set_message("PICK COLOUR, NUMBER AND BET")

    # ================================================================= building
    def _build_buttons(self):
        panel = self.panel_rect
        left = panel.left + 16
        width = panel.width - 32

        self.color_buttons = []
        y = panel.top + 96
        for index, name in enumerate(settings.COLOR_ORDER):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4), y + row * 38,
                               width // 2 - 4, 32)
            button = ui.Button(rect, name, font_size=16,
                               accent=settings.DICE_COLORS[name],
                               on_click=lambda n=name: self.pick_color(n))
            self.color_buttons.append(button)

        self.number_buttons = []
        y = panel.top + 240
        for index, value in enumerate(settings.DICE_FACES):
            column, row = index % 3, index // 3
            rect = pygame.Rect(left + column * (width // 3 + 2), y + row * 40,
                               width // 3 - 4, 34)
            button = ui.Button(rect, str(value), font_size=20,
                               on_click=lambda v=value: self.pick_number(v))
            button.pip_value = value      # show a dice face, not a digit
            self.number_buttons.append(button)

        self.bet_buttons = []
        y = panel.top + 330
        for index, amount in enumerate(settings.BET_AMOUNTS):
            column, row = index % 2, index // 2
            rect = pygame.Rect(left + column * (width // 2 + 4), y + row * 36,
                               width // 2 - 4, 32)
            button = ui.Button(rect, str(amount), font_size=18,
                               accent=settings.GOLD,
                               on_click=lambda a=amount: self.pick_amount(a))
            self.bet_buttons.append(button)

        lucky = pygame.Rect(left, panel.bottom - 182, width, 32)
        self.lucky_button = ui.Button(lucky, "LUCKY PICK", accent=settings.NEON_PINK,
                                      font_size=16, on_click=self.lucky_pick)

        place = pygame.Rect(left, panel.bottom - 146, width, 50)
        self.place_button = ui.Button(place, "PLACE BET", accent=settings.WIN_GREEN,
                                      font_size=24, on_click=self.place_bet)

    def buttons(self):
        return (self.color_buttons + self.number_buttons + self.bet_buttons
                + [self.lucky_button, self.place_button, self.back_button]
                + self.result_panel.buttons())

    # ================================================================ shortcuts
    def lucky_pick(self):
        """Fill in a random colour, number and affordable bet.

        Useful at a booth: a player who cannot decide can be rolling in one
        click instead of holding up the queue.
        """
        if self.phase != BETTING:
            return
        affordable = [a for a in settings.BET_AMOUNTS if a <= self.betting.credits]
        if not affordable:
            self.set_message("NOT ENOUGH CREDITS", settings.LOSE_RED)
            return

        self.audio.play("place")
        self.betting.select_color(random.choice(settings.COLOR_ORDER))
        self.betting.select_number(random.choice(settings.DICE_FACES))
        self.betting.select_amount(random.choice(affordable))
        self._refresh_selection()

    # =================================================================== picking
    def pick_color(self, name):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.betting.select_color(name)
        self._refresh_selection()

    def pick_number(self, value):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.betting.select_number(value)
        self._refresh_selection()

    def pick_amount(self, amount):
        if self.phase != BETTING:
            return
        self.audio.play("click")
        self.betting.select_amount(amount)
        self._refresh_selection()

    def _refresh_selection(self):
        """Light up the chosen buttons and update the hint line."""
        for button in self.color_buttons:
            button.selected = (button.label == self.betting.color)
        for button in self.number_buttons:
            button.selected = (button.label == str(self.betting.number))
        for button in self.bet_buttons:
            button.selected = (button.label == str(self.betting.amount))

        if self.betting.is_complete:
            ok, why = self.betting.validate()
            self.set_message("READY - PRESS PLACE BET" if ok else why,
                             settings.WIN_GREEN if ok else settings.LOSE_RED)
        else:
            self.set_message("PICK COLOUR, NUMBER AND BET")

    # ==================================================================== round
    def place_bet(self):
        if self.phase != BETTING:
            return

        ok, why = self.betting.place()
        if not ok:
            self.audio.play("lose")
            self.set_message(why, settings.LOSE_RED)
            return

        self.audio.play("place")
        self.manager.credits = self.betting.credits
        self.phase = COUNTDOWN
        self.timer = settings.COUNTDOWN_SECONDS
        self.set_message("GET READY", settings.NEON_CYAN)

    def play_again(self):
        self.audio.play("click")
        self.result_panel.hide()
        self.betting.clear_selection()
        self._refresh_selection()
        self.phase = BETTING

    def update_mode(self, dt):
        self.confetti.update(dt)

        # Roll the credit counter towards the real value. Watching the number
        # climb after a win is a small thing that makes the win feel bigger.
        target = float(self.betting.credits)
        gap = target - self.shown_credits
        if abs(gap) < 0.6:
            self.shown_credits = target
        else:
            self.shown_credits += gap * min(1.0, dt * 7.0)
        self.lucky_button.enabled = (self.phase == BETTING)
        self.result_panel.update(dt)

        # betting controls are live in exactly one phase
        live = (self.phase == BETTING)
        for button in self.color_buttons + self.number_buttons + self.bet_buttons:
            button.enabled = live
        self.place_button.enabled = live and self.betting.is_complete

        # Lock the exit while the dice are moving. The stake has already left
        # the wallet, so wandering out mid-roll would just lose it.
        self.back_button.enabled = self.phase in (BETTING, RESULT)

        if self.phase == COUNTDOWN:
            previous = self.timer
            self.timer -= dt
            # one beep per whole second
            if int(previous) != int(self.timer) and self.timer > 0:
                self.audio.play("beep")
            if self.timer <= 0:
                self.audio.play("place")
                self.dice.roll()
                self.phase = ROLLING
                self.timer = 0.0
                self.set_message("ROLLING...", settings.NEON_CYAN)

        elif self.phase == ROLLING:
            self.timer += dt
            if self.timer > MAX_ROLL_SECONDS:
                self.dice.force_settle_all()
            if self.dice_settled(dt):
                self._finish_round()

    def _finish_round(self):
        result = self.betting.settle(self.dice.results())
        self.manager.credits = self.betting.credits
        self.phase = RESULT

        self.history.add(result["color"], result["number"], result["won"])
        self.streaks.record(result["won"], result["payout"])

        if result["won"]:
            self.confetti.burst((self.play_rect.centerx, self.play_rect.centery))
            self.audio.play("win")
            title, color = "YOU WIN!", settings.WIN_GREEN
            note = f"+{result['change']} CREDITS"
        else:
            self.audio.play("lose")
            title, color = "YOU LOSE", settings.LOSE_RED
            note = f"{result['change']} CREDITS"

        lines = [
            ("YOUR PICK", f"{result['color']}  {result['number']}", settings.TEXT_BRIGHT),
            ("ACTUAL ROLL", f"{result['color']}  {result['actual']}", color),
            ("BET", str(result["bet"]), settings.GOLD),
            ("RETURNED", str(result["payout"]), settings.GOLD),
            ("CREDITS NOW", str(result["credits"]), settings.GOLD),
            ("STREAK", self.streaks.label(), settings.NEON_CYAN),
        ]
        # the whole board, so the player can see every die, not just theirs
        chips = [(name, result["results"][name]) for name in settings.COLOR_ORDER]

        self.result_panel.show(title, lines, title_color=color,
                               big_note=note, big_note_color=color,
                               chips=chips, chip_highlight=result["color"])
        self.set_message("")

    def help_content(self):
        return {
            "title": "HOW TO PLAY  ·  COLOR ROYALE",
            "summary": "Call one colour AND one number. Hit both and your bet doubles.",
            "steps": [
                "Pick a COLOUR - that is the die you are betting on.",
                "Pick a NUMBER from 1 to 6.",
                "Pick how much to bet, then press PLACE BET.",
                "All six dice roll. Your colour must land on your number.",
            ],
            "payouts": [("EXACT HIT", f"{settings.WIN_MULTIPLIER}x")],
            "controls": ("Q W E A S D  colour     1-6  number     "
                         "L  lucky pick     SPACE  roll     R  new player"),
        }

    # ==================================================================== input
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
            if event.key == pygame.K_l:
                self.lucky_pick()
                return
            if self.phase == BETTING and pygame.K_1 <= event.key <= pygame.K_6:
                # number keys 1-6 pick the face
                self.pick_number(event.key - pygame.K_0)
                return
            if self.phase == BETTING and event.key in COLOR_KEYS:
                self.pick_color(COLOR_KEYS[event.key])
                return
            if event.key == pygame.K_r:
                # Booth operator: start a fresh player. Streaks belong to the
                # player so they reset, but the history strip belongs to the
                # machine and keeps rolling, like a real perya board.
                self.streaks.reset()
                self.betting.reset_credits()
                self.manager.credits = self.betting.credits
                self._refresh_selection()
                self.set_message("CREDITS RESET", settings.GOLD)
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

        ui.draw_text(surface, "BETTING", (panel.centerx, panel.top + 14),
                     size=22, color=settings.NEON_CYAN, bold=True, align="midtop")

        chip = pygame.Rect(0, 0, panel.width - 32, 36)
        chip.midtop = (panel.centerx, panel.top + 44)
        pygame.draw.rect(surface, (12, 14, 34), chip, border_radius=18)
        pygame.draw.rect(surface, settings.GOLD, chip, width=2, border_radius=18)
        counting = abs(self.shown_credits - self.betting.credits) > 0.6
        credit_color = settings.WIN_GREEN if counting else settings.GOLD
        ui.draw_text(surface, f"CREDITS  {int(round(self.shown_credits))}",
                     chip.center, size=20, color=credit_color, bold=True,
                     align="center")

        for label, y in (("COLOUR", panel.top + 80),
                         ("NUMBER", panel.top + 224),
                         ("BET", panel.top + 314)):
            ui.draw_text(surface, label, (panel.left + 18, y), size=15,
                         color=settings.TEXT_DIM, bold=True)

        for button in self.color_buttons + self.number_buttons + self.bet_buttons:
            button.draw(surface)
        self.lucky_button.draw(surface)
        self.place_button.draw(surface)

        # the message and the out-of-credits warning share one line, so they
        # can never land on top of each other
        if self.betting.can_afford_anything():
            self.draw_message(surface, panel.bottom - 92)
        else:
            ui.draw_text(surface, "OUT OF CREDITS - PRESS R",
                         (panel.centerx, panel.bottom - 92), size=15,
                         color=settings.LOSE_RED, bold=True, align="midtop")

        if self.phase == BETTING:
            ui.draw_text(surface, "Q W E A S D = COLOUR      1-6 = NUMBER",
                         (panel.centerx, panel.bottom - 210), size=11,
                         color=settings.TEXT_DIM, bold=True, align="midtop")
            ui.draw_text(surface, "L = LUCKY PICK   SPACE = ROLL   R = NEW PLAYER",
                         (panel.centerx, panel.bottom - 198), size=11,
                         color=settings.TEXT_DIM, bold=True, align="midtop")

    def draw_overlay(self, surface):
        self._draw_session_bar(surface)
        self._draw_history_strip(surface)

        if self.phase == COUNTDOWN:
            self._draw_countdown(surface)
        elif self.phase == ROLLING:
            # inside the machine's empty upper panel, clear of its lit sign
            ui.draw_glow_text(surface, "ROLLING...",
                              (self.play_rect.centerx, self.play_rect.top + 118),
                              size=32, color=settings.NEON_CYAN, align="center")

        self.result_panel.draw(surface)
        self.confetti.draw(surface)      # paper falls in front of everything

    # ------------------------------------------------------------- the extras
    def _draw_session_bar(self, surface):
        """Streak and totals, in the thin band above the machine."""
        if self.phase in (COUNTDOWN, ROLLING):
            return          # keep this space clear for the countdown

        y = self.play_rect.top + 6
        streak_color = settings.TEXT_DIM
        if self.streaks.current > 0:
            streak_color = settings.WIN_GREEN
        elif self.streaks.current < 0:
            streak_color = settings.LOSE_RED

        ui.draw_text(surface, self.streaks.label(), (self.play_rect.left + 14, y),
                     size=16, color=streak_color, bold=True)

        if self.streaks.rounds:
            summary = (f"ROUNDS {self.streaks.rounds}   "
                       f"WON {self.streaks.wins}   "
                       f"BEST RUN {self.streaks.best_win_streak}")
            ui.draw_text(surface, summary, (self.play_rect.right - 14, y),
                         size=16, color=settings.TEXT_DIM, bold=True,
                         align="topright")

    def _draw_history_strip(self, surface):
        """The last dozen rounds, oldest on the left.

        This is decoration and a talking point, not a prediction tool: every
        roll is independent of the one before it.
        """
        entries = self.history.recent()
        if not entries:
            return

        strip_y = self.tumbler.rect.bottom - 42
        ui.draw_text(surface, "LAST ROUNDS",
                     (self.tumbler.rect.left + 26, strip_y + 4),
                     size=13, color=settings.TEXT_DIM, bold=True)

        tile_w, gap = 34, 5
        x = self.tumbler.rect.left + 128
        for entry in entries:
            color = settings.DICE_COLORS[entry["color"]]
            tile = pygame.Rect(x, strip_y, tile_w, 24)
            pygame.draw.rect(surface, ui.shade(color, 0.35), tile, border_radius=5)
            pygame.draw.rect(surface, color, tile, width=1, border_radius=5)
            ui.draw_text(surface, str(entry["number"]), (tile.centerx, tile.centery),
                         size=15, color=settings.TEXT_BRIGHT, bold=True,
                         align="center")
            if entry["won"]:
                pygame.draw.rect(surface, settings.WIN_GREEN, tile, width=2,
                                 border_radius=5)
            x += tile_w + gap

    def _draw_countdown(self, surface):
        number = max(1, int(self.timer) + 1)
        # the number shrinks as its second runs out
        fraction = self.timer - int(self.timer)
        size = int(90 + 60 * fraction)
        ui.draw_glow_text(surface, str(number),
                          (self.play_rect.centerx, self.play_rect.centery),
                          size=size, color=settings.GOLD, align="center", glow=10)
