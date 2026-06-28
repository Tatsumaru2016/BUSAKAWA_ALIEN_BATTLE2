"""Boss attack orchestration (Phase 3)."""

from boss_attacks.common import (
    update_boss_supply_drop,
    run_boss_attack_mix,
    boss_mix_blockers,
)
from boss_attacks.boss1 import update_boss1_special
from boss_attacks.boss2 import update_boss2_special
from boss_attacks.boss3 import update_boss3_special
from boss_attacks.boss4_kraken import update_boss4_special


def update_boss_attacks(boss, *, grace_skip, is_low_hp, is_critical_hp):
    """ボス1〜4の共通攻撃（mix・供給・固有特殊）。"""
    if grace_skip:
        return
    update_boss_supply_drop(boss)
    b4_tentacle, b2_charge, b3_burst = boss_mix_blockers(boss)
    if not b4_tentacle and not b2_charge and not b3_burst and boss.boss_type not in (4, 5):
        run_boss_attack_mix(boss)
    if boss.boss_type == 1:
        update_boss1_special(boss, is_low_hp)
    elif boss.boss_type == 2:
        update_boss2_special(boss, is_low_hp, is_critical_hp)
    elif boss.boss_type == 3:
        update_boss3_special(boss, is_critical_hp)
    elif boss.boss_type == 4:
        update_boss4_special(boss, is_low_hp, is_critical_hp)
