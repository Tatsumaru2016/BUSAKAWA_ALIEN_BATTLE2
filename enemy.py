import pygame
import random
import math

from settings import is_enemy_ace_type


class Enemy:

    def __init__(self, images, x, y, enemy_type):

        if not images:
            raise ValueError("enemy images missing")
        enemy_type = int(enemy_type) % len(images)
        self.type = enemy_type
        self.image = images[enemy_type]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = random.randint(4, 7)
        self.hp = 1

        if enemy_type == 3:
            self.hp = 6

        # 発射タイミング分散（弾の塊防止）
        self.timer = random.randint(0, 59)
        self.shot_offset = random.randint(0, 59)
        self.base_y = y

        # variant: 0/1/2 をランダム割り当て
        self.variant = random.randint(0, 2)

        # ---- type0 固有: スラスト（速度変化） ----
        # variant0: 等速、variant1: 加速突入, variant2: 減速後加速
        self.thrust_phase = "in"   # "in" / "hold" / "burst"
        self.thrust_timer = 0
        self.thrust_speed = float(self.speed)

        # ---- 全タイプ共通: 上下ウォブル ----
        # タイプ・バリアントごとに振幅・周波数をばらつかせる
        self.wobble_amp   = random.uniform(30, 70)
        self.wobble_freq  = random.uniform(0.05, 0.13)
        self.wobble_phase = random.uniform(0, math.pi * 2)  # 初期位相をランダムに

        # ---- type1 固有: サイン波（振幅・周波数が variant 別） ----
        self._prev_y = y
        # variant0: 標準, variant1: 大振幅・遅い, variant2: 小振幅・速い
        if enemy_type == 1:
            if self.variant == 0:
                self.sin_amp = 110
                self.sin_freq = 0.09
            elif self.variant == 1:
                self.sin_amp = 170
                self.sin_freq = 0.055
            else:
                self.sin_amp = 65
                self.sin_freq = 0.17

        # ---- type2 固有: 接近停止（一定距離で止まりホーミング連発） ----
        self.approach_state = "move"  # "move" / "hover" / "retreat"
        self.hover_timer = 0
        self.hover_x = random.randint(480, 680)   # 停止目標X

        # ---- type3 固有: 突進フラグ ----
        self.charge = False
        self.charge_vx = 0.0
        self.charge_vy = 0.0
        self.charge_return = False  # 突進後に退場するか

        # type2 variant2: 停止→発射用
        self.freeze_timer = 0
        self.burst_ready = False

        # 全タイプ: 画面内に入るまで射撃控えめ（横STGの進入フェーズ）
        self.combat_ready = True
        self.entry_speed_mul = 1.0
        self.ace_leader = False
        self.special_leader = False
        self.max_hp = self.hp

        # ---- エース機（編隊リーダー・レガシー経路） ----
        if is_enemy_ace_type(enemy_type):
            self.ace_phase = "enter"
            self.ace_broadside_timer = 0
            self.sin_amp = 75
            self.sin_freq = 0.072
            self._prev_y = y

    # ==========================================================
    # UPDATE
    # ==========================================================
    def update(self):
        self.timer += 1

        if getattr(self, "grunt_behavior", None):
            try:
                from game_loop.resources import frame_core

                core = frame_core()
                from grunt_behavior import update_grunt_behavior

                update_grunt_behavior(self, core.width, core.height)
            except Exception:
                pass
            return

        # ---- TYPE 0: 直線型（スラスト変化） ----
        if self.type == 0:
            self._update_type0()
            return

        # ---- TYPE 1: サイン波型（振幅・周波数 variant別） ----
        if self.type == 1:
            self._update_type1()
            return

        # ---- TYPE 2: ホーミング型（接近停止） ----
        if self.type == 2:
            # variant2: 停止ギミック中は移動しない
            if self.variant == 2 and self.freeze_timer > 0:
                self.freeze_timer -= 1
                return
            self._update_type2()
            return

        # ---- TYPE 3: 重装甲型（突進 or 往復） ----
        if self.type == 3:
            self._update_type3()
            return

        # ---- TYPE 4: スイープ型（中振幅の蛇行直進） ----
        if self.type == 4:
            self._update_type4()
            return

        # ---- エース機体（進入→加速巡航→舷側砲撃） ----
        if is_enemy_ace_type(self.type):
            self._update_type5()
            return

    def _entry_speed(self) -> float:
        mul = float(getattr(self, "entry_speed_mul", 1.0))
        if getattr(self, "combat_ready", True):
            return float(self.speed)
        return max(1.5, float(self.speed) * mul)

    # ----------------------------------------------------------
    # type0: variant別スラスト + 上下ウォブル
    # ----------------------------------------------------------
    def _update_type0(self):
        # 上下ウォブル（全variant共通）
        wobble_y = int(math.sin(self.timer * self.wobble_freq + self.wobble_phase) * self.wobble_amp)
        target_y = self.base_y + wobble_y

        spd_mul = self._entry_speed() / max(1.0, self.thrust_speed)
        if self.variant == 0:
            # 等速
            self.rect.x -= int(self.thrust_speed * spd_mul)

        elif self.variant == 1:
            # 急加速突入: 遅く入って一定フレームで加速
            self.thrust_timer += 1
            if self.thrust_timer < 28:
                spd = self.thrust_speed * 0.4 * spd_mul
            else:
                spd = self.thrust_speed * 1.9
            self.rect.x -= int(spd)

        elif self.variant == 2:
            # 減速→停止→ダッシュ
            self.thrust_timer += 1
            if self.thrust_timer < 25:
                spd = self.thrust_speed * 1.0 * spd_mul
            elif self.thrust_timer < 55:
                spd = 0  # 一時停止
            else:
                spd = self.thrust_speed * 2.8  # 急ダッシュ
            self.rect.x -= int(spd)

        # Y座標をウォブルに向けて徐々に追従（急激な移動防止）
        diff_y = target_y - self.rect.y
        self.rect.y += int(diff_y * 0.12)

    # ----------------------------------------------------------
    # type1: variant別サイン波
    # ----------------------------------------------------------
    def _update_type1(self):
        self._prev_y = self.rect.y
        self.rect.x -= int(self._entry_speed())
        new_y = self.base_y + math.sin(self.timer * self.sin_freq) * self.sin_amp
        self.rect.y = int(new_y)

    # ----------------------------------------------------------
    # type2: 接近→hover（停止）→撤退 + 接近中上下ウォブル
    # ----------------------------------------------------------
    def _update_type2(self):
        if self.approach_state == "move":
            # 接近中: 上下ウォブル
            wobble_y = int(math.sin(self.timer * self.wobble_freq + self.wobble_phase) * self.wobble_amp * 0.7)
            target_y = self.base_y + wobble_y
            diff_y = target_y - self.rect.y
            self.rect.y += int(diff_y * 0.10)
            if self.rect.right > self.hover_x + 120:
                self.rect.x -= self.speed
            else:
                # 画面中央付近に到達したらhoverへ
                self.approach_state = "hover"
                self.hover_timer = random.randint(100, 160)  # 1.7〜2.7秒待機

        elif self.approach_state == "hover":
            # その場で上下に小揺れ（より大きく）
            self.rect.y = int(self.base_y + math.sin(self.timer * 0.16) * 32)
            self.hover_timer -= 1
            if self.hover_timer <= 0:
                self.approach_state = "retreat"

        elif self.approach_state == "retreat":
            # 右に退場（速め）
            self.rect.x += int(self.speed * 2.4)

    # ----------------------------------------------------------
    # type3: HP半減で突進、突進後退場 + 上下ウォブル
    # ----------------------------------------------------------
    def _update_type3(self):
        if self.charge:
            self.rect.x += int(self.charge_vx)
            self.rect.y += int(self.charge_vy)
            return

        # 通常移動 + ウォブル
        self.rect.x -= self.speed
        wobble_y = int(math.sin(self.timer * self.wobble_freq + self.wobble_phase) * self.wobble_amp * 0.85)
        target_y = self.base_y + wobble_y
        diff_y = target_y - self.rect.y
        self.rect.y += int(diff_y * 0.14)

        # variant0: HP半減で自機に体当たり突進
        if self.variant == 0 and not self.charge and self.hp <= 3:
            self.charge = True
            # 現在位置からプレイヤーへ
            from player import Player  # 循環import回避のためローカル
            # main.py 側でplayer参照を使うので、ここでは vx/vy=0 に設定
            # main.py の try_enemy_shoot 内で charge_vx/vy を設定する
            self.charge_vx = 0.0
            self.charge_vy = 0.0

    # サイン移動の現在の上下方向
    def sine_dir(self):
        return 1 if self.rect.y >= self._prev_y else -1

    # ----------------------------------------------------------
    # type4: 中振幅スイープ（5種目の見た目用・挙動は独立）
    # ----------------------------------------------------------
    def _update_type4(self):
        self._prev_y = self.rect.y
        self.rect.x -= int(self._entry_speed())
        if self.variant == 0:
            amp, freq = 95, 0.10
        elif self.variant == 1:
            amp, freq = 140, 0.075
        else:
            amp, freq = 60, 0.14
        self.rect.y = int(self.base_y + math.sin(self.timer * freq) * amp)

    # ----------------------------------------------------------
    # type5: エース — Gradius型の中央加速 + R-Type型舷側滞空
    # ----------------------------------------------------------
    def _update_type5(self):
        try:
            from game_loop.resources import frame_core

            width = int(frame_core().width)
        except Exception:
            width = 1280
        self._prev_y = self.rect.y
        phase = getattr(self, "ace_phase", "enter")

        if not getattr(self, "combat_ready", False) and self.rect.left < width - 200:
            self.combat_ready = True
            self.ace_phase = "cruise"

        if phase == "enter":
            self.rect.x -= int(max(2.0, self.speed * self.entry_speed_mul))
            self.rect.y = int(self.base_y + math.sin(self.timer * 0.06) * 28)
            if self.combat_ready:
                self.ace_phase = "cruise"
            return

        if phase == "cruise":
            cx_gate = int(width * 0.62)
            spd = float(self.speed)
            if self.rect.left < cx_gate:
                spd *= 1.35
            self.rect.x -= int(spd)
            self.rect.y = int(self.base_y + math.sin(self.timer * self.sin_freq) * self.sin_amp)
            if self.rect.left < int(width * 0.48):
                self.ace_phase = "broadside"
                self.ace_broadside_timer = 0
            return

        if phase == "broadside":
            self.ace_broadside_timer = int(getattr(self, "ace_broadside_timer", 0)) + 1
            drift = 0.45 if self.ace_broadside_timer < 90 else 0.85
            self.rect.x -= int(self.speed * drift)
            sway = math.sin(self.timer * 0.11) * 22
            self.rect.y = int(self.base_y + sway)
            if self.ace_broadside_timer > 150:
                self.ace_phase = "exit"
            return

        # exit: 左へ退場
        self.rect.x -= int(self.speed * 1.1)
        self.rect.y = int(self.base_y + math.sin(self.timer * 0.09) * 40)

    def draw(self, screen):
        if getattr(self, "grunt_behavior", None):
            from grunt_behavior import (
                draw_grunt_entry_fx,
                grunt_invuln_sprite_visible,
                grunt_special_sprite_visible,
            )

            draw_grunt_entry_fx(screen, self)
            if grunt_invuln_sprite_visible(self) and grunt_special_sprite_visible(self):
                screen.blit(self.image, self.rect)
            return
        screen.blit(self.image, self.rect)
