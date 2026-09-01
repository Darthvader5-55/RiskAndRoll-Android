"""
config/settings.py
------------------
ONE place for every number, colour and file path used by the game.

Rule for this project: if you ever feel like typing a raw number such as
1280 or (0, 255, 255) inside another file, add it here first and import it.
That way you can re-balance or re-skin the whole game from this single file.
"""

import os

# ---------------------------------------------------------------- PATHS ----
# BASE_DIR = the game folder (one level up from config/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
DICE_DIR = os.path.join(ASSETS_DIR, "dice")
TUMBLER_DIR = os.path.join(ASSETS_DIR, "tumbler")
SOUND_DIR = os.path.join(ASSETS_DIR, "sounds")
BACKGROUND_DIR = os.path.join(ASSETS_DIR, "backgrounds")
UI_DIR = os.path.join(ASSETS_DIR, "ui")
EFFECTS_DIR = os.path.join(ASSETS_DIR, "effects")

CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONSEQUENCES_FILE = os.path.join(CONFIG_DIR, "consequences.json")

# --------------------------------------------------------------- WINDOW ----
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "RISK & ROLL"
# Change the line above and the whole game renames itself: the window title,
# the big name on the main menu, and the lit sign on the machine. Keep it
# short - anything past about 14 letters starts to crowd the machine's sign.
FULLSCREEN = True
# The game is DRAWN at 1280x720 no matter what, then stretched to fill the
# screen. That is what pygame.SCALED does, and it is why fullscreen needs no
# layout changes: every button stays exactly where it was, just bigger. The
# picture keeps its shape, so a widescreen laptop gets black bars at the
# sides rather than a squashed image.
#
# Press F11 (or Alt+Enter) at any time to switch between fullscreen and a
# window. Set this to False if you would rather it started windowed.

# ---------------------------------------------------------------- FONTS ----
# If you later drop a .ttf file into assets/fonts/, put its file name here.
# Leave it as None and the game will fall back to a clean system font.
FONT_FILE = None
FALLBACK_FONTS = ["bahnschrift", "dejavusans", "arial", "freesans"]

# --------------------------------------------------------------- COLOURS ---
# Arcade-cabinet look: deep navy cabinet, neon cyan + magenta accents, gold money.
BG_TOP = (10, 12, 30)          # top of the background gradient
BG_BOTTOM = (26, 10, 42)       # bottom of the background gradient
PANEL_FILL = (20, 24, 48)      # metallic panel body
PANEL_EDGE = (58, 66, 110)     # panel border
NEON_CYAN = (60, 240, 255)
NEON_PINK = (255, 60, 170)
NEON_LIME = (150, 255, 120)
GOLD = (255, 205, 70)
TEXT_BRIGHT = (240, 245, 255)
TEXT_DIM = (150, 160, 195)
SHADOW = (0, 0, 0)
WIN_GREEN = (70, 230, 140)
LOSE_RED = (255, 85, 85)

# ------------------------------------------------------------- SIX DICE ----
# The order here is the order the dice appear in the UI and in results.
COLOR_ORDER = ["RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE"]

DICE_COLORS = {
    "RED":    (228, 52, 62),
    "BLUE":   (48, 128, 246),
    "GREEN":  (46, 196, 108),
    "YELLOW": (248, 202, 48),
    "PURPLE": (168, 88, 240),
    "ORANGE": (250, 138, 40),
}

DICE_FACES = [1, 2, 3, 4, 5, 6]

# -------------------------------------------------------------- BETTING ----
STARTING_CREDITS = 250
BET_AMOUNTS = [10, 20, 50, 100]
WIN_MULTIPLIER = 2          # a winning bet is doubled (50 -> 100 returned)
# READ THIS BEFORE THE BOOTH RUNS.
# Picking one colour AND one number is a 1-in-6 shot, so a player wins about
# 17% of the time. Paying 2x means that over many rounds players get back only
# about a third of what they stake, and most people will lose five rounds in a
# row before winning one. That is fine for a demo, harsh for a queue of
# classmates. Change the number above to shift the balance:
#     2  as written in the design document (very hard)
#     4  players win back about two thirds - lively, still favours the booth
#     5  close to fair, good if the booth is for fun rather than profit
#     6  mathematically fair - the booth breaks even in the long run

# --------------------------------------------------------- ROUND TIMING ----
# All values are in seconds. Tuned so a booth round stays short.
# 1. the "3... 2... 1..." before the dice are thrown
COUNTDOWN_SECONDS = 3.0

# 2. HOW LONG THE DICE TUMBLE is not a setting, and cannot be, because the
#    dice stop when they run out of energy exactly like real dice do. It is
#    controlled by two numbers in game/physics.py. Measured over 90 rolls:
#
#        BOUNCE_DAMPING  0.40 -> 1.6s     GRAVITY  900  -> 2.5s
#                        0.55 -> 2.0s              1800 -> 2.0s
#                        0.70 -> 2.4s              2600 -> 1.8s
#                        0.80 -> 3.2s
#
#    Bouncier dice roll for longer; heavier dice land sooner.

# 3. the pause after the dice stop, before the result card slides in. Without
#    it the card covers the dice the instant they land and nobody gets to see
#    what they rolled.
RESULT_DELAY = 0.5

# ------------------------------------------------------------- GAMEPLAY ----
MIN_PLAYERS = 1             # Consequence Pool
MAX_PLAYERS = 6

# ---------------------------------------------------------------- AUDIO ----
MUSIC_VOLUME = 0.4
SFX_VOLUME = 0.7
AUDIO_ENABLED = True

# ------------------------------------------------------------- HOW TO PLAY -
# Show the rules card automatically when a mode opens. At a booth this is
# what you want: a new person walks up to every round, and the screen has to
# explain itself before they touch anything. Set it to False if you are
# demonstrating and do not want to dismiss the card each time.
SHOW_RULES_ON_ENTER = True

# ---------------------------------------------------------------- DEBUG ----
SHOW_FPS = True             # small FPS counter in the corner
DEBUG = False               # extra outlines / info for testing
