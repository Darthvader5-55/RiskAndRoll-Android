"""
ui/ui.py
--------
Shared building blocks used by every screen: fonts, text, gradients,
neon panels and the Button class.

Nothing in this file knows about dice or betting. It only knows how to
draw pretty rectangles and text, so every other UI file can reuse it.
"""

import math
import pygame

from config import settings

# ===========================================================================
# SMALL MATH HELPERS
# ===========================================================================

def clamp(value, low, high):
    """Keep a number inside a range."""
    return max(low, min(high, value))


def lerp(a, b, t):
    """Blend smoothly from a to b. t = 0.0 gives a, t = 1.0 gives b."""
    return a + (b - a) * t


def shade(color, factor):
    """Make a colour lighter (factor > 1) or darker (factor < 1)."""
    return (
        int(clamp(color[0] * factor, 0, 255)),
        int(clamp(color[1] * factor, 0, 255)),
        int(clamp(color[2] * factor, 0, 255)),
    )


def pulse(speed=1.0, low=0.0, high=1.0):
    """A value that gently bounces between low and high forever.

    Handy for glowing / breathing effects. It uses the clock time, so any
    object calling it will stay in sync with the rest of the game.
    """
    t = (math.sin(pygame.time.get_ticks() / 1000.0 * speed * math.pi * 2) + 1) / 2
    return lerp(low, high, t)


# ===========================================================================
# FONTS
# ===========================================================================

_font_cache = {}


def get_font(size, bold=False):
    """Load a font once and remember it (loading fonts every frame is slow)."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    font = None
    if settings.FONT_FILE:
        import os
        path = os.path.join(settings.FONT_DIR, settings.FONT_FILE)
        if os.path.exists(path):
            font = pygame.font.Font(path, size)

    if font is None:
        # Try a few nice system fonts, then fall back to pygame's default.
        name = pygame.font.match_font(",".join(settings.FALLBACK_FONTS), bold=bold)
        font = pygame.font.Font(name, size) if name else pygame.font.Font(None, size)
        font.set_bold(bold)

    _font_cache[key] = font
    return font


_text_cache = {}


def render_text(text, size=24, color=settings.TEXT_BRIGHT, bold=False):
    """Render text once and reuse the picture next frame (much faster)."""
    key = (text, size, color, bold)
    if key not in _text_cache:
        if len(_text_cache) > 400:      # keep the cache from growing forever
            _text_cache.clear()
        _text_cache[key] = get_font(size, bold).render(text, True, color)
    return _text_cache[key]


def draw_text(surface, text, pos, size=24, color=settings.TEXT_BRIGHT,
              bold=False, align="topleft", shadow=True):
    """Draw text and return its rect.

    align can be "topleft", "center", "midtop", "midbottom", "topright", ...
    (any attribute name a pygame Rect understands).
    """
    image = render_text(text, size, color, bold)
    rect = image.get_rect()
    setattr(rect, align, pos)

    if shadow:
        dark = render_text(text, size, (0, 0, 0), bold)
        dark.set_alpha(140)
        surface.blit(dark, (rect.x + 2, rect.y + 2))

    surface.blit(image, rect)
    return rect


_glow_cache = {}


def make_glow_text(text, size=24, color=settings.NEON_CYAN, bold=True, glow=8):
    """Build (once) a text image with a soft neon halo baked into it.

    Building this every frame would be slow, so the finished picture is kept
    in a dictionary and reused. This is called 'caching'.
    """
    key = (text, size, color, bold, glow)
    if key in _glow_cache:
        return _glow_cache[key]

    font = get_font(size, bold)
    image = font.render(text, True, color)

    canvas = pygame.Surface((image.get_width() + glow * 2,
                             image.get_height() + glow * 2), pygame.SRCALPHA)
    halo = image.copy()
    halo.set_alpha(38)
    for offset in range(glow, 0, -2):
        canvas.blit(halo, (glow - offset, glow))
        canvas.blit(halo, (glow + offset, glow))
        canvas.blit(halo, (glow, glow - offset))
        canvas.blit(halo, (glow, glow + offset))
    canvas.blit(image, (glow, glow))

    _glow_cache[key] = canvas
    return canvas


def draw_glow_text(surface, text, pos, size=24, color=settings.NEON_CYAN,
                   bold=True, align="center", glow=8):
    """Draw neon-halo text. Used for titles."""
    image = make_glow_text(text, size, color, bold, glow)
    rect = image.get_rect()
    setattr(rect, align, pos)
    surface.blit(image, rect)
    return rect


# ===========================================================================
# BACKGROUNDS AND PANELS
# ===========================================================================

def draw_vertical_gradient(surface, rect, top_color, bottom_color):
    """Fill a rect with a smooth top-to-bottom colour fade."""
    rect = pygame.Rect(rect)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        color = (
            int(lerp(top_color[0], bottom_color[0], t)),
            int(lerp(top_color[1], bottom_color[1], t)),
            int(lerp(top_color[2], bottom_color[2], t)),
        )
        pygame.draw.line(surface, color, (rect.left, rect.top + y),
                         (rect.right, rect.top + y))


_background_cache = {}


def draw_background(surface, top_color=settings.BG_TOP, bottom_color=settings.BG_BOTTOM):
    """Fill the whole screen with the cabinet gradient (built only once)."""
    key = (surface.get_size(), top_color, bottom_color)
    if key not in _background_cache:
        layer = pygame.Surface(surface.get_size())
        draw_vertical_gradient(layer, layer.get_rect(), top_color, bottom_color)
        _background_cache[key] = layer
    surface.blit(_background_cache[key], (0, 0))


_vignette_cache = {}


def _vignette_layer(w, h, strength=110):
    """The darkening picture on its own, built once per size."""
    key = (w, h, strength)

    if key not in _vignette_cache:
        # Trick: draw the darkening on a tiny 40x24 surface (fast), then blow
        # it up with smoothscale. Stretching blurs it into a perfect fade.
        small_w, small_h = 40, 24
        small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        for y in range(small_h):
            ny = (y / (small_h - 1)) * 2 - 1
            for x in range(small_w):
                nx = (x / (small_w - 1)) * 2 - 1
                distance = min(1.0, math.sqrt(nx * nx + ny * ny) / math.sqrt(2))
                small.set_at((x, y), (0, 0, 0, int(strength * distance ** 2.2)))
        _vignette_cache[key] = pygame.transform.smoothscale(small, (w, h))
    return _vignette_cache[key]


def draw_vignette(surface, strength=110):
    """Darken the screen edges so the middle feels lit, like a real cabinet."""
    w, h = surface.get_size()
    surface.blit(_vignette_layer(w, h, strength), (0, 0))


_panel_cache = {}


def _make_panel_body(size, fill, radius):
    """The rounded metal plate itself, built once per size/colour/radius."""
    key = ("body", size, fill, radius)
    if key in _panel_cache:
        return _panel_cache[key]

    body = pygame.Surface(size, pygame.SRCALPHA)
    draw_vertical_gradient(body, body.get_rect(), shade(fill, 1.35), shade(fill, 0.75))

    # Round off the corners by masking the gradient with a rounded rect.
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    _panel_cache[key] = body
    return body


def _make_panel_glow(size, color, radius):
    key = ("glow", size, color, radius)
    if key not in _panel_cache:
        glow = pygame.Surface((size[0] + 24, size[1] + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color, 45), glow.get_rect(), border_radius=radius + 10)
        _panel_cache[key] = glow
    return _panel_cache[key]


def draw_panel(surface, rect, fill=settings.PANEL_FILL, edge=settings.PANEL_EDGE,
               radius=16, glow_color=None, screws=False):
    """A metallic-looking rounded panel with a light top edge.

    screws=True adds four little bolts in the corners, which makes a big panel
    read as a bolted-on metal plate rather than a floating rectangle.
    """
    rect = pygame.Rect(rect)

    if glow_color:
        surface.blit(_make_panel_glow(rect.size, glow_color, radius),
                     (rect.x - 12, rect.y - 12))

    surface.blit(_make_panel_body(rect.size, fill, radius), rect.topleft)

    if screws:
        for x, y in ((rect.left + 13, rect.top + 13),
                     (rect.right - 13, rect.top + 13),
                     (rect.left + 13, rect.bottom - 13),
                     (rect.right - 13, rect.bottom - 13)):
            pygame.draw.circle(surface, (74, 84, 128), (x, y), 4)
            pygame.draw.circle(surface, (26, 30, 58), (x, y), 4, 1)
            pygame.draw.line(surface, (26, 30, 58), (x - 2, y), (x + 2, y), 1)
    pygame.draw.rect(surface, edge, rect, width=2, border_radius=radius)
    # thin highlight along the top = metal sheen
    pygame.draw.line(surface, shade(edge, 1.6),
                     (rect.left + radius, rect.top + 2),
                     (rect.right - radius, rect.top + 2), 2)


# ===========================================================================
# GLASS, SCANLINES, LIGHT SWEEP
# These are the "polish" layers. The tumbler in Phase 3 reuses all of them.
# ===========================================================================

_glass_cache = {}


def make_glass(size, radius=18, tint=(150, 210, 255), strength=26):
    """A transparent window pane with a diagonal shine across it.

    Real glass is not just "see-through". What makes the eye believe glass is
    the reflection sliding over it, so we bake one in.
    """
    key = (size, radius, tint, strength)
    if key in _glass_cache:
        return _glass_cache[key]

    w, h = size
    glass = pygame.Surface(size, pygame.SRCALPHA)
    glass.fill((*tint, max(0, strength // 3)))

    # Two diagonal shine bands. They are drawn on a quarter-size surface and
    # then blown back up, which blurs their edges for free.
    small_w, small_h = max(8, w // 4), max(8, h // 4)
    shine = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    for start, width, alpha in ((0.16, 0.10, strength + 14),
                                (0.34, 0.05, strength // 2)):
        left = start * small_w
        band = width * small_w
        slant = small_h * 0.35
        pygame.draw.polygon(shine, (255, 255, 255, alpha), [
            (left, small_h),
            (left + band, small_h),
            (left + band + slant, 0),
            (left + slant, 0),
        ])
    glass.blit(pygame.transform.smoothscale(shine, size), (0, 0))

    # bright line along the very top = the edge of the pane catching light
    pygame.draw.line(glass, (255, 255, 255, strength + 30),
                     (radius, 2), (w - radius, 2), 2)

    # keep it inside the rounded shape
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    glass.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    _glass_cache[key] = glass
    return glass


def draw_glass(surface, rect, radius=18):
    rect = pygame.Rect(rect)
    surface.blit(make_glass(rect.size, radius), rect.topleft)


_sweep_cache = {}


def get_sweep_image(width, height, tint=(30, 50, 90)):
    """A soft vertical light band used for moving highlights.

    IMPORTANT: this image is blitted with BLEND_RGB_ADD, which ignores the
    alpha channel completely. So the fade has to be baked into the COLOUR
    (dark at the edges, bright in the middle), not into transparency.
    """
    key = (width, height, tint)
    if key not in _sweep_cache:
        sweep = pygame.Surface((max(1, width), max(1, height)))
        for x in range(width):
            fade = (1 - abs(x - width / 2) / (width / 2)) ** 2
            color = (int(tint[0] * fade), int(tint[1] * fade), int(tint[2] * fade))
            pygame.draw.line(sweep, color, (x, 0), (x, height))
        _sweep_cache[key] = sweep
    return _sweep_cache[key]


_scanline_cache = {}


def draw_scanlines(surface, spacing=3, alpha=16):
    """Faint dark stripes, like looking at an old arcade monitor."""
    key = (surface.get_size(), spacing, alpha)
    if key not in _scanline_cache:
        w, h = surface.get_size()
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, spacing):
            pygame.draw.line(layer, (0, 0, 0, alpha), (0, y), (w, y))
        _scanline_cache[key] = layer
    surface.blit(_scanline_cache[key], (0, 0))


# ===========================================================================
# READY-MADE UI PIECES
# ===========================================================================

def draw_header(surface, title, accent=settings.NEON_CYAN, subtitle=None):
    """The title strip every mode screen shows along the top."""
    w = settings.SCREEN_WIDTH
    bar = pygame.Rect(0, 0, w, 76)

    strip = pygame.Surface(bar.size, pygame.SRCALPHA)
    draw_vertical_gradient(strip, strip.get_rect(), (14, 18, 40), (14, 18, 40))
    strip.set_alpha(220)
    surface.blit(strip, (0, 0))
    pygame.draw.line(surface, accent, (0, bar.bottom), (w, bar.bottom), 2)

    _draw_header_pattern(surface, bar, accent)

    draw_glow_text(surface, title, (w // 2, 38), size=40, color=accent,
                   align="center", glow=6)
    if subtitle:
        draw_text(surface, subtitle, (24, 38), size=18,
                  color=settings.TEXT_DIM, align="midleft")


def _draw_header_pattern(surface, bar, accent):
    """A faint dice-pip pattern in the empty ends of the title strip.

    The middle is taken by the title, so the pattern only fills the corners.
    It is cached because it never changes.
    """
    key = (bar.size, accent)
    if key not in _header_cache:
        layer = pygame.Surface(bar.size, pygame.SRCALPHA)
        block = 34
        for column in range(0, 300, block):
            for row in range(0, bar.height, block):
                # a 2x2 of pips, fading out towards the middle of the screen
                fade = 1.0 - column / 300.0
                alpha = int(26 * fade)
                if alpha < 2:
                    continue
                for dx, dy in ((10, 10), (24, 10), (10, 24), (24, 24)):
                    pygame.draw.circle(layer, (*accent, alpha),
                                       (column + dx, row + dy), 2)
                    pygame.draw.circle(layer, (*accent, alpha),
                                       (bar.width - column - dx, row + dy), 2)
        _header_cache[key] = layer
    surface.blit(_header_cache[key], bar.topleft)


_header_cache = {}


def draw_credit_chip(surface, credits, topright=None):
    """The gold CREDITS badge. Shown in every mode so players always see it."""
    chip = pygame.Rect(0, 0, 210, 44)
    chip.topright = topright or (settings.SCREEN_WIDTH - 24, 90)
    draw_panel(surface, chip, radius=22, glow_color=settings.GOLD)
    draw_text(surface, f"CREDITS  {credits}", chip.center, size=22,
              color=settings.GOLD, bold=True, align="center")
    return chip


def draw_divider(surface, center, width=220, color=settings.NEON_PINK):
    """A line with a small diamond in the middle."""
    cx, cy = center
    pygame.draw.line(surface, settings.PANEL_EDGE,
                     (cx - width, cy), (cx - 14, cy), 2)
    pygame.draw.line(surface, settings.PANEL_EDGE,
                     (cx + 14, cy), (cx + width, cy), 2)
    pygame.draw.polygon(surface, color,
                        [(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)])


# ===========================================================================
# BUTTON
# ===========================================================================

class Button:
    """A rounded arcade button.

    Usage:
        b = Button(rect, "PLAY", on_click=self.start_game)
        b.handle_event(event)   # inside the event loop
        b.update(dt)            # once per frame
        b.draw(screen)          # once per frame
    """

    DEPTH = 5      # how tall the button's side is, in pixels

    def __init__(self, rect, label, on_click=None, accent=settings.NEON_CYAN,
                 font_size=26, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.accent = accent
        self.font_size = font_size
        self.enabled = enabled

        self.selected = False     # used later for colour / number / bet choices
        self.hovered = False
        self.pressed = False
        self.hover_amount = 0.0   # 0.0 -> 1.0, animates the hover effect
        self.press_amount = 0.0   # 0.0 -> 1.0, how far it is pushed down
        self.pip_value = None     # set 1-6 to show dice pips instead of text
        self.label_dy = 0         # nudge the label up or down inside the face,
                                  # for buttons with extra lines underneath

    # ---------------------------------------------------------------- input
    def handle_event(self, event):
        """Return True if this button was clicked."""
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True

        return False

    # --------------------------------------------------------------- update
    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)

        target = 1.0 if (self.hovered or self.selected) else 0.0
        # move hover_amount towards the target => smooth fade instead of a jump
        self.hover_amount += (target - self.hover_amount) * min(1.0, dt * 12)

        # A real arcade button has a body you push down into. Animating this
        # rather than snapping is what makes a click feel physical.
        press_target = 1.0 if (self.pressed or not self.enabled) else 0.0
        self.press_amount += (press_target - self.press_amount) * min(1.0, dt * 22)

    # ----------------------------------------------------------------- draw
    def draw(self, surface):
        """A button with a visible side, so it stands off the panel.

        Three pieces: a dark socket at the bottom, the coloured face lifted
        above it, and the label. Pressing shrinks the lift to zero, so the
        face drops into the socket exactly like a real arcade button.
        """
        accent = self.accent if self.enabled else settings.TEXT_DIM
        lift = self.DEPTH * (1.0 - self.press_amount)
        face = self.rect.move(0, -lift)

        # 1. the socket: the side of the button, always in the same place
        socket = self.rect.copy()
        socket.height += 2
        pygame.draw.rect(surface, shade(accent, 0.26), socket, border_radius=12)
        pygame.draw.rect(surface, shade(accent, 0.16), socket, width=1,
                         border_radius=12)

        # 2. the glow, only while the mouse is over it or it is chosen
        if self.hover_amount > 0.02 and self.enabled:
            glow = _make_panel_glow(face.size, accent, 12)
            glow.set_alpha(int(150 * self.hover_amount))
            surface.blit(glow, (face.x - 12, face.y - 12))

        # 3. the face
        surface.blit(_make_panel_body(face.size, settings.PANEL_FILL, 12),
                     face.topleft)
        pygame.draw.rect(surface, shade(accent, lerp(0.55, 1.0, self.hover_amount)),
                         face, width=2, border_radius=12)

        # a thin bright line along the top edge = light catching the plastic
        pygame.draw.line(surface, shade(accent, 1.5),
                         (face.left + 12, face.top + 2),
                         (face.right - 12, face.top + 2), 1)

        # 4. the accent tab on the left, growing when active
        bar_h = int(face.height * lerp(0.35, 0.78, self.hover_amount))
        bar = pygame.Rect(face.left + 6, face.centery - bar_h // 2, 4, bar_h)
        pygame.draw.rect(surface, accent, bar, border_radius=2)

        # 5. the label, or dice pips for the number buttons
        text_color = settings.TEXT_BRIGHT if self.enabled else settings.TEXT_DIM
        if self.hover_amount > 0.5 and self.enabled:
            text_color = accent

        if self.pip_value:
            self._draw_pips(surface, face, text_color)
        else:
            draw_text(surface, self.label,
                      (face.centerx, face.centery + self.label_dy),
                      self.font_size, text_color, bold=True, align="center")

    def _draw_pips(self, surface, face, color):
        """Draw a dice face instead of a number, like a real die.

        Reading a pattern of dots is faster than reading a digit, which
        matters when someone is choosing quickly at a busy booth.
        """
        layout = _PIP_LAYOUT[self.pip_value]
        # A dice face is square, so the pattern is sized by the button's
        # height. Bigger dots read faster from arm's length at a booth.
        box = face.height - 6
        radius = max(3, int(box * 0.145))
        left = face.centerx - box // 2
        top = face.centery - box // 2
        for u, v in layout:
            pygame.draw.circle(surface, color,
                               (int(left + u * box), int(top + v * box)), radius)


_PIP_LAYOUT = {
    1: [(0.5, 0.5)],
    2: [(0.27, 0.27), (0.73, 0.73)],
    3: [(0.24, 0.24), (0.5, 0.5), (0.76, 0.76)],
    4: [(0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)],
    5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
    6: [(0.27, 0.2), (0.27, 0.5), (0.27, 0.8),
        (0.73, 0.2), (0.73, 0.5), (0.73, 0.8)],
}


_haze_cache = {}


def get_haze_image(width, height):
    """A soft horizontal band of light, built once and reused.

    Used where the floor meets the back wall: real rooms have light pooling
    along that join, and adding it stops the two planes looking like two flat
    rectangles stuck together.
    """
    key = (width, height)
    if key not in _haze_cache:
        small = pygame.Surface((8, 32), pygame.SRCALPHA)
        for y in range(32):
            strength = 1.0 - abs(y - 16) / 16.0
            small.fill((int(26 * strength), int(48 * strength),
                        int(70 * strength), 255),
                       pygame.Rect(0, y, 8, 1))
        _haze_cache[key] = pygame.transform.smoothscale(small, (width, height))
    return _haze_cache[key]


_soft_shadow_cache = {}


def get_soft_shadow(width, height):
    """A blurry dark oval, built once per size and reused.

    Anything standing on the floor needs one of these or it looks like it is
    hovering. Built small and stretched, which is what blurs the edge.
    """
    key = (int(width), int(height))
    if key not in _soft_shadow_cache:
        small = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(small, (0, 0, 0, 120), small.get_rect().inflate(-2, -2))
        _soft_shadow_cache[key] = pygame.transform.smoothscale(small, key)
    return _soft_shadow_cache[key]


_screen_effects_cache = {}


def draw_screen_effects(surface, spacing=3, alpha=16, strength=110):
    """Scanlines and edge darkening in ONE pass.

    They used to be two separate full-screen blits. Baking them into a single
    picture halves the cost, and since neither one ever changes there is no
    reason to keep them apart. This was the most expensive thing left in the
    frame before it was combined.
    """
    size = surface.get_size()
    key = (size, spacing, alpha, strength)
    if key not in _screen_effects_cache:
        layer = pygame.Surface(size, pygame.SRCALPHA)
        width, height = size
        for y in range(0, height, spacing):
            pygame.draw.line(layer, (0, 0, 0, alpha), (0, y), (width, y))
        layer.blit(_vignette_layer(width, height, strength), (0, 0))
        _screen_effects_cache[key] = layer
    surface.blit(_screen_effects_cache[key], (0, 0))
