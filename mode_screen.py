"""
ui/mode_screen.py
-----------------
The parts that Color Royale, Consequence Pool and Arcade Duel all share.

All three modes show the same thing on the left: the arcade room, the tumbler
and six dice, drawn through the depth renderer. Only the right-hand panel and
the rules differ. Rather than copy that setup into three files, it lives here
once and each mode inherits it.

A mode only has to provide:

    draw_panel(surface)   what goes in the right-hand column
    handle_event(event)   its own clicks (and call super() for ESC)

and it gets the machine, the dice and the layout for free.
"""

import pygame

from config import settings
from game.dice import DiceSet
from game.game_manager import Screen, GameState
from game.layers import Layer, DepthRenderer
from game.tumbler import Tumbler
from ui import ui
from ui.help_ui import HelpPanel

# The key that opens HOW TO PLAY. Change it here and every mode follows.
HELP_KEY = pygame.K_h
from ui.scene import ArcadeScene

# The 75% / 25% split from the design document.
TOP_MARGIN = 88
SIDE_MARGIN = 20
PANEL_WIDTH = 320


class ModeScreen(Screen):

    title = "MODE"
    subtitle = None

    def __init__(self, manager, dice_size=26):
        super().__init__(manager)

        bottom = settings.SCREEN_HEIGHT - SIDE_MARGIN
        self.play_rect = pygame.Rect(
            SIDE_MARGIN, TOP_MARGIN,
            settings.SCREEN_WIDTH - PANEL_WIDTH - SIDE_MARGIN * 3,
            bottom - TOP_MARGIN)
        self.panel_rect = pygame.Rect(
            self.play_rect.right + SIDE_MARGIN, TOP_MARGIN,
            PANEL_WIDTH, bottom - TOP_MARGIN)

        # The machine does not fill the play area any more. Leaving a margin
        # of room around it - sky above, floor below, walls at the sides - is
        # what lets the background read as a place the cabinet stands in.
        machine = pygame.Rect(0, 0,
                              self.play_rect.width - 116,
                              self.play_rect.height - 92)
        machine.midtop = (self.play_rect.centerx, self.play_rect.top + 16)
        self.tumbler = Tumbler(machine)
        self.stage = self.tumbler.stage

        # The scene keeps its OWN full-screen floor, separate from the small
        # floor inside the machine, so the room has its own horizon.
        self.scene = ArcadeScene(pillars=False, dust_count=16)

        # a painted ring on the floor for the machine to stand in
        self.scene.set_stage_ring((machine.centerx, machine.bottom + 26),
                                  int(machine.width * 0.92))

        # lit signs on the wall above the speakers
        sign_w = machine.left - self.play_rect.left - 20
        self.scene.set_wall_signs([
            pygame.Rect(self.play_rect.left + 9, self.play_rect.top + 26,
                        sign_w, 150),
            pygame.Rect(machine.right + 11, self.play_rect.top + 26,
                        sign_w, 150),
        ])

        # a few dice tumbling slowly in the room, in the gaps at the sides
        self.scene.add_drifting_dice([
            (self.play_rect.left + 8, machine.left - 8),
            (machine.right + 8, self.play_rect.right - 8),
        ], count=6)

        # PA cabinets stand in the gaps either side of the machine
        speaker_w = machine.left - self.play_rect.left - 14
        speaker_h = 250
        self.scene.set_speakers([
            pygame.Rect(self.play_rect.left + 6, machine.bottom - speaker_h + 30,
                        speaker_w, speaker_h),
            pygame.Rect(machine.right + 8, machine.bottom - speaker_h + 30,
                        speaker_w, speaker_h),
        ])
        self.renderer = DepthRenderer()
        self.dice = DiceSet(self.tumbler, size=dice_size)

        self.audio = manager.audio
        self._rumbling = False
        self._result_wait = 0.0
        # every bounce, wall hit and dice-on-dice knock makes its own clack
        self.dice.on_impact = self.audio.play_clack
        self.message = ""
        self.message_color = settings.TEXT_DIM

        # Every mode has a back button in the same place.
        # The HOW TO PLAY card and the small "?" that opens it. Every mode
        # gets these for free; each one only supplies its own words through
        # help_content() below.
        card = pygame.Rect(0, 0, 660, 470)
        card.center = (self.play_rect.centerx, settings.SCREEN_HEIGHT // 2)
        self.help_panel = HelpPanel(card)

        self.help_button = ui.Button(
            pygame.Rect(self.play_rect.right - 46, 18, 40, 40), "?",
            accent=settings.NEON_CYAN, font_size=24, on_click=self.open_help)

        back = pygame.Rect(0, 0, self.panel_rect.width - 40, 46)
        back.midbottom = (self.panel_rect.centerx, self.panel_rect.bottom - 16)
        self.back_button = ui.Button(back, "MAIN MENU", accent=settings.TEXT_DIM,
                                     font_size=20, on_click=self.go_to_menu)

    # ============================================================== how to play
    def help_content(self):
        """What the HOW TO PLAY card says. Each mode overrides this."""
        return {
            "title": f"HOW TO PLAY  ·  {self.title}",
            "summary": "",
            "steps": [],
            "payouts": [],
            "controls": "ESC  back to the menu",
        }

    def on_enter(self):
        """Called once by the GameManager when this mode opens.

        The rules card is shown here rather than in __init__ because the
        subclass has finished setting itself up by now - help_content() often
        reads the mode's own state, which does not exist yet during __init__.
        """
        if settings.SHOW_RULES_ON_ENTER:
            self.help_panel.show(self.help_content())

    def open_help(self):
        self.audio.play("click")
        self.help_panel.show(self.help_content())

    def is_typing(self):
        """True while the player is typing into a text box on this screen.

        Modes with name boxes override this. It exists so keyboard SHORTCUTS
        stand down while someone is typing - otherwise a name like SETH opens
        the rules card on the H instead of typing the letter.
        """
        return False

    def handle_help_event(self, event):
        """Call this FIRST in a mode's handle_event.

        Returns True when the help card has taken the event, which means the
        mode should ignore it - otherwise a click meant for the rules card
        would also land on a button behind it.
        """
        if self.help_panel.handle_event(event):
            return True

        # H opens the rules - unless a name is being typed, in which case H
        # is just a letter.
        if (event.type == pygame.KEYDOWN and event.key == HELP_KEY
                and not self.is_typing()):
            self.open_help()
            return True

        return self.help_button.handle_event(event)

    # =================================================================== helpers
    def go_to_menu(self):
        self.audio.stop_rumble()
        self._rumbling = False
        self._result_wait = 0.0
        self.audio.play("click")
        self.manager.change_state(GameState.MAIN_MENU)

    def set_message(self, text, color=None):
        self.message = text
        self.message_color = color or settings.TEXT_DIM

    def buttons(self):
        """Every clickable button on this screen. Modes extend this."""
        return [self.back_button]

    # ==================================================================== input
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change_state(GameState.MAIN_MENU)
            return
        for button in self.buttons():
            button.handle_event(event)

    # =================================================================== update
    def update(self, dt):
        self.audio.begin_frame()      # reset the clack limit for this frame
        self._update_rumble()
        self.scene.update(dt)
        self.tumbler.update(dt)
        self.dice.update(dt)
        for button in self.buttons():
            button.update(dt)
        self.help_button.update(dt)
        self.help_panel.update(dt)
        self.update_mode(dt)

    def dice_settled(self, dt):
        """True once the dice have stopped AND the result pause has passed.

        Modes call this instead of checking dice.all_finished directly, so
        settings.RESULT_DELAY gives the player a moment to look at what they
        rolled before the result card covers it up.
        """
        if not self.dice.all_finished:
            self._result_wait = 0.0
            return False
        self._result_wait += dt
        return self._result_wait >= settings.RESULT_DELAY

    def _update_rumble(self):
        """Run the tumbler noise for as long as the dice are moving.

        The volume follows how lively the dice still are, so the rumble fades
        away as they settle instead of cutting off. Every mode gets this
        without having to ask for it.
        """
        moving = [die for die in self.dice.dice
                  if die.visible and die.state != die.IDLE]
        if not moving:
            if self._rumbling:
                self.audio.stop_rumble()
                self._rumbling = False
            return

        if not self._rumbling:
            self.audio.start_rumble()
            self._rumbling = True

        # the liveliest die sets the level, so one straggler still hums
        energy = max(die.body.energy() for die in moving)
        self.audio.set_rumble_level(0.25 + 0.75 * energy)

    def update_mode(self, dt):
        """Modes put their round logic here."""
        pass

    # ===================================================================== draw
    def draw(self, surface):
        renderer = self.renderer
        renderer.add(Layer.BACKGROUND, self.scene.draw_back)
        self.tumbler.add_to(renderer)
        self.dice.add_to(renderer)
        renderer.add(Layer.UI, self._draw_interface)
        renderer.draw(surface)

        # The machine is now on the screen, so its pixels can be mirrored onto
        # the floor beneath it. Doing it here - after the machine, before the
        # screen effects - is what makes the cabinet look like it is standing
        # on something instead of floating.
        self.scene.draw_reflection(surface, self.tumbler.rect)

        self.scene.draw_front(surface)
        self.draw_overlay(surface)
        self.help_panel.draw(surface)      # rules sit on top of everything

    def _draw_interface(self, surface):
        ui.draw_header(surface, self.title, subtitle=self.subtitle)
        self._draw_panel_thickness(surface)
        ui.draw_panel(surface, self.panel_rect, radius=18,
                      glow_color=settings.NEON_CYAN, screws=True)
        self.draw_panel(surface)
        self.back_button.draw(surface)
        self.help_button.draw(surface)

    def _draw_panel_thickness(self, surface):
        """A slanted face above and beside the control panel.

        The panel is a flat rectangle. Drawing a thin face along its top and
        left, leaning away from the viewer, turns it into a slab with an edge
        - the same trick the dice use, just with one shape instead of a cube.
        """
        panel = self.panel_rect
        lean = 9

        top_face = [(panel.left, panel.top + 12),
                    (panel.right, panel.top + 12),
                    (panel.right - lean, panel.top + 12 - lean),
                    (panel.left - lean, panel.top + 12 - lean)]
        side_face = [(panel.left, panel.top + 12),
                     (panel.left - lean, panel.top + 12 - lean),
                     (panel.left - lean, panel.bottom - lean),
                     (panel.left, panel.bottom)]

        pygame.draw.polygon(surface, (30, 36, 68), side_face)
        pygame.draw.polygon(surface, (46, 55, 96), top_face)
        pygame.draw.line(surface, (74, 86, 138),
                         (panel.left - lean, panel.top + 12 - lean),
                         (panel.right - lean, panel.top + 12 - lean), 1)

    def draw_panel(self, surface):
        """Modes fill the right-hand column here."""
        pass

    def draw_overlay(self, surface):
        """Modes draw their result screen here, on top of everything."""
        pass

    # ------------------------------------------------------------ shared bits
    def draw_message(self, surface, y):
        if self.message:
            ui.draw_text(surface, self.message,
                         (self.panel_rect.centerx, y), size=17,
                         color=self.message_color, bold=True, align="midtop")

    def draw_dice_readout(self, surface, y, colors=None, highlight=None):
        """A small COLOUR -> NUMBER table, used by every result screen."""
        results = self.dice.results()
        for color_name in (colors or settings.COLOR_ORDER):
            swatch = pygame.Rect(self.panel_rect.left + 20, y, 16, 16)
            pygame.draw.rect(surface, settings.DICE_COLORS[color_name],
                             swatch, border_radius=4)
            bright = (highlight is None or color_name in highlight)
            ui.draw_text(surface, color_name,
                         (swatch.right + 10, y - 2), size=16,
                         color=settings.TEXT_BRIGHT if bright else settings.TEXT_DIM,
                         bold=True)
            ui.draw_text(surface, str(results[color_name]),
                         (self.panel_rect.right - 20, y - 2), size=18,
                         color=settings.TEXT_BRIGHT if bright else settings.TEXT_DIM,
                         bold=True, align="topright")
            y += 24
        return y
