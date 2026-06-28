# game_input.py — キーボード／ゲームパッド入力ヘルパ

from __future__ import annotations

import pygame


def joy_button(joystick, btn_id: int) -> bool:
    if joystick is None:
        return False
    try:
        return joystick.get_button(btn_id)
    except Exception:
        return False


def joy_axis(joystick, axis_id: int) -> float:
    if joystick is None:
        return 0.0
    try:
        return joystick.get_axis(axis_id)
    except Exception:
        return 0.0


def joy_hat(joystick) -> tuple:
    if joystick is None or joystick.get_numhats() == 0:
        return (0, 0)
    try:
        return joystick.get_hat(0)
    except Exception:
        return (0, 0)


def make_joy_helpers(joystick, controller_map: dict):
    """main の joy_* 互換関数群を生成。"""

    def _btn(btn_id: int) -> bool:
        return joy_button(joystick, btn_id)

    def _axis(axis_id: int) -> float:
        return joy_axis(joystick, axis_id)

    def _hat() -> tuple:
        return joy_hat(joystick)

    c = controller_map
    dz = c["deadzone"]

    def joy_shoot() -> bool:
        return _btn(c["shoot"])

    def joy_confirm() -> bool:
        return _btn(c["confirm"])

    def joy_move_left() -> bool:
        return _axis(c["axis_x"]) < -dz or _hat()[0] < 0

    def joy_move_right() -> bool:
        return _axis(c["axis_x"]) > dz or _hat()[0] > 0

    def joy_move_up() -> bool:
        return _axis(c["axis_y"]) < -dz or _hat()[1] > 0

    def joy_move_down() -> bool:
        return _axis(c["axis_y"]) > dz or _hat()[1] < 0

    def joy_ems() -> bool:
        return _btn(c.get("ems", 3))

    def joy_pause() -> bool:
        return _btn(c.get("pause", 7))

    return {
        "joy_shoot": joy_shoot,
        "joy_confirm": joy_confirm,
        "joy_move_left": joy_move_left,
        "joy_move_right": joy_move_right,
        "joy_move_up": joy_move_up,
        "joy_move_down": joy_move_down,
        "joy_ems": joy_ems,
        "joy_pause": joy_pause,
    }


def install_input_to_namespace(namespace: dict, joystick, controller_map: dict) -> None:
    namespace["_joystick"] = joystick
    namespace.update(make_joy_helpers(joystick, controller_map))
