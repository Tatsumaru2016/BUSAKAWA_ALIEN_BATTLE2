# sfx_mute.py — 効果音ミュート（audio / assets_loader の循環 import 回避）

import pygame

_sfx_muted_game = False
_focus_muted = False


def is_sfx_muted() -> bool:
    return _sfx_muted_game or _focus_muted


def _stop_sfx_channels_if_muted() -> None:
    if is_sfx_muted():
        try:
            pygame.mixer.stop()
        except Exception:
            pass


def set_sfx_muted(muted: bool) -> None:
    """演出用 SFX ミュート（GO など）。BGM は audio_focus / mixer.music。"""
    global _sfx_muted_game
    _sfx_muted_game = muted
    _stop_sfx_channels_if_muted()


def set_focus_sfx_muted(muted: bool) -> None:
    """ウィンドウ背面時の SFX ミュート（ゲーム用フラグとは独立）。"""
    global _focus_muted
    _focus_muted = muted
    _stop_sfx_channels_if_muted()
