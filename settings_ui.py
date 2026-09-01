"""
ui/settings_ui.py
-----------------
SETTINGS — a small screen for the booth operator.

Everything here changes values while the game is running. Nothing is saved to
disk: to change the permanent defaults, edit config/settings.py.
"""

import pygame

from config import settings
from game.game_manager import Screen, GameState
from ui import ui
from ui.scene import ArcadeScene


class SettingsUI(Screen):

    def __init__(self, manager):
        super().__init__(manager)
        self.scene = ArcadeScene(dust_count=20)
        self.audio = manager.audio

        center_x = settings.SCREEN_WIDTH // 2
        width, height, gap = 420, 54, 14
        y = 220

        self.rows = []
        for label, action in (
            ("SOUND", self.toggle_sound),
            ("VOLUME DOWN", lambda: self.change_volume(-0.1)),
            ("VOLUME UP", lambda: self.change_volume(+0.1)),
            ("FULLSCREEN", self.toggle_fullscreen),
            ("FPS COUNTER", self.toggle_fps),
            ("RESET CREDITS TO START", self.reset_credits),
        ):
            rect = pygame.Rect(0, 0, width, height)
            rect.centerx, rect.y = center_x, y
            self.rows.append(ui.Button(rect, label, on_click=action, font_size=20))
            y += height + gap

        back = pygame.Rect(0, 0, width, height)
        back.centerx, back.y = center_x, y + 10
        self.back_button = ui.Button(back, "BACK", accent=settings.TEXT_DIM,
                                     font_size=20, on_click=self.go_back)

    # =================================================================== actions
    def toggle_sound(self):
        muted = self.audio.toggle_mute()
        self.audio.play("click")
        return muted

    def change_volume(self, delta):
        self.audio.set_volume(self.audio.sfx_volume + delta)
        self.audio.play("click")

    def toggle_fullscreen(self):
        """Switch between fullscreen and a window, right now.

        main.py owns the actual swap because it owns the display; this only
        asks for it and remembers the new state for the label.
        """
        import main
        main.toggle_fullscreen()
        settings.FULLSCREEN = not settings.FULLSCREEN
        self.audio.play("click")

    def toggle_fps(self):
        settings.SHOW_FPS = not settings.SHOW_FPS
        self.audio.play("click")

    def reset_credits(self):
        self.manager.credits = settings.STARTING_CREDITS
        self.audio.play("place")

    def go_back(self):
        self.audio.play("click")
        self.manager.change_state(GameState.MAIN_MENU)

    # ==================================================================== input
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change_state(GameState.MAIN_MENU)
            return
        for button in self.rows + [self.back_button]:
            button.handle_event(event)

    def update(self, dt):
        self.scene.update(dt)
        for button in self.rows + [self.back_button]:
            button.update(dt)

    # ===================================================================== draw
    def draw(self, surface):
        self.scene.draw_back(surface)
        ui.draw_header(surface, "SETTINGS", subtitle="BOOTH OPTIONS")

        center_x = settings.SCREEN_WIDTH // 2
        for button in self.rows + [self.back_button]:
            button.draw(surface)

        # live values on the right of each row
        values = [
            "OFF" if self.audio.muted else "ON",
            f"{int(self.audio.sfx_volume * 100)}%",
            f"{int(self.audio.sfx_volume * 100)}%",
            "ON" if settings.FULLSCREEN else "OFF",
            "ON" if settings.SHOW_FPS else "OFF",
            str(self.manager.credits),
        ]
        for button, value in zip(self.rows, values):
            ui.draw_text(surface, value, (button.rect.right + 24, button.rect.centery),
                         size=20, color=settings.GOLD, bold=True, align="midleft")

        if not self.audio.enabled:
            ui.draw_text(surface, "no audio device found - the game runs silently",
                         (center_x, 170), size=17, color=settings.TEXT_DIM,
                         align="center")

        ui.draw_text(surface,
                     "Permanent defaults live in config/settings.py",
                     (center_x, settings.SCREEN_HEIGHT - 30), size=16,
                     color=settings.TEXT_DIM, align="center")
        self.scene.draw_front(surface)
