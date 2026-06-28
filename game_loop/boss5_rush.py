# game_loop/boss5_rush.py — ボス5突進（開始時スナイプ方向のみ・誘導なし）

from __future__ import annotations

import math

from boss5_attack_patterns import B5_RUSH_SPEED, B5_RUSH_SPIN_PER_FRAME, is_b5_rush_active
from boss5_update import (
    apply_b5_sin_position,
    b5_end_rush_scale,
    get_b5_sin_position,
)
from combat import apply_player_hit, player_hit_by_b5_rush

def _b5_rush_offscreen(boss, width: int, height: int) -> bool:
    """突進方向へボス全体がプレイ領域外に出るまで charge を継続。"""
    vx = float(getattr(boss, "b5_rush_vx", -1.0))
    vy = float(getattr(boss, "b5_rush_vy", 0.0))
    fw = float(getattr(boss, "b5_rush_full_w", boss.rect.width))
    fh = float(getattr(boss, "b5_rush_full_h", boss.rect.height))
    pad = int(math.hypot(fw, fh) * 0.35) + 24

    if vx < -0.25:
        return boss.rect.right < -pad
    if vx > 0.25:
        return boss.rect.left > width + pad
    if vy < -0.25:
        return boss.rect.bottom < -pad
    if vy > 0.25:
        return boss.rect.top > height + pad
    return boss.rect.right < -pad


def init_b5_snipe_rush_velocity(boss, player) -> None:
    """突進開始瞬間のプレイヤー位置へ直線（以降は速度固定・追尾しない）。"""
    dx = float(player.rect.centerx - boss.rect.centerx)
    dy = float(player.rect.centery - boss.rect.centery)
    dist = max(1.0, math.hypot(dx, dy))
    spd = B5_RUSH_SPEED
    boss.b5_rush_vx = spd * dx / dist
    boss.b5_rush_vy = spd * dy / dist


def update_boss5_rush(boss, player, player_dead, width: int, height: int) -> None:
    if boss.boss_type != 5:
        return

    rs = getattr(boss, "b5_rush_state", "idle")
    if rs == "charge":
        _update_charge(boss, player, player_dead, width, height)
    elif rs == "wait":
        _update_wait(boss, width)
    elif rs == "return":
        _update_return(boss)


def _update_charge(boss, player, player_dead, width: int, height: int) -> None:
    if getattr(boss, "b5_rush_flash_timer", 0) > 0:
        boss.b5_rush_flash_timer -= 1
        return

    boss.b5_rush_spin_angle = (
        getattr(boss, "b5_rush_spin_angle", 0.0) + B5_RUSH_SPIN_PER_FRAME
    ) % 360.0

    boss.b5_rush_prev_center = (boss.rect.centerx, boss.rect.centery)
    boss.rect.x += int(round(getattr(boss, "b5_rush_vx", -B5_RUSH_SPEED)))
    boss.rect.y += int(round(getattr(boss, "b5_rush_vy", 0.0)))

    if not player_dead and player.invincible_timer == 0:
        if player_hit_by_b5_rush(player, boss):
            apply_player_hit(hit_kind="boss")

    if _b5_rush_offscreen(boss, width, height):
        boss.b5_rush_state = "wait"
        boss.b5_rush_timer = 0
        boss.b5_rush_prev_center = None


def _update_wait(boss, width: int) -> None:
    boss.b5_rush_timer += 1
    if boss.b5_rush_timer >= 45:
        boss.rect.left = width + 80
        boss.b5_rush_state = "return"
        boss.b5_rush_timer = 0
        boss.b5_rush_prev_center = None


def _update_return(boss) -> None:
    home_x, home_y = get_b5_sin_position(boss)
    dx = home_x - boss.rect.centerx
    dy = home_y - boss.rect.centery
    dist = max(1.0, math.hypot(dx, dy))
    if dist > 12.0:
        boss.rect.centerx += int((dx / dist) * 12.0)
        boss.rect.centery += int((dy / dist) * 12.0)
    else:
        b5_end_rush_scale(boss)
        apply_b5_sin_position(boss)
        boss.b5_rush_state = "idle"
        boss.b5_rush_timer = 0
        boss.b5_rush_prev_center = None


def b5_rush_blocks_movement(boss) -> bool:
    return boss.boss_type == 5 and is_b5_rush_active(boss)
