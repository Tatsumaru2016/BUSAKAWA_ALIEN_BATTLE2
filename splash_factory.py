# splash_factory.py — 起動スプラッシュの切替（video / logo）

from __future__ import annotations

from settings import SPLASH_MODE, SPLASH_VIDEO_FILE


def create_splash(resolve_asset, play_w: int, play_h: int, *, font_path=None, screen_w: int, screen_h: int):
    """SPLASH_MODE に応じて VideoSplash または GGameSplash を返す。"""
    from platform_web import is_web

    mode = "logo" if is_web() else str(SPLASH_MODE).strip().lower()
    if mode == "video":
        try:
            from splash_video import VideoSplash

            splash = VideoSplash(resolve_asset, screen_w, screen_h, SPLASH_VIDEO_FILE)
            if not getattr(splash, "_failed", False):
                return splash
        except Exception:
            pass

    from splash_logo import GGameSplash

    return GGameSplash(resolve_asset, play_w, play_h, font_path=font_path)
