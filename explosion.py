# explosion.py

import pygame
import random

_GRUNT_EXPLOSION_DURATION = 30
_GRUNT_EXPLOSION_GROW = 10
_GRUNT_SCALE_MIN = 0.05
_GRUNT_SCALE_PEAK = 1.14
_GRUNT_HOLD_FRAMES = 6
_GRUNT_FLASH_FRAMES = 7


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 2


class GruntExplosion:
    """雑魚撃破: スプライトを中心から拡大し、最大原寸でフェードアウト。"""

    def __init__(self, x, y, base_img):
        self.x = float(x)
        self.y = float(y)
        self.base_img = base_img
        self.frame = 0
        self.duration = _GRUNT_EXPLOSION_DURATION
        self.grow_frames = _GRUNT_EXPLOSION_GROW
        self.hold_frames = _GRUNT_HOLD_FRAMES
        self._cached_scale = -1.0
        self._scaled = None

    def _current_scale(self) -> float:
        if self.frame < self.grow_frames:
            t = self.frame / max(1, self.grow_frames)
            return _GRUNT_SCALE_MIN + (_GRUNT_SCALE_PEAK - _GRUNT_SCALE_MIN) * _ease_out_quad(
                t
            )
        hold_end = self.grow_frames + self.hold_frames
        if self.frame < hold_end:
            return _GRUNT_SCALE_PEAK
        fade_len = max(1, self.duration - hold_end)
        t = (self.frame - hold_end) / fade_len
        return _GRUNT_SCALE_PEAK + (1.0 - _GRUNT_SCALE_PEAK) * min(1.0, t)

    def _current_alpha(self) -> int:
        fade_start = self.grow_frames + self.hold_frames
        if self.frame < fade_start:
            return 255
        if self.frame >= self.duration:
            return 0
        t = (self.frame - fade_start) / (self.duration - fade_start)
        return int(255 * (1.0 - t ** 1.35))

    def _scaled_surface(self):
        scale = self._current_scale()
        if scale != self._cached_scale or self._scaled is None:
            bw, bh = self.base_img.get_size()
            w = max(1, int(bw * scale))
            h = max(1, int(bh * scale))
            self._scaled = pygame.transform.smoothscale(self.base_img, (w, h))
            self._cached_scale = scale
        return self._scaled

    def update(self):
        self.frame += 1

    def draw(self, screen):
        alpha = self._current_alpha()
        if alpha <= 0:
            return
        center = (int(self.x), int(self.y))
        if self.frame < _GRUNT_FLASH_FRAMES:
            flash_a = int(90 * (1.0 - self.frame / _GRUNT_FLASH_FRAMES))
            if flash_a > 0:
                bw, bh = self.base_img.get_size()
                scale = self._current_scale() * 1.18
                fw = max(1, int(bw * scale))
                fh = max(1, int(bh * scale))
                glow = pygame.transform.smoothscale(self.base_img, (fw, fh))
                glow = glow.copy()
                glow.fill((255, 240, 200), special_flags=pygame.BLEND_RGBA_MULT)
                glow.set_alpha(flash_a)
                screen.blit(
                    glow,
                    glow.get_rect(center=center),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )
        surf = self._scaled_surface()
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        screen.blit(surf, surf.get_rect(center=center))

    def dead(self):
        return self.frame >= self.duration


class MeteorZakoExplosion:
    """explosion_zako スプライトを短時間表示。"""

    damages_player = False

    def __init__(self, x, y, base_img):
        self.x = float(x)
        self.y = float(y)
        self.base_img = base_img
        self.frame = 0
        self.duration = 28
        self.grow_frames = 10

    def _scale(self) -> float:
        t = self.frame / max(1, self.grow_frames)
        return 0.35 + 0.65 * _ease_out_quad(min(1.0, t))

    def _alpha(self) -> int:
        if self.frame < self.grow_frames:
            return 255
        fade = (self.frame - self.grow_frames) / max(
            1, self.duration - self.grow_frames
        )
        return int(255 * (1.0 - min(1.0, fade)))

    def display_surface_and_rect(self):
        """描画と同じスケール・位置のスプライト（当たり判定用）。"""
        alpha = self._alpha()
        if alpha <= 0:
            return None
        bw, bh = self.base_img.get_size()
        scale = self._scale()
        surf = pygame.transform.smoothscale(
            self.base_img,
            (max(1, int(bw * scale)), max(1, int(bh * scale))),
        )
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        rect = surf.get_rect(center=(int(self.x), int(self.y)))
        return surf, rect

    def update(self):
        self.frame += 1

    def draw(self, screen):
        pair = self.display_surface_and_rect()
        if pair is None:
            return
        surf, rect = pair
        screen.blit(surf, rect)

    def dead(self):
        return self.frame >= self.duration


class ExtraStrikerBombExplosion(MeteorZakoExplosion):
    """エクストラ爆弾落とし: zako爆発スプライト＋プレイヤー当たり判定。"""

    damages_player = True

    def __init__(self, x, y, base_img, *, scale_mul: float = 1.0):
        super().__init__(x, y, base_img)
        self.scale_mul = max(0.5, float(scale_mul))

    def _scale(self) -> float:
        return super()._scale() * self.scale_mul


class Explosion:

    def __init__(self, x, y, big=False):

        self.particles = []

        count = 80 if big else 10

        for i in range(count):

            self.particles.append({

                "x": x,
                "y": y,

                "vx": random.uniform(-8, 8),
                "vy": random.uniform(-8, 8),

                "life": random.randint(20, 50),

                "size": random.randint(2, 5)

            })

    # ==================================
    # UPDATE
    # ==================================

    def update(self):

        for p in self.particles:

            p["x"] += p["vx"]
            p["y"] += p["vy"]

            p["life"] -= 1

    # ==================================
    # DRAW
    # ==================================

    def draw(self, screen):

        for p in self.particles:

            if p["life"] > 0:

                pygame.draw.circle(

                    screen,

                    (255, 180, 50),

                    (int(p["x"]), int(p["y"])),

                    p["size"]

                )

    # ==================================
    # DEAD
    # ==================================

    def dead(self):

        for p in self.particles:

            if p["life"] > 0:

                return False

        return True
