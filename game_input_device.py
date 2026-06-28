# game_input_device.py — ゲームパッド接続・入力ヘルパの更新

from __future__ import annotations

import pygame

from game_input import install_input_to_namespace


def init_joystick() -> pygame.joystick.Joystick | None:
    pygame.joystick.init()
    if pygame.joystick.get_count() <= 0:
        return None
    stick = pygame.joystick.Joystick(0)
    stick.init()
    return stick


def refresh_input(namespace: dict, joystick, controller_map: dict) -> None:
    namespace["_joystick"] = joystick
    install_input_to_namespace(namespace, joystick, controller_map)


def handle_joystick_plug_event(
    event: pygame.event.Event,
    namespace: dict,
) -> None:
    """JOYDEVICEADDED / JOYDEVICEREMOVED を処理し、必要なら入力ヘルパを再構築。"""
    joystick = namespace.get("_joystick")
    controller_map = namespace["_c"]

    if event.type == pygame.JOYDEVICEADDED:
        if joystick is None:
            joystick = pygame.joystick.Joystick(event.device_index)
            joystick.init()
            refresh_input(namespace, joystick, controller_map)
    elif event.type == pygame.JOYDEVICEREMOVED:
        if joystick is not None and event.instance_id == joystick.get_instance_id():
            refresh_input(namespace, None, controller_map)
