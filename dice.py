"""
game/dice.py
------------
PHASE 2 PART: the ARTWORK of a die.
(Phase 4 adds movement, rotation and bouncing to this same file.)

A real 3D engine would rotate a cube for us. In Pygame we fake it: a cube is
just three four-sided shapes sharing a corner. Paint the top face bright, the
right face medium and the left face dark, and the eye reads a solid object.
"""

import pygame

from config import settings
from ui.ui import shade


# Where the pips sit on a face, in that face's own 0.0-1.0 coordinates.
PIP_LAYOUT = {
    1: [(0.5, 0.5)],
    2: [(0.28, 0.28), (0.72, 0.72)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
    5: [(0.26, 0.26), (0.74, 0.26), (0.5, 0.5), (0.26, 0.74), (0.74, 0.74)],
    6: [(0.28, 0.22), (0.28, 0.5), (0.28, 0.78),
        (0.72, 0.22), (0.72, 0.5), (0.72, 0.78)],
}

# On a real die, opposite faces always add up to 7 (1-6, 2-5, 3-4). So two
# opposite faces can never be visible at the same time. This table gives a
# valid (left, right) pair for every possible top face.
FACE_TRIPLES = {
    1: (2, 3),
    2: (6, 3),
    3: (1, 5),
    4: (1, 2),
    5: (1, 3),
    6: (2, 4),
}

_die_cache = {}


def _draw_face(surface, origin, u_corner, v_corner, color, value, pip_radius):
    """Fill one face of the cube and stamp its pips on it.

    A face is a parallelogram described by a corner and its two neighbours.
    Any point inside is origin + u * u_vector + v * v_vector, which lets the
    flat pip layout above bend onto a slanted face.
    """
    u_vec = (u_corner[0] - origin[0], u_corner[1] - origin[1])
    v_vec = (v_corner[0] - origin[0], v_corner[1] - origin[1])
    far = (origin[0] + u_vec[0] + v_vec[0], origin[1] + u_vec[1] + v_vec[1])

    pygame.draw.polygon(surface, color, [origin, u_corner, far, v_corner])
    pygame.draw.polygon(surface, shade(color, 0.6),
                        [origin, u_corner, far, v_corner], 1)

    for (u, v) in PIP_LAYOUT[value]:
        px = origin[0] + u_vec[0] * u + v_vec[0] * v
        py = origin[1] + u_vec[1] * u + v_vec[1] * v
        pygame.draw.circle(surface, shade(color, 0.35),
                           (int(px + 1), int(py + 1)), pip_radius)
        pygame.draw.circle(surface, (250, 250, 255), (int(px), int(py)), pip_radius)


def make_die_surface(color, size, top_value, left_value=None, right_value=None):
    """A still picture of a die showing `top_value` on top.

    The tumbling dice draw themselves straight onto the screen and never come
    through here. This is for the places that need a picture instead: the
    floating dice on the main menu. Each one is built once and remembered,
    because building them every frame would be wasteful.
    """
    key = (color, int(size), top_value)
    if key not in _die_cache:
        ax, az = cube.VALUE_ORIENTATION[top_value]
        _die_cache[key] = cube.render_to_surface(size, color, ax, 0.0, az)
    return _die_cache[key]


def die_color(color_name):
    """Look up one of the six dice colours by name, e.g. "RED"."""
    return settings.DICE_COLORS[color_name]


# ===========================================================================
# PHASE 4: A DIE THAT MOVES
# ===========================================================================

import random

from game import cube
from game.layers import Layer, draw_shadow
from game.physics import Body

# How the die behaves while it tumbles.
# The die now turns in real 3D (see game/cube.py), so it has a tumbling speed
# around each of the three axes instead of one flat spin.
SPIN_MIN, SPIN_MAX = 260, 780   # degrees per second at launch, per axis
SPIN_BOUNCE_LOSS = 0.58  # tumbling speed kept after each bounce
SPIN_AIR_DRAG = 0.30     # how quickly it slows down in the air, per second
SQUASH_RECOVERY = 6.0    # how fast a squashed die springs back
SETTLE_EASE = 7.0        # how fast it topples into its final face
TRAIL_LENGTH = 2         # ghost images behind a fast die
SETTLE_TIMEOUT = 1.1     # seconds; a safety net so a round always ends


class Die:
    """One die: artwork + physics + the value it will finish on.

    States it moves through:

        IDLE      sitting still, showing its value
        ROLLING   flying and spinning, showing random faces
        SETTLING  slowing down, the real face has been revealed
    """

    IDLE = "IDLE"
    ROLLING = "ROLLING"
    SETTLING = "SETTLING"

    def __init__(self, color_name, tumbler, size=26):
        self.color_name = color_name
        self.color = settings.DICE_COLORS[color_name]
        self.tumbler = tumbler
        self.stage = tumbler.stage
        self.size = size

        self.body = Body(x=0.0, depth=0.5, height=0.0)
        self.state = self.IDLE

        self.value = 1           # the face currently drawn
        self.final_value = 1     # the face it will end on (the real result)

        # The three angles the cube is turned by, and how fast each is
        # changing. Three axes are what make it tumble instead of spin flat.
        self.ax = self.ay = self.az = 0.0
        self.wx = self.wy = self.wz = 0.0
        self.target_ax = self.target_az = 0.0

        self.squash = 0.0        # 0 = normal, 1 = fully flattened
        self.settle_timer = 0.0
        self.visible = True      # False = this die is not in the current game
        self.impact = 0.0        # how hard it hit something this frame
        self.trail = []          # recent positions, for the motion blur

    # ==================================================================== roll
    def roll(self, final_value=None, x=None, depth=None):
        """Throw the die. If you do not pass a value, one is picked now.

        IMPORTANT: the result is decided HERE, at the start, and stored in
        self.final_value. The tumbling faces afterwards are pure decoration.
        That is what guarantees the number on screen always matches the
        number the betting code checks.
        """
        self.final_value = final_value or random.randint(1, 6)

        self.body.launch(
            x=x if x is not None else random.uniform(-0.5, 0.5),
            depth=depth if depth is not None else random.uniform(0.3, 0.7),
        )

        # a random starting attitude and a random tumble on all three axes
        self.ax = random.uniform(0, 360)
        self.ay = random.uniform(0, 360)
        self.az = random.uniform(0, 360)
        self.wx = random.choice((-1, 1)) * random.uniform(SPIN_MIN, SPIN_MAX)
        self.wy = random.choice((-1, 1)) * random.uniform(SPIN_MIN, SPIN_MAX)
        self.wz = random.choice((-1, 1)) * random.uniform(SPIN_MIN, SPIN_MAX) * 0.7

        self.value = cube.top_value(self.ax, self.ay, self.az)
        self.squash = 0.0
        self.trail.clear()
        self.state = self.ROLLING

    def force_settle(self):
        """Used by the round timer if a die is still dawdling."""
        self.body.stop()
        self._snap_to_final()
        self.state = self.IDLE

    def _snap_to_final(self):
        """Put the cube exactly in the attitude that shows its result on top.

        ay is left alone: turning on the spot never changes which face is up,
        so a settled die keeps whatever angle it happened to land at.
        """
        self.ax, self.az = cube.VALUE_ORIENTATION[self.final_value]
        self.wx = self.wy = self.wz = 0.0
        self.value = self.final_value

    # ================================================================== update
    def update(self, dt):
        """Move every die, then report anything that hit something.

        on_impact is set by the screen to Audio.play_clack, so the dice make
        their own noise without knowing that sound exists.
        """
        if self.state == self.IDLE:
            self.squash = max(0.0, self.squash - dt * SQUASH_RECOVERY)
            return

        events = self.body.update(dt, self.tumbler)

        # ---- squash and stretch on landing --------------------------------
        if events["floor"]:
            # remembered for one frame so DiceSet can turn it into a clack.
            # The sound is driven by the real landing, not by a timer, which
            # is why the rattle always matches what you can see.
            self.impact = events["strength"]
            self.squash = min(0.85, events["strength"])
            # A landing knocks the tumble about: it loses speed, and the
            # bounce adds a fresh kick, which is what makes a die look like
            # it CATCHES on a corner rather than spinning smoothly.
            self.wx *= SPIN_BOUNCE_LOSS
            self.wy *= SPIN_BOUNCE_LOSS
            self.wz *= SPIN_BOUNCE_LOSS
            kick = 240 * events["strength"]
            self.wx += random.uniform(-kick, kick)
            self.wz += random.uniform(-kick, kick)
        if events["wall"]:
            self.impact = max(self.impact, 0.35)
            self.wy *= 0.8
            self.wx += random.uniform(-120, 120)
        self.squash = max(0.0, self.squash - dt * SQUASH_RECOVERY)

        energy = self.body.energy()

        if self.state == self.ROLLING:
            # ---- tumble freely on all three axes --------------------------
            self.ax = (self.ax + self.wx * dt) % 360
            self.ay = (self.ay + self.wy * dt) % 360
            self.az = (self.az + self.wz * dt) % 360

            slow = max(0.0, 1.0 - dt * SPIN_AIR_DRAG)
            self.wx *= slow
            self.wy *= slow
            self.wz *= slow

            # No face flickering any more: whichever face the maths turns
            # upwards IS the face you see, exactly like a real die.
            self.value = cube.top_value(self.ax, self.ay, self.az)

            if energy < 0.30 or self.body.bounces >= 4:
                self.state = self.SETTLING
                self.settle_timer = 0.0
                self._pick_settle_target()

        elif self.state == self.SETTLING:
            # ---- topple into the final face -------------------------------
            # Only ax and az are steered, because those two decide which face
            # ends up on top. ay keeps its leftover turn and just slows down,
            # so every die comes to rest at a different angle.
            self.settle_timer += dt
            blend = min(1.0, dt * SETTLE_EASE)

            self.ax = _ease_angle(self.ax, self.target_ax, blend)
            self.az = _ease_angle(self.az, self.target_az, blend)

            self.wy *= max(0.0, 1.0 - dt * 5.0)
            self.ay = (self.ay + self.wy * dt) % 360

            self.value = cube.top_value(self.ax, self.ay, self.az)

            close = (abs(_angle_gap(self.ax, self.target_ax)) < 1.5
                     and abs(_angle_gap(self.az, self.target_az)) < 1.5)
            if (self.body.resting and close) or self.settle_timer > SETTLE_TIMEOUT:
                self.body.stop()
                self._snap_to_final()
                self.state = self.IDLE

        # ---- motion trail -------------------------------------------------
        if energy > 0.55:
            self.trail.append((self.body.x, self.body.depth, self.body.height,
                               self.ax, self.ay, self.az))
            if len(self.trail) > TRAIL_LENGTH:
                self.trail.pop(0)
        elif self.trail:
            self.trail.pop(0)

    def _pick_settle_target(self):
        """Choose the attitude to topple into.

        The die must finish showing final_value. There is more than one way
        to get there (turning right way up, or all the way over), so we take
        whichever is the shorter tip from where the cube is now. That is what
        makes the last turn look like it fell into place instead of snapping.
        """
        base_ax, base_az = cube.VALUE_ORIENTATION[self.final_value]
        best = None
        for turns in (-360, 0, 360):
            candidate_ax = base_ax + turns
            for side in (-360, 0, 360):
                candidate_az = base_az + side
                cost = (abs(_angle_gap(self.ax, candidate_ax))
                        + abs(_angle_gap(self.az, candidate_az)))
                if best is None or cost < best[0]:
                    best = (cost, candidate_ax, candidate_az)
        _cost, self.target_ax, self.target_az = best

    def _reveal(self):
        """Swap the flickering face for the real result."""
        self.value = self.final_value

    # ==================================================================== draw
    def add_to(self, renderer):
        """Queue this die's shadow and body with the depth renderer."""
        if not self.visible:
            return
        _, screen_y, _ = self.stage.project(self.body.x, self.body.depth,
                                            self.body.height)
        renderer.add(Layer.DICE_SHADOW, self.draw_shadow, sort_y=screen_y)
        renderer.add(Layer.DICE, self.draw, sort_y=screen_y)

    def draw_shadow(self, surface):
        draw_shadow(surface, self.stage, self.body.x, self.body.depth,
                    self.body.height, size=self.size,
                    max_height=max(60.0, self.tumbler.ceiling_height()))

    def draw(self, surface):
        """Draw the die by turning a real cube in 3D. See game/cube.py."""
        sx, sy, scale = self.stage.project(self.body.x, self.body.depth,
                                           self.body.height)
        sy -= self._base_offset(scale)
        draw_size = self.size * scale

        # faint ghosts of where it just was, while it is moving fast
        for index, (gx, gdepth, gheight, gax, gay, gaz) in enumerate(self.trail):
            fade = (index + 1) / (len(self.trail) + 2)
            ghost_x, ghost_y, gscale = self.stage.project(gx, gdepth, gheight)
            ghost_y -= self._base_offset(gscale)
            ghost = cube.render_to_surface(self.size * gscale, self.color,
                                           gax, gay, gaz)
            ghost.set_alpha(int(55 * fade))
            surface.blit(ghost, ghost.get_rect(center=(int(ghost_x),
                                                       int(ghost_y))))

        cube.draw_die(surface, (sx, sy), draw_size, self.color,
                      self.ax, self.ay, self.az, squash=self.squash)

    def _base_offset(self, scale):
        """Lift the drawing so the cube's BASE sits on the floor.

        The cube is drawn around its middle, so without this it would look
        half sunk into the floor and would cover its own shadow.
        """
        return 0.62 * self.size * scale

    # ================================================================= helpers
    @property
    def is_finished(self):
        """True once the die has stopped and is showing its real face."""
        return self.state == self.IDLE and self.body.resting


def _angle_gap(current, target):
    """The shortest way round from one angle to another, in degrees.

    Without this an angle of 359 would travel the long way to reach 1.
    """
    gap = (target - current + 180) % 360 - 180
    return gap


def _ease_angle(current, target, blend):
    """Move part of the way towards an angle, going the short way round."""
    return current + _angle_gap(current, target) * blend


# ===========================================================================
# PHASE 5: ALL SIX DICE TOGETHER
# ===========================================================================

# How close two dice may get before they shove each other apart. These are in
# stage units (x and depth) and pixels (height).
MIN_X_GAP = 0.26
MIN_DEPTH_GAP = 0.17
MAX_HEIGHT_GAP = 34.0
PUSH_STRENGTH = 0.55


class DiceSet:
    """The six coloured dice, rolled and read as one group.

    Every mode uses this: Color Royale reads one colour, Consequence Pool
    compares them all, Arcade Duel adds them up in two teams.
    """

    def __init__(self, tumbler, color_names=None, size=26):
        self.tumbler = tumbler
        names = color_names or settings.COLOR_ORDER
        self.dice = [Die(name, tumbler, size) for name in names]
        self.by_color = {die.color_name: die for die in self.dice}
        self.on_impact = None      # the screen plugs Audio.play_clack in here
        self.roll_timer = 0.0
        self._arrange_at_rest()

    def _arrange_at_rest(self):
        """Lay the dice out tidily before the first roll.

        Without this they would all start stacked in the exact centre showing
        a 1, which looks broken on the screen the player sees first.
        """
        for index, die in enumerate(self.dice):
            column, row = index % 3, index // 3
            die.body.x = -0.45 + column * 0.45
            die.body.depth = 0.38 + row * 0.30
            die.body.height = 0.0
            die.value = die.final_value = random.randint(1, 6)

    # ==================================================================== roll
    def roll(self, only_colors=None):
        """Throw the dice. Pass only_colors to reroll a few (sudden death).

        Each die is launched from its own slot along the back of the machine
        and given its own random speed, so the six never move as one blob.
        """
        targets = ([self.by_color[name] for name in only_colors]
                   if only_colors else self.dice)

        count = max(1, len(targets))
        for index, die in enumerate(targets):
            # spread the launch points evenly across the machine
            slot = (index + 0.5) / count          # 0.0 - 1.0
            start_x = -0.62 + slot * 1.24
            die.roll(x=start_x, depth=random.uniform(0.25, 0.55))

        self.roll_timer = 0.0

    def force_settle_all(self):
        """Stop everything immediately and show the real faces."""
        for die in self.dice:
            if die.state != Die.IDLE:
                die.force_settle()

    # ================================================================== update
    def update(self, dt):
        """Move every die, then report anything that hit something.

        on_impact is set by the screen to Audio.play_clack, so the dice can
        make their own noise without this file knowing that sound exists.
        """
        self.roll_timer += dt
        for die in self.dice:
            die.update(dt)
        self._separate()

        if self.on_impact is not None:
            for die in self.dice:
                if die.impact > 0.0 and die.visible:
                    self.on_impact(die.impact)
                die.impact = 0.0
        else:
            for die in self.dice:
                die.impact = 0.0

    def _separate(self):
        """Collision-LIKE behaviour: keep dice from overlapping.

        This is not real collision physics. We simply check every pair, and if
        two dice are sharing the same spot at the same height we push them
        apart and swap a little sideways speed. On screen that reads as a
        bump, which is all an arcade game needs.

        Six dice means only fifteen pairs to check, so this is cheap.
        """
        for index, first in enumerate(self.dice):
            for second in self.dice[index + 1:]:
                a, b = first.body, second.body

                if abs(a.height - b.height) > MAX_HEIGHT_GAP:
                    continue        # one is flying over the other

                dx = b.x - a.x
                dd = b.depth - a.depth
                if abs(dx) >= MIN_X_GAP or abs(dd) >= MIN_DEPTH_GAP:
                    continue        # not touching

                # push along whichever axis they overlap on least
                if abs(dx) / MIN_X_GAP < abs(dd) / MIN_DEPTH_GAP:
                    overlap = MIN_X_GAP - abs(dx)
                    direction = 1.0 if dx >= 0 else -1.0
                    a.x -= overlap * 0.5 * direction
                    b.x += overlap * 0.5 * direction
                    if not (a.resting and b.resting):
                        a.vx, b.vx = (b.vx * PUSH_STRENGTH, a.vx * PUSH_STRENGTH)
                else:
                    overlap = MIN_DEPTH_GAP - abs(dd)
                    direction = 1.0 if dd >= 0 else -1.0
                    a.depth -= overlap * 0.5 * direction
                    b.depth += overlap * 0.5 * direction
                    if not (a.resting and b.resting):
                        a.vdepth, b.vdepth = (b.vdepth * PUSH_STRENGTH,
                                              a.vdepth * PUSH_STRENGTH)

                # A knock sets both dice tumbling harder. Adding it to the
                # x and z axes (not the upright one) makes them look like they
                # caught each other's corners.
                for die in (first, second):
                    die.wx += random.uniform(-160, 160)
                    die.wz += random.uniform(-160, 160)
                    die.impact = max(die.impact, 0.3)
                a.x, a.depth = self.tumbler.clamp_position(a.x, a.depth)
                b.x, b.depth = self.tumbler.clamp_position(b.x, b.depth)

    # ==================================================================== draw
    def add_to(self, renderer):
        for die in self.dice:
            die.add_to(renderer)

    # ================================================================ in play
    def set_in_play(self, color_names):
        """Show only these colours. Arcade Duel uses it when the players
        choose to roll fewer than six dice; pass None to show them all."""
        for die in self.dice:
            die.visible = (color_names is None or die.color_name in color_names)
        self.arrange_in_play()

    def arrange_in_play(self):
        """Lay the dice that ARE in play out neatly across the floor."""
        live = [die for die in self.dice if die.visible]
        if not live:
            return
        for index, die in enumerate(live):
            if len(live) <= 3:
                die.body.x = -0.45 + index * (0.9 / max(1, len(live) - 1)) \
                    if len(live) > 1 else 0.0
                die.body.depth = 0.55
            else:
                column, row = index % 3, index // 3
                die.body.x = -0.45 + column * 0.45
                die.body.depth = 0.38 + row * 0.30
            die.body.height = 0.0

    # ================================================================= reading
    @property
    def all_finished(self):
        """True once every die has stopped and shows its real face."""
        return all(die.is_finished for die in self.dice if die.visible)

    @property
    def is_rolling(self):
        return not self.all_finished

    def results(self):
        """{"RED": 3, "BLUE": 6, ...} — the official result of the round."""
        return {die.color_name: die.final_value for die in self.dice}

    def value_of(self, color_name):
        return self.by_color[color_name].final_value
