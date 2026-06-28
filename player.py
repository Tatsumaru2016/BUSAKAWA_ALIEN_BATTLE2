# player.py

import pygame
from bullet import Bullet  # bullet.py の共通 Bullet クラスを使用
from settings import (
    LASER_GAUGE_DRAIN_PER_SHOT,
    LASER_GAUGE_MAX,
    LASER_GAUGE_REFILL_PER_WEAPON,
    PLAY_TOP_MARGIN,
    PLAYER_MAX_WEAPON_LEVEL,
    PLAYER_NORMAL_BULLET_DAMAGE,
    PLAYER_NORMAL_BULLET_DAMAGE_EARLY,
    PLAYER_NORMAL_BULLET_DAMAGE_EARLY_MAX_LEVEL,
    SPEED_BOOST_SPEED,
    SPEED_GAUGE_DRAIN_PER_FRAME_MOVING,
    SPEED_GAUGE_MAX,
    SPEED_GAUGE_REFILL_PER_ITEM,
    SHOT_MUZZLE_FLASH_FRAMES,
    SHOT_VISUAL_HOLD_FRAMES,
)


class Player:
    def __init__(self, images, bullet_img, laser_img, shield_bar_img):
        self.images = images
        self.bullet_img = bullet_img
        self.laser_img = laser_img
        self.shield_bar_img = shield_bar_img

        self.image = self.images["normal"]
        self.rect = self.image.get_rect()

        self.rect.x = 120
        self.rect.y = 360 - (self.rect.height // 2)

        self.base_speed = 7
        self.speed = self.base_speed
        self.weapon_level = 1
        self.shield_meter = 0.0
        self.laser_gauge = 0.0
        self.speed_gauge = 0.0
        self.fire_mode = "normal"  # "laser" | "normal"（Lv5のみレーザー選択可）
        self._laser_low_warned = False

        self.shot_visual_timer = 0
        self.muzzle_flash_timer = 0
        self.recoil_x = 0

    def hitbox(self):
        """描画 rect（粗い範囲）。実際の被弾判定はスプライト不透明ピクセルのマスク。"""
        return self.rect

    def can_select_fire_mode(self) -> bool:
        return self.weapon_level >= PLAYER_MAX_WEAPON_LEVEL

    def uses_laser_fire(self) -> bool:
        """レーザー弾を撃つ条件（自然消費なし・使用時のみ減る）。"""
        return (
            self.can_select_fire_mode()
            and self.fire_mode == "laser"
            and float(self.laser_gauge) > 0.001
        )

    def _show_shot_sprite(self, firing: bool) -> bool:
        if firing:
            self.shot_visual_timer = SHOT_VISUAL_HOLD_FRAMES
        elif self.shot_visual_timer > 0:
            self.shot_visual_timer -= 1
        return self.shot_visual_timer > 0 and "shot" in self.images

    def _set_sprite_image(self, image: pygame.Surface) -> None:
        center = self.rect.center
        self.image = image
        self.rect = self.image.get_rect(center=center)

    def _resolve_image(self, firing: bool, up, down, left, right) -> None:
        if up and "up" in self.images:
            self._set_sprite_image(self.images["up"])
        elif down and "down" in self.images:
            self._set_sprite_image(self.images["down"])
        elif left and "left" in self.images:
            self._set_sprite_image(self.images["left"])
        elif right and "right" in self.images:
            self._set_sprite_image(self.images["right"])
        elif self._show_shot_sprite(firing):
            self._set_sprite_image(self.images["shot"])
        else:
            self._set_sprite_image(self.images["normal"])

    def apply_fire_feedback(self) -> None:
        self.muzzle_flash_timer = SHOT_MUZZLE_FLASH_FRAMES
        self.recoil_x = -2
        self.shot_visual_timer = SHOT_VISUAL_HOLD_FRAMES
        if "shot" in self.images:
            self._set_sprite_image(self.images["shot"])

    def tick_visual_feedback(self) -> None:
        if self.muzzle_flash_timer > 0:
            self.muzzle_flash_timer -= 1
        if self.recoil_x < 0:
            self.recoil_x += 1

    def update(
        self,
        keys,
        screen_width,
        screen_height,
        joy_funcs=None,
        key_bindings=None,
        *,
        firing=False,
    ):
        jf = joy_funcs or {}
        kb = key_bindings or {
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
        }

        up = keys[kb.get("up", pygame.K_UP)] or jf.get("up", lambda: False)()
        down = keys[kb.get("down", pygame.K_DOWN)] or jf.get("down", lambda: False)()
        left = keys[kb.get("left", pygame.K_LEFT)] or jf.get("left", lambda: False)()
        right = keys[kb.get("right", pygame.K_RIGHT)] or jf.get("right", lambda: False)()
        moving = bool(up or down or left or right)

        if float(self.speed_gauge) > 0.001:
            self.speed = int(self.base_speed) + int(SPEED_BOOST_SPEED)
            if moving:
                self.speed_gauge = max(
                    0.0, float(self.speed_gauge) - float(SPEED_GAUGE_DRAIN_PER_FRAME_MOVING)
                )
        else:
            self.speed_gauge = 0.0
            self.speed = int(self.base_speed)

        if up:
            self.rect.y -= self.speed
        elif down:
            self.rect.y += self.speed

        if left:
            self.rect.x -= self.speed
        elif right:
            self.rect.x += self.speed

        self._resolve_image(firing, up, down, left, right)
        self.tick_visual_feedback()

        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > screen_width:
            self.rect.right = screen_width
        if self.rect.top < PLAY_TOP_MARGIN:
            self.rect.top = PLAY_TOP_MARGIN
        if self.rect.bottom > screen_height - 10:
            self.rect.bottom = screen_height - 10

    def _draw_muzzle_flash(self, screen: pygame.Surface) -> None:
        if self.muzzle_flash_timer <= 0:
            return
        t = self.muzzle_flash_timer / max(1, SHOT_MUZZLE_FLASH_FRAMES)
        alpha = int(90 + 70 * t)
        mx = self.rect.right - 2
        my = self.rect.centery
        w, h = 22, 10
        flash = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(flash, (255, 200, 120, alpha), (0, 1, w - 2, h - 2))
        pygame.draw.ellipse(
            flash, (255, 248, 220, min(200, alpha + 50)), (5, 3, 10, 4)
        )
        screen.blit(flash, (mx, my - h // 2))

    def draw(self, screen):
        draw_x = self.rect.x + self.recoil_x
        screen.blit(self.image, (draw_x, self.rect.y))
        self._draw_muzzle_flash(screen)

    def _spawn_level4_bullets(self, muzzle_x: int, cy: int) -> list:
        dmg = self._normal_bullet_damage()
        spawned = []
        b_center = Bullet(muzzle_x, cy, self.bullet_img, damage=dmg)
        b_up = Bullet(muzzle_x, cy - 10, self.bullet_img, damage=dmg)
        b_up.custom_vy = -4
        b_down = Bullet(muzzle_x, cy + 10, self.bullet_img, damage=dmg)
        b_down.custom_vy = 4
        spawned.extend([b_center, b_up, b_down])

        lane_up = Bullet(muzzle_x, cy, self.bullet_img, damage=dmg)
        lane_up.lane_crawl = "top"
        lane_up.custom_vy = -7
        lane_down = Bullet(muzzle_x, cy, self.bullet_img, damage=dmg)
        lane_down.lane_crawl = "bottom"
        lane_down.custom_vy = 7
        spawned.extend([lane_up, lane_down])
        return spawned

    def _spawn_laser_bullets(self, muzzle_x: int, cy: int) -> list:
        spawned = []
        laser_spd = 16.0
        diag = laser_spd * 0.70710678
        for vx, vy in ((laser_spd, 0.0), (diag, -diag), (diag, diag)):
            laser = Bullet(
                muzzle_x,
                cy,
                self.laser_img,
                damage=1,
                is_laser=True,
                laser_variant="blue",
                speed=laser_spd,
            )
            laser.vx = vx
            laser.vy = vy
            spawned.append(laser)
        return spawned

    def _normal_bullet_damage(self) -> int:
        wl = int(self.weapon_level)
        if wl <= PLAYER_NORMAL_BULLET_DAMAGE_EARLY_MAX_LEVEL:
            return PLAYER_NORMAL_BULLET_DAMAGE_EARLY
        return PLAYER_NORMAL_BULLET_DAMAGE

    def shoot(self):
        """武器レベルと fire_mode に応じた弾を発射する。"""
        spawned_bullets = []
        cy = self.rect.centery
        muzzle_x = self.rect.right - 8

        dmg = self._normal_bullet_damage()
        if self.weapon_level == 1:
            spawned_bullets.append(Bullet(muzzle_x, cy, self.bullet_img, damage=dmg))

        elif self.weapon_level == 2:
            spawned_bullets.append(Bullet(muzzle_x, cy - 12, self.bullet_img, damage=dmg))
            spawned_bullets.append(Bullet(muzzle_x, cy + 12, self.bullet_img, damage=dmg))

        elif self.weapon_level == 3:
            b_center = Bullet(muzzle_x, cy, self.bullet_img, damage=dmg)
            b_up = Bullet(muzzle_x, cy - 10, self.bullet_img, damage=dmg)
            b_up.custom_vy = -2
            b_down = Bullet(muzzle_x, cy + 10, self.bullet_img, damage=dmg)
            b_down.custom_vy = 2
            spawned_bullets.extend([b_center, b_up, b_down])

        elif self.weapon_level == 4:
            spawned_bullets.extend(self._spawn_level4_bullets(muzzle_x, cy))

        elif self.weapon_level >= 5:
            if self.uses_laser_fire():
                spawned_bullets.extend(self._spawn_laser_bullets(muzzle_x, cy))
            else:
                spawned_bullets.extend(self._spawn_level4_bullets(muzzle_x, cy))

        return spawned_bullets

    def refill_laser_gauge(self, amount: float | None = None) -> None:
        amt = float(LASER_GAUGE_REFILL_PER_WEAPON if amount is None else amount)
        self.laser_gauge = min(float(LASER_GAUGE_MAX), float(self.laser_gauge) + amt)
        if self.laser_gauge > float(LASER_GAUGE_MAX) * 0.5:
            self._laser_low_warned = False

    def drain_laser_gauge_for_shot(self) -> None:
        self.laser_gauge = max(0.0, float(self.laser_gauge) - float(LASER_GAUGE_DRAIN_PER_SHOT))

    def on_unlock_laser(self) -> None:
        self.laser_gauge = float(LASER_GAUGE_MAX)
        self.fire_mode = "laser"
        self._laser_low_warned = False

    def refill_speed_gauge(self, amount: float | None = None) -> None:
        amt = float(SPEED_GAUGE_REFILL_PER_ITEM if amount is None else amount)
        self.speed_gauge = min(float(SPEED_GAUGE_MAX), float(self.speed_gauge) + amt)

    def apply_special_kill_bonus(self) -> None:
        """特別機撃破: 無敵5秒・レーザー/スピード/シールド全快。"""
        from settings import PLAYER_SPECIAL_KILL_INVINCIBLE_FRAMES

        self.invincible_timer = int(PLAYER_SPECIAL_KILL_INVINCIBLE_FRAMES)
        self.laser_gauge = float(LASER_GAUGE_MAX)
        self.speed_gauge = float(SPEED_GAUGE_MAX)
        self.shield_meter = 1.0
        self._laser_low_warned = False
