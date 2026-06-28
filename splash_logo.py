# splash_logo.py — 起動時メーカーロゴ "G GAME" アニメーション（刷新版）

import math
import random

import pygame

from splash_audio import load_electric_shock_sfx, load_thunder_sfx, play_thunder_then_shock, stop_channels


def _clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def _ease_out_cubic(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def _ease_in_cubic(t: float) -> float:
    t = _clamp01(t)
    return t * t * t


class GGameSplash:
    """左→右の稲妻、中央ロゴ表示、振動、2秒後終了。"""

    T_LIGHTNING = 16
    T_LOGO_ACTIVE = 72
    T_PRE_FADE_WAIT = 90  # 1.5sec
    T_FADE_OUT = 30
    T_POST_FADE_WAIT = 60  # 1sec (60fps)
    Y_OFFSET = 50

    def __init__(self, resolve_asset, width, height, font_path=None):
        self.width = width
        self.height = height
        self.timer = 0
        self.finished = False
        self.logo_shake = 0.0

        logo_path = resolve_asset("assets/splash_logo_game.png")
        try:
            logo_raw = pygame.image.load(logo_path).convert_alpha()
            # 指定画像サイズをそのまま使う（リサイズしない）
            self.logo_surf = logo_raw
        except Exception:
            font_path = font_path or resolve_asset("assets/NotoSansJP-Regular.ttf")
            f = pygame.font.Font(font_path, 120)
            self.logo_surf = f.render("G GAME", True, (240, 240, 240))

        lightning_path = resolve_asset("assets/splash_lightning.png")
        try:
            self.lightning_surf = pygame.image.load(lightning_path).convert_alpha()
        except Exception:
            self.lightning_surf = None

        self.logo_rect = self.logo_surf.get_rect(
            center=(width // 2, height // 2 + self.Y_OFFSET)
        )
        self._seed = random.Random(7713)
        self._thunder_played = False
        self._thunder_sfx = load_thunder_sfx(resolve_asset)
        self._shock_sfx = load_electric_shock_sfx(resolve_asset)
        self._thunder_channel = None
        self._shock_channel = None
        self._logo_outline = []
        self._logo_inner = []
        mask = pygame.mask.from_surface(self.logo_surf)
        outline = mask.outline()
        if outline:
            step = max(1, len(outline) // 220)
            self._logo_outline = outline[::step]
        if not self._logo_outline:
            r = self.logo_surf.get_rect()
            self._logo_outline = [
                (r.left, r.top),
                (r.right - 1, r.top),
                (r.right - 1, r.bottom - 1),
                (r.left, r.bottom - 1),
            ]
        w, h = self.logo_surf.get_size()
        stride = 6
        for y in range(0, h, stride):
            for x in range(0, w, stride):
                if mask.get_at((x, y)):
                    self._logo_inner.append((x, y))
        if len(self._logo_inner) < 8:
            self._logo_inner = [(w // 2, h // 2)]
    def _phase(self):
        t = self.timer
        if t < self.T_LIGHTNING:
            return "lightning", t / self.T_LIGHTNING
        t -= self.T_LIGHTNING
        if t < self.T_LOGO_ACTIVE:
            return "logo_active", t / self.T_LOGO_ACTIVE
        t -= self.T_LOGO_ACTIVE
        if t < self.T_PRE_FADE_WAIT:
            return "pre_fade_wait", t / self.T_PRE_FADE_WAIT
        t -= self.T_PRE_FADE_WAIT
        if t < self.T_FADE_OUT:
            return "fade_out", t / self.T_FADE_OUT
        t -= self.T_FADE_OUT
        if t < self.T_POST_FADE_WAIT:
            return "post_fade_wait", t / self.T_POST_FADE_WAIT
        return "done", 1.0

    def update(self):
        if self.finished:
            return
        self.timer += 1
        if self._phase()[0] == "done":
            self.finished = True

    def stop_audio(self) -> None:
        """SPLASHスキップ時などに雷音を確実停止する。"""
        self._thunder_played = False
        stop_channels(self._thunder_channel, self._shock_channel)
        self._thunder_channel = None
        self._shock_channel = None

    def _draw_lightning(self, surface, progress: float) -> None:
        # 初動の稲妻は上部中央から高速で画面中央へ落ちる
        cx = self.width // 2
        target_y = self.height // 2 + self.Y_OFFSET
        q = _ease_in_cubic(progress)
        if self.lightning_surf is not None:
            h = self.lightning_surf.get_height()
            y = int(-h + (target_y + 14) * q)
            x = cx - self.lightning_surf.get_width() // 2
            surface.blit(self.lightning_surf, (x, y))
            if progress > 0.78:
                a = int(180 * (progress - 0.78) / 0.22)
                flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                flash.fill((220, 245, 255, max(0, min(180, a))))
                surface.blit(flash, (0, 0))
            return

        # フォールバック（画像未配置時）
        line_col = (230, 245, 255)
        glow_col = (110, 210, 255)
        y_mid = int(target_y * q)
        amp = 38
        points = []
        y = y_mid - 280
        while y <= y_mid + 24:
            noise = self._seed.randint(-amp, amp)
            points.append((cx + noise, y))
            y += self._seed.randint(18, 30)
        if len(points) >= 2:
            pygame.draw.lines(surface, glow_col, False, points, 8)
            pygame.draw.lines(surface, line_col, False, points, 3)

    def _draw_logo(self, surface, alpha: int = 255, shake: float = 0.0) -> None:
        img = self.logo_surf
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        x = self.logo_rect.x + int(shake)
        y = self.logo_rect.y + int(-shake * 0.35)
        surface.blit(img, (x, y))

    def _draw_logo_edge_lightning(self, surface, progress: float) -> None:
        if len(self._logo_outline) < 2:
            return
        line_col = (240, 250, 255)
        glow_col = (85, 205, 255)
        n = len(self._logo_outline)
        span = max(10, n // 12)
        for k in range(3):
            idx = int((progress * n + k * (n / 3)) % n)
            seg = []
            for i in range(span):
                px, py = self._logo_outline[(idx + i) % n]
                seg.append((self.logo_rect.left + px, self.logo_rect.top + py))
            if len(seg) >= 2:
                pygame.draw.lines(surface, glow_col, False, seg, 5)
                pygame.draw.lines(surface, line_col, False, seg, 2)

    def _draw_logo_inner_lightning(self, surface, progress: float) -> None:
        if len(self._logo_inner) < 2:
            return
        bolts = 5 if progress < 0.55 else 3
        amp = 12
        for i in range(bolts):
            rng = random.Random(self.timer * 131 + i * 17)
            a = self._logo_inner[rng.randrange(len(self._logo_inner))]
            b = self._logo_inner[rng.randrange(len(self._logo_inner))]
            sx, sy = self.logo_rect.left + a[0], self.logo_rect.top + a[1]
            ex, ey = self.logo_rect.left + b[0], self.logo_rect.top + b[1]
            pts = []
            steps = 5
            for j in range(steps):
                t = j / (steps - 1)
                x = int(sx + (ex - sx) * t) + rng.randint(-amp, amp)
                y = int(sy + (ey - sy) * t) + rng.randint(-amp, amp)
                pts.append((x, y))
            pts[0] = (sx, sy)
            pts[-1] = (ex, ey)
            pygame.draw.lines(surface, (70, 180, 245), False, pts, 8)
            pygame.draw.lines(surface, (120, 220, 255), False, pts, 5)
            pygame.draw.lines(surface, (240, 250, 255), False, pts, 2)
            # 枝分かれ放電
            if len(pts) >= 3:
                bx, by = pts[rng.randint(1, len(pts) - 2)]
                ex2 = bx + rng.randint(-46, 46)
                ey2 = by + rng.randint(-46, 46)
                branch = [
                    (bx, by),
                    (int((bx + ex2) * 0.5) + rng.randint(-8, 8), int((by + ey2) * 0.5) + rng.randint(-8, 8)),
                    (ex2, ey2),
                ]
                pygame.draw.lines(surface, (90, 205, 255), False, branch, 4)
                pygame.draw.lines(surface, (245, 252, 255), False, branch, 1)

    def draw(self, surface):
        surface.fill((0, 0, 0))
        phase, p = self._phase()

        # 落雷〜ロゴ放電中だけ効果音を鳴らす
        if phase in ("lightning", "logo_active"):
            if not self._thunder_played:
                if self._thunder_sfx is not None or self._shock_sfx is not None:
                    self._thunder_played = True
                    self._thunder_channel, self._shock_channel = play_thunder_then_shock(
                        self._thunder_sfx,
                        self._shock_sfx,
                        thunder_loops=-1,
                    )
        else:
            if self._thunder_played:
                self._thunder_played = False
                stop_channels(self._thunder_channel, self._shock_channel)
                self._thunder_channel = None
                self._shock_channel = None

        if phase == "lightning":
            q = _ease_in_cubic(p)
            self._draw_lightning(surface, q)
            return

        if phase == "logo_active":
            # ロゴ表示と同時に振動＋縁＆内部放電
            shake_amp = 8.0 if p < 0.35 else 5.0
            self.logo_shake += 0.72
            shake = pygame.math.Vector2(1, 0).rotate(self.logo_shake * 57.3).x * shake_amp
            self._draw_logo(surface, 255, shake=shake)
            self._draw_logo_edge_lightning(surface, p)
            self._draw_logo_inner_lightning(surface, p)
            # 大放電フラッシュ
            flash = 0.0
            if p < 0.22:
                flash = 1.0 - (p / 0.22)
            elif (self.timer // 5) % 4 == 0:
                flash = 0.18
            if flash > 0.01:
                ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                ov.fill((190, 235, 255, int(130 * flash)))
                surface.blit(ov, (0, 0))
            # 画面全体シェイク（カメラ揺れ感）
            shake_x = int(math.sin(self.logo_shake * 2.2) * 4.0)
            shake_y = int(math.cos(self.logo_shake * 1.7) * 2.0)
            if shake_x != 0 or shake_y != 0:
                snap = surface.copy()
                surface.fill((0, 0, 0))
                surface.blit(snap, (shake_x, shake_y))
            return

        if phase == "pre_fade_wait":
            self._draw_logo(surface, 255, shake=0.0)
            return

        if phase == "fade_out":
            a = int(255 * (1.0 - _ease_out_cubic(p)))
            self._draw_logo(surface, a, shake=0.0)
            return

        if phase == "post_fade_wait":
            return

        # done
        return
