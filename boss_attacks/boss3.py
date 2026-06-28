"""Boss attacks (Phase 3)."""

import math
import random

import pygame

from game_runtime import RT
from enemy_bullets import (
    spawn_enemy_bullet,
    spawn_b1_ground_tentacle,
    spawn_boss2_fish_swarm,
    spawn_boss3_giant_laser,
    spawn_boss5_red_laser,
    spawn_boss5_ripple,
)
from boss_attacks.common import boss_easy_bullet_count
from meteors import spawn_boss5_meteor
from combat import apply_player_hit
from explosion import Explosion
from powerup import PowerItem


def g():
    return RT.g()


def boss3_special_active(boss) -> bool:
    if getattr(boss, "b3_sp_state", "idle") == "burst":
        return True
    for eb in g()["enemy_bullets"]:
        if eb.get("attack_type") == "b3_ufo_fleet" and eb.get("life", 0) > 0:
            return True
    for el in g()["enemy_lasers"]:
        if getattr(el, "beam_track_boss", False) and getattr(el, "life", 0) > 0:
            return True
    return False


def boss3_body_sprite(boss):
    rt = g()
    normal = rt["midboss_img3"]
    if boss3_special_active(boss):
        return rt.get("midboss_img3b", normal)
    return normal


def sync_boss3_body_sprite(boss) -> None:
    if boss.boss_type != 3:
        return
    target = boss3_body_sprite(boss)
    if boss.image is target:
        return
    center = boss.rect.center
    boss.image = target
    boss.rect = boss.image.get_rect(center=center)


def draw_boss3(screen, boss) -> None:
    sync_boss3_body_sprite(boss)
    screen.blit(boss.image, boss.rect)


def update_boss3_special(boss, is_critical_hp):
    if not hasattr(boss, "b3_sp_state"):
        boss.b3_sp_state = "idle"
        boss.b3_sp_sub = 0
        boss.b3_sp_cooldown = 180
    B3_SP_INTERVAL = 220 if is_critical_hp else 280
    B3_LASER_INTERVAL = 300
    B3_ATTACK_GAP = 140
    B3_LASER_PHASE_OFFSET = 110

    b3_fleet_busy = boss.b3_sp_state == "burst"
    b3_laser_active = any(
        getattr(el, "beam_track_boss", False) for el in g()["enemy_lasers"]
    )

    if boss.b3_sp_state == "idle":
        boss.b3_sp_cooldown -= 1
        if boss.b3_sp_cooldown <= 0 and not b3_laser_active:
            boss.b3_sp_state = "burst"
            boss.b3_sp_sub = 0
            boss.b3_laser_cd = max(
                getattr(boss, "b3_laser_cd", 0), B3_ATTACK_GAP
            )
            from boss_attacks.common import boss_special_alert_pulse

            g()["_bubble"].show("boss3_special")
            boss_special_alert_pulse(50)
            g()["boss_special_alert_sound"].play()
    if boss.b3_sp_state == "burst":
        boss.b3_sp_sub += 1
        if boss.b3_sp_sub == 1:
            count = boss_easy_bullet_count(7 if is_critical_hp else 5)
            center_y = max(130, min(g()["HEIGHT"] - 130, g()["player"].rect.centery))
            for i in range(count):
                row = i - (count - 1) / 2
                target_x = 850 + (abs(row) % 2) * 70
                target_y = center_y + row * 58
                spawn_enemy_bullet(
                    x=g()["WIDTH"] + 120 + i * 35,
                    y=target_y + random.choice((-180, 180)),
                    vx=0.0, vy=0.0,
                    is_boss_bullet=True, image_type="boss3_ufo",
                    special_attack=True, attack_type="b3_ufo_fleet",
                    target_x=target_x,
                    target_y=max(80, min(g()["HEIGHT"] - 80, target_y)),
                    wave_phase=i * 0.9,
                    hold_frames=98 if is_critical_hp else 112,
                    fire_frames=(34, 56, 78) if is_critical_hp else (42, 72),
                    life=175,
                )
        if boss.b3_sp_sub >= 130:
            boss.b3_sp_state = "idle"
            boss.b3_sp_cooldown = B3_SP_INTERVAL

    # HP25%以下: 巨大ビーム（艦隊と同時にならない）
    if is_critical_hp:
        if not hasattr(boss, "b3_laser_phase_init"):
            boss.b3_laser_phase_init = True
            boss.b3_laser_cd = B3_LASER_PHASE_OFFSET
        if not b3_fleet_busy and not b3_laser_active:
            boss.b3_laser_cd -= 1
            if boss.b3_laser_cd <= 0:
                boss.b3_laser_cd = B3_LASER_INTERVAL
                spawn_boss3_giant_laser(boss, g()["player"])
                boss.b3_sp_cooldown = max(
                    getattr(boss, "b3_sp_cooldown", 0), B3_ATTACK_GAP
                )
                from boss_attacks.common import boss_special_alert_pulse

                g()["_bubble"].show("boss3_special")
                boss_special_alert_pulse(55)
                g()["boss_special_alert_sound"].play()


