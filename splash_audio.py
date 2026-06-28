# splash_audio.py — 起動スプラッシュ用 SE（雷 → 電撃）

from __future__ import annotations

import os

import pygame

# 稲妻・電撃の2つともこのファイル（g:\GAME\Electric.wav）
SPLASH_ELECTRIC_WAV = r"g:\GAME\Electric.wav"


def _load_first_sound(candidates: tuple[str, ...]) -> pygame.mixer.Sound | None:
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                return pygame.mixer.Sound(path)
        except Exception:
            continue
    return None


def load_splash_electric_sfx(resolve_asset) -> pygame.mixer.Sound | None:
    import sys

    candidates: list[str] = []
    if sys.platform != "emscripten":
        candidates.append(SPLASH_ELECTRIC_WAV)
    candidates.extend(
        (
            resolve_asset("assets/splash_electric.ogg"),
            resolve_asset("assets/splash_electric.wav"),
        )
    )
    return _load_first_sound(tuple(candidates))


def load_thunder_sfx(resolve_asset) -> pygame.mixer.Sound | None:
    return load_splash_electric_sfx(resolve_asset)


def load_electric_shock_sfx(resolve_asset) -> pygame.mixer.Sound | None:
    return load_splash_electric_sfx(resolve_asset)


def play_thunder_then_shock(
    thunder: pygame.mixer.Sound | None,
    shock: pygame.mixer.Sound | None,
    *,
    thunder_loops: int = -1,
) -> tuple[pygame.mixer.Channel | None, pygame.mixer.Channel | None]:
    """雷SEを鳴らした直後に電撃SEを1回再生する（同一ファイルなら1回のみ）。"""
    if thunder is None and shock is None:
        return None, None
    if thunder is shock and thunder is not None:
        try:
            return thunder.play(loops=thunder_loops), None
        except Exception:
            return None, None

    thunder_ch = None
    shock_ch = None
    try:
        if thunder is not None:
            thunder_ch = thunder.play(loops=thunder_loops)
    except Exception:
        thunder_ch = None
    try:
        if shock is not None:
            shock_ch = shock.play()
    except Exception:
        shock_ch = None
    return thunder_ch, shock_ch


def stop_channels(*channels: pygame.mixer.Channel | None) -> None:
    for ch in channels:
        if ch is None:
            continue
        try:
            ch.stop()
        except Exception:
            pass
