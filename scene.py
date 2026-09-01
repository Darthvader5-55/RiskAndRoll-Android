"""
ui/scene.py
-----------
The room the game happens in.

Every mode (Color Royale, Consequence Pool, Arcade Duel) shows the same
arcade room, so it is written once here and reused. The room is split into
two halves:

    draw_back()   floor, walls, lights   -> drawn BEHIND everything
    draw_front()  vignette, scanlines    -> drawn IN FRONT of everything

Anything that never changes is painted once into a stored picture. Only the
moving parts (light sweep, dust, neon pulse) are redrawn each frame, which is
why the game still runs at 60 FPS.
"""

import math
import random

import pygame

from config import settings
from game.layers import Stage
from game import cube
from ui import ui


class ArcadeScene:

    def __init__(self, stage=None, pillars=True, dust_count=26):
        self.stage = stage or Stage(
            pygame.Rect(60, int(settings.SCREEN_HEIGHT * 0.42),
                        settings.SCREEN_WIDTH - 120,
                        int(settings.SCREEN_HEIGHT * 0.58) - 30))
        self.pillars = pillars
        self.time = 0.0

        self.speakers = []          # PA cabinets standing beside the machine
        self._speaker_cache = {}
        self.wall_signs = []        # lit signs on the wall behind the machine
        self.stage_ring = None      # painted circle the machine stands on
        self.drifters = []          # slow 3D dice tumbling in the room
        self.static = self._build_static()
        self.dust = [self._new_speck(anywhere=True) for _ in range(dust_count)]
        self.speck_image = self._make_speck_image()

    # ======================================================== static room ==
    def _build_static(self):
        """Paint the whole room ONCE into a picture we can blit each frame."""
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        layer = pygame.Surface((w, h))
        ui.draw_vertical_gradient(layer, layer.get_rect(),
                                  settings.BG_TOP, settings.BG_BOTTOM)

        horizon = self.stage.row_y(0.0)
        self._draw_back_wall(layer, horizon)
        self._draw_ceiling(layer, horizon)
        self._draw_far_cabinets(layer, horizon)
        if self.pillars:
            self._draw_pillars(layer, horizon)
        self._draw_horizon_glow(layer, horizon)
        self._draw_floor(layer)
        return layer

    def _draw_ceiling(self, surface, horizon):
        """Light bars running away to the vanishing point.

        A floor alone reads as a flat backdrop. Give the room a TOP that
        shrinks towards the same vanishing point as the floor and the eye
        suddenly accepts it as a space you could walk into.
        """
        w = settings.SCREEN_WIDTH
        vanish = (w // 2, int(horizon))
        ceiling = pygame.Surface((w, int(horizon)), pygame.SRCALPHA)

        # the dark ceiling plane
        pygame.draw.polygon(ceiling, (8, 10, 26, 230),
                            [(0, 0), (w, 0), (vanish[0] + 240, vanish[1]),
                             (vanish[0] - 240, vanish[1])])

        # rails going back
        for offset in (-460, -170, 170, 460):
            pygame.draw.line(ceiling, (46, 58, 104, 120),
                             (vanish[0] + offset * 2, 0),
                             (vanish[0] + offset * 0.35, vanish[1]), 2)

        # strip lights, spaced closer together the further away they are
        for index in range(7):
            depth = (index / 7.0) ** 1.7
            y = int(horizon * depth)
            half = int(w * 0.46 * (1 - depth * 0.72))
            glow = int(150 * (1 - depth * 0.75))
            bar = pygame.Rect(vanish[0] - half, y, half * 2, max(2, int(9 - depth * 6)))
            pygame.draw.rect(ceiling, (*settings.NEON_CYAN, glow), bar,
                             border_radius=3)
            halo = pygame.Rect(bar.left, bar.top - 4, bar.width, bar.height + 10)
            pygame.draw.rect(ceiling, (*settings.NEON_CYAN, glow // 5), halo,
                             border_radius=6)

        surface.blit(ceiling, (0, 0))

    def _draw_far_cabinets(self, surface, horizon):
        """A row of other arcade machines along the back wall.

        They are small, dim and low-contrast on purpose. Detail that is far
        away must look WEAKER than detail up close, or the eye reads it as
        being nearby and the depth collapses.
        """
        w = settings.SCREEN_WIDTH
        base = int(horizon)
        row = pygame.Surface((w, 90), pygame.SRCALPHA)

        random_state = 12345
        x = 40
        while x < w - 40:
            random_state = (random_state * 1103515245 + 12345) % 2147483648
            width = 46 + random_state % 34
            height = 48 + (random_state // 7) % 26
            body = pygame.Rect(x, 90 - height, width, height)
            pygame.draw.rect(row, (14, 17, 38, 150), body, border_radius=4)
            pygame.draw.rect(row, (30, 38, 68, 90), body, width=1, border_radius=4)

            # a lit screen on each one
            tint = ((settings.NEON_PINK if random_state % 3 else settings.NEON_CYAN))
            screen = pygame.Rect(body.left + 6, body.top + 7, body.width - 12, 16)
            pygame.draw.rect(row, (*tint, 34), screen, border_radius=2)
            x += width + 12 + random_state % 20

        surface.blit(row, (0, base - 90))

    def _draw_back_wall(self, surface, horizon):
        """A slightly lighter panel above the horizon = the far wall."""
        wall = pygame.Surface((settings.SCREEN_WIDTH, int(horizon)), pygame.SRCALPHA)
        for y in range(int(horizon)):
            t = y / max(1, horizon)
            alpha = int(ui.lerp(0, 46, t))
            pygame.draw.line(wall, (70, 90, 160, alpha), (0, y),
                             (settings.SCREEN_WIDTH, y))
        surface.blit(wall, (0, 0))

    def _draw_pillars(self, surface, horizon):
        """Dark vertical supports at the sides, like a real cabinet."""
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        band = pygame.Surface((w, h), pygame.SRCALPHA)
        for side in (0, 1):
            base_x = 0 if side == 0 else w - 74
            pygame.draw.rect(band, (0, 0, 0, 90), (base_x, 0, 74, h))
            edge_x = 73 if side == 0 else w - 74
            pygame.draw.line(band, (*settings.NEON_CYAN, 55),
                             (edge_x, 40), (edge_x, h - 40), 2)
        surface.blit(band, (0, 0))

    def _draw_horizon_glow(self, surface, horizon):
        """A soft neon strip where the wall meets the floor."""
        w = settings.SCREEN_WIDTH
        glow = pygame.Surface((w, 70), pygame.SRCALPHA)
        for y in range(70):
            alpha = int(34 * (1 - abs(y - 35) / 35))
            pygame.draw.line(glow, (*settings.NEON_CYAN, alpha), (0, y), (w, y))
        surface.blit(glow, (0, int(horizon) - 35))

    def _draw_floor(self, surface):
        """The perspective grid, drawn straight from the Stage maths."""
        stage = self.stage
        floor = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        pygame.draw.polygon(floor, (16, 22, 52, 150), stage.corners())

        # rows running left-to-right, packed tighter towards the back
        for i in range(11):
            depth = i / 10.0
            y = stage.row_y(depth)
            half = stage.half_width(depth)
            alpha = int(ui.lerp(28, 80, depth))
            pygame.draw.line(floor, (60, 110, 180, alpha),
                             (stage.rect.centerx - half, y),
                             (stage.rect.centerx + half, y), 1)

        # lines running away from the player, converging at the back
        for i in range(-4, 5):
            x = i / 4.0
            start = stage.floor_point(x, 0.0)
            end = stage.floor_point(x, 1.0)
            pygame.draw.line(floor, (60, 110, 180, 50), start, end, 1)

        # a pool of light in the middle of the floor
        cx, cy = stage.floor_point(0.0, 0.62)
        pool_w = int(stage.rect.width * 0.62)
        pool = pygame.Surface((pool_w, int(pool_w * 0.32)), pygame.SRCALPHA)
        pygame.draw.ellipse(pool, (*settings.NEON_CYAN, 26), pool.get_rect())
        floor.blit(pygame.transform.smoothscale(pool, pool.get_size()),
                   pool.get_rect(center=(int(cx), int(cy))))

        surface.blit(floor, (0, 0))

    # ============================================================== dust ===
    def _make_speck_image(self):
        speck = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(speck, (*settings.NEON_CYAN, 110), (3, 3), 3)
        return speck

    def _new_speck(self, anywhere=False):
        return {
            "x": random.uniform(0, settings.SCREEN_WIDTH),
            "y": random.uniform(0, settings.SCREEN_HEIGHT) if anywhere
                 else settings.SCREEN_HEIGHT + 10,
            "speed": random.uniform(8, 30),
            "drift": random.uniform(-6, 6),
            "size": random.uniform(0.4, 1.3),
            "alpha": random.randint(30, 90),
        }

    # ============================================================ update ===
    def update(self, dt):
        self.time += dt
        self._update_drifters(dt)
        for speck in self.dust:
            speck["y"] -= speck["speed"] * dt
            speck["x"] += speck["drift"] * dt
            if speck["y"] < -10:
                speck.update(self._new_speck())

    # ============================================================== draw ===
    def set_speakers(self, rects):
        """Stand a PA cabinet in each of these spaces, beside the machine."""
        self.speakers = [pygame.Rect(rect) for rect in rects]

    def add_drifting_dice(self, columns, count=5):
        """Put a few slowly tumbling dice in the room itself.

        They use the same 3D cube maths as the real dice, just small, dim and
        far away. Because they turn rather than spin flat, the background gets
        the same sense of depth the machine has.
        """
        import random
        self.drifters = []
        for index in range(count):
            left, right = columns[index % len(columns)]
            self.drifters.append({
                "x": random.uniform(left, right),
                "y": random.uniform(0, settings.SCREEN_HEIGHT),
                "size": random.uniform(11, 19),
                "alpha": random.randint(45, 90),
                "speed": random.uniform(7, 17),
                "color": settings.DICE_COLORS[random.choice(settings.COLOR_ORDER)],
                "ax": random.uniform(0, 360), "ay": random.uniform(0, 360),
                "az": random.uniform(0, 360),
                "wx": random.uniform(-16, 16), "wy": random.uniform(-19, 19),
                "wz": random.uniform(-13, 13),
                "left": left, "right": right,
            })

    def _update_drifters(self, dt):
        for die in self.drifters:
            die["y"] -= die["speed"] * dt
            die["ax"] = (die["ax"] + die["wx"] * dt) % 360
            die["ay"] = (die["ay"] + die["wy"] * dt) % 360
            die["az"] = (die["az"] + die["wz"] * dt) % 360
            if die["y"] < -40:
                die["y"] = settings.SCREEN_HEIGHT + 40
                import random
                die["x"] = random.uniform(die["left"], die["right"])

    def _draw_drifters(self, surface):
        for die in self.drifters:
            image = cube.render_to_surface(die["size"], die["color"],
                                           die["ax"], die["ay"], die["az"])
            image.set_alpha(die["alpha"])
            surface.blit(image, image.get_rect(center=(int(die["x"]),
                                                       int(die["y"]))))

    def set_wall_signs(self, rects):
        """Hang a lit sign in each of these spaces."""
        self.wall_signs = [pygame.Rect(rect) for rect in rects]

    def set_stage_ring(self, center, width):
        """Paint a ring on the floor for the machine to stand inside."""
        self.stage_ring = (center, width)

    def draw_back(self, surface):
        """Room behind everything else."""
        surface.blit(self.static, (0, 0))
        self._draw_light_sweep(surface)
        self._draw_floor_haze(surface)
        self._draw_stage_ring(surface)
        self._draw_wall_signs(surface)
        self._draw_speakers(surface)
        self._draw_drifters(surface)
        self._draw_dust(surface)

    def _draw_stage_ring(self, surface):
        """A painted ring on the floor, like the marked-out spot a real booth
        machine stands in. It reads as floor because it is squashed into an
        ellipse - a circle would look like it was floating upright."""
        if not self.stage_ring:
            return
        center, width = self.stage_ring
        height = int(width * 0.30)
        pulse = ui.pulse(0.22, 0.45, 1.0)

        for index, (inset, alpha) in enumerate(((0, 70), (22, 40), (46, 22))):
            box = pygame.Rect(0, 0, width - inset * 2, height - int(inset * 0.3))
            box.center = center
            if box.width < 20 or box.height < 6:
                continue
            ring = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.ellipse(ring, (*settings.NEON_CYAN,
                                       int(alpha * (pulse if index == 0 else 1))),
                                ring.get_rect(), 2)
            surface.blit(ring, box.topleft)

    def _draw_wall_signs(self, surface):
        """Small lit signs on the wall either side of the machine.

        Real arcades are covered in signage. Two of them fill the empty wall
        above the speakers, and because they blink on a slow offset they give
        the room something moving that is not the game itself.
        """
        for index, rect in enumerate(self.wall_signs):
            glow = ui.pulse(0.3 + index * 0.11, 0.35, 1.0)
            tint = settings.NEON_PINK if index % 2 else settings.NEON_CYAN

            pygame.draw.rect(surface, (13, 16, 38), rect, border_radius=8)
            pygame.draw.rect(surface, ui.shade(tint, glow), rect, width=2,
                             border_radius=8)

            # a column of dice pips down the sign, lighting one at a time
            slots = max(1, (rect.height - 20) // 26)
            lit = int(self.time * 2.2) % slots
            for slot in range(slots):
                y = rect.top + 16 + slot * 26
                on = (slot == lit)
                radius = 6 if on else 4
                color = (ui.shade(tint, 1.0) if on
                         else (34, 40, 74))
                pygame.draw.circle(surface, color, (rect.centerx, y), radius)
                if on:
                    halo = pygame.Surface((26, 26), pygame.SRCALPHA)
                    pygame.draw.circle(halo, (*tint, 60), (13, 13), 12)
                    surface.blit(halo, (rect.centerx - 13, y - 13))

    def _draw_speakers(self, surface):
        """Speaker stacks either side of the machine, cones pumping.

        Booths have PA speakers, and putting real objects in the space beside
        the cabinet does more for the sense of a room than any amount of extra
        detail on the walls. The cone pulses on a slow beat so the room feels
        like it has sound in it.
        """
        beat = (math.sin(self.time * 3.1) + 1) / 2          # 0 .. 1
        thump = beat ** 3                                    # sharper attack

        for rect in self.speakers:
            # a soft shadow pooled under the cabinet, so it stands on the
            # floor instead of hovering over it
            shadow = ui.get_soft_shadow(rect.width + 26, 20)
            surface.blit(shadow, shadow.get_rect(center=(rect.centerx,
                                                          rect.bottom + 2)))

            # The cabinet never changes, so it is painted once into a picture
            # and reused. Only the cone and the lamp are drawn live. Before
            # this, the grille alone was several hundred little circles every
            # single frame.
            surface.blit(self._speaker_cabinet(rect.size), rect.topleft)

            woofer = (rect.centerx, rect.bottom - rect.width)
            radius = int(rect.width * 0.36)
            inner = max(3, int(radius * (0.42 + 0.22 * thump)))
            pygame.draw.circle(surface, (30, 36, 70), woofer, inner)
            pygame.draw.circle(surface, ui.shade(settings.NEON_CYAN, 0.35 + 0.5 * thump),
                               woofer, inner, 1)

            pygame.draw.circle(surface, ui.shade(settings.NEON_PINK, 0.5 + 0.5 * beat),
                               (rect.centerx, rect.top + 8), 2)

    def _speaker_cabinet(self, size):
        """The unchanging parts of a speaker: box, grille, tweeter, cone rim."""
        if size in self._speaker_cache:
            return self._speaker_cache[size]

        width, height = size
        image = pygame.Surface(size, pygame.SRCALPHA)
        body = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(image, (17, 20, 44), body, border_radius=6)
        pygame.draw.rect(image, (44, 54, 96), body, width=2, border_radius=6)
        pygame.draw.line(image, (70, 84, 140), (3, 6), (3, height - 6), 1)

        for y in range(12, height - 12, 7):
            for x in range(8, width - 6, 7):
                pygame.draw.circle(image, (26, 31, 60), (x, y), 1)

        radius = int(width * 0.36)
        woofer = (width // 2, height - width)
        pygame.draw.circle(image, (10, 12, 28), woofer, radius)
        pygame.draw.circle(image, (52, 62, 104), woofer, radius, 2)

        tweeter = (width // 2, int(width * 0.75))
        pygame.draw.circle(image, (10, 12, 28), tweeter, max(3, radius // 2))
        pygame.draw.circle(image, (48, 58, 98), tweeter, max(3, radius // 2), 1)

        self._speaker_cache[size] = image
        return image

    def draw_reflection(self, surface, source_rect):
        """Mirror whatever is in source_rect onto the floor below it.

        This is the single strongest depth trick available in a 2D engine: a
        reflection proves to the eye that the floor is a real surface lying
        underneath a real object. It is done by copying the pixels that are
        already on the screen, flipping them, squashing them, and fading them
        out - so it costs one copy, not a second render.
        """
        source_rect = pygame.Rect(source_rect).clip(surface.get_rect())
        if source_rect.height < 8:
            return

        mirror = surface.subsurface(source_rect).copy()
        mirror = pygame.transform.flip(mirror, False, True)
        squashed_height = max(8, int(source_rect.height * 0.16))
        mirror = pygame.transform.smoothscale(
            mirror, (source_rect.width, squashed_height))

        # fade it out towards the bottom, so it dissolves into the floor
        fade = pygame.Surface((source_rect.width, squashed_height), pygame.SRCALPHA)
        for y in range(squashed_height):
            strength = 1.0 - y / squashed_height
            fade.fill((255, 255, 255, int(72 * strength ** 1.7)),
                      pygame.Rect(0, y, source_rect.width, 1))
        mirror.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        surface.blit(mirror, (source_rect.left, source_rect.bottom))

    def _draw_floor_haze(self, surface):
        """A soft band of light where the floor meets the back wall."""
        horizon = int(self.stage.row_y(0.0))
        haze = ui.get_haze_image(settings.SCREEN_WIDTH, 120)
        surface.blit(haze, (0, horizon - 60), special_flags=pygame.BLEND_RGB_ADD)

    def draw_front(self, surface):
        """Screen effects on top of everything else."""
        ui.draw_screen_effects(surface)

    def _draw_light_sweep(self, surface):
        """A wide soft highlight sliding slowly across the back wall."""
        w = settings.SCREEN_WIDTH
        x = (self.time * 60) % (w + 500) - 250
        sweep = ui.get_sweep_image(300, int(self.stage.row_y(0.0)))
        surface.blit(sweep, (int(x), 0), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_dust(self, surface):
        for speck in self.dust:
            size = max(2, int(6 * speck["size"]))
            image = pygame.transform.smoothscale(self.speck_image, (size, size))
            image.set_alpha(speck["alpha"])
            surface.blit(image, (int(speck["x"]), int(speck["y"])))
