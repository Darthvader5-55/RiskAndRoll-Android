"""
ui/result_ui.py
---------------
The result card that slides up at the end of a round.

One class, used by all three modes:

    Color Royale     YOU WIN / YOU LOSE + payout
    Consequence Pool who lost + their dare
    Arcade Duel      which player won + the totals

The mode builds a ResultPanel, fills in a title and some lines, and the panel
handles the animation, the two buttons and the drawing.
"""

import pygame

from config import settings
from ui import ui


class ResultPanel:
    """A pop-up card with a title, a few lines of text and two buttons."""

    def __init__(self, rect, primary_label="PLAY AGAIN", secondary_label="MAIN MENU"):
        self.rect = pygame.Rect(rect)
        self.visible = False
        self.slide = 0.0            # 0.0 = off screen, 1.0 = fully up

        self.title = ""
        self.title_color = settings.TEXT_BRIGHT
        self.lines = []             # list of (label, value, colour)
        self.big_note = ""
        self.big_note_color = settings.TEXT_BRIGHT
        self.chips = []             # list of (colour name, value) for the six dice
        self.chip_highlight = None  # one colour name to ring in white

        button_w = (self.rect.width - 60) // 2
        primary = pygame.Rect(0, 0, button_w, 52)
        primary.bottomleft = (self.rect.left + 20, self.rect.bottom - 20)
        secondary = pygame.Rect(0, 0, button_w, 52)
        secondary.bottomright = (self.rect.right - 20, self.rect.bottom - 20)

        self.primary = ui.Button(primary, primary_label, accent=settings.NEON_CYAN)
        self.secondary = ui.Button(secondary, secondary_label,
                                   accent=settings.TEXT_DIM)

    # ==================================================================== setup
    def show(self, title, lines, title_color=settings.TEXT_BRIGHT,
             big_note="", big_note_color=settings.TEXT_BRIGHT,
             chips=None, chip_highlight=None):
        self.title = title
        self.title_color = title_color
        self.lines = lines
        self.big_note = big_note
        self.big_note_color = big_note_color
        self.chips = chips or []
        self.chip_highlight = chip_highlight
        self.visible = True
        self.slide = 0.0

    def hide(self):
        self.visible = False
        self.slide = 0.0

    def buttons(self):
        return [self.primary, self.secondary] if self.visible else []

    # =================================================================== update
    def update(self, dt):
        if not self.visible:
            return
        # ease towards 1.0: fast at first, slow at the end
        self.slide += (1.0 - self.slide) * min(1.0, dt * 9)
        for button in self.buttons():
            button.update(dt)

    def handle_event(self, event):
        if not self.visible:
            return
        for button in self.buttons():
            button.handle_event(event)

    # ===================================================================== draw
    def draw(self, surface):
        if not self.visible:
            return

        # dim everything behind the card
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(150 * self.slide)))
        surface.blit(dim, (0, 0))

        rect = self.rect.copy()
        rect.y += int((1 - self.slide) * 60)      # slide up into place

        ui.draw_panel(surface, rect, radius=22, glow_color=self.title_color)
        pygame.draw.rect(surface, self.title_color, rect, width=2, border_radius=22)

        ui.draw_glow_text(surface, self.title, (rect.centerx, rect.top + 24),
                          size=42, color=self.title_color, align="midtop", glow=8)

        y = rect.top + 88
        if self.big_note:
            ui.draw_text(surface, self.big_note, (rect.centerx, y), size=30,
                         color=self.big_note_color, bold=True, align="midtop")
            y += 46

        if self.chips:
            y = self._draw_chips(surface, rect, y)

        for label, value, color in self.lines:
            ui.draw_text(surface, label, (rect.left + 32, y), size=19,
                         color=settings.TEXT_DIM, bold=True)
            ui.draw_text(surface, value, (rect.right - 32, y), size=19,
                         color=color, bold=True, align="topright")
            y += 30

        self.primary.draw(surface)
        self.secondary.draw(surface)

    def _draw_chips(self, surface, rect, y):
        """A row of six little coloured tiles: the whole board at a glance.

        The player bet on one colour, but they still want to see what every
        die landed on. The one they picked gets a white ring around it.
        """
        count = len(self.chips)
        tile_w, gap = 74, 8
        total = count * tile_w + (count - 1) * gap
        x = rect.centerx - total // 2

        for name, value in self.chips:
            color = settings.DICE_COLORS.get(name, settings.TEXT_DIM)
            tile = pygame.Rect(x, y, tile_w, 56)
            pygame.draw.rect(surface, ui.shade(color, 0.30), tile, border_radius=8)
            pygame.draw.rect(surface, color, tile, width=2, border_radius=8)
            if name == self.chip_highlight:
                pygame.draw.rect(surface, settings.TEXT_BRIGHT,
                                 tile.inflate(6, 6), width=2, border_radius=10)
            ui.draw_text(surface, name[:3], (tile.centerx, tile.top + 6), size=14,
                         color=color, bold=True, align="midtop")
            ui.draw_text(surface, str(value), (tile.centerx, tile.top + 24), size=26,
                         color=settings.TEXT_BRIGHT, bold=True, align="midtop")
            x += tile_w + gap

        return y + 70
