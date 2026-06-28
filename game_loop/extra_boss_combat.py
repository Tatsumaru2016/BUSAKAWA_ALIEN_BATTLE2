# game_loop/extra_boss_combat.py — エクストラステージボス戦

from __future__ import annotations

from combat import apply_player_hit, player_hits_boss_body
from extra_boss import draw_extra_boss, update_extra_boss_combat, update_extra_intro
from extra_boss_victory import (
    draw_extra_ending_fade_overlay,
    draw_extra_ending_fin,
    draw_extra_ending_slide,
    draw_extra_victory_boss,
    draw_extra_victory_fx,
    is_extra_victory_active,
    update_extra_boss_victory,
)
from bullet import Bullet
from extra_stage_support import (
    check_deploy_extra_support,
    draw_extra_support_squad,
    update_extra_support_squad,
)
from game_loop.resources import frame_core
from game_runtime import RT
from screen_modes import EXTRA_PLAY


def run_extra_boss_combat_phase() -> None:
    core = frame_core()
    if core.state != EXTRA_PLAY:
        return

    play = core.play
    player = core.player
    screen = core.screen
    player_dead = play.player_dead

    update_extra_intro(play)

    if is_extra_victory_active(play):
        update_extra_boss_victory(play, player)
        t = play.extra_victory_timer
        boss = play.boss
        phase = play.extra_victory_phase
        if phase == "gallery":
            draw_extra_ending_slide(screen, play)
            return
        if phase in ("fin_pre_wait", "fin_draw", "fin_post_wait", "fade_out"):
            draw_extra_ending_fin(screen, play)
            if phase == "fade_out":
                draw_extra_ending_fade_overlay(screen, play)
            return
        if phase == "explode":
            draw_extra_victory_fx(screen, play, t, layer="under")
            if boss is not None:
                draw_extra_victory_boss(screen, play, boss)
            draw_extra_support_squad(screen, play)
            draw_extra_victory_fx(screen, play, t, layer="over")
        elif phase in ("lineup", "tally", "bubbles", "depart", "post_exit_wait"):
            draw_extra_support_squad(screen, play)
        return

    phase = getattr(play, "extra_intro_phase", "")
    if phase and phase != "fight":
        if phase in ("bg_roll", "bubble") and play.boss is not None:
            draw_extra_boss(screen, play)
        return

    if not play.boss_active or play.boss is None:
        return

    g = RT.g()
    boss = play.boss
    update_extra_boss_combat(play, player, player_dead)
    if not getattr(boss, "ex_tank_transform_active", False):
        check_deploy_extra_support(
            play,
            boss,
            player,
            g.get("support_fighter_images") or [],
            g.get("_bubble"),
            g["WIDTH"],
            g["HEIGHT"],
            g.get("support_arrive_sound"),
        )
        update_extra_support_squad(
            play,
            player,
            player_dead,
            boss,
            play.bullets,
            g.get("bullet_img"),
            g.get("support_fighter_images") or [],
            g.get("_bubble"),
            g["WIDTH"],
            g["HEIGHT"],
            Bullet,
            g.get("support_arrive_sound"),
        )
    draw_extra_boss(screen, play)
    draw_extra_support_squad(screen, play)

    if not player_dead and player.invincible_timer == 0:
        if player_hits_boss_body(player, boss):
            apply_player_hit(hit_kind="boss")
