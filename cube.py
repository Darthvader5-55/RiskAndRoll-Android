"""
game/cube.py
------------
A real 3D die, drawn with nothing but Pygame polygons.

Pygame cannot draw 3D. So we do the three steps a 3D engine does, by hand:

    1. ROTATE     spin the cube's 8 corners in 3D space using rotation maths
    2. PROJECT    flatten those 3D corners onto the flat screen
    3. SORT       draw only the faces pointing at us, back ones first

That is genuinely all a basic 3D renderer is. Because we do it every frame
with the die's current angles, the cube TUMBLES: you see faces turn away and
new ones come into view, instead of a flat picture being spun around.

WHY THE OLD VERSION LOOKED WRONG
    Before, a die was one picture rotated with pygame.transform.rotate. That
    turns the image on the screen, like spinning a sticker. A real die turns
    in space. Same colours, same pips, completely different feel.

THE THREE ANGLES
    ax  tip forwards / backwards
    ay  spin on the spot (like a turntable)
    az  tip left / right

They are applied in the order ax, then az, then ay. That order matters: ay is
applied LAST, around the upright axis, so spinning it never changes which
face is on top. That is what lets a settled die keep a random turn while
still showing the correct number.
"""

import math

import pygame

# ===========================================================================
# THE CUBE
# ===========================================================================
# Eight corners of a cube, each 1 unit from the middle.
VERTICES = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),   # back face  (z = -1)
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),       # front face (z = +1)
]

# Each face lists its four corners, going anticlockwise seen from outside,
# plus the number printed on it and the direction it points (its "normal").
#
# Opposite faces of a real die always add up to 7, and this table follows
# that: 1 opposite 6, 2 opposite 5, 3 opposite 4.
FACES = [
    # (corner indices, value, normal direction)
    ((3, 2, 6, 7), 1, (0, 1, 0)),     # top       +Y
    ((0, 4, 5, 1), 6, (0, -1, 0)),    # bottom    -Y
    ((4, 7, 6, 5), 2, (0, 0, 1)),     # front     +Z
    ((1, 5, 6, 2), 3, (1, 0, 0)),     # right     +X
    ((0, 3, 7, 4), 4, (-1, 0, 0)),    # left      -X
    ((1, 2, 3, 0), 5, (0, 0, -1)),    # back      -Z
]

# To finish showing a chosen number face-up we need to know how to tip the
# cube. (ax, az) for each value; ay stays free so a settled die can still sit
# at any turn on the table.
VALUE_ORIENTATION = {
    1: (0.0, 0.0),
    6: (180.0, 0.0),
    2: (-90.0, 0.0),
    5: (90.0, 0.0),
    3: (0.0, 90.0),
    4: (0.0, -90.0),
}

# Where the pips sit on a face, in that face's own 0..1 coordinates.
PIP_LAYOUT = {
    1: [(0.5, 0.5)],
    2: [(0.27, 0.27), (0.73, 0.73)],
    3: [(0.24, 0.24), (0.5, 0.5), (0.76, 0.76)],
    4: [(0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)],
    5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
    6: [(0.27, 0.21), (0.27, 0.5), (0.27, 0.79),
        (0.73, 0.21), (0.73, 0.5), (0.73, 0.79)],
}

# ===========================================================================
# THE CAMERA AND THE LIGHT
# ===========================================================================
# The camera looks down at the dice from above and slightly to one side. These
# two angles are what give the whole game its "arcade cabinet" viewpoint, and
# they are why a resting die still shows three faces like the old artwork did.
CAMERA_YAW = 32.0
CAMERA_PITCH = 26.0

# The light comes from above, in front, and slightly right - the same
# direction the dice shadows fall away from.
LIGHT = (0.45, 0.82, 0.36)

AMBIENT = 0.42          # how lit a face is even when facing away from the light
DIFFUSE = 0.72          # how much extra a face gets for facing the light

PIP_COLOR = (252, 252, 255)
PIP_RADIUS = 0.104      # pip size as a fraction of the face, so every face
                        # gets the same size dot no matter how it is turned
BEVEL = 0.10            # how far the lit inner panel is inset from the edge

# A ring of points making a circle, in the face's own flat coordinates. Bending
# THIS through the face's corners is what makes a pip squash correctly when the
# face is turned away, instead of staying a flat circle stuck on top of it.
_PIP_RING = [(math.cos(step * math.tau / 14), math.sin(step * math.tau / 14))
             for step in range(14)]

# Try to use the smooth-edged drawing functions. They are part of Pygame but
# marked experimental, so if anything goes wrong we fall back to the plain
# ones rather than let the game crash.
try:
    from pygame import gfxdraw
    _HAS_GFX = True
except ImportError:
    _HAS_GFX = False


# ===========================================================================
# MATHS HELPERS
# ===========================================================================

def _rotate_x(point, sin_a, cos_a):
    x, y, z = point
    return (x, y * cos_a - z * sin_a, y * sin_a + z * cos_a)


def _rotate_y(point, sin_a, cos_a):
    x, y, z = point
    return (x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a)


def _rotate_z(point, sin_a, cos_a):
    x, y, z = point
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a, z)


def _orient(point, ax, ay, az):
    """Turn one 3D point by the die's three angles, in order ax, az, ay."""
    point = _rotate_x(point, math.sin(ax), math.cos(ax))
    point = _rotate_z(point, math.sin(az), math.cos(az))
    point = _rotate_y(point, math.sin(ay), math.cos(ay))
    return point


_CAM_YAW_RAD = math.radians(CAMERA_YAW)
_CAM_PITCH_RAD = math.radians(CAMERA_PITCH)
_CAM_SIN_Y, _CAM_COS_Y = math.sin(_CAM_YAW_RAD), math.cos(_CAM_YAW_RAD)
_CAM_SIN_P, _CAM_COS_P = math.sin(_CAM_PITCH_RAD), math.cos(_CAM_PITCH_RAD)


def _to_camera(point):
    """Turn a point from world space into the camera's view."""
    point = _rotate_y(point, _CAM_SIN_Y, _CAM_COS_Y)
    return _rotate_x(point, _CAM_SIN_P, _CAM_COS_P)


def _shade(color, level):
    return (max(0, min(255, int(color[0] * level))),
            max(0, min(255, int(color[1] * level))),
            max(0, min(255, int(color[2] * level))))


# ===========================================================================
# BUILDING ONE FRAME OF THE CUBE
# ===========================================================================

def build_faces(size, ax, ay, az):
    """Work out which faces are visible and where their corners land.

    Returns a list, furthest away first, of:
        (screen corners, value, brightness, depth)

    Everything is measured from the middle of the die, so the caller just
    adds its screen position.
    """
    ax, ay, az = math.radians(ax), math.radians(ay), math.radians(az)

    # 1. rotate every corner, then move it into the camera's view
    corners = []
    for vertex in VERTICES:
        turned = _orient(vertex, ax, ay, az)
        corners.append(_to_camera(turned))

    visible = []
    for indices, value, normal in FACES:
        # 2. rotate the face's own direction the same way
        facing = _to_camera(_orient(normal, ax, ay, az))

        # 3. if it points away from the camera, skip it. This one line is
        #    what stops us drawing the inside of the cube, and it is the
        #    reason the die looks solid.
        if facing[2] <= 0.02:
            continue

        points = [corners[index] for index in indices]
        depth = sum(point[2] for point in points) / 4.0

        # 4. how lit is this face? Faces turned towards the light are brighter.
        towards_light = sum(a * b for a, b in zip(facing, LIGHT))
        brightness = AMBIENT + DIFFUSE * max(0.0, towards_light)

        # 5. flatten 3D to 2D. Screen y grows downwards, so it is negated.
        screen = [(point[0] * size, -point[1] * size) for point in points]
        visible.append((screen, value, brightness, depth))

    # furthest first, so nearer faces are painted over them
    visible.sort(key=lambda face: face[3])
    return visible


def top_value(ax, ay, az):
    """Which number is face-up right now. Used to check the maths is right."""
    ax, ay, az = math.radians(ax), math.radians(ay), math.radians(az)
    best_value, best_up = None, -2.0
    for _indices, value, normal in FACES:
        up = _orient(normal, ax, ay, az)[1]
        if up > best_up:
            best_value, best_up = value, up
    return best_value


# ===========================================================================
# DRAWING
# ===========================================================================

def _polygon(surface, points, color, outline=None, antialias=True):
    if antialias and _HAS_GFX:
        try:
            gfxdraw.filled_polygon(surface, points, color)
            gfxdraw.aapolygon(surface, points, outline or color)
            return
        except (ValueError, OverflowError):
            pass
    pygame.draw.polygon(surface, color, points)
    if outline:
        pygame.draw.polygon(surface, outline, points, 1)


def _circle(surface, center, radius, color, antialias=True):
    x, y = int(center[0]), int(center[1])
    radius = int(radius)
    if radius < 1:
        return
    if antialias and _HAS_GFX:
        try:
            gfxdraw.filled_circle(surface, x, y, radius, color)
            gfxdraw.aacircle(surface, x, y, radius, color)
            return
        except (ValueError, OverflowError):
            pass
    pygame.draw.circle(surface, color, (x, y), radius)


def draw_die(surface, center, size, color, ax, ay, az, squash=0.0,
             antialias=True):
    """Draw one tumbling die straight onto a surface.

    Nothing is cached and no temporary picture is made: the polygons go
    directly onto the screen, which is what keeps six spinning dice cheap.

    antialias smooths the edges. Turn it OFF when drawing onto a see-through
    picture rather than the screen: smoothing works by blending with whatever
    is underneath, and on a transparent surface there is nothing to blend
    with, so the edges come out ringed with dark fringes instead of smooth.
    """
    cx, cy = center
    stretch = 1.0 + squash * 0.30      # squash makes it wider and shorter
    flatten = 1.0 - squash * 0.32

    for screen_points, value, brightness, _depth in build_faces(size, ax, ay, az):
        points = [(cx + px * stretch, cy + py * flatten)
                  for px, py in screen_points]

        # Real dice have rounded, slightly darker edges. Drawing a darker
        # outer face and then a brighter panel inset inside it fakes that
        # rounding, and stops the cube looking like flat cut card.
        rim_color = _shade(color, brightness * 0.62)
        face_color = _shade(color, brightness)
        _polygon(surface, points, rim_color, _shade(color, brightness * 0.45),
                 antialias)

        panel = _inset(points, BEVEL)
        _polygon(surface, panel, face_color, None, antialias)

        _draw_pips(surface, panel, value, size, antialias, brightness, color)


def _draw_pips(surface, points, value, size, antialias=True, brightness=1.0,
               base_color=(255, 255, 255)):
    """Put the dots on one face.

    The important part is that a pip is NOT drawn as a circle. The face is a
    square in 3D, so on screen it is a squashed parallelogram, and a circle
    painted on it should squash the same way. So each pip is a ring of points
    in the face's own coordinates, bent through the same two edges as
    everything else on that face. Turn the die and the pips stretch and
    flatten with it, exactly like dots printed on real plastic.
    """
    p0, p1, p2, p3 = points
    edge_u = (p1[0] - p0[0], p1[1] - p0[1])
    edge_v = (p3[0] - p0[0], p3[1] - p0[1])

    # skip the work entirely when the face is too small or too edge-on to see
    if min(math.hypot(*edge_u), math.hypot(*edge_v)) < 11:
        return

    # A pip is a shallow dip in the plastic, so it is lit slightly less than
    # the face around it and has a dark edge on one side.
    # Pips keep most of their brightness even on a face turned away from the
    # light. Physically they would go as dark as the face, but then they read
    # as dirty grey rather than as white dots, and the number gets hard to
    # count from across a booth - which is the whole point of them.
    pip_level = 0.62 + 0.38 * brightness
    pip_color = _shade(PIP_COLOR, pip_level)
    hollow = _shade(base_color, brightness * 0.38)

    for u, v in PIP_LAYOUT[value]:
        ring = []
        shadow = []
        for cos_a, sin_a in _PIP_RING:
            ru = u + cos_a * PIP_RADIUS
            rv = v + sin_a * PIP_RADIUS
            ring.append((p0[0] + edge_u[0] * ru + edge_v[0] * rv,
                         p0[1] + edge_u[1] * ru + edge_v[1] * rv))
            # the same ring, nudged a little, to sit behind as the dip's rim
            su = ru - PIP_RADIUS * 0.20
            sv = rv - PIP_RADIUS * 0.20
            shadow.append((p0[0] + edge_u[0] * su + edge_v[0] * sv,
                           p0[1] + edge_u[1] * su + edge_v[1] * sv))

        _polygon(surface, shadow, hollow, None, antialias)
        _polygon(surface, ring, pip_color, None, antialias)


def _inset(points, amount):
    """Pull a face's corners in towards its middle."""
    cx = sum(point[0] for point in points) / 4.0
    cy = sum(point[1] for point in points) / 4.0
    return [(x + (cx - x) * amount, y + (cy - y) * amount) for x, y in points]


def render_to_surface(size, color, ax, ay, az, padding=4):
    """Draw a die onto its own small picture instead of the screen.

    Used where a picture is needed rather than direct drawing: the menu's
    floating dice, and the faded ghosts behind a fast-moving die.
    """
    extent = int(size * 1.75) + padding
    surface = pygame.Surface((extent * 2, extent * 2), pygame.SRCALPHA)
    draw_die(surface, (extent, extent), size, color, ax, ay, az,
             antialias=False)
    return surface
