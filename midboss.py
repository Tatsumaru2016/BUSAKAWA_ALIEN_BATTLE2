# midboss.py

import pygame
import random
from settings import BOSS_MID_BODY_HIT_INSET, HEIGHT, WIDTH

def _inset_rect(rect, ratio_x, ratio_y):
    mx = int(rect.width * ratio_x)
    my = int(rect.height * ratio_y)
    return rect.inflate(-mx * 2, -my * 2)


class MidBoss:
    def __init__(self, boss_type, image):
        self.boss_type = boss_type
        self.image = image

        self.rect = self.image.get_rect(center=(1500, 360))

        if boss_type == 1:
            self.max_hp = 120
            self.hp = 120
        elif boss_type == 2:
            self.max_hp = 180
            self.hp = 180
        else:
            self.max_hp = 260
            self.hp = 260

        self.speed = 2
        self.move_dir = 1
        self.shot_timer = 0
        self.vertical_speed = random.uniform(2.5, 4.0)

    def update(self):
        # ボス4/5/6(エクストラ)は専用ロジックで位置管理
        if self.boss_type in (4, 5, 6):
            return
        if self.rect.centerx > 980:
            self.rect.x -= self.speed
        else:
            self.rect.y += self.move_dir * self.vertical_speed

            if self.rect.top <= 40:
                self.move_dir = 1
            elif self.rect.bottom >= 680:
                self.move_dir = -1

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def bullet_hit_rect(self, screen_width=WIDTH):
        """自機弾が当たる領域（ボス4・5は画面内の見えている壁全体）。"""
        if self.boss_type in (4, 5, 6):
            return pygame.Rect(
                self.rect.left,
                self.rect.top,
                screen_width - self.rect.left,
                self.rect.height,
            )
        return self.rect

    def body_hit_rect(self, screen_width=WIDTH):
        """自機の体当たりが当たる領域。"""
        if self.boss_type == 4:
            return self.bullet_hit_rect(screen_width)
        if self.boss_type in (5, 6):
            return _inset_rect(
                self.rect,
                BOSS_MID_BODY_HIT_INSET,
                BOSS_MID_BODY_HIT_INSET,
            )
        return _inset_rect(
            self.rect,
            BOSS_MID_BODY_HIT_INSET,
            BOSS_MID_BODY_HIT_INSET,
        )

