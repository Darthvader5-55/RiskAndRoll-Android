"""
game/tumbler.py
---------------
The dice machine itself — the visual centrepiece of the game.

There is no 3D model here. The machine is FIVE flat pictures stacked in the
right order, with the dice sandwiched in the middle:

        FRONT_FRAME   metal frame, sign, bolts, neon strips   <- in front
        GLASS         the window, with a shine baked in
        ---------     (the dice and their shadows go here)
        INTERIOR      lit floor, grid, light pool
        TUMBLER_BACK  back wall and the two side walls

Because the dice are drawn AFTER the interior but BEFORE the glass, the eye
reads them as being inside a box. That one ordering trick is what sells the
whole illusion.

The four pictures never change, so each is painted once in _build_images()
and then blitted every frame. Only the neon lights are redrawn live.

The class also answers the question the physics will ask in Phase 4:
"where are the walls?" — see the BOUNDS section at the bottom.
"""

import math

import pygame

from config import settings
from game.layers import Stage, Layer
from ui import ui

# Frame thickness in pixels. The sign is the lit header, the base is the
# chunky bottom that makes the machine look like it stands on the floor.
FRAME_THICKNESS = 22
SIGN_HEIGHT = 56
BASE_HEIGHT = 46

METAL_LIGHT = (78, 88, 130)
METAL_DARK = (26, 30, 56)
INTERIOR_DARK = (10, 13, 32)


class Tumbler:
    """One dice machine, positioned by a screen rectangle."""

    def __init__(self, rect, title=None):
        self.rect = pygame.Rect(rect)
        # the name on the machine's lit sign, from settings so renaming the
        # game is a single line rather than a hunt through the code
        self.title = title or settings.GAME_TITLE
        self.time = 0.0
        self._lamp_stops = None

        # The opening is the see-through part: the whole machine minus the
        # frame, the sign at the top and the base at the bottom.
        self.opening = pygame.Rect(
            self.rect.left + FRAME_THICKNESS,
            self.rect.top + SIGN_HEIGHT,
            self.rect.width - FRAME_THICKNESS * 2,
            self.rect.height - SIGN_HEIGHT - BASE_HEIGHT,
        )

        # The floor the dice land on. It fills the lower half of the opening,
        # inset a little so dice never touch the side walls exactly.
        self.stage = Stage(pygame.Rect(
            self.opening.left + 26,
            self.opening.top + int(self.opening.height * 0.42),
            self.opening.width - 52,
            int(self.opening.height * 0.52),
        ))

        self._build_images()

    # =======================================================================
    # BUILDING THE PICTURES  (runs once)
    # =======================================================================
    def _build_images(self):
        self.back_image = self._build_back()
        self.interior_image = self._build_interior()
        self.glass_image = ui.make_glass(self.opening.size, radius=10,
                                         strength=14)
        self.frame_image = self._build_frame()

    # ------------------------------------------------------------ back ----
    def _build_back(self):
        """Back wall + the two side walls, drawn on the opening's own surface."""
        w, h = self.opening.size
        image = pygame.Surface((w, h))
        ui.draw_vertical_gradient(image, image.get_rect(),
                                  INTERIOR_DARK, (18, 20, 46))

        floor_top = self.stage.rect.top - self.opening.top
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        # --- back wall: a panel above the floor line, with vertical ribs ---
        pygame.draw.rect(overlay, (16, 20, 48, 255), (0, 0, w, floor_top))
        for x in range(0, w, 34):
            pygame.draw.line(overlay, (40, 52, 96, 70), (x, 0), (x, floor_top), 1)

        # a recessed panel with neon corner brackets, so the upper half of
        # the machine is not dead space while the dice are on the floor
        panel = pygame.Rect(60, 26, w - 120, floor_top - 56)
        # remember it in screen coordinates so the live parts (the equaliser
        # and the running lights) know where to draw each frame
        self.back_panel = panel.move(self.opening.left, self.opening.top)
        pygame.draw.rect(overlay, (10, 13, 34, 200), panel, border_radius=8)
        pygame.draw.rect(overlay, (46, 58, 104, 160), panel, width=1, border_radius=8)
        bracket = 26
        for cx, cy, dx, dy in ((panel.left, panel.top, 1, 1),
                               (panel.right, panel.top, -1, 1),
                               (panel.left, panel.bottom, 1, -1),
                               (panel.right, panel.bottom, -1, -1)):
            pygame.draw.line(overlay, (*settings.NEON_CYAN, 120),
                             (cx, cy), (cx + bracket * dx, cy), 2)
            pygame.draw.line(overlay, (*settings.NEON_CYAN, 120),
                             (cx, cy), (cx, cy + bracket * dy), 2)

        # --- side walls: quads that lean inwards towards the back ---------
        # The slant is what turns two flat bars into a room with depth.
        wall_inset = self.stage.rect.left - self.opening.left
        left_wall = [(0, 0), (wall_inset, floor_top), (wall_inset, h), (0, h)]
        right_wall = [(w, 0), (w - wall_inset, floor_top),
                      (w - wall_inset, h), (w, h)]
        pygame.draw.polygon(overlay, (12, 15, 38, 240), left_wall)
        pygame.draw.polygon(overlay, (12, 15, 38, 240), right_wall)
        pygame.draw.line(overlay, (*settings.NEON_CYAN, 60),
                         (wall_inset, floor_top), (wall_inset, h), 2)
        pygame.draw.line(overlay, (*settings.NEON_CYAN, 60),
                         (w - wall_inset, floor_top), (w - wall_inset, h), 2)

        # --- a soft glow where the back wall meets the floor ---------------
        for offset in range(-16, 17):
            alpha = int(48 * (1 - abs(offset) / 16))
            pygame.draw.line(overlay, (*settings.NEON_CYAN, alpha),
                             (0, floor_top + offset), (w, floor_top + offset))

        image.blit(overlay, (0, 0))
        return image

    # -------------------------------------------------------- interior ----
    def _build_interior(self):
        """The lit floor the dice roll on, drawn from the Stage maths."""
        image = pygame.Surface(self.opening.size, pygame.SRCALPHA)
        stage = self.stage
        # Stage coordinates are screen coordinates, so shift them onto this
        # smaller surface by subtracting the opening's top-left corner.
        ox, oy = self.opening.left, self.opening.top

        def local(point):
            return (point[0] - ox, point[1] - oy)

        corners = [local(c) for c in stage.corners()]
        pygame.draw.polygon(image, (22, 30, 66, 255), corners)

        # rows across the floor, packed tighter towards the back
        for i in range(11):
            depth = i / 10.0
            y = stage.row_y(depth) - oy
            half = stage.half_width(depth)
            alpha = int(ui.lerp(26, 78, depth))
            pygame.draw.line(image, (70, 120, 190, alpha),
                             (stage.rect.centerx - half - ox, y),
                             (stage.rect.centerx + half - ox, y), 1)

        # lines running away from the player
        for i in range(-4, 5):
            x = i / 4.0
            pygame.draw.line(image, (70, 120, 190, 45),
                             local(stage.floor_point(x, 0.0)),
                             local(stage.floor_point(x, 1.0)), 1)

        # pool of light in the middle of the floor (small -> stretched = soft)
        pool_w = int(stage.rect.width * 0.7)
        pool_h = int(pool_w * 0.34)
        small = pygame.Surface((96, 40), pygame.SRCALPHA)
        for i in range(5):          # a few nested ellipses = a soft falloff
            fade = 1 - i / 5.0
            inset = int(i * 7)
            pygame.draw.ellipse(small, (*settings.NEON_CYAN, int(14 * fade)),
                                small.get_rect().inflate(-inset, -inset * 0.4))
        pool = pygame.transform.smoothscale(small, (pool_w, pool_h))
        center = local(stage.floor_point(0.0, 0.6))
        image.blit(pool, pool.get_rect(center=(int(center[0]), int(center[1]))))

        # bright edge along the front lip of the floor
        pygame.draw.line(image, (*settings.NEON_CYAN, 110),
                         corners[3], corners[2], 2)
        return image

    # ----------------------------------------------------------- frame ----
    def _build_frame(self):
        """The metal shell. The window area is punched out so we can see in."""
        w, h = self.rect.size
        image = pygame.Surface((w, h), pygame.SRCALPHA)

        # solid metal body first
        body = pygame.Surface((w, h), pygame.SRCALPHA)
        ui.draw_vertical_gradient(body, body.get_rect(), METAL_LIGHT, METAL_DARK)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=26)
        body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        image.blit(body, (0, 0))

        # punch the window out. pygame.draw writes RGBA straight onto the
        # surface, so drawing a fully transparent colour cuts a real hole.
        hole = self.opening.move(-self.rect.left, -self.rect.top)
        pygame.draw.rect(image, (0, 0, 0, 0), hole, border_radius=10)
        pygame.draw.rect(image, (10, 12, 28, 255), hole, width=3, border_radius=10)

        # --- sign panel at the top -----------------------------------------
        sign = pygame.Rect(FRAME_THICKNESS, 10, w - FRAME_THICKNESS * 2, SIGN_HEIGHT - 18)
        pygame.draw.rect(image, (14, 17, 40), sign, border_radius=10)
        pygame.draw.rect(image, settings.NEON_CYAN, sign, width=2, border_radius=10)
        ui.draw_glow_text(image, self.title, sign.center, size=30,
                          color=settings.NEON_CYAN, align="center", glow=6)

        # --- base: a darker slab with vents --------------------------------
        base = pygame.Rect(FRAME_THICKNESS, h - BASE_HEIGHT + 6,
                           w - FRAME_THICKNESS * 2, BASE_HEIGHT - 16)
        pygame.draw.rect(image, (18, 21, 46), base, border_radius=8)
        for i in range(7):
            vent_x = base.centerx - 90 + i * 30
            pygame.draw.line(image, (44, 52, 92),
                             (vent_x, base.top + 8), (vent_x, base.bottom - 8), 3)

        # --- bolts in the four corners -------------------------------------
        for bx, by in ((26, SIGN_HEIGHT + 6), (w - 26, SIGN_HEIGHT + 6),
                       (26, h - BASE_HEIGHT - 6), (w - 26, h - BASE_HEIGHT - 6)):
            pygame.draw.circle(image, (96, 106, 150), (bx, by), 5)
            pygame.draw.circle(image, (30, 34, 62), (bx, by), 5, 1)

        # --- highlight down the left edge = curved metal --------------------
        pygame.draw.line(image, (120, 135, 190, 120), (6, 30), (6, h - 30), 2)
        return image

    # =======================================================================
    # PER-FRAME
    # =======================================================================
    def update(self, dt):
        self.time += dt

    def add_to(self, renderer):
        """Register all four pictures with the DepthRenderer.

        The screen calls this, then adds its dice. The renderer sorts by
        layer, so the dice always end up between the interior and the glass
        no matter what order things were added in.
        """
        renderer.add(Layer.TUMBLER_BACK, self.draw_back)
        renderer.add(Layer.INTERIOR_LIGHT, self.draw_interior)
        renderer.add(Layer.GLASS, self.draw_glass)
        renderer.add(Layer.FRONT_FRAME, self.draw_frame)

    def draw_back(self, surface):
        surface.blit(self.back_image, self.opening.topleft)
        self._draw_equaliser(surface)
        self._draw_running_lights(surface)

    def _draw_equaliser(self, surface):
        """Bars bouncing along the bottom of the back panel.

        The upper half of the machine is empty while the dice are on the
        floor. A row of moving bars fills it without covering anything, and
        because they move it stops the whole back wall looking like a still
        picture.
        """
        panel = self.back_panel
        count = 26
        gap = 3
        bar_w = max(3, (panel.width - 40 - gap * (count - 1)) // count)
        base = panel.bottom - 10
        max_h = min(46, panel.height - 20)
        x = panel.left + 20

        for index in range(count):
            # three sine waves at different speeds, so the pattern never
            # repeats in an obvious way
            wave = (math.sin(self.time * 2.1 + index * 0.55)
                    + math.sin(self.time * 3.7 + index * 0.21)
                    + math.sin(self.time * 1.3 + index * 0.9))
            level = (wave + 3.0) / 6.0
            height = max(3, int(max_h * (0.15 + 0.85 * level ** 1.6)))

            tint = settings.NEON_CYAN if level < 0.72 else settings.NEON_PINK
            bar = pygame.Rect(x, base - height, bar_w, height)
            glow = pygame.Surface(bar.size, pygame.SRCALPHA)
            glow.fill((*tint, 70))
            surface.blit(glow, bar.topleft)
            pygame.draw.rect(surface, ui.shade(tint, 0.9),
                             pygame.Rect(bar.left, bar.top, bar_w, 2))
            x += bar_w + gap

    def _lamp_positions(self):
        """Where the marquee lamps sit. Worked out once, not every frame."""
        if self._lamp_stops is None:
            panel = self.back_panel.inflate(-6, -6)
            spacing = 34
            stops = []
            for x in range(panel.left, panel.right, spacing):
                stops.append((x, panel.top))
            for y in range(panel.top, panel.bottom, spacing):
                stops.append((panel.right, y))
            for x in range(panel.right, panel.left, -spacing):
                stops.append((x, panel.bottom))
            for y in range(panel.bottom, panel.top, -spacing):
                stops.append((panel.left, y))
            self._lamp_stops = stops
        return self._lamp_stops

    def _draw_running_lights(self, surface):
        """A chase of small lamps around the back panel, like a real marquee."""
        stops = self._lamp_positions()
        head = (self.time * 9.0) % len(stops)
        for index, (x, y) in enumerate(stops):
            # how far this lamp is behind the moving head, 0 = lit now
            behind = (head - index) % len(stops)
            if behind > 6:
                continue
            fade = 1.0 - behind / 6.0
            pygame.draw.circle(surface, ui.shade(settings.NEON_CYAN, fade),
                               (int(x), int(y)), 2)

    def draw_interior(self, surface):
        surface.blit(self.interior_image, self.opening.topleft)

    def draw_glass(self, surface):
        surface.blit(self.glass_image, self.opening.topleft)

    def draw_frame(self, surface):
        surface.blit(self.frame_image, self.rect.topleft)
        self._draw_plinth(surface)
        self._draw_neon_strips(surface)

    def _draw_plinth(self, surface):
        """A base that flares out towards the viewer.

        A rectangle standing on a floor still looks like a rectangle. Give it
        a base that is WIDER at the front than at the back and the eye reads
        the whole cabinet as a box with a footprint, because only something
        with depth would spread out like that.
        """
        rect = self.rect
        top_y = rect.bottom - 34
        spread = 20

        face = [(rect.left + 4, top_y),
                (rect.right - 4, top_y),
                (rect.right + spread, rect.bottom),
                (rect.left - spread, rect.bottom)]
        pygame.draw.polygon(surface, (21, 25, 52), face)
        pygame.draw.polygon(surface, (52, 62, 104), face, 2)

        # a lit strip along the front edge, and vents in the middle
        pygame.draw.line(surface, ui.shade(settings.NEON_CYAN, 0.55),
                         (rect.left + 4, top_y), (rect.right - 4, top_y), 2)
        for index in range(9):
            x = rect.centerx - 128 + index * 32
            pygame.draw.line(surface, (40, 48, 88),
                             (x, top_y + 9), (x - 3, rect.bottom - 7), 3)

        # feet, so it is standing rather than sunk into the floor
        for x in (rect.left - spread + 26, rect.right + spread - 26):
            foot = pygame.Rect(0, 0, 34, 9)
            foot.midtop = (x, rect.bottom - 3)
            pygame.draw.rect(surface, (16, 19, 42), foot, border_radius=3)

    def _draw_neon_strips(self, surface):
        """Two breathing light tubes down the sides. Drawn live, not cached,
        because their brightness changes every frame."""
        brightness = ui.pulse(0.5, 0.45, 1.0)
        color = ui.shade(settings.NEON_PINK, brightness)
        top = self.rect.top + SIGN_HEIGHT + 14
        bottom = self.rect.bottom - BASE_HEIGHT - 14
        for x in (self.rect.left + 11, self.rect.right - 11):
            pygame.draw.line(surface, color, (x, top), (x, bottom), 3)

    # =======================================================================
    # BOUNDS  (Phase 4 physics will ask these questions)
    # =======================================================================
    # Dice live in Stage coordinates: x from -1.0 to 1.0, depth 0.0 to 1.0.
    # Keeping them slightly inside those limits stops a die from visually
    # sinking into a wall.

    WALL_X = 0.88          # how far left/right a die may travel
    BACK_DEPTH = 0.10      # nearest the back wall a die may sit
    FRONT_DEPTH = 0.96     # nearest the glass a die may sit

    def ceiling_height(self):
        """How high above the floor a die may fly, in pixels."""
        return self.stage.rect.top - self.opening.top + 40

    def clamp_position(self, x, depth):
        """Push a position back inside the machine. Returns (x, depth)."""
        return (max(-self.WALL_X, min(self.WALL_X, x)),
                max(self.BACK_DEPTH, min(self.FRONT_DEPTH, depth)))
