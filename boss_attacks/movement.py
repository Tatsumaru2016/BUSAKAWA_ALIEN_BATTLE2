"""Boss movement patterns (Phase 3)."""

import math

from game_runtime import RT
from boss5_update import apply_b5_sin_position
from boss_attacks.boss4_kraken import sync_boss4_body_layout


def g():
    return RT.g()


def update_boss_sin_movement(boss, b2_charge_active):
    if boss.boss_type <= 3 and not b2_charge_active:
        if not hasattr(boss, "move_timer"):
            boss.move_timer = 0
        boss.move_timer += 1
        mix = getattr(boss, "attack_mix", ())
        x_amp_bonus = 16 if any(p in mix for p in ("ring", "spiral")) else 0
        y_amp_scale = 0.55 if "accel_lanes" in mix else 0.80 if "aim_fan" in mix else 1.0
        x_hold = 0.55 if "aim_fan" in mix else 1.0

        if boss.boss_type == 1:
            boss.rect.x = 860 + int(math.sin(boss.move_timer * 0.012) * (70 + x_amp_bonus) * x_hold)
            boss.rect.y = 150 + int(math.sin(boss.move_timer * 0.02) * 110 * y_amp_scale)
        elif boss.boss_type == 2:
            boss.rect.x = 860 + int(math.sin(boss.move_timer * 0.016) * (75 + x_amp_bonus) * x_hold)
            boss.rect.y = 150 + int(math.sin(boss.move_timer * 0.035) * 100 * y_amp_scale)
        elif boss.boss_type == 3:
            boss.rect.x = 860 + int(math.sin(boss.move_timer * 0.010) * (80 + x_amp_bonus) * x_hold)
            boss.rect.y = 150 + int(math.sin(boss.move_timer * 0.015) * 130 * y_amp_scale)
    elif boss.boss_type > 3:
        if boss.boss_type == 4:
            sync_boss4_body_layout(boss)
        elif boss.boss_type == 5:
            boss.move_timer = getattr(boss, "move_timer", 0) + 1
            _b5_rush = getattr(boss, "b5_rush_state", "idle")
            if _b5_rush not in ("charge", "wait", "return"):
                apply_b5_sin_position(boss)
