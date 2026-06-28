# game_config_ui.py — キー／パッド設定画面の定義

from __future__ import annotations

from config_manager import ConfigManager

CONFIG_KEY_ITEMS = [
    ("up", "MOVE UP"),
    ("down", "MOVE DOWN"),
    ("left", "MOVE LEFT"),
    ("right", "MOVE RIGHT"),
    ("shoot", "SHOT"),
    ("ems", "EMS"),
    ("pause", "PAUSE"),
    ("weapon_mode", "WEAPON (Laser/Normal)"),
]

CONFIG_PAD_ITEMS = [
    ("shoot", "SHOT BUTTON"),
    ("confirm", "CONFIRM BUTTON"),
    ("cancel", "CANCEL BUTTON"),
    ("ems", "EMS BUTTON"),
    ("pause", "PAUSE (Start)"),
    ("weapon_mode", "WEAPON MODE"),
]

_CONFIG_UI_NAMES = ("CONFIG_KEY_ITEMS", "CONFIG_PAD_ITEMS")


def create_config_screen_state() -> dict:
    return {"mode": "keyboard", "cursor": 0, "waiting": None}


def install_config_ui(namespace: dict, config_mgr: ConfigManager) -> None:
    namespace["config_mgr"] = config_mgr
    namespace["_c"] = config_mgr.get_controller()
    namespace["KEY_BINDINGS"] = config_mgr.get_all_key_bindings()
    namespace["_config"] = create_config_screen_state()
    for name in _CONFIG_UI_NAMES:
        namespace[name] = globals()[name]
