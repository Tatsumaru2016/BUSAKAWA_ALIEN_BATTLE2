# game_loop/gameplay_spawns.py — 敵・タレット出現

from __future__ import annotations

import random

import pygame

from enemy_waves import reset_grunt_waves, tick_grunt_waves
from game_loop.resources import frame_core, spawn_images
from game_runtime import RT
from screen_modes import ENDING, PLAY


def run_gameplay_spawns_phase() -> None:
    g = RT.g()
    if g.get("_gameplay_paused"):
        return

    core = frame_core()
    play = core.play
    state = core.state
    diff = core.diff
    WIDTH = core.width
    HEIGHT = core.height
    sprites = spawn_images()
    player_dead = play.player_dead
    ending_delay_timer = play.ending_delay_timer
    boss_active = play.boss_active
    boss_warning = play.boss_warning

    if not (
        state == PLAY
        and not player_dead
        and not boss_active
        and not boss_warning
        and ending_delay_timer == 0
    ):
        return

    enemies = play.enemies
    turrets = play.turrets
    enemy_images = sprites.enemy_images
    turret_top_img = sprites.turret_top_img
    turret_bottom_img = sprites.turret_bottom_img

    if getattr(play, "_grunt_wave", None) is None:
        reset_grunt_waves(play)

    tick_grunt_waves(play, diff, WIDTH, HEIGHT, enemy_images, core.player)

    play.set("enemy_timer", play.enemy_timer + 1)

    turret_spawn_timer = play.turret_spawn_timer + 1
    if turret_spawn_timer >= diff.turret_interval:
        turret_spawn_timer = 0
        is_top = random.choice([True, False])
        turret_img = turret_top_img if is_top else turret_bottom_img
        turret_w, turret_h = turret_img.get_width(), turret_img.get_height()
        turret_y = 0 if is_top else HEIGHT - turret_h
        turrets.append({
            "rect": pygame.Rect(WIDTH, turret_y, turret_w, turret_h),
            "hp": 2,
            "shot_timer": random.randint(0, 20),
            "is_top": is_top,
            "image": turret_img,
        })

    play.set("turret_spawn_timer", turret_spawn_timer)
