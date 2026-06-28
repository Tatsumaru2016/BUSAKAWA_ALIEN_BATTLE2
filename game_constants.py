# game_constants.py — プレイ／UI 用の固定パラメータ

from __future__ import annotations

GAME_TITLE = "BUSAKAWA ALIEN BATTLE2 [v1.0]"
SHOT_INTERVAL = 8  # 8f ≈ 7.5発/秒（60fps）
EMS_MAX = 3

_CONSTANT_NAMES = ("GAME_TITLE", "SHOT_INTERVAL", "EMS_MAX")


def install_game_constants(namespace: dict) -> None:
    for name in _CONSTANT_NAMES:
        namespace[name] = globals()[name]
