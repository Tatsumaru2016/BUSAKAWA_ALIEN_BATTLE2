# enemy_waves.py — 編隊・突進・横STGウェーブ



from __future__ import annotations



import math

import random

from dataclasses import dataclass, field



from enemy_spawn import apply_enemy_hp, make_enemy

from grunt_behavior import (

    BEH_ACE,
    BEH_SPECIAL,

    BEH_DASH,

    BEH_FORMATION_SINE,

    BEH_HIT_RUN,

    BEH_SINE,

    BEH_WARP_BURST,

    BEH_WEAVE,

    BEH_ZIGZAG,

    pick_grunt_behavior,

)

from settings import (
    ENEMY_GRUNT_TYPE_MAX,
    ENEMY_TYPE_SPECIAL,
    grunt_spawn_tuning,
    is_enemy_ace_type,
    pick_ace_enemy_type,
)

ACE_SPAWN_COOLDOWN_AFTER_CLEAR = 720





@dataclass

class _SpawnCmd:

    enemy_type: int

    lane: str = "mid"

    stagger: int = 0

    ace_leader: bool = False

    special_leader: bool = False

    escort: bool = False

    wait: int = 0

    behavior: str | None = None

    formation_phase: float | None = None

    formation_index: int = 0





@dataclass

class GruntWaveState:

    cooldown: int = 0

    spawn_gap: int = 0

    queue: list[_SpawnCmd] = field(default_factory=list)

    lane_flip: int = 0

    ace_cooldown: int = 0

    ace_was_active: bool = False

    special_cooldown: int = 0





def _state(play) -> GruntWaveState:

    st = getattr(play, "_grunt_wave", None)

    if st is None:

        st = GruntWaveState()

        play._grunt_wave = st

    return st


def _weapon_level(player) -> int:

    return max(1, min(5, int(getattr(player, "weapon_level", 1))))


def _formation_count(base: int, tuning: dict) -> int:

    return max(2, int(round(base * float(tuning["formation_mul"]))))





def reset_grunt_waves(play) -> None:

    play._grunt_wave = GruntWaveState(cooldown=8)

    play.grunt_hit_ghosts = []





def _lane_alternate(st: GruntWaveState) -> str:

    lanes = ("top", "mid", "bottom")

    st.lane_flip = (st.lane_flip + 1) % 3

    return lanes[st.lane_flip]





def _lane_spread() -> str:

    return random.choice(("top", "mid", "bottom"))





def _wave_formation_sine(count: int = 4) -> list[_SpawnCmd]:

    """大振幅サイン波で編隊が左へ流れる。"""

    t = random.randint(0, ENEMY_GRUNT_TYPE_MAX)

    lanes = ("top", "mid", "bottom", "mid")

    phase = random.uniform(0, math.tau)

    return [

        _SpawnCmd(

            t,

            lane=lanes[i % len(lanes)],

            stagger=i * 38,

            wait=i * 5,

            behavior=BEH_FORMATION_SINE,

            formation_phase=phase,

            formation_index=i,

        )

        for i in range(count)

    ]





def _wave_dash_pair(st: GruntWaveState) -> list[_SpawnCmd]:

    a, b = _lane_alternate(st), _lane_alternate(st)

    return [

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=a, behavior=BEH_DASH),

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=b, stagger=28, wait=8, behavior=BEH_DASH),

    ]





def _wave_toaplan_pair(st: GruntWaveState) -> list[_SpawnCmd]:

    a, b = _lane_alternate(st), _lane_alternate(st)

    return [

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=a, behavior=BEH_DASH),

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=b, stagger=32, wait=10, behavior=BEH_FORMATION_SINE),

    ]





def _wave_v_formation() -> list[_SpawnCmd]:

    t = random.randint(0, ENEMY_GRUNT_TYPE_MAX)

    phase = random.uniform(0, math.tau)

    return [

        _SpawnCmd(

            t, lane="top", stagger=0, wait=0,

            behavior=BEH_FORMATION_SINE, formation_phase=phase, formation_index=0,

        ),

        _SpawnCmd(

            t, lane="mid", stagger=42, wait=6,

            behavior=BEH_DASH, formation_phase=phase, formation_index=1,

        ),

        _SpawnCmd(

            t, lane="bottom", stagger=84, wait=12,

            behavior=BEH_FORMATION_SINE, formation_phase=phase, formation_index=2,

        ),

    ]





def _wave_line(count: int = 3) -> list[_SpawnCmd]:

    t = random.randint(0, ENEMY_GRUNT_TYPE_MAX)

    lanes = ("top", "mid", "bottom")

    return [

        _SpawnCmd(

            t,

            lane=lanes[i % 3],

            stagger=i * 40,

            wait=i * 6,

            behavior=BEH_WARP_BURST,

        )

        for i in range(max(2, count))

    ]





def _wave_hit_run_pair(st: GruntWaveState) -> list[_SpawnCmd]:

    a, b = _lane_alternate(st), _lane_alternate(st)

    return [

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=a, behavior=BEH_HIT_RUN, wait=0),

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane=b, stagger=30, wait=12, behavior=BEH_HIT_RUN),

    ]





def _wave_pop_weave() -> list[_SpawnCmd]:

    return [

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane="mid", behavior=BEH_DASH),

        _SpawnCmd(

            random.randint(0, ENEMY_GRUNT_TYPE_MAX),

            lane=random.choice(["top", "bottom"]),

            stagger=24,

            wait=10,

            behavior=random.choice((BEH_SINE, BEH_WEAVE, BEH_FORMATION_SINE)),

        ),

    ]





def _wave_special_solo(st: GruntWaveState) -> list[_SpawnCmd]:
    st.special_cooldown = 960
    return [
        _SpawnCmd(
            ENEMY_TYPE_SPECIAL,
            lane="mid",
            special_leader=True,
            behavior=BEH_SPECIAL,
            wait=12,
        ),
    ]


def _ace_on_screen(enemies) -> bool:
    for enemy in enemies:
        if getattr(enemy, "grunt_behavior", None) == BEH_ACE:
            return True
        if is_enemy_ace_type(getattr(enemy, "type", -1)):
            return True
    return False


def _tick_ace_spawn_lock(st: GruntWaveState, enemies) -> None:
    """エースがいる間は再出現不可。撃破／左退場後にクールダウン。"""
    if _ace_on_screen(enemies):
        st.ace_was_active = True
        st.ace_cooldown = 1
        return
    if getattr(st, "ace_was_active", False):
        st.ace_was_active = False
        st.ace_cooldown = ACE_SPAWN_COOLDOWN_AFTER_CLEAR
    elif st.ace_cooldown > 0:
        st.ace_cooldown -= 1


def _wave_ace_escort(st: GruntWaveState) -> list[_SpawnCmd]:
    st.ace_was_active = True
    st.ace_cooldown = 1

    return [

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane="top", stagger=18, escort=True, behavior=BEH_WARP_BURST),

        _SpawnCmd(pick_ace_enemy_type(), lane="mid", ace_leader=True, behavior=BEH_ACE, wait=10),

        _SpawnCmd(random.randint(0, ENEMY_GRUNT_TYPE_MAX), lane="bottom", stagger=36, escort=True, wait=18, behavior=BEH_WARP_BURST),

    ]





def _pick_wave(
    st: GruntWaveState, diff, tuning: dict, enemies
) -> list[_SpawnCmd]:

    special_chance = 0.045 * float(tuning["special_chance_mul"])

    if st.special_cooldown <= 0 and random.random() < special_chance:

        return _wave_special_solo(st)

    ace_chance = 0.11 * float(tuning["ace_chance_mul"])

    if (
        st.ace_cooldown <= 0
        and not _ace_on_screen(enemies)
        and random.random() < ace_chance
    ):
        return _wave_ace_escort(st)

    roll = random.random()

    if roll < 0.28:

        base = 5 if random.random() < 0.55 else 4

        return _wave_formation_sine(_formation_count(base, tuning))

    if roll < 0.48:

        return _wave_dash_pair(st)

    if roll < 0.62:

        return _wave_hit_run_pair(st)

    if roll < 0.76:

        return _wave_v_formation()

    if roll < 0.86:

        return _wave_line(_formation_count(3, tuning))

    if roll < 0.94:

        return _wave_pop_weave()

    return [

        _SpawnCmd(

            random.randint(0, ENEMY_GRUNT_TYPE_MAX),

            lane=_lane_spread(),

            behavior=pick_grunt_behavior(),

        )

    ]


def _ensure_lane_minimum(cmds: list[_SpawnCmd]) -> list[_SpawnCmd]:
    """上/中/下レーンを最低1機ずつ保証する。"""
    if not cmds:
        return cmds
    lanes = {"top", "mid", "bottom"}
    existing = {str(c.lane) for c in cmds}
    missing = [ln for ln in ("top", "mid", "bottom") if ln not in existing]
    if not missing:
        return cmds

    # 既存コマンドをベースに不足レーン分を追加
    out = list(cmds)
    for i, lane in enumerate(missing):
        base = random.choice(cmds)
        out.append(
            _SpawnCmd(
                enemy_type=int(base.enemy_type),
                lane=lane,
                stagger=int(base.stagger) + 22 * (i + 1),
                wait=max(0, int(base.wait) + 4 * (i + 1)),
                ace_leader=False,
                special_leader=False,
                escort=bool(base.escort),
                behavior=base.behavior,
                formation_phase=base.formation_phase,
                formation_index=int(base.formation_index) + i + 1,
            )
        )
    return out


def _double_wave_count(cmds: list[_SpawnCmd]) -> list[_SpawnCmd]:
    """既存ウェーブにランダム複製を追加して出現数を2倍化。"""
    if not cmds:
        return cmds
    out = list(cmds)
    src = list(cmds)
    for i in range(len(src)):
        base = random.choice(src)
        lane = random.choice(("top", "mid", "bottom"))
        out.append(
            _SpawnCmd(
                enemy_type=int(base.enemy_type),
                lane=lane,
                stagger=max(0, int(base.stagger) + random.randint(16, 64)),
                wait=max(0, int(base.wait) + random.randint(2, 12)),
                ace_leader=False,
                special_leader=False,
                escort=bool(base.escort) and random.random() < 0.5,
                behavior=base.behavior if random.random() < 0.7 else pick_grunt_behavior(),
                formation_phase=base.formation_phase,
                formation_index=int(base.formation_index) + i + 1,
            )
        )
    return out





def _wave_cooldown_frames(diff, tuning: dict) -> int:

    base = max(12, int(getattr(diff, "enemy_interval", 56)))

    return max(10, int(base * float(tuning["cooldown_mul"])))





def _spawn_gap_frames(diff, tuning: dict) -> int:

    base = max(3, int(getattr(diff, "enemy_interval", 56) // 9))

    return max(2, int(base * float(tuning["gap_mul"])))





def tick_grunt_waves(play, diff, width: int, height: int, images, player) -> None:

    if not images:

        return



    st = _state(play)

    enemies = play.enemies

    tuning = grunt_spawn_tuning(_weapon_level(player))



    _tick_ace_spawn_lock(st, enemies)

    if st.special_cooldown > 0:

        st.special_cooldown -= 1



    if len(enemies) >= int(tuning["max_on_screen"]):

        return



    if st.cooldown > 0:

        st.cooldown -= 1

        return



    if st.spawn_gap > 0:

        st.spawn_gap -= 1

        return



    if not st.queue:
        picked = list(_pick_wave(st, diff, tuning, enemies))
        picked = _ensure_lane_minimum(picked)
        st.queue = _double_wave_count(picked)



    if not st.queue:

        st.cooldown = _wave_cooldown_frames(diff, tuning)

        return



    cmd = st.queue.pop(0)

    if cmd.wait > 0:

        st.spawn_gap = cmd.wait

        cmd.wait = 0

        st.queue.insert(0, cmd)

        return



    e = make_enemy(

        images,

        width,

        height,

        cmd.enemy_type,

        player,

        lane=cmd.lane,

        stagger=cmd.stagger,

        ace_leader=cmd.ace_leader,

        special_leader=cmd.special_leader,

        escort=cmd.escort,

        behavior=cmd.behavior,

        formation_phase=cmd.formation_phase,

        formation_index=cmd.formation_index,

    )

    e.speed = max(2, int(e.speed * float(getattr(diff, "enemy_spd_scale", 1.0))))

    apply_enemy_hp(e, diff)

    enemies.append(e)



    if st.queue:

        st.spawn_gap = _spawn_gap_frames(diff, tuning)

    else:

        st.cooldown = _wave_cooldown_frames(diff, tuning)


