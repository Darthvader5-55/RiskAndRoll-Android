"""
ui/help_ui.py
-------------
The HOW TO PLAY card, shared by every mode.

At a booth nobody reads a sign taped to the table. They walk up, look at the
screen, and either understand it in five seconds or leave. So every mode has
a "?" button in the corner that opens this card: what the mode is, the steps
in order, what it pays, and the keys.

Each mode supplies its own words through help_content() - this file only
knows how to lay them out, exactly like ResultPanel only knows how to lay out
a result.
"""

import pygame

from config import settings
from ui import ui

SLIDE_SPEED = 9.0


class HelpPanel:
    """A card explaining one mode. Hidden until the player asks for it."""

    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.visible = False
        self.slide = 0.0            # 0 = off screen, 1 = fully in

        self.title = ""
        self.summary = ""
        self.steps = []             # list of strings, numbered on screen
        self.payouts = []           # list of (label, value) pairs
        self.controls = ""

        button = pygame.Rect(0, 0, 220, 46)
        button.midbottom = (self.rect.centerx, self.rect.bottom - 18)
        self.close_button = ui.Button(button, "GOT IT",
                                      accent=settings.WIN_GREEN, font_size=22,
                                      on_click=self.hide)

    # ==================================================================== show
    def show(self, content):
        """content is the dictionary a mode's help_content() returns."""
        self.title = content.get("title", "HOW TO PLAY")
        self.summary = content.get("summary", "")
        self.steps = content.get("steps", [])
        self.payouts = content.get("payouts", [])
        self.controls = content.get("controls", "")
        self.visible = True
        self.slide = 0.0

    def hide(self):
        self.visible = False
        self.slide = 0.0

    def toggle(self, content):
        if self.visible:
            self.hide()
        else:
            self.show(content)

    # ================================================================== update
    def update(self, dt):
        if self.visible and self.slide < 1.0:
            self.slide = min(1.0, self.slide + dt * SLIDE_SPEED)
        self.close_button.update(dt)

    def handle_event(self, event):
        """Returns True if the card swallowed the event.

        While the card is open it takes every click and key, so a player
        reading the rules cannot accidentally place a bet behind it.
        """
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN,
                             pygame.K_h):
                self.hide()
            return True

        self.close_button.handle_event(event)
        return True

    # ==================================================================== draw
    def draw(self, surface):
        if not self.visible:
            return

        # dim everything behind, so the card is clearly the only thing to read
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((3, 5, 16, int(200 * self.slide)))
        surface.blit(veil, (0, 0))

        rect = self.rect.move(0, int((1.0 - self.slide) * 40))
        ui.draw_panel(surface, rect, radius=20, glow_color=settings.NEON_CYAN,
                      screws=True)
        pygame.draw.rect(surface, settings.NEON_CYAN, rect, width=2,
                         border_radius=20)

        y = rect.top + 22
        ui.draw_glow_text(surface, self.title, (rect.centerx, y), size=34,
                          color=settings.NEON_CYAN, align="midtop", glow=6)
        y += 46

        if self.summary:
            ui.draw_text(surface, self.summary, (rect.centerx, y), size=17,
                         color=settings.TEXT_BRIGHT, bold=True, align="midtop")
            y += 30

        # the steps, numbered in their own little circles
        for index, step in enumerate(self.steps, start=1):
            pygame.draw.circle(surface, settings.NEON_CYAN,
                               (rect.left + 40, y + 9), 11)
            ui.draw_text(surface, str(index), (rect.left + 40, y + 9), size=15,
                         color=(8, 10, 26), bold=True, align="center")
            ui.draw_text(surface, step, (rect.left + 62, y), size=17,
                         color=settings.TEXT_BRIGHT, bold=True)
            y += 30

        if self.payouts:
            y += 8
            ui.draw_text(surface, "PAYS", (rect.left + 30, y), size=13,
                         color=settings.TEXT_DIM, bold=True)
            y += 20
            width = (rect.width - 60) // max(1, len(self.payouts))
            for index, (label, value) in enumerate(self.payouts):
                box = pygame.Rect(rect.left + 30 + index * width, y,
                                  width - 8, 42)
                accent = (settings.GOLD if index == len(self.payouts) - 1
                          else settings.NEON_CYAN)
                pygame.draw.rect(surface, (14, 17, 40), box, border_radius=8)
                pygame.draw.rect(surface, accent, box, width=1, border_radius=8)
                ui.draw_text(surface, label, (box.centerx, box.top + 5),
                             size=12, color=settings.TEXT_DIM, bold=True,
                             align="midtop")
                ui.draw_text(surface, value, (box.centerx, box.top + 19),
                             size=19, color=accent, bold=True, align="midtop")
            y += 52

        if self.controls:
            ui.draw_text(surface, self.controls, (rect.centerx, y), size=14,
                         color=settings.TEXT_DIM, bold=True, align="midtop")

        self.close_button.draw(surface)
