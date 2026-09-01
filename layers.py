"""
game/layers.py
--------------
THE 2.5D ENGINE OF THE PROJECT.

Pygame only knows flat pictures. To make things look three-dimensional we
need two simple ideas, and both live in this file.

IDEA 1 - THE STAGE (perspective)
    We pretend the screen shows a floor that runs away from the camera.
    Every object is described with three numbers instead of two:

        x       -1.0 = left wall, 0.0 = middle, 1.0 = right wall
        depth    0.0 = far away at the back, 1.0 = closest to the player
        height   how many pixels the object floats above the floor

    Stage.project() turns those three numbers into a screen position PLUS a
    scale. Far objects come out small and close together, near objects come
    out big and spread apart. That is perspective.

IDEA 2 - LAYERS (draw order)
    Even with perspective, a die drawn after the glass would look like it is
    outside the machine. So every drawing is put in a numbered layer and the
    DepthRenderer sorts them before anything reaches the screen.

Nothing here imports Pygame drawing of dice or the tumbler, so both can use
it without knowing about each other.
"""

import pygame

from ui.ui import lerp, clamp


# ===========================================================================
# LAYERS
# ===========================================================================

class Layer:
    """Draw order, exactly as planned in the design document.

    Lower numbers are painted first, so higher numbers end up on top.
    """

    BACKGROUND = 0      # room, floor, walls
    TUMBLER_BACK = 1    # inside back wall of the machine
    INTERIOR_LIGHT = 2  # glow inside the machine
    DICE_SHADOW = 3     # shadows on the machine floor
    DICE = 4            # the dice themselves
    EFFECTS = 5         # sparks, dust, motion trails
    GLASS = 6           # the transparent front window
    FRONT_FRAME = 7     # metal frame in front of the glass
    UI = 8              # buttons, text, panels


class DepthRenderer:
    """Collects drawing jobs, sorts them, then runs them.

    Instead of calling draw() in a fixed order, each object hands over a
    small function. Example:

        renderer.add(Layer.DICE, die.draw, sort_y=die.screen_y)

    Two dice in the SAME layer are sorted by sort_y, so the die lower on the
    screen (closer to the player) is drawn last and appears in front.
    """

    def __init__(self):
        self.jobs = []

    def add(self, layer, draw_function, sort_y=0.0):
        self.jobs.append((layer, sort_y, len(self.jobs), draw_function))

    def draw(self, surface):
        # sort by layer, then by screen height, then by insertion order
        self.jobs.sort(key=lambda job: (job[0], job[1], job[2]))
        for _layer, _y, _index, draw_function in self.jobs:
            draw_function(surface)
        self.jobs.clear()


# ===========================================================================
# STAGE (the fake 3D floor)
# ===========================================================================

class Stage:
    """A trapezoid floor drawn in perspective.

    back_width  how wide the far edge is compared to the near edge
    back_scale  how small an object looks when it sits at the very back
    """

    def __init__(self, rect, back_width=0.58, back_scale=0.62, squeeze=0.85):
        self.rect = pygame.Rect(rect)
        self.back_width = back_width
        self.back_scale = back_scale
        self.squeeze = squeeze   # <1.0 packs the far rows closer together

    # ------------------------------------------------------------ geometry
    def row_y(self, depth):
        """Screen y of the floor line at this depth."""
        depth = clamp(depth, 0.0, 1.0)
        return lerp(self.rect.top, self.rect.bottom, depth ** self.squeeze)

    def half_width(self, depth):
        """Half the floor width at this depth (small at the back)."""
        depth = clamp(depth, 0.0, 1.0)
        return lerp(self.rect.width * 0.5 * self.back_width,
                    self.rect.width * 0.5, depth)

    def scale(self, depth):
        """How big an object at this depth should be drawn."""
        return lerp(self.back_scale, 1.0, clamp(depth, 0.0, 1.0))

    def project(self, x, depth, height=0.0):
        """The one function everything else calls.

        Returns (screen_x, screen_y, scale).
        """
        s = self.scale(depth)
        screen_x = self.rect.centerx + x * self.half_width(depth)
        screen_y = self.row_y(depth) - height * s
        return screen_x, screen_y, s

    def floor_point(self, x, depth):
        """Where an object's shadow lands, ignoring its height."""
        screen_x, screen_y, _ = self.project(x, depth, 0.0)
        return screen_x, screen_y

    def corners(self):
        """The four screen corners of the floor, for drawing it."""
        back = self.half_width(0.0)
        front = self.half_width(1.0)
        cx = self.rect.centerx
        return [
            (cx - back, self.row_y(0.0)),
            (cx + back, self.row_y(0.0)),
            (cx + front, self.row_y(1.0)),
            (cx - front, self.row_y(1.0)),
        ]


# ===========================================================================
# SHADOWS
# ===========================================================================

_shadow_cache = {}


def _shadow_image(width, height, alpha):
    """A soft dark ellipse, built once per size."""
    key = (int(width), int(height), int(alpha))
    if key not in _shadow_cache:
        w, h = max(6, int(width)), max(4, int(height))
        # Draw the ellipse at QUARTER size, then blow it back up. Stretching a
        # small picture blurs it, so we get a soft-edged shadow for free
        # instead of a hard black blob. The inflate leaves a transparent
        # border for the blur to bleed into.
        small_w, small_h = max(3, w // 4), max(3, h // 4)
        small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        pygame.draw.ellipse(small, (0, 0, 0, int(alpha)),
                            small.get_rect().inflate(-2, -2))
        _shadow_cache[key] = pygame.transform.smoothscale(small, (w, h))
    return _shadow_cache[key]


def draw_shadow(surface, stage, x, depth, height, size, max_height=220.0):
    """Drop a shadow on the floor underneath a flying object.

    The higher the object, the smaller and fainter its shadow gets. This one
    detail does more for the 2.5D illusion than anything else in the game.
    """
    floor_x, floor_y = stage.floor_point(x, depth)
    scale = stage.scale(depth)

    lift = clamp(height / max_height, 0.0, 1.0)
    shrink = lerp(1.0, 0.45, lift)
    alpha = lerp(115, 40, lift)

    # The shadow has to be WIDER than the object, or the object sits on top of
    # it and hides it completely. It is also nudged down and to the left,
    # because the dice are lit from above and to the right.
    width = size * 2.7 * scale * shrink
    center = (int(floor_x - size * 0.10 * scale),
              int(floor_y + size * 0.18 * scale))
    image = _shadow_image(width, width * 0.44, alpha)
    surface.blit(image, image.get_rect(center=center))
