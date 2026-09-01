"""
main.py
-------
Start the game from here:

    python main.py

This file stays deliberately short. It only:
  1. starts Pygame,
  2. creates the window,
  3. runs the game loop (events -> update -> draw),
  4. hands all the real work to the GameManager.
"""

import sys

import pygame

from config import settings
from game.game_manager import GameManager
from ui import ui


def _is_fullscreen_key(event):
    """F11, or Alt+Enter, the two things people already try."""
    if event.key == pygame.K_F11:
        return True
    return bool(event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                and event.mod & pygame.KMOD_ALT)


def toggle_fullscreen():
    """Swap between fullscreen and a window without restarting.

    Wrapped in try/except because a few graphics drivers refuse it, and
    failing to resize is not a reason to lose the game mid-round.
    """
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        pass


def main():
    pygame.init()
    pygame.display.set_caption(settings.GAME_TITLE)

    # SCALED means: draw at 1280x720, then stretch the finished picture to
    # whatever the screen is. Every position in the game stays the same, so
    # nothing has to be re-laid-out for a bigger display.
    flags = pygame.SCALED
    if settings.FULLSCREEN:
        flags |= pygame.FULLSCREEN

    try:
        surface = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), flags)
    except pygame.error:
        # Some machines refuse fullscreen. A window is better than no game.
        surface = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))

    clock = pygame.time.Clock()
    manager = GameManager(surface)

    # ---------------------------------------------------------- game loop --
    while manager.running:
        # dt = how many seconds the previous frame took. Multiplying movement
        # by dt keeps the animation the same speed on fast and slow computers.
        dt = clock.tick(settings.FPS) / 1000.0
        dt = min(dt, 0.05)   # safety cap after a lag spike

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.running = False
            elif event.type == pygame.KEYDOWN and _is_fullscreen_key(event):
                toggle_fullscreen()
                continue      # the game itself should not see this key
            manager.handle_event(event)

        manager.update(dt)
        manager.draw(surface)

        if settings.SHOW_FPS:
            ui.draw_text(surface, f"{int(clock.get_fps())} FPS", (12, 10),
                         size=16, color=settings.TEXT_DIM)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
