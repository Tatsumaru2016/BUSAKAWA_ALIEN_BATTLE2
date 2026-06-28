# enemy_spawn.py — 雑魚の生成・HP・画面外スポーン

from __future__ import annotations

import random

from enemy import Enemy
from grunt_behavior import BEH_ACE, BEH_SPECIAL, init_grunt_behavior, pick_grunt_behavior
from settings import (
    ACE_HP_BY_INDEX,
    ENEMY_SPAWN_EDGE_INSET,
    ENEMY_SPAWN_OFFSCREEN_PAD,
    ENEMY_TYPE_ACE_FIRST,
    GRUNT_HP_BONUS_WEAPON_LEVEL,
    is_enemy_ace_type,
    is_enemy_special_type,
)


def spawn_y_bounds(height: int, sprite_h: int) -> tuple[int, int]:
    margin = 36
    y_min = margin
    y_max = max(y_min, height - margin - sprite_h)
    return y_min, y_max


def spawn_y_for_lane(height: int, sprite_h: int, lane: str) -> int:
    """画面上中下を均等に使う（下部に偏らない）。"""
    y_min, y_max = spawn_y_bounds(height, sprite_h)
    span = y_max - y_min
    if span <= 0:
        return y_min
    if lane == "top":
        band = 0.14
    elif lane == "bottom":
        band = 0.66
    else:
        band = 0.40
    jitter = random.randint(-max(8, span // 10), max(8, span // 10))
    y = y_min + int(span * band) + jitter
    return max(y_min, min(y_max, y))


def make_enemy(
    images,
    width: int,
    height: int,
    enemy_type: int,
    player,
    *,
    lane: str = "mid",
    stagger: int = 0,
    ace_leader: bool = False,
    special_leader: bool = False,
    escort: bool = False,
    behavior: str | None = None,
    formation_phase: float | None = None,
    formation_index: int = 0,
) -> Enemy:
    if not images:
        raise ValueError("enemy images missing")
    enemy_type = int(enemy_type) % len(images)
    img = images[enemy_type]
    sprite_w = img.get_width()
    sprite_h = img.get_height()

    enemy_y = spawn_y_for_lane(height, sprite_h, lane)
    # 画面右外から無敵侵入。stagger は手前（左）へ編隊を広げる
    x = width + ENEMY_SPAWN_OFFSCREEN_PAD - int(stagger)
    e = Enemy(images, x, enemy_y, enemy_type)
    if e.image is None:
        raise ValueError(f"enemy image missing for type {enemy_type}")

    if special_leader or is_enemy_special_type(enemy_type):
        e.special_leader = True
        e.ace_leader = False
        beh = BEH_SPECIAL
    elif ace_leader or is_enemy_ace_type(enemy_type):
        e.special_leader = False
        e.ace_leader = True
        beh = BEH_ACE
    else:
        e.special_leader = False
        e.ace_leader = False
        beh = behavior or pick_grunt_behavior()

    init_grunt_behavior(
        e,
        beh,
        width,
        height,
        player,
        lane=lane,
        formation_phase=formation_phase,
        formation_index=formation_index,
    )
    if escort:
        e.speed = max(2, int(e.speed * 1.05))
        e.grunt_wait = max(0, int(getattr(e, "grunt_wait", 0)) - 8)

    return e


def apply_enemy_hp(enemy: Enemy, diff, *, weapon_level: int | None = None) -> None:
    scale = float(getattr(diff, "enemy_hp_scale", 1.0))
    t = int(enemy.type)

    if is_enemy_special_type(t):
        enemy.hp = max(8, int(18 * scale))
        enemy.max_hp = enemy.hp
        return

    if is_enemy_ace_type(t):
        idx = max(0, min(len(ACE_HP_BY_INDEX) - 1, t - ENEMY_TYPE_ACE_FIRST))
        base_hp = ACE_HP_BY_INDEX[idx]
        enemy.hp = max(6, int(base_hp * scale))
        enemy.max_hp = enemy.hp
        return

    if t == 1:
        enemy.hp = max(3, int(5 * scale))
    elif t == 2:
        enemy.hp = max(3, int(4 * scale))
    elif t == 3:
        enemy.hp = max(3, int(8 * scale))
    elif t == 4:
        enemy.hp = max(3, int(6 * scale))
    elif t == 5:
        enemy.hp = max(3, int(5 * scale))
    elif t == 6:
        enemy.hp = max(3, int(4 * scale))
    elif t == 7:
        enemy.hp = max(3, int(6 * scale))
    else:
        enemy.hp = max(3, int(3 * scale))

    if getattr(enemy, "grunt_behavior", None) and weapon_level is None:
        try:
            from game_runtime import RT

            weapon_level = int(RT.g()["player"].weapon_level)
        except Exception:
            weapon_level = 1
    wl = int(weapon_level or 1)
    if getattr(enemy, "grunt_behavior", None) and wl >= GRUNT_HP_BONUS_WEAPON_LEVEL:
        enemy.hp += 1

    enemy.max_hp = enemy.hp
