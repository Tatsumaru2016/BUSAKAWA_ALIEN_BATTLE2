"""Boss attack package (Phase 3)."""

from boss_attacks.common import (
    boss_hp_stage,
    run_boss_attack_mix,
    update_boss_supply_drop,
    boss_mix_blockers,
)
from boss_attacks.movement import update_boss_sin_movement
from boss_attacks.boss2 import draw_boss2, sync_boss2_body_sprite, update_boss2_charge_movement
from boss_attacks.boss1 import draw_boss1, sync_boss1_body_sprite
from boss_attacks.boss3 import draw_boss3, sync_boss3_body_sprite
from boss_attacks.boss4_kraken import (
    bullet_hits_boss4_overlays,
    draw_boss4,
    player_hits_boss4_screen_overlays,
    update_boss4_strip_sniper,
)
from boss_attacks.draw_fx import draw_boss_special_fx
from boss_attacks.orchestrator import update_boss_attacks

__all__ = [
    "boss_hp_stage",
    "run_boss_attack_mix",
    "update_boss_supply_drop",
    "boss_mix_blockers",
    "update_boss_sin_movement",
    "draw_boss2",
    "sync_boss2_body_sprite",
    "update_boss2_charge_movement",
    "draw_boss1",
    "sync_boss1_body_sprite",
    "draw_boss3",
    "sync_boss3_body_sprite",
    "draw_boss4",
    "draw_boss_special_fx",
    "update_boss_attacks",
]
