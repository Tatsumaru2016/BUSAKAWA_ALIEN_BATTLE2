# extra_stage.py — エクストラステージ開始

from __future__ import annotations

import pygame

from boss5_support import clear_boss5_support
from boss_spawn import clear_boss_warning
from extra_boss import apply_extra_boss_barrier, create_extra_boss
from extra_boss_victory import clear_extra_victory, init_extra_victory_state
from extra_stage_support import clear_extra_support, init_extra_support_state
from game_runtime import RT


def spawn_extra_stage_boss(play) -> None:
    """導入演出: 定位置に配置（背景スクロールと同時に表示）。"""
    diff = RT.g()["diff"]
    boss = create_extra_boss(diff)
    play.set("boss", boss)
    apply_extra_boss_barrier(play, diff)
    play.set("boss_active", False)
    play.set("boss_fight_active", False)


def begin_extra_stage(play, app) -> None:
    """沈黙ボス口ダイブ後: 専用パララックス背景 → ボス戦導入。"""
    from screen_modes import EXTRA_PLAY

    g = RT.g()
    player = g["player"]
    height = g["HEIGHT"]

    try:
        pygame.mixer.music.fadeout(500)
    except Exception:
        pass

    play.enemies.clear()
    play.turrets.clear()
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.meteors.clear()
    play.bullets.clear()
    play.explosions.clear()
    play.power_items.clear()

    spawn_extra_stage_boss(play)
    play.set("boss_active", False)
    clear_boss_warning(play)
    play.set("boss_fight_active", False)
    play.set("boss5_bg_mode", False)
    clear_boss5_support()
    clear_extra_support(play)
    init_extra_support_state(play)
    clear_extra_victory(play)
    init_extra_victory_state(play)
    play.set("extra_bg_mode", True)
    play.set("extra_bg_frozen", False)
    play.set("extra_intro_phase", "bg_roll")
    play.set("extra_intro_timer", 0)
    play.set("extra_far_x", 0)
    play.set("extra_mid_x", 0)
    play.set("extra_front_x", 0)
    play.set("extra_run", True)
    play.set("extra_dive_timer", 0)
    play.set("extra_dive_done", False)
    play.set("extra_dive_phase", "")
    play.set("extra_dive_snap_timer", 0)
    play.set("extra_dive_suck_bubble_idx", -1)
    play.set("extra_dive_boss_surf", None)
    play.set("extra_dive_boss_rect", None)
    play.set("b5_death_active", False)
    play.set("player_dead", False)
    play.set("ending_delay_timer", 0)
    play.boss_score_tally.reset()

    player.rect.x = 120
    player.rect.y = height // 2
    player.invincible_timer = 120

    app.set_screen_mode(EXTRA_PLAY)
