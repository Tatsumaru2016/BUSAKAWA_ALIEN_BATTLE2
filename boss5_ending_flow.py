# boss5_ending_flow.py — ボス5撃破後: 沈黙→スコア確定→吸い込み→エンディング

from __future__ import annotations

import pygame

from audio import BGM_ENDING, play_bgm
from ending_extra_dive import (
    _setup_battle_layout,
    draw_extra_dive,
    draw_extra_dive_bubble,
    update_extra_dive,
)
from game_loop.boss_tally import start_boss_score_tally
from game_loop.resources import title_flow_resources
from game_runtime import RT
from game_state import AppState
from screen_modes import ENDING, ENDING_EXTRA_DIVE

FADE_TO_ENDING_FRAMES = 90


class _TallyBossRef:
    """撃破スコア確定用の最小ボス参照。"""

    def __init__(self, rect: pygame.Rect, boss_type: int = 5):
        self.rect = rect
        self.boss_type = boss_type


def _draw_b5_tally_backdrop(play_screen: pygame.Surface, play) -> None:
    """スコア確定中: 撃破後のボスを背景に表示。"""
    boss_surf = play.extra_dive_boss_surf
    boss_rect = play.extra_dive_boss_rect
    if boss_surf is not None and boss_rect is not None:
        play_screen.blit(boss_surf, boss_rect.topleft)


def begin_boss5_post_death_epilogue(
    play,
    app,
    player,
    dead_img: pygame.Surface,
) -> None:
    """沈黙・フェード終了後: スコア確定→吸い込み→エンディングへ。"""
    g = RT.g()
    g["_bubble"].clear()
    _setup_battle_layout(play, player, dead_img)
    play.set("b5_clear_cinematic", True)
    play.set("b5_epilogue_phase", "tally")
    play.set("b5_epilogue_timer", 0)
    play.set("b5_epilogue_fade", 0)
    play.set("boss5_bg_mode", True)
    play.set("extra_dive_done", False)
    play.set("extra_dive_phase", "")
    play.set("extra_dive_snap_timer", 0)
    play.set("extra_dive_timer", 0)
    play.set("extra_dive_suck_bubble_idx", -1)
    play.set("extra_dive_suck_sfx_played", False)
    play.set("boss_fight_active", False)
    play.set("boss", None)
    play.set("boss_active", False)
    play.boss_score_tally.reset()
    app.set_screen_mode(ENDING_EXTRA_DIVE)
    _start_final_boss_tally(play)


def _start_final_boss_tally(play) -> None:
    rect = play.extra_dive_boss_rect
    if rect is None:
        rect = pygame.Rect(900, 300, 120, 120)
    g = RT.g()
    g["_bubble"].clear()
    start_boss_score_tally(_TallyBossRef(rect.copy()))


def begin_boss5_dive_after_tally(play, app) -> None:
    """スコア確定後: 吸い込み演出へ。"""
    g = RT.g()
    g["_bubble"].clear()
    play.boss_score_tally.reset()
    play.set("b5_epilogue_phase", "dive")
    play.set("extra_dive_done", False)
    play.set("extra_dive_phase", "snap")
    play.set("extra_dive_snap_timer", 0)
    play.set("extra_dive_timer", 0)
    play.set("extra_dive_suck_bubble_idx", -1)
    play.set("extra_dive_suck_sfx_played", False)


def _begin_boss5_ending_fade(play) -> None:
    play.set("b5_epilogue_phase", "fade")
    play.set("b5_epilogue_timer", 0)
    play.set("b5_epilogue_fade", 0)


def _enter_ending_screen(play, app) -> None:
    g = RT.g()
    app.record_hard_clear_if_applicable()
    if AppState.can_enter_extra_stage(app.diff.name):
        play.set("ending_menu_choice", 0)
    else:
        play.set("ending_menu_choice", 1)
    play.set("b5_clear_cinematic", False)
    play.set("b5_epilogue_phase", "")
    play.set("b5_epilogue_timer", 0)
    play.set("b5_epilogue_fade", 255)
    play.boss_score_tally.reset()
    play.set("ending_delay_timer", 0)
    play.set("boss", None)
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.bullets.clear()
    title_flow_resources().title_cheat.reset_all()
    play_bgm(BGM_ENDING)
    app.set_screen_mode(ENDING)
    play.set("_ending_sfx_timer", g["FPS"] * 3)
    play.set("_ending_screen_sfx_played", False)


def update_boss5_clear_epilogue(play, app) -> None:
    """ENDING_EXTRA_DIVE 中のエピローグ進行。"""
    phase = getattr(play, "b5_epilogue_phase", "")

    if phase == "tally":
        return

    if phase == "dive":
        update_extra_dive(play)
        if play.extra_dive_done:
            _begin_boss5_ending_fade(play)
        return

    if phase == "fade":
        t = play.b5_epilogue_timer + 1
        play.set("b5_epilogue_timer", t)
        alpha = min(255, int(255 * t / max(1, FADE_TO_ENDING_FRAMES)))
        play.set("b5_epilogue_fade", alpha)
        if t >= FADE_TO_ENDING_FRAMES:
            _enter_ending_screen(play, app)


def draw_boss5_clear_epilogue(
    play_screen: pygame.Surface,
    full_screen: pygame.Surface,
    play,
    player_img: pygame.Surface,
    font,
    font_hud_sm,
    font_lg,
    big_font,
) -> None:
    phase = getattr(play, "b5_epilogue_phase", "")

    if phase == "tally":
        _draw_b5_tally_backdrop(play_screen, play)
        if play.boss_score_tally.active:
            play.boss_score_tally.draw(
                full_screen, font, font_hud_sm, font_lg, big_font
            )
        return

    if phase in ("dive", "fade"):
        draw_extra_dive(play_screen, play, player_img, font, big_font)
        if phase == "dive":
            draw_extra_dive_bubble(play_screen, play)
        fade = int(getattr(play, "b5_epilogue_fade", 0))
        if fade > 0:
            sw, sh = full_screen.get_size()
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, fade))
            full_screen.blit(overlay, (0, 0))
        return

    fade = int(getattr(play, "b5_epilogue_fade", 0))
    if fade > 0:
        sw, sh = full_screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, fade))
        full_screen.blit(overlay, (0, 0))


# 互換: 旧関数名
def begin_boss5_clear_cinematic(play, app, player=None, dead_img=None) -> None:
    from game_runtime import RT

    g = RT.g()
    if player is None:
        player = g["player"]
    if dead_img is None:
        dead_img = g["midboss5_images"].get("defeat") or g["midboss5_images"]["normal"]
    begin_boss5_post_death_epilogue(play, app, player, dead_img)
