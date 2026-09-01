"""
ui/particles.py
---------------
A confetti burst for winning rounds.

Each piece of confetti is a tiny rectangle with a position, a speed and a
spin. Gravity pulls them down, they fade out, and once they are all gone the
burst empties itself. This is the same physics idea as the dice, just simpler
and with no bouncing.

Nothing else in the game depends on this file, so if it ever misbehaves you
can delete the two calls to it in ui/color_royale_ui.py and lose nothing else.
"""

import random

import pygame

from config import settings

GRAVITY = 900.0        # pixels per second, per second
DRAG = 0.99            # sideways slowdown per frame
FADE_SECONDS = 1.6     # how long a piece lasts


class Confetti:
    """A burst of paper. Create one, call burst(), then update and draw it."""

    def __init__(self):
        self.pieces = []

    def burst(self, center, count=70):
        """Throw confetti outwards and upwards from a point."""
        x, y = center
        for _ in range(count):
            angle = random.uniform(0, 6.283)
            speed = random.uniform(120, 460)
            self.pieces.append({
                "x": x + random.uniform(-60, 60),
                "y": y + random.uniform(-20, 20),
                "vx": speed * random.uniform(-1, 1),
                "vy": -abs(speed) * random.uniform(0.5, 1.2),
                "spin": random.uniform(-540, 540),
                "angle": random.uniform(0, 360),
                "life": FADE_SECONDS * random.uniform(0.7, 1.2),
                "age": 0.0,
                "w": random.randint(5, 10),
                "h": random.randint(8, 14),
                "color": random.choice(list(settings.DICE_COLORS.values())
                                       + [settings.GOLD, settings.NEON_CYAN]),
            })

    @property
    def active(self):
        return bool(self.pieces)

    def clear(self):
        self.pieces.clear()

    # ================================================================= update
    def update(self, dt):
        for piece in self.pieces:
            piece["vy"] += GRAVITY * dt
            piece["vx"] *= DRAG
            piece["x"] += piece["vx"] * dt
            piece["y"] += piece["vy"] * dt
            piece["angle"] += piece["spin"] * dt
            piece["age"] += dt

        # keep only the pieces that are still alive and still on screen
        self.pieces = [p for p in self.pieces
                       if p["age"] < p["life"] and p["y"] < settings.SCREEN_HEIGHT + 40]

    # =================================================================== draw
    def draw(self, surface):
        for piece in self.pieces:
            fade = 1.0 - piece["age"] / piece["life"]
            paper = pygame.Surface((piece["w"], piece["h"]), pygame.SRCALPHA)
            paper.fill((*piece["color"], int(255 * max(0.0, fade))))
            paper = pygame.transform.rotate(paper, piece["angle"])
            surface.blit(paper, paper.get_rect(center=(int(piece["x"]),
                                                       int(piece["y"]))))
