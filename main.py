# main.py - entry point (bootstrap: game_bootstrap, loop: submodules)

import asyncio
import sys

import pygame

from settings import *
import game_loop
import screen_handlers
from audio_focus import handle_window_focus_event
from game_bootstrap import bootstrap
from game_input_device import handle_joystick_plug_event
from game_layout import (
    activate_play_view,
    deactivate_play_view,
    draw_frame_chrome,
)
from screen_modes import ENDING_EXTRA_DIVE, EXTRA_PLAY, GAMEOVER, PLAY, TITLE

_PLAYFIELD_STATES = (PLAY, GAMEOVER, EXTRA_PLAY, ENDING_EXTRA_DIVE)


async def main() -> None:
    _boot = await bootstrap(globals())
    app = _boot.app
    play = _boot.play

    running = True
    while running:
        diff = app.diff
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handle_joystick_plug_event(event, globals())
            handle_window_focus_event(event, play, state)
            screen_handlers.handle_event(event)

        screen.fill((0, 0, 0))

        if state == TITLE:
            from game_loop.title_flow import poll_title_cheat_controller

            poll_title_cheat_controller()

        if screen_handlers.draw_intro_screen():
            await asyncio.sleep(0)
            continue
        if state in _PLAYFIELD_STATES:
            draw_frame_chrome(screen)
            activate_play_view(globals())
        try:
            if state in _PLAYFIELD_STATES:
                screen_handlers.update_play_background()
            if screen_handlers.draw_menu_screen():
                await asyncio.sleep(0)
                continue
            game_loop.run_play_frame()
        finally:
            if globals().get("_play_surface_active"):
                deactivate_play_view(globals())

        if state in (PLAY, EXTRA_PLAY):
            play.capture_from(globals())

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
sys.exit()
