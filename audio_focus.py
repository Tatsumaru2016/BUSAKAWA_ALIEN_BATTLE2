# audio_focus.py — ウィンドウが背面のとき音を止め、前面復帰で再開

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from sfx_mute import set_focus_sfx_muted

if TYPE_CHECKING:
    from game_state import PlayState

_focus_audio_suppressed = False

def _event_types(*names: str) -> frozenset[int]:
    return frozenset(t for n in names if (t := getattr(pygame, n, None)) is not None)


_FOCUS_LOST = _event_types("WINDOWFOCUSLOST", "WINDOWMINIMIZED")
_FOCUS_GAINED = _event_types("WINDOWFOCUSGAINED", "WINDOWRESTORED")


def is_focus_audio_suppressed() -> bool:
    return _focus_audio_suppressed


def set_window_audio_active(active: bool, play: "PlayState | None" = None, state: int | None = None) -> None:
    """前面=True で BGM 再開・SFX はゲーム状態に応じて復帰。背面=False で両方停止。"""
    global _focus_audio_suppressed
    if active:
        if not _focus_audio_suppressed:
            return
        _focus_audio_suppressed = False
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass
        from audio import ensure_music_playing

        ensure_music_playing()
        set_focus_sfx_muted(False)
        if play is not None and state is not None:
            from game_flow import should_mute_sfx

            from sfx_mute import set_sfx_muted

            set_sfx_muted(should_mute_sfx(play, state))
        else:
            from sfx_mute import set_sfx_muted

            set_sfx_muted(False)
    else:
        if _focus_audio_suppressed:
            return
        _focus_audio_suppressed = True
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass
        set_focus_sfx_muted(True)


def handle_window_focus_event(event: pygame.event.Event, play: "PlayState | None" = None, state: int | None = None) -> None:
    et = event.type
    active_evt = getattr(pygame, "ACTIVEEVENT", None)
    if active_evt is not None and et == active_evt:
        set_window_audio_active(bool(getattr(event, "gain", 0)), play, state)
        return
    if et in _FOCUS_LOST:
        set_window_audio_active(False, play, state)
    elif et in _FOCUS_GAINED:
        set_window_audio_active(True, play, state)
