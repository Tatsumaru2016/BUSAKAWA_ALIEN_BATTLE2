# ending_extra_dive.py — 沈黙後: 画面切替 → 吸い込み（吹き出し3段）→ エクストラへ

from __future__ import annotations

import math

import pygame

from boss5_support import clear_boss5_support
from boss5_update import B5_SIN_ANCHOR_X, B5_SIN_ANCHOR_Y
from score_system import _draw_blink_enter
from settings import HEIGHT

DIVE_SNAP_FRAMES = 70
DIVE_DURATION_FRAMES = 420
DIVE_PLAYER_SCALE_START = 1.0
DIVE_PLAYER_SCALE_END = 0.05
DIVE_SPIN_TURNS = 2.25
# ボス中心より左（口付近・やや奥）
DIVE_TARGET_X_OFFSET = -150
B5_PLAYER_START_X = 120
# pygame: loops=2 → 計3回再生
DIVE_SUCK_SFX_LOOPS = 2
DIVE_SUCK_SHAKE_AMP = 3

EXTRA_SUCK_BUBBLE_TRIGGERS = ("extra_suck_1", "extra_suck_2", "extra_suck_3")


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _suck_shake(timer: int) -> tuple[int, int]:
    """吸い込み中: 自機を少し震わせる。"""
    amp = DIVE_SUCK_SHAKE_AMP
    ox = int(math.sin(timer * 0.71) * amp + math.sin(timer * 1.37) * (amp // 2 + 1))
    oy = int(math.cos(timer * 0.63) * amp + math.cos(timer * 1.19) * (amp // 2 + 1))
    return ox, oy


def _suck_motion(play, raw_t: float) -> tuple[int, int, float, float]:
    """吸い込み中の自機位置・スケール・回転角（震え込み）。"""
    t = _smoothstep(raw_t)
    start_x = play.extra_dive_player_x
    start_y = play.extra_dive_player_y
    px = int(start_x + (play.extra_dive_target_x - start_x) * t)
    py = int(start_y + (play.extra_dive_target_y - start_y) * t)
    if getattr(play, "extra_dive_phase", "") == "suck":
        sx, sy = _suck_shake(int(getattr(play, "extra_dive_timer", 0)))
        px += sx
        py += sy
    scale = DIVE_PLAYER_SCALE_START + (DIVE_PLAYER_SCALE_END - DIVE_PLAYER_SCALE_START) * t
    angle = 360.0 * DIVE_SPIN_TURNS * t
    return px, py, scale, angle


def _setup_battle_layout(play, player, dead_img: pygame.Surface) -> None:
    boss_rect = dead_img.get_rect(center=(B5_SIN_ANCHOR_X, B5_SIN_ANCHOR_Y))
    play.set("extra_dive_boss_surf", dead_img)
    play.set("extra_dive_boss_rect", boss_rect.copy())
    play.set("extra_dive_target_x", boss_rect.centerx + DIVE_TARGET_X_OFFSET)
    play.set("extra_dive_target_y", boss_rect.centery)
    play.set("extra_dive_player_x", B5_PLAYER_START_X)
    play.set("extra_dive_player_y", HEIGHT // 2)
    player.rect.x = B5_PLAYER_START_X
    player.rect.y = HEIGHT // 2


def _clear_extra_dive_layout(play) -> None:
    play.set("extra_dive_boss_surf", None)
    play.set("extra_dive_boss_rect", None)
    play.set("extra_dive_target_x", 0)
    play.set("extra_dive_target_y", 0)
    play.set("extra_dive_phase", "")
    play.set("extra_dive_snap_timer", 0)
    play.set("extra_dive_suck_bubble_idx", -1)
    play.set("extra_dive_suck_sfx_played", False)


def _play_suck_sfx(play) -> None:
    if play.extra_dive_suck_sfx_played:
        return
    from game_runtime import RT

    sfx = RT.g().get("boss5_suck_sound")
    if sfx is not None:
        try:
            sfx.play(loops=DIVE_SUCK_SFX_LOOPS)
        except Exception:
            pass
    play.set("extra_dive_suck_sfx_played", True)


def _update_suck_bubbles(play) -> None:
    """吸い込み中に吹き出しを3段、等間隔で順番表示。"""
    from messages import MESSAGES
    from game_runtime import RT

    n = len(EXTRA_SUCK_BUBBLE_TRIGGERS)
    step = max(1, DIVE_DURATION_FRAMES // n)
    idx = min(n - 1, play.extra_dive_timer // step)
    if idx == play.extra_dive_suck_bubble_idx:
        return

    play.set("extra_dive_suck_bubble_idx", idx)
    key = EXTRA_SUCK_BUBBLE_TRIGGERS[idx]
    text = MESSAGES[key][0]
    # 前の台詞を割り込みで切り替える（吸い込み演出は約7秒で3段）
    RT.g()["_bubble"].show_text(text, priority=5 + idx)


def _begin_extra_dive(play, app, player, dead_img: pygame.Surface) -> None:
    from screen_modes import ENDING_EXTRA_DIVE

    _setup_battle_layout(play, player, dead_img)
    play.set("extra_run", True)
    play.set("extra_dive_phase", "snap")
    play.set("extra_dive_snap_timer", 0)
    play.set("extra_dive_timer", 0)
    play.set("extra_dive_done", False)
    play.set("extra_dive_suck_bubble_idx", -1)
    play.set("extra_dive_suck_sfx_played", False)
    play.set("boss5_bg_mode", True)
    clear_boss5_support()
    try:
        pygame.mixer.music.fadeout(800)
    except Exception:
        pass
    app.set_screen_mode(ENDING_EXTRA_DIVE)


def start_extra_dive_after_boss5_death(play, app, player, dead_img: pygame.Surface) -> None:
    play.set("b5_death_active", False)
    play.set("b5_death_from_surface", None)
    play.set("b5_death_dead_surface", None)
    play.set("b5_death_draw_rect", None)
    _begin_extra_dive(play, app, player, dead_img)


def start_ending_extra_dive(play, app) -> None:
    from game_runtime import RT

    g = RT.g()
    player = g["player"]
    dead_img = g["midboss5_images"].get("defeat") or g["midboss5_images"]["normal"]
    play.set("b5_clear_cinematic", False)
    play.set("b5_epilogue_phase", "")
    play.set("b5_epilogue_timer", 0)
    play.set("b5_epilogue_fade", 0)
    _begin_extra_dive(play, app, player, dead_img)


def go_to_difficulty_select(app, play, title_cheat) -> None:
    from audio import set_sfx_muted, stop_bgm
    from screen_modes import DIFFICULTY_SELECT

    set_sfx_muted(False)
    stop_bgm()
    title_cheat.reset_all()
    play.set("_ending_screen_sfx_played", False)
    play.set("_ending_sfx_timer", 0)
    play.set("extra_dive_timer", 0)
    play.set("extra_dive_done", False)
    play.set("ending_menu_choice", 0)
    _clear_extra_dive_layout(play)
    app.set_screen_mode(DIFFICULTY_SELECT)


def update_extra_dive(play) -> None:
    if play.extra_dive_done:
        return
    phase = play.extra_dive_phase
    if phase == "snap":
        play.set("extra_dive_snap_timer", play.extra_dive_snap_timer + 1)
        if play.extra_dive_snap_timer >= DIVE_SNAP_FRAMES:
            play.set("extra_dive_phase", "suck")
            play.set("extra_dive_timer", 0)
            play.set("extra_dive_suck_bubble_idx", -1)
            _play_suck_sfx(play)
    elif phase == "suck":
        play.set("extra_dive_timer", play.extra_dive_timer + 1)
        _update_suck_bubbles(play)
        if play.extra_dive_timer >= DIVE_DURATION_FRAMES:
            play.set("extra_dive_done", True)


def _blit_alpha(dst: pygame.Surface, src: pygame.Surface, pos: tuple[int, int], alpha: int) -> None:
    if alpha >= 255:
        dst.blit(src, pos)
        return
    if alpha <= 0:
        return
    temp = src.copy()
    temp.set_alpha(alpha)
    dst.blit(temp, pos)


def _draw_ship(
    surf: pygame.Surface,
    player_img: pygame.Surface,
    cx: int,
    cy: int,
    scale: float,
    angle_deg: float,
) -> None:
    base_w, base_h = player_img.get_size()
    pw = max(1, int(base_w * scale))
    ph = max(1, int(base_h * scale))
    ship = pygame.transform.smoothscale(player_img, (pw, ph))
    ship = pygame.transform.rotate(ship, angle_deg)
    ship_rect = ship.get_rect(center=(cx, cy))
    surf.blit(ship, ship_rect.topleft)


def _draw_battle_scene(
    surf: pygame.Surface,
    play,
    player_img: pygame.Surface,
    *,
    player_alpha: int = 255,
    suck_t: float | None = None,
) -> None:
    boss_surf = play.extra_dive_boss_surf
    boss_rect = play.extra_dive_boss_rect
    if boss_surf is not None and boss_rect is not None:
        surf.blit(boss_surf, boss_rect.topleft)

    start_x = play.extra_dive_player_x
    start_y = play.extra_dive_player_y
    if suck_t is None:
        _draw_ship(surf, player_img, start_x, start_y, DIVE_PLAYER_SCALE_START, 0.0)
        return

    px, py, scale, angle = _suck_motion(play, suck_t)
    if player_alpha < 255:
        base_w, base_h = player_img.get_size()
        pw = max(1, int(base_w * scale))
        ph = max(1, int(base_h * scale))
        ship = pygame.transform.smoothscale(player_img, (pw, ph))
        ship = pygame.transform.rotate(ship, angle)
        _blit_alpha(surf, ship, ship.get_rect(center=(px, py)).topleft, player_alpha)
    else:
        _draw_ship(surf, player_img, px, py, scale, angle)


def draw_extra_dive(
    play_screen: pygame.Surface,
    play,
    player_img: pygame.Surface,
    font,
    big_font,
) -> None:
    phase = play.extra_dive_phase

    if phase == "snap":
        t = play.extra_dive_snap_timer / max(1, DIVE_SNAP_FRAMES)
        if t >= 0.55:
            reveal = _smoothstep((t - 0.55) / 0.45)
            _draw_battle_scene(
                play_screen, play, player_img, player_alpha=int(255 * reveal)
            )
        if t < 0.45:
            fade = _smoothstep(t / 0.45)
            overlay_alpha = int(255 * fade)
        elif t < 0.55:
            overlay_alpha = 255
        else:
            fade = _smoothstep((t - 0.55) / 0.45)
            overlay_alpha = int(255 * (1.0 - fade))
        if overlay_alpha > 0:
            overlay = pygame.Surface(play_screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, overlay_alpha))
            play_screen.blit(overlay, (0, 0))
        return

    if phase == "suck":
        suck_t = min(1.0, play.extra_dive_timer / max(1, DIVE_DURATION_FRAMES))
        _draw_battle_scene(play_screen, play, player_img, suck_t=suck_t)


def draw_extra_dive_bubble(play_screen: pygame.Surface, play) -> None:
    """吸い込み中: 自機の現在位置に吹き出しを追従。"""
    if play.extra_dive_phase != "suck":
        return
    from game_runtime import RT

    raw_t = min(1.0, play.extra_dive_timer / max(1, DIVE_DURATION_FRAMES))
    px, py, _, _ = _suck_motion(play, raw_t)
    anchor = pygame.Rect(px, py - 24, 1, 1)
    RT.g()["_bubble"].update_and_draw(play_screen, anchor)


def draw_extra_dive_enter_prompt(
    full_screen: pygame.Surface, font, big_font, play
) -> None:
    if not play.extra_dive_done:
        return
    sw, sh = full_screen.get_size()
    hint = font.render("エクストラステージへ", True, (180, 185, 195))
    full_screen.blit(hint, hint.get_rect(center=(sw // 2, sh // 2 - 28)))
    if (pygame.time.get_ticks() // 480) % 2 == 0:
        _draw_blink_enter(full_screen, big_font, sw // 2, sh // 2 + 28)
