# support_movement.py — 支援機の独自移動（追従なし・ボス接近で後退）

from __future__ import annotations

import math
import random

from settings import PLAYER_SPRITE_SIZE

SUPPORT_SIZE = PLAYER_SPRITE_SIZE

SUPPORT_PATROL_SPEED = 3.4
SUPPORT_PATROL_SPEED_VAR = 1.5
SUPPORT_WANDER_INTERVAL_MIN = 32
SUPPORT_WANDER_INTERVAL_MAX = 92
SUPPORT_MAX_SPEED = 5.8
SUPPORT_DRIFT = 0.14

SUPPORT_BOSS_MARGIN = 80
SUPPORT_BOSS_REPULSE = 0.72
SUPPORT_BOSS_MAX_PUSH = 5.2
SUPPORT_BOSS_RETREAT_BOOST = 1.35
SUPPORT_BOSS_AHEAD_PAD = 52

SUPPORT_PLAY_MARGIN_X = 28
SUPPORT_PLAY_MARGIN_Y = 68
SUPPORT_WALL_BOUNCE_DAMP = 0.92


def _play_bounds(width: int, height: int) -> tuple[float, float, float, float]:
    sw, sh = SUPPORT_SIZE
    return (
        sw * 0.5 + SUPPORT_PLAY_MARGIN_X,
        float(width) - sw * 0.5 - SUPPORT_PLAY_MARGIN_X,
        sh * 0.5 + SUPPORT_PLAY_MARGIN_Y,
        float(height) - sh * 0.5 - SUPPORT_PLAY_MARGIN_Y,
    )


def _boss_keep_distance(boss) -> float:
    bw = max(80, boss.rect.width)
    bh = max(60, boss.rect.height)
    return math.hypot(bw, bh) * 0.44 + SUPPORT_BOSS_MARGIN


def _boss_repulsion(sf, boss) -> tuple[float, float]:
    if boss is None or getattr(boss, "hp", 1) <= 0:
        return 0.0, 0.0
    bx = float(boss.rect.centerx)
    by = float(boss.rect.centery)
    dx = sf["x"] - bx
    dy = sf["y"] - by
    dist = math.hypot(dx, dy)
    keep = _boss_keep_distance(boss)
    if dist >= keep or dist < 0.5:
        return 0.0, 0.0
    push = (keep - dist) / keep
    push = min(1.0, push * push)
    mag = SUPPORT_BOSS_REPULSE * push * SUPPORT_MAX_SPEED * SUPPORT_BOSS_RETREAT_BOOST
    mag = min(SUPPORT_BOSS_MAX_PUSH, mag)
    return (dx / dist) * mag, (dy / dist) * mag


def _boss_x_ceiling(boss) -> float | None:
    if boss is None or getattr(boss, "hp", 1) <= 0:
        return None
    return float(boss.rect.left) - SUPPORT_BOSS_AHEAD_PAD


def _pick_wander_velocity(sf, variant: int = 0) -> None:
    base = (variant + 1) * 0.73
    angle = random.uniform(0.0, math.pi * 2.0)
    angle += math.sin(sf.get("frame", 0) * 0.019 + base) * 0.9
    spd = SUPPORT_PATROL_SPEED + random.uniform(
        -SUPPORT_PATROL_SPEED_VAR, SUPPORT_PATROL_SPEED_VAR,
    )
    sf["vx"] = math.cos(angle) * spd
    sf["vy"] = math.sin(angle) * spd


def init_support_autonomy(
    sf,
    start_x: float,
    start_y: float,
    *,
    variant: int = 0,
    width: int = 1280,
    height: int = 760,
) -> None:
    """戦闘開始位置から完全独立して動き始める。"""
    min_x, max_x, min_y, max_y = _play_bounds(width, height)
    sf["x"] = max(min_x, min(max_x, float(start_x)))
    sf["y"] = max(min_y, min(max_y, float(start_y)))
    _pick_wander_velocity(sf, variant)
    sf["wander_timer"] = random.randint(
        SUPPORT_WANDER_INTERVAL_MIN, SUPPORT_WANDER_INTERVAL_MAX,
    )


def _bounce_walls(sf, width: int, height: int) -> None:
    min_x, max_x, min_y, max_y = _play_bounds(width, height)
    damp = SUPPORT_WALL_BOUNCE_DAMP
    if sf["x"] <= min_x:
        sf["x"] = min_x
        sf["vx"] = abs(sf["vx"]) * damp
    elif sf["x"] >= max_x:
        sf["x"] = max_x
        sf["vx"] = -abs(sf["vx"]) * damp
    if sf["y"] <= min_y:
        sf["y"] = min_y
        sf["vy"] = abs(sf["vy"]) * damp
    elif sf["y"] >= max_y:
        sf["y"] = max_y
        sf["vy"] = -abs(sf["vy"]) * damp


def update_support_free_move(
    sf,
    boss,
    width: int,
    height: int,
    *,
    variant: int = 0,
) -> None:
    """自機・ホーム位置への追従なし。画面内を独自に動き、ボス付近では後退。"""
    if "vx" not in sf:
        init_support_autonomy(
            sf, sf["x"], sf["y"], variant=variant, width=width, height=height,
        )

    sf["wander_timer"] = sf.get("wander_timer", 0) - 1
    if sf["wander_timer"] <= 0:
        sf["wander_timer"] = random.randint(
            SUPPORT_WANDER_INTERVAL_MIN, SUPPORT_WANDER_INTERVAL_MAX,
        )
        _pick_wander_velocity(sf, variant)

    frame = sf.get("frame", 0)
    sf["vx"] += math.sin(frame * 0.05 + variant) * SUPPORT_DRIFT
    sf["vy"] += math.cos(frame * 0.043 + variant * 0.7) * SUPPORT_DRIFT

    rx, ry = _boss_repulsion(sf, boss)
    sf["vx"] += rx
    sf["vy"] += ry

    spd = math.hypot(sf["vx"], sf["vy"])
    if spd > SUPPORT_MAX_SPEED:
        sf["vx"] = sf["vx"] / spd * SUPPORT_MAX_SPEED
        sf["vy"] = sf["vy"] / spd * SUPPORT_MAX_SPEED
    elif spd < 0.35:
        _pick_wander_velocity(sf, variant)

    sf["x"] += sf["vx"]
    sf["y"] += sf["vy"]

    x_ceil = _boss_x_ceiling(boss)
    if x_ceil is not None:
        sw, _ = SUPPORT_SIZE
        limit = x_ceil - sw * 0.5
        if sf["x"] > limit:
            sf["x"] = limit
            sf["vx"] = min(0.0, sf["vx"]) - 0.5

    _bounce_walls(sf, width, height)
