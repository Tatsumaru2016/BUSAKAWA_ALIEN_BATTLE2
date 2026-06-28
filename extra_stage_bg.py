# extra_stage_bg.py — エクストラ背景（横スクロールのみ / 停止）

from __future__ import annotations

import pygame

from extra_boss import EXTRA_INTRO_SCROLL_SPEED
from game_runtime import RT
from render_ui import draw_scroll


def _blit_parallax(layer: pygame.Surface, g, play, scroll: bool) -> None:
    w, h = g["WIDTH"], g["HEIGHT"]
    if scroll:
        play.update(
            extra_far_x=draw_scroll(
                layer, g["extra_bg_far"], play.extra_far_x, EXTRA_INTRO_SCROLL_SPEED[0]
            ),
            extra_mid_x=draw_scroll(
                layer, g["extra_bg_mid"], play.extra_mid_x, EXTRA_INTRO_SCROLL_SPEED[1]
            ),
            extra_front_x=draw_scroll(
                layer, g["extra_bg_front"], play.extra_front_x, EXTRA_INTRO_SCROLL_SPEED[2]
            ),
        )
    else:
        far, mid, front = play.extra_far_x, play.extra_mid_x, play.extra_front_x
        fw = g["extra_bg_far"].get_width()
        mw = g["extra_bg_mid"].get_width()
        pw = g["extra_bg_front"].get_width()
        layer.blit(g["extra_bg_far"], (far, 0))
        layer.blit(g["extra_bg_far"], (far + fw, 0))
        layer.blit(g["extra_bg_mid"], (mid, 0))
        layer.blit(g["extra_bg_mid"], (mid + mw, 0))
        layer.blit(g["extra_bg_front"], (front, 0))
        layer.blit(g["extra_bg_front"], (front + pw, 0))


def draw_extra_play_background(screen) -> None:
    g = RT.g()
    play = g["play"]
    w, h = g["WIDTH"], g["HEIGHT"]
    phase = getattr(play, "extra_intro_phase", "fight")
    scroll = phase == "bg_roll" and not getattr(play, "extra_bg_frozen", False)

    layer = pygame.Surface((w, h))
    _blit_parallax(layer, g, play, scroll=scroll)
    screen.blit(layer, (0, 0))
