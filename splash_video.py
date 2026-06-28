# splash_video.py — 起動スプラッシュ（MP4再生 + 雷SE）

from __future__ import annotations

import os

import pygame

from settings import FPS, SPLASH_VIDEO_POST_HOLD_SEC
from splash_audio import (
    load_electric_shock_sfx,
    load_thunder_sfx,
    play_thunder_then_shock,
    stop_channels,
)

def _import_cv2():
    """遅延 import（ビルド時の依存収集用。EXE には collect_all('cv2') で同梱）。"""
    try:
        import cv2 as _cv2

        return _cv2
    except ImportError:
        return None


class VideoSplash:
    """MP4をフルスクリーン再生。APIは GGameSplash と揃える。"""

    def __init__(self, resolve_asset, width: int, height: int, video_name: str = "splash_intro.mp4"):
        self.width = int(width)
        self.height = int(height)
        self.timer = 0
        self.finished = False
        self._failed = False
        self._hold = 0
        self._frame_interval = 2
        self._frame_surf: pygame.Surface | None = None
        self._cap = None
        self._thunder_sfx = load_thunder_sfx(resolve_asset)
        self._shock_sfx = load_electric_shock_sfx(resolve_asset)
        self._thunder_played = False
        self._thunder_channel = None
        self._shock_channel = None
        self._video_ended = False
        self._post_hold_timer = 0
        self._post_hold_frames = max(1, int(round(float(SPLASH_VIDEO_POST_HOLD_SEC) * FPS)))

        cv2 = _import_cv2()
        self._cv2 = cv2
        if cv2 is None:
            self._failed = True
            self.finished = True
            return

        video_path = self._resolve_video_path(resolve_asset, video_name)
        if video_path is None:
            self._failed = True
            self.finished = True
            return

        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            self._failed = True
            self.finished = True
            self._cap = None
            return

        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 24.0)
        if fps < 1.0:
            fps = 24.0
        self._frame_interval = max(1, int(round(60.0 / fps)))

        ok, frame = self._cap.read()
        if ok:
            self._frame_surf = self._bgr_to_surface(frame)
        else:
            self._failed = True
            self.finished = True
            self._release_cap()

    def _resolve_video_path(self, resolve_asset, video_name: str) -> str | None:
        candidates = [resolve_asset(f"assets/{video_name}")]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def _bgr_to_surface(self, frame) -> pygame.Surface:
        cv2 = self._cv2
        if cv2 is None:
            raise RuntimeError("cv2 not available")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if rgb.shape[1] != self.width or rgb.shape[0] != self.height:
            rgb = cv2.resize(
                rgb,
                (self.width, self.height),
                interpolation=cv2.INTER_LINEAR,
            )
        surf = pygame.image.frombuffer(rgb.tobytes(), (self.width, self.height), "RGB")
        return surf.convert()

    def _release_cap(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _stop_splash_audio(self) -> None:
        self._thunder_played = False
        stop_channels(self._thunder_channel, self._shock_channel)
        self._thunder_channel = None
        self._shock_channel = None

    def _sync_thunder_audio(self) -> None:
        if self._video_ended or self.finished:
            return
        if self._thunder_played:
            return
        if self._thunder_sfx is None and self._shock_sfx is None:
            return
        self._thunder_played = True
        self._thunder_channel, self._shock_channel = play_thunder_then_shock(
            self._thunder_sfx,
            self._shock_sfx,
            thunder_loops=-1,
        )

    def _on_video_end(self) -> None:
        """再生終了: キャプチャ解放・雷SE停止・最終フレームでホールドへ。"""
        self._video_ended = True
        self._release_cap()
        self._stop_splash_audio()

    def update(self) -> None:
        if self.finished:
            return

        self.timer += 1

        if self._video_ended:
            self._post_hold_timer += 1
            if self._post_hold_timer >= self._post_hold_frames:
                self.finished = True
            return

        if self._cap is None:
            return

        self._sync_thunder_audio()
        self._hold += 1
        if self._hold < self._frame_interval:
            return
        self._hold = 0

        ok, frame = self._cap.read()
        if not ok:
            self._on_video_end()
            return
        self._frame_surf = self._bgr_to_surface(frame)

    def stop_audio(self) -> None:
        self._stop_splash_audio()
        self.finished = True
        self._video_ended = True
        self._release_cap()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        if self._frame_surf is not None:
            surface.blit(self._frame_surf, (0, 0))
