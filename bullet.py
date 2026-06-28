# bullet.py

import pygame
import math

class Bullet:
    def __init__(self, x, y, image, damage=1, is_laser=False, speed=14, laser_variant="blue"):
        self.image = image
        self.is_laser = is_laser
        self.speed = speed
        self.damage = damage
        self.laser_variant = laser_variant  # "blue"=自機, "red"=ボス5など

        if self.is_laser:
            # ---- レーザー固有パラメータ ----
            self.vx = float(speed)   # 初期は右方向
            self.vy = 0.0
            self.angle = 0.0         # 描画用傾き（ラジアン）
            self.bounce_count = 0    # 壁バウンス回数（最大2回で消滅）
            self.laser_length = 120  # 描画・当たり判定の全長（ボス5赤レーザーは60）
            # 中心点を基準とした論理 rect（位置管理用）
            self.rect = pygame.Rect(x, y - 3, 6, 6)
            # 寿命（壁バウンス0～2回の間でも一定時間で消滅）
            self.life = 180          # 約3秒
        else:
            self.rect = self.image.get_rect(center=(x, y))
            self.custom_vy = 0   # 斜め弾の垂直速度
            self.lane_crawl = None   # "top" / "bottom": 上下端まで進み右へ這う
            self.lane_active = False

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self):
        if self.is_laser:
            # レーザーの位置移動は main.py 側で vx/vy を使って処理する
            # 寿命カウントのみここで行う
            self.life -= 1
        else:
            # 上下レーン弾の移動は main.py で一元管理
            if not self.lane_crawl:
                self.rect.x += self.speed

    # ------------------------------------------------------------------
    # DRAW  ― PNG 不使用、グラフィック命令のみ
    # ------------------------------------------------------------------
    def draw(self, screen):
        if self.is_laser:
            self._draw_laser(screen)
        else:
            screen.blit(self.image, self.rect)

    def _draw_laser(self, screen):
        """
        レーザーをグラフィック命令だけで描画する。
        移動方向（vx, vy）から angle を更新してから描く。
        """
        # 現在の速度ベクトルから描画角度を算出
        if abs(self.vx) + abs(self.vy) > 0.1:
            self.angle = math.atan2(self.vy, self.vx)

        cx = self.rect.centerx
        cy = self.rect.centery
        length = getattr(self, "laser_length", 120)
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        # ボス3など: 根元から先端へ伸びるビーム（中心対称にしない）
        if getattr(self, "beam_from_anchor", False):
            x1, y1 = int(cx), int(cy)
            x2 = int(cx + cos_a * length)
            y2 = int(cy + sin_a * length)
        else:
            half = length / 2
            x1 = int(cx - cos_a * half)
            y1 = int(cy - sin_a * half)
            x2 = int(cx + cos_a * half)
            y2 = int(cy + sin_a * half)

        # 残り寿命に応じてフェードアウト
        if getattr(self, "extra_beam_rifle", False):
            fade_start = 28
            alpha_ratio = 1.0 if self.life > fade_start else min(1.0, self.life / fade_start)
            a = max(0.92, alpha_ratio)
        else:
            alpha_ratio = min(1.0, self.life / 30.0)  # 最後の0.5秒でフェード
            a = alpha_ratio

        if self.laser_variant == "red":
            aura_col = (int(180 * a), 0, 0)
            main_col = (int(255 * a), int(60 * a), int(60 * a))
            core_col = (int(255 * a), int(180 * a), int(180 * a))
            flare_col = (int(255 * a), int(200 * a), int(200 * a))
            aura_w, main_w, core_w, flare_r = 7, 4, 2, 5
        elif self.laser_variant == "giant_orange":
            aura_col = (int(220 * a), int(90 * a), 0)
            main_col = (int(255 * a), int(170 * a), int(30 * a))
            core_col = (int(255 * a), int(255 * a), int(140 * a))
            flare_col = (int(255 * a), int(240 * a), int(100 * a))
            aura_w, main_w, core_w, flare_r = 18, 12, 6, 14
        elif self.laser_variant == "purple_thick":
            aura_col = (int(90 * a), 0, int(160 * a))
            main_col = (int(170 * a), int(50 * a), int(255 * a))
            core_col = (int(230 * a), int(160 * a), int(255 * a))
            flare_col = (int(255 * a), int(200 * a), int(255 * a))
            if getattr(self, "extra_beam_rifle", False):
                aura_w, main_w, core_w, flare_r = 26, 16, 7, 20
            else:
                aura_w, main_w, core_w, flare_r = 16, 10, 4, 12
        elif self.laser_variant == "purple_thin":
            aura_col = (int(70 * a), 0, int(120 * a))
            main_col = (int(150 * a), int(40 * a), int(230 * a))
            core_col = (int(210 * a), int(140 * a), int(255 * a))
            flare_col = (int(240 * a), int(180 * a), int(255 * a))
            aura_w, main_w, core_w, flare_r = 5, 3, 1, 4
        elif self.laser_variant == "purple_ground_crescent":
            self._draw_purple_ground_crescent(screen, x1, y1, cos_a, sin_a, length, a)
            return
        else:
            aura_col = (0, int(80 * a), int(200 * a))
            main_col = (int(80 * a), int(180 * a), int(255 * a))
            core_col = (int(200 * a), int(240 * a), int(255 * a))
            flare_col = (int(220 * a), int(245 * a), int(255 * a))
            aura_w, main_w, core_w, flare_r = 7, 4, 2, 5

        pygame.draw.line(screen, aura_col, (x1, y1), (x2, y2), aura_w)
        pygame.draw.line(screen, main_col, (x1, y1), (x2, y2), main_w)
        pygame.draw.line(screen, core_col, (x1, y1), (x2, y2), core_w)
        pygame.draw.circle(screen, flare_col, (x2, y2), flare_r)

    def _draw_purple_ground_crescent(
        self,
        screen,
        x1: int,
        y1: int,
        cos_a: float,
        sin_a: float,
        length: float,
        a: float,
    ) -> None:
        """地面を這う三日月型紫レーザー。"""
        n = max(12, int(length / 14))
        outer = []
        inner = []
        bulge = float(getattr(self, "crescent_bulge", 42.0))
        for i in range(n):
            t = i / max(1, n - 1)
            dist = length * t
            bx = x1 + cos_a * dist
            by = y1 + sin_a * dist
            hump = math.sin(t * math.pi) * bulge
            px = bx - sin_a * hump
            py = by + cos_a * hump
            outer.append((int(px), int(py)))
            inner.append((int(px), int(py + 6)))
        if len(outer) < 2:
            return
        aura = (int(80 * a), 0, int(140 * a))
        main = (int(160 * a), int(50 * a), int(240 * a))
        core = (int(220 * a), int(150 * a), int(255 * a))
        pygame.draw.lines(screen, aura, False, outer, 9)
        pygame.draw.lines(screen, main, False, outer, 5)
        pygame.draw.lines(screen, core, False, outer, 2)
        pygame.draw.lines(screen, (int(100 * a), 0, int(180 * a)), False, inner, 2)
        tip = outer[-1]
        pygame.draw.circle(screen, (int(255 * a), int(200 * a), int(255 * a)), tip, 6)

    # ------------------------------------------------------------------
    # COLLISION
    # ------------------------------------------------------------------
    def collide_with_rect(self, target_rect):
        """相手の Rect と接触しているか判定"""
        if not self.is_laser:
            return self.rect.colliderect(target_rect)

        # レーザーは線分サンプリングで判定
        cx = self.rect.centerx
        cy = self.rect.centery
        length = getattr(self, "laser_length", 120)
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        if getattr(self, "beam_from_anchor", False):
            x1, y1 = float(cx), float(cy)
            x2 = cx + cos_a * length
            y2 = cy + sin_a * length
        else:
            half = length / 2
            x1 = cx - cos_a * half
            y1 = cy - sin_a * half
            x2 = cx + cos_a * half
            y2 = cy + sin_a * half

        if self.laser_variant == "purple_ground_crescent":
            n = max(8, int(length / 16))
            for i in range(n):
                t = i / max(1, n - 1)
                dist = length * t
                bx = x1 + cos_a * dist
                by = y1 + sin_a * dist
                hump = math.sin(t * math.pi) * float(getattr(self, "crescent_bulge", 42.0))
                px = bx - sin_a * hump
                py = by + cos_a * hump
                if target_rect.collidepoint(int(px), int(py)):
                    return True
            return False

        samples = max(6, int(length / 10))
        for i in range(samples):
            t = i / (samples - 1)
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            if target_rect.collidepoint(px, py):
                return True
        return False
