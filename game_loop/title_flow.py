# game_loop/title_flow.py — タイトルからプレイ開始・チート入力

from __future__ import annotations

import pygame

from audio import BGM_NORMAL, play_bgm, set_sfx_muted
from game_loop.resources import frame_core, frame_core_with_app, title_flow_resources
from game_runtime import RT
from extra_stage import begin_extra_stage
from game_constants import GAME_TITLE
from screen_modes import PLAY, TITLE
from title_cheat import TitleCheat, cardinal_from_bools


def title_cheat_dir_from_key(key) -> str | None:
    res = title_flow_resources()
    arrow_map = {
        pygame.K_UP: "up",
        pygame.K_DOWN: "down",
        pygame.K_LEFT: "left",
        pygame.K_RIGHT: "right",
    }
    if key in arrow_map:
        return arrow_map[key]
    bind_map = {
        res.keys.get("up"): "up",
        res.keys.get("down"): "down",
        res.keys.get("left"): "left",
        res.keys.get("right"): "right",
    }
    return bind_map.get(key)


def _title_cheat_hat_xy() -> tuple[int, int]:
    """十字キー（ハット）の生値。スティックと併用する。"""
    joystick = RT.g().get("_joystick")
    if joystick is None or joystick.get_numhats() <= 0:
        return (0, 0)
    try:
        return joystick.get_hat(0)
    except Exception:
        return (0, 0)


def poll_title_cheat_controller() -> None:
    """タイトル画面: スティック・十字ボタン（ハット）で隠しコマンドを検出。"""
    g = RT.g()
    if frame_core().state != TITLE:
        g["_title_cheat_ctrl_prev"] = None
        return
    res = title_flow_resources()
    hx, hy = _title_cheat_hat_xy()
    cur = cardinal_from_bools(
        res.joy_move_up() or hy > 0,
        res.joy_move_down() or hy < 0,
        res.joy_move_left() or hx < 0,
        res.joy_move_right() or hx > 0,
    )
    prev = g.get("_title_cheat_ctrl_prev")
    title_cheat = res.title_cheat
    if cur != prev:
        if cur is not None and title_cheat.feed(cur):
            res.title_cheat_sound.play()
        elif cur is None:
            title_cheat.release_direction()
        g["_title_cheat_ctrl_prev"] = cur


def poll_title_cheat_stick() -> None:
    """後方互換エイリアス。"""
    poll_title_cheat_controller()


def start_game_from_title(reset_game_fn) -> None:
    """reset_game_fn: reset_game（デバッグ設定込み）。"""
    set_sfx_muted(False)
    reset_game_fn()
    core = frame_core()
    session = frame_core_with_app()
    res = title_flow_resources()
    if res.title_cheat.armed:
        TitleCheat.apply_to_player(core.player)
    res.title_cheat.clear_armed()
    res.title_cheat.reset_sequence()
    res.launch_sound.play()
    if getattr(core.play, "_debug_pending_extra", False):
        core.play.set("_debug_pending_extra", False)
        begin_extra_stage(session.play, session.app)
        pygame.display.set_caption(f"{GAME_TITLE}  [DEBUG: EXTRA]")
        return
    if not core.play.boss_warning:
        play_bgm(BGM_NORMAL)
    session.app.set_screen_mode(PLAY)
