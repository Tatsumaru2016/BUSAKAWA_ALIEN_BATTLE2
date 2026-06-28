"""Boss attacks (Phase 3)."""

import math
import random

import pygame

from game_runtime import RT
from enemy_bullets import (
    spawn_enemy_bullet,
    spawn_b1_ground_tentacle_wave,
    b1_ground_tentacle_count,
    b1_ground_tentacle_retract_all,
    spawn_boss2_fish_swarm,
    spawn_boss3_giant_laser,
    spawn_boss5_red_laser,
    spawn_b1_diagonal_ripple_alternate,
)
from meteors import spawn_boss5_meteor
from combat import apply_player_hit
from explosion import Explosion
from powerup import PowerItem


def g():
    return RT.g()


# ボス1本体のシアン系（弾・エフェクトと揃える）
B1_GROUND_TENTACLE_COLORS = {
    "outer": (30, 140, 210),
    "inner": (100, 220, 255),
    "base": (70, 200, 255),
    "tip": (210, 255, 255),
}


def boss1_ground_tentacle_active() -> bool:
    """地面触手（b1_ground_tentacle）が画面上に残っている間 True。"""
    for eb in g()["enemy_bullets"]:
        if eb.get("attack_type") != "b1_ground_tentacle":
            continue
        if eb.get("life", 0) <= 0:
            continue
        return True
    return False


def boss1_body_sprite(boss):
    """地面触手攻撃中のみ midboss1b、終了後は通常 midboss1。"""
    rt = g()
    normal = rt["midboss_img1"]
    if boss1_ground_tentacle_active():
        return rt.get("midboss_img1b", normal)
    return normal


def sync_boss1_body_sprite(boss) -> None:
    if boss.boss_type != 1:
        return
    target = boss1_body_sprite(boss)
    if boss.image is target:
        return
    center = boss.rect.center
    boss.image = target
    boss.rect = boss.image.get_rect(center=center)


def draw_boss1(screen, boss) -> None:
    sync_boss1_body_sprite(boss)
    screen.blit(boss.image, boss.rect)


def update_boss1_special(boss, is_low_hp):
    if not hasattr(boss, "b1_sp_state"):
        boss.b1_sp_state = "idle"   # idle / burst
        boss.b1_burst_count = 0
        boss.b1_burst_timer = 0
        boss.b1_sp_cooldown = 150
    B1_SP_INTERVAL = 180 if is_low_hp else 240
    if boss.b1_sp_state == "idle":
        boss.b1_sp_cooldown -= 1
        if boss.b1_sp_cooldown <= 0:
            boss.b1_sp_state = "burst"
            boss.b1_burst_count = 0
            boss.b1_burst_timer = 0
            from boss_attacks.common import boss_special_alert_pulse

            g()["_bubble"].show("boss1_special")
            boss_special_alert_pulse(50)
            g()["boss_special_alert_sound"].play()
    if boss.b1_sp_state == "burst":
        boss.b1_burst_timer += 1
        if boss.b1_burst_timer == 1 and b1_ground_tentacle_count() == 0:
            spawn_b1_ground_tentacle_wave(
                boss,
                tentacle_colors=B1_GROUND_TENTACLE_COLORS,
            )
        if 35 <= boss.b1_burst_timer < 110:
            if boss.b1_burst_timer == 35 and g().get("ripple_sound"):
                g()["ripple_sound"].play()
            if boss.b1_burst_timer % 14 == 0:
                spawn_b1_diagonal_ripple_alternate(
                    boss,
                    boss.rect.left - 12,
                    boss.rect.centery,
                    is_low_hp=is_low_hp,
                )
        if boss.b1_burst_timer >= 115:
            b1_ground_tentacle_retract_all()
            boss.b1_sp_state = "idle"
            boss.b1_sp_cooldown = B1_SP_INTERVAL

    # HP50%以下: 上下から3本（Xランダム・中心／自機帯まで伸びない）
    if is_low_hp:
        if not hasattr(boss, "b1_ground_cd"):
            boss.b1_ground_cd = 100
        boss.b1_ground_cd -= 1
        if boss.b1_ground_cd <= 0 and b1_ground_tentacle_count() == 0:
            boss.b1_ground_cd = random.randint(310, 390)
            spawn_b1_ground_tentacle_wave(
                boss,
                tentacle_colors=B1_GROUND_TENTACLE_COLORS,
            )
            from boss_attacks.common import boss_special_alert_pulse

            g()["_bubble"].show("boss1_special")
            boss_special_alert_pulse(45)
            g()["boss_special_alert_sound"].play()


