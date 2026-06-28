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
)
from meteors import spawn_boss5_meteor
from combat import apply_player_hit
from explosion import Explosion
from powerup import PowerItem


def g():
    return RT.g()


def boss2_charge_active(boss) -> bool:
    return getattr(boss, "b2_charge_state", "idle") in ("charge", "wait", "return")


def boss2_special_visual_active_for(boss) -> bool:
    if boss2_charge_active(boss):
        return False
    if getattr(boss, "b2_fish_visual_timer", 0) > 0:
        return True
    for eb in g()["enemy_bullets"]:
        if eb.get("attack_type") == "b2_fish_swarm" and eb.get("life", 0) > 0:
            return True
    return False


def boss2_body_sprite(boss):
    rt = g()
    normal = rt["midboss_img2"]
    if boss2_special_visual_active_for(boss):
        return rt.get("midboss_img2b", normal)
    return normal


def sync_boss2_body_sprite(boss) -> None:
    if boss.boss_type != 2:
        return
    target = boss2_body_sprite(boss)
    if boss.image is target:
        return
    center = boss.rect.center
    boss.image = target
    boss.rect = boss.image.get_rect(center=center)


def draw_boss2(screen, boss) -> None:
    sync_boss2_body_sprite(boss)
    screen.blit(boss.image, boss.rect)


def update_boss2_charge_movement(boss):
    if getattr(boss, "b2_charge_state", "idle") == "charge":
        boss.rect.x += int(getattr(boss, "b2_charge_vx", -15.0))
        boss.rect.y += int(getattr(boss, "b2_charge_vy", 0.0))
        boss.rect.y = max(60, min(g()["HEIGHT"] - boss.rect.height - 10, boss.rect.y))
        if not g()["player_dead"] and g()["player"].invincible_timer == 0:
            from combat import player_hits_boss_body

            if player_hits_boss_body(g()["player"], boss):
                apply_player_hit(hit_kind="boss")
        if boss.rect.right < -80:
            boss.b2_charge_state = "wait"
            boss.b2_charge_timer = 0
    elif getattr(boss, "b2_charge_state", "idle") == "wait":
        boss.b2_charge_timer += 1
        if boss.b2_charge_timer >= 45:
            boss.rect.left = g()["WIDTH"] + 80
            boss.b2_charge_state = "return"
            boss.b2_charge_timer = 0
    elif getattr(boss, "b2_charge_state", "idle") == "return":
        home_x = 860 + int(math.sin(getattr(boss, "move_timer", 0) * 0.016) * 75)
        home_y = 150 + int(math.sin(getattr(boss, "move_timer", 0) * 0.035) * 100)
        dx = home_x - boss.rect.x
        dy = home_y - boss.rect.y
        dist = max(1.0, math.hypot(dx, dy))
        return_spd = 12.0
        if dist > return_spd:
            boss.rect.x += int((dx / dist) * return_spd)
            boss.rect.y += int((dy / dist) * return_spd)
        else:
            boss.rect.x = home_x
            boss.rect.y = home_y
            boss.b2_charge_state = "idle"
            boss.b2_charge_timer = 0


def update_boss2_special(boss, is_low_hp, is_critical_hp):
    hold = getattr(boss, "b2_fish_visual_timer", 0)
    if hold > 0:
        boss.b2_fish_visual_timer = hold - 1

    if not hasattr(boss, "b2_charge_state"):
        boss.b2_charge_state = "idle"
        boss.b2_charge_timer = 0
        boss.b2_charge_vx = 0.0
        boss.b2_charge_vy = 0.0
        boss.b2_charge_miss_count = 0
    if not hasattr(boss, "b2_try_timer"):
        boss.b2_try_timer = 0
    B2_CHARGE_SPD   = 15.0
    B2_RETURN_SPD   = 10.0
    B2_WAIT_FRAMES  = 60      # 左端で1秒停止
    B2_TRY_INTERVAL = 300
    B2_FISH_INTERVAL = 210
    B2_FISH_PHASE_OFFSET = 105
    B2_ATTACK_GAP = 130

    b2_charge_busy = boss.b2_charge_state in ("charge", "wait", "return")

    if boss.b2_charge_state == "idle" and is_low_hp:
        boss.b2_try_timer += 1
        if boss.b2_try_timer >= B2_TRY_INTERVAL:
            boss.b2_try_timer = 0
            force_charge = boss.b2_charge_miss_count >= 2
            if force_charge or random.randint(0, 99) < 30:
                dy = g()["player"].rect.centery - boss.rect.centery
                boss.b2_charge_vx = -B2_CHARGE_SPD
                boss.b2_charge_vy = max(-5.5, min(5.5, dy * 0.035))
                boss.b2_charge_state = "charge"
                boss.b2_charge_timer = 0
                boss.b2_charge_miss_count = 0
                _keep_fish = [
                    eb for eb in g()["enemy_bullets"]
                    if eb.get("attack_type") == "b2_fish_swarm"
                ]
                g()["enemy_bullets"].clear()
                g()["enemy_bullets"].extend(_keep_fish)
                boss.b2_fish_cd = max(
                    getattr(boss, "b2_fish_cd", 0), B2_ATTACK_GAP
                )
                from boss_attacks.common import boss_special_alert_pulse

                g()["_bubble"].show("boss2_rush")
                boss_special_alert_pulse(50)
                g()["boss_special_alert_sound"].play()
            else:
                boss.b2_charge_miss_count += 1

    if is_critical_hp:
        if not hasattr(boss, "b2_fish_phase_init"):
            boss.b2_fish_phase_init = True
            boss.b2_fish_cd = B2_FISH_PHASE_OFFSET
        if not b2_charge_busy:
            boss.b2_fish_cd -= 1
            if boss.b2_fish_cd <= 0:
                boss.b2_fish_cd = B2_FISH_INTERVAL
                spawn_boss2_fish_swarm(boss)
                boss.b2_fish_visual_timer = 240
                boss.b2_try_timer = min(
                    boss.b2_try_timer, B2_TRY_INTERVAL - B2_ATTACK_GAP
                )
                from boss_attacks.common import boss_special_alert_pulse

                boss_special_alert_pulse(40)
                try:
                    g()["boss_special_alert_sound"].play()
                except Exception:
                    pass


