# screen_modes.py — 画面モード定数（main 専用グローバルから分離）

from __future__ import annotations

SPLASH = -4
NOTICE = -1
NEW_SCREEN = -2
NEW_SCREEN2 = -3
TITLE = 0
DIFFICULTY_SELECT = 4
CONFIG = 5
PLAY = 1
GAMEOVER = 2
ENDING = 3
# エクストラステージ用
ENDING_EXTRA_PROMPT = 6
EXTRA_PLAY = 7
ENDING_EXTRA_DIVE = 8

_SCREEN_MODE_NAMES = (
    "SPLASH",
    "NOTICE",
    "NEW_SCREEN",
    "NEW_SCREEN2",
    "TITLE",
    "DIFFICULTY_SELECT",
    "CONFIG",
    "PLAY",
    "GAMEOVER",
    "ENDING",
    "ENDING_EXTRA_PROMPT",
    "EXTRA_PLAY",
    "ENDING_EXTRA_DIVE",
)


def install_screen_modes(namespace: dict) -> None:
    """RT.g() 互換のため従来どおり namespace に画面定数を展開する。"""
    for name in _SCREEN_MODE_NAMES:
        namespace[name] = globals()[name]
