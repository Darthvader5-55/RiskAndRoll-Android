"""
game/physics.py
---------------
The fake physics that makes a die look like a real object.

This is NOT a physics engine. It is about forty lines of arithmetic chosen to
LOOK right, which is all an arcade game needs.

A Body has three positions and three speeds:

    x        -1.0 = left wall, 1.0 = right wall   (across the machine)
    depth     0.0 = back wall, 1.0 = the glass     (into the machine)
    height    pixels above the floor               (up)

Every frame we do the same four things:

    1. gravity pulls height down
    2. every position moves by its speed
    3. if it hit the floor or a wall, bounce it back
    4. friction slowly steals the speed until it stops

Tuning constants live at the top so you can feel the difference immediately:
raise BOUNCE_DAMPING and the dice bounce like ping-pong balls, lower it and
they land like bricks.
"""

import random

# --------------------------------------------------------------- TUNING ---
GRAVITY = 1800.0        # pixels per second, per second. Bigger = heavier.
BOUNCE_DAMPING = 0.55   # how much upward speed survives a bounce (0-1)
FLOOR_FRICTION = 0.80   # sideways speed kept after touching the floor
WALL_BOUNCE = 0.62      # speed kept after hitting a wall
AIR_DRAG = 0.9985       # very slight slowdown while in the air
GROUND_DRAG = 2.2       # how quickly a die skidding on the floor slows down

# How hard a die is thrown upwards. Raising it does very little: the machine
# has a ceiling only about 230 pixels above the floor, so a harder throw just
# bounces off it. If you want LONGER rolls, change BOUNCE_DAMPING above.
LAUNCH_SPEED = 760.0

# When the movement drops below BOTH of these, the body is declared asleep.
REST_FALL_SPEED = 95.0   # pixels per second of bouncing
REST_SLIDE_SPEED = 0.14  # stage units per second of sliding


class Body:
    """One moving object inside the machine."""

    def __init__(self, x=0.0, depth=0.5, height=0.0):
        self.x = x
        self.depth = depth
        self.height = height

        self.vx = 0.0        # stage units per second
        self.vdepth = 0.0
        self.vheight = 0.0   # pixels per second

        self.bounces = 0
        self.resting = True

    # ------------------------------------------------------------- launch
    def launch(self, x=None, depth=None, height=None,
               speed=1.1, lift=None):
        """Throw the body into the machine with a randomised toss.

        Every die gets slightly different numbers, which is why six dice
        rolled together never look like six copies of the same animation.

        lift is how hard the die is thrown upwards, LAUNCH_SPEED above.
        """
        if lift is None:
            lift = LAUNCH_SPEED
        if x is not None:
            self.x = x
        if depth is not None:
            self.depth = depth
        self.height = height if height is not None else random.uniform(120, 220)

        self.vx = random.uniform(-speed, speed)
        self.vdepth = random.uniform(-speed * 0.55, speed * 0.55)
        self.vheight = lift * random.uniform(0.75, 1.15)

        self.bounces = 0
        self.resting = False

    # ------------------------------------------------------------- update
    def update(self, dt, bounds):
        """Move one frame. Returns a dict saying what it hit this frame.

        bounds is the Tumbler: it knows where the walls and ceiling are.
        """
        events = {"floor": False, "wall": False, "strength": 0.0}
        if self.resting:
            return events

        # ---- 1. gravity ---------------------------------------------------
        self.vheight -= GRAVITY * dt

        # ---- 2. move ------------------------------------------------------
        self.x += self.vx * dt
        self.depth += self.vdepth * dt
        self.height += self.vheight * dt

        self.vx *= AIR_DRAG
        self.vdepth *= AIR_DRAG

        # ---- 3a. side walls, back wall and glass --------------------------
        if self.x < -bounds.WALL_X:
            self.x = -bounds.WALL_X
            self.vx = abs(self.vx) * WALL_BOUNCE
            events["wall"] = True
        elif self.x > bounds.WALL_X:
            self.x = bounds.WALL_X
            self.vx = -abs(self.vx) * WALL_BOUNCE
            events["wall"] = True

        if self.depth < bounds.BACK_DEPTH:
            self.depth = bounds.BACK_DEPTH
            self.vdepth = abs(self.vdepth) * WALL_BOUNCE
            events["wall"] = True
        elif self.depth > bounds.FRONT_DEPTH:
            self.depth = bounds.FRONT_DEPTH
            self.vdepth = -abs(self.vdepth) * WALL_BOUNCE
            events["wall"] = True

        # ---- 3b. the ceiling ----------------------------------------------
        ceiling = bounds.ceiling_height()
        if self.height > ceiling:
            self.height = ceiling
            self.vheight = -abs(self.vheight) * 0.4

        # ---- 3c. the floor: the important one -----------------------------
        if self.height <= 0.0:
            self.height = 0.0
            if self.vheight < 0:
                events["floor"] = True
                # 'strength' is how hard the landing was, 0.0 to 1.0. The die
                # uses it to decide how much to squash and how loud to be.
                events["strength"] = min(1.0, abs(self.vheight) / 700.0)

                self.vheight = -self.vheight * BOUNCE_DAMPING
                self.vx *= FLOOR_FRICTION
                self.vdepth *= FLOOR_FRICTION
                self.bounces += 1

        # ---- 3d. skidding: rub off speed while touching the floor ---------
        # Without this a die can slide almost forever on tiny bounces, and a
        # booth round has to finish in a few seconds.
        if self.height <= 0.0:
            keep = max(0.0, 1.0 - GROUND_DRAG * dt)
            self.vx *= keep
            self.vdepth *= keep

        # ---- 4. fall asleep when the movement is tiny ---------------------
        slide = abs(self.vx) + abs(self.vdepth)
        if (self.height <= 0.0
                and abs(self.vheight) < REST_FALL_SPEED
                and slide < REST_SLIDE_SPEED):
            self.stop()

        return events

    # --------------------------------------------------------------- rest
    def stop(self):
        """Freeze the body exactly on the floor."""
        self.height = 0.0
        self.vx = self.vdepth = self.vheight = 0.0
        self.resting = True

    def energy(self):
        """A rough 0.0-1.0 measure of how lively the body still is.

        The die uses it to fade out its motion trail and slow its spin.
        """
        moving = abs(self.vheight) / 700.0 + (abs(self.vx) + abs(self.vdepth))
        return min(1.0, moving)
