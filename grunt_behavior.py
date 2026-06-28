# grunt_behavior.py — 横STG定番の雑魚挙動（Gradius / Toaplan / R-Type 系）

from __future__ import annotations

import math
import random

import pygame

from settings import (
    ENEMY_INVULN_ENTRY_SPEED_MUL,
    ENEMY_INVULN_FRAMES_MAX,
    ENEMY_INVULN_FRAMES_MIN,
    ENEMY_SPAWN_EDGE_INSET,
    GRUNT_DAMAGE_MAX_CENTER_X_RATIO,
    GRUNT_POST_INVULN_ARMOR_FRAMES,
    GRUNT_POST_INVULN_RUSH_FRAMES,
    GRUNT_POST_INVULN_RUSH_MUL,
    GRUNT_SPECIAL_ACTIVE_WARP_CD_MAX,
    GRUNT_SPECIAL_ACTIVE_WARP_CD_MIN,
    GRUNT_SPECIAL_DODGE_RADIUS,
    GRUNT_SPECIAL_DODGE_STRENGTH,
    GRUNT_SPECIAL_WARP_COUNT,
    GRUNT_SPECIAL_WARP_FRAMES,
    is_enemy_ace_type,
    is_enemy_special_type,
)

# 挙動ID（ウェーブから指定）
BEH_WARP_BURST = "warp_burst"       # 待機→ワープ突入→加速通過
BEH_HIT_RUN = "hit_run"              # 侵入→回避→射撃→右退場
BEH_STRAIGHT = "straight"            # 直線（プレイヤー方向に一度補正）
BEH_ZIGZAG = "zigzag"                # ジグザグ突進
BEH_SINE = "sine"                    # 波状
BEH_WEAVE = "weave"                  # 円運動風ウェーブ
BEH_POP_SHOT = "pop_shot"            # 出現弾1発＋直進
BEH_FORMATION_SINE = "formation_sine"  # 編隊で大振幅サイン波＋左進行
BEH_DASH = "dash"                    # 自機方向へ突進→左スイープ
BEH_ACE = "ace"                      # エース旗艦
BEH_SPECIAL = "special"              # 特別機（弾回避・ワープのみ）

_BEHAVIOR_WEIGHTS = (
    (BEH_FORMATION_SINE, 4),
    (BEH_DASH, 4),
    (BEH_WARP_BURST, 3),
    (BEH_HIT_RUN, 3),
    (BEH_SINE, 3),
    (BEH_ZIGZAG, 2),
    (BEH_WEAVE, 2),
    (BEH_STRAIGHT, 1),
    (BEH_POP_SHOT, 1),
)
_PICK_POOL = [b for b, w in _BEHAVIOR_WEIGHTS for _ in range(w)]


def pick_grunt_behavior() -> str:
    return random.choice(_PICK_POOL)


def init_grunt_behavior(
    enemy,
    behavior: str,
    width: int,
    height: int,
    player,
    *,
    lane: str = "mid",
    formation_phase: float | None = None,
    formation_index: int = 0,
) -> None:
    enemy.grunt_behavior = behavior
    enemy.grunt_phase = "wait"
    enemy.grunt_wait = random.randint(4, 14)
    enemy.spawn_lane = lane
    enemy.invuln_timer = 0
    # 右端出現→即行動。侵入判定は使わない。
    enemy._screen_entered = True
    enemy.entry_fx_timer = 0
    enemy.death_scatter = False
    enemy.death_scatter_count = 0
    enemy.pop_shot_done = False
    enemy.aim_applied = False
    enemy.vy_drift = 0.0
    enemy.zigzag_dir = 1
    enemy.zigzag_flip = random.randint(14, 22)
    enemy.sin_amp = random.uniform(22, 48)
    enemy.sin_freq = random.uniform(0.07, 0.12)
    enemy.base_y = float(enemy.rect.centery)
    enemy.hover_x = random.randint(int(width * 0.45), int(width * 0.62))
    enemy.hit_run_timer = 0
    enemy.post_invuln_rush = 0
    enemy._rush_started = False
    enemy.formation_phase = float(
        formation_phase if formation_phase is not None else random.uniform(0, math.tau)
    )
    enemy.formation_index = int(formation_index)

    if behavior == BEH_SPECIAL or is_enemy_special_type(enemy.type):
        enemy.grunt_behavior = BEH_SPECIAL
        enemy.grunt_phase = "active"
        enemy.grunt_wait = 0
        enemy.invuln_timer = 0
        enemy.special_phase = "enter"
        enemy.special_warps_done = 0
        enemy.special_warp_timer = 0
        enemy.special_warp_cd = random.randint(
            GRUNT_SPECIAL_ACTIVE_WARP_CD_MIN, GRUNT_SPECIAL_ACTIVE_WARP_CD_MAX
        )
        enemy.depth_style = "none"
        _init_grunt_smooth_pos(enemy)
        return

    if behavior == BEH_ACE or is_enemy_ace_type(enemy.type):
        from grunt_ace_profiles import init_ace_profile

        enemy.grunt_behavior = BEH_ACE
        enemy.grunt_phase = "enter"
        enemy.grunt_wait = 0
        enemy.depth_style = "none"
        init_ace_profile(enemy)
        _init_grunt_smooth_pos(enemy)
        return

    _init_grunt_smooth_pos(enemy)

    # Y は spawn 時のレーン配置を維持（プレイヤー方向へ寄せない）
    enemy.base_y = float(enemy.rect.centery)

    py = player.rect.centery
    cy = enemy.rect.centery
    dy = py - cy
    dist = max(1.0, abs(dy))
    enemy.aim_vy = max(-2.2, min(2.2, (dy / dist) * random.uniform(0.5, 1.0)))
    enemy.aim_vx = -random.uniform(5.5, 8.0)

    if behavior == BEH_FORMATION_SINE:
        enemy.sin_amp = random.uniform(72, 105)
        enemy.sin_freq = random.uniform(0.065, 0.095)
        enemy.grunt_phase = "dive"
    elif behavior == BEH_DASH:
        enemy.sin_amp = random.uniform(35, 55)
        enemy.grunt_phase = "dive"
        _apply_aim_once(enemy)
    elif behavior in (BEH_SINE, BEH_WEAVE):
        enemy.sin_amp = random.uniform(40, 72)

    enemy.depth_st = random.choice(("press", "feint"))
    enemy.depth_tm = 0
    enemy.depth_style = (
        "feint"
        if behavior in (BEH_WARP_BURST, BEH_HIT_RUN) and random.random() < 0.28
        else "none"
    )
    enemy.feint_cd = random.randint(30, 70)
    enemy.feint_boost = 0
    enemy.feint_vx = 0

    # 右外から無敵侵入（左へ移動、終了後に行動）
    enemy.invuln_timer = random.randint(ENEMY_INVULN_FRAMES_MIN, ENEMY_INVULN_FRAMES_MAX)
    enemy.grunt_armor_timer = 0
    enemy._grunt_armor_block = False
    enemy.entry_fx_timer = 26
    if enemy.grunt_phase == "wait":
        enemy.grunt_phase = "dive"


def grunt_invulnerable(enemy) -> bool:
    return int(getattr(enemy, "invuln_timer", 0)) > 0


def grunt_damage_allowed(enemy, width: int) -> bool:
    """画面右端ゾーンでは被弾しない。"""
    limit = int(width * GRUNT_DAMAGE_MAX_CENTER_X_RATIO)
    return int(enemy.rect.centerx) < limit


def apply_grunt_bullet_damage(enemy, base_damage: int) -> int:
    """無敵明け装甲: 先頭1ヒット無効。"""
    if getattr(enemy, "_grunt_armor_block", False):
        enemy._grunt_armor_block = False
        return 0
    return int(base_damage)


def grunt_special_sprite_visible(enemy) -> bool:
    """特別機ワープ中は一瞬非表示（テレポート演出）。"""
    if getattr(enemy, "grunt_behavior", None) != BEH_SPECIAL:
        return True
    if getattr(enemy, "special_phase", "") != "warp":
        return True
    t = int(getattr(enemy, "special_warp_timer", 0))
    total = int(GRUNT_SPECIAL_WARP_FRAMES)
    mid = total // 2
    return t > mid or t <= max(1, total // 6)


def grunt_invuln_sprite_visible(enemy) -> bool:
    """自機の無敵点滅と同じ周期（4fごとに表示/非表示）。"""
    t = int(getattr(enemy, "invuln_timer", 0))
    if t <= 0:
        return True
    return (t // 4) % 2 == 0


def _mark_screen_enter(enemy, width: int) -> None:
    # 右端出現方式では侵入トリガを使わない（互換のため残す）
    return


def _grunt_invuln_entry_move(enemy, width: int, height: int) -> None:
    _init_grunt_smooth_pos(enemy)
    target_x = width - enemy.rect.width - ENEMY_SPAWN_EDGE_INSET
    if enemy._smooth_x > target_x:
        enemy._smooth_x -= max(1.2, _spd(enemy, ENEMY_INVULN_ENTRY_SPEED_MUL))
        enemy.rect.x = int(round(enemy._smooth_x))
    _clamp_y(enemy, height)


def update_grunt_behavior(enemy, width: int, height: int) -> None:
    beh = getattr(enemy, "grunt_behavior", None)
    if not beh:
        return

    _mark_screen_enter(enemy, width)
    armor_t = int(getattr(enemy, "grunt_armor_timer", 0))
    if armor_t > 0:
        enemy.grunt_armor_timer = armor_t - 1

    if beh == BEH_SPECIAL:
        _update_special(enemy, width, height)
        return

    if grunt_invulnerable(enemy):
        enemy.invuln_timer -= 1
        _grunt_invuln_entry_move(enemy, width, height)
        return

    if not getattr(enemy, "_rush_started", False):
        enemy._rush_started = True
        enemy.post_invuln_rush = GRUNT_POST_INVULN_RUSH_FRAMES
        enemy.grunt_armor_timer = GRUNT_POST_INVULN_ARMOR_FRAMES
        enemy._grunt_armor_block = True

    if beh == BEH_ACE:
        _update_ace(enemy, width, height)
        return
    if beh == BEH_WARP_BURST:
        _update_warp_burst(enemy, width)
    elif beh == BEH_HIT_RUN:
        _update_hit_run(enemy, width, height)
    elif beh == BEH_STRAIGHT:
        _update_straight(enemy, width)
    elif beh == BEH_ZIGZAG:
        _update_zigzag(enemy, width)
    elif beh == BEH_SINE:
        _update_sine(enemy, width)
    elif beh == BEH_WEAVE:
        _update_weave(enemy, width)
    elif beh == BEH_POP_SHOT:
        _update_pop_shot(enemy, width)
    elif beh == BEH_FORMATION_SINE:
        _update_formation_sine(enemy, width)
    elif beh == BEH_DASH:
        _update_dash(enemy, width)
    else:
        _update_straight(enemy, width)

    _left_edge_release(enemy, width)
    _clamp_y(enemy, height)


def _spd(enemy, mul: float = 1.0) -> float:
    return float(enemy.speed) * mul


def _init_grunt_smooth_pos(enemy) -> None:
    if getattr(enemy, "_smooth_init", False):
        return
    enemy._smooth_x = float(enemy.rect.x)
    enemy._smooth_y = float(enemy.rect.centery)
    enemy._smooth_init = True


def _clamp_y(enemy, height: int) -> None:
    margin = 28
    _init_grunt_smooth_pos(enemy)
    if enemy._smooth_y < margin:
        enemy._smooth_y = float(margin)
    elif enemy._smooth_y > height - margin:
        enemy._smooth_y = float(height - margin)
    enemy.base_y = enemy._smooth_y
    enemy.rect.y = int(round(enemy._smooth_y))


def _left_edge_release(enemy, width: int) -> None:
    """左側で滞留しないよう、左抜け速度を段階的に強制する。"""
    if getattr(enemy, "grunt_phase", "") in ("retreat", "right_exit", "u_turn_exit"):
        return
    _init_grunt_smooth_pos(enemy)
    x_left = int(enemy.rect.left)
    # 画面左 1/3 に入った個体は最低でも一定速度で左へ流す。
    # 特に左端付近で sin/feint と相殺して滞留するケースを潰す。
    if x_left < int(width * 0.34):
        if x_left < 28:
            min_drift = max(2.8, _spd(enemy, 1.35))
        elif x_left < int(width * 0.14):
            min_drift = max(2.1, _spd(enemy, 0.95))
        else:
            min_drift = max(1.4, _spd(enemy, 0.62))
        enemy._smooth_x -= min_drift
        enemy.rect.x = int(round(enemy._smooth_x))


def _move_left(enemy, mul: float) -> None:
    """右→左への基本移動（サブピクセルで滑らか）。"""
    _init_grunt_smooth_pos(enemy)
    rush = int(getattr(enemy, "post_invuln_rush", 0))
    if rush > 0:
        enemy.post_invuln_rush = rush - 1
        mul *= GRUNT_POST_INVULN_RUSH_MUL
    enemy._smooth_x -= max(0.35, _spd(enemy, mul))
    enemy.rect.x = int(round(enemy._smooth_x))


def _nudge_smooth(enemy, dx: float, dy: float) -> None:
    _init_grunt_smooth_pos(enemy)
    enemy._smooth_x += dx
    enemy._smooth_y += dy
    enemy.rect.x = int(round(enemy._smooth_x))
    if getattr(enemy, "grunt_behavior", None) in (BEH_ACE, BEH_SPECIAL):
        enemy.rect.centery = int(round(enemy._smooth_y))
    else:
        enemy.rect.y = int(round(enemy._smooth_y))


def _apply_y_sine(enemy, amp_scale: float = 1.0) -> None:
    from settings import GRUNT_MOVE_Y_LERP

    _init_grunt_smooth_pos(enemy)
    amp = float(getattr(enemy, "sin_amp", 32)) * amp_scale
    freq = float(getattr(enemy, "sin_freq", 0.11))
    target_y = enemy.base_y + math.sin(enemy.timer * freq) * amp
    enemy._smooth_y += (target_y - enemy._smooth_y) * GRUNT_MOVE_Y_LERP
    enemy.rect.y = int(round(enemy._smooth_y))


def _maybe_feint_x(enemy, *, allow_retreat: bool = True) -> None:
    if not allow_retreat or getattr(enemy, "depth_style", "none") != "feint":
        return

    st = getattr(enemy, "depth_st", "wave")
    tm = int(getattr(enemy, "depth_tm", 0)) + 1
    enemy.depth_tm = tm

    if st == "feint":
        if tm <= 22:
            # 停止/右戻りを防ぐため、フェイント中もわずかに左進行を維持
            _nudge_smooth(enemy, -_spd(enemy, 0.18), 0.0)
        elif tm <= 28:
            _nudge_smooth(enemy, -_spd(enemy, 2.2), 0.0)
        else:
            enemy.depth_st = "press"
            enemy.depth_tm = 0
    elif st == "press":
        if tm > random.randint(40, 65):
            enemy.depth_st = "feint"
            enemy.depth_tm = 0
    elif st == "wave" and getattr(enemy, "feint_cd", 0) <= 0:
        enemy.feint_cd = random.randint(55, 95)
        enemy.feint_boost = random.randint(14, 22)
        # 右向きブーストは左端での停止要因になるため左向きへ統一
        enemy.feint_vx = -int(_spd(enemy, 0.95))

    if getattr(enemy, "feint_cd", 0) > 0:
        enemy.feint_cd -= 1
    if getattr(enemy, "feint_boost", 0) > 0:
        _nudge_smooth(enemy, float(getattr(enemy, "feint_vx", 0)), 0.0)
        enemy.feint_boost -= 1


def _layer_depth_motion(
    enemy,
    net_left_mul: float,
    *,
    allow_retreat: bool = True,
    y_sine: float = 0.0,
) -> None:
    """左進行＋任意の縦サイン波・フェイント。"""
    # エース以外の単調化を防ぐため、左移動に軽い拍動を入れる
    pulse = 1.0 + math.sin(enemy.timer * 0.085 + float(getattr(enemy, "formation_phase", 0.0))) * 0.12
    _move_left(enemy, max(0.2, net_left_mul * pulse))
    _maybe_feint_x(enemy, allow_retreat=allow_retreat)
    if y_sine > 0:
        _apply_y_sine(enemy, y_sine)


def _apply_aim_once(enemy) -> None:
    if getattr(enemy, "aim_applied", False):
        return
    enemy.aim_applied = True
    enemy.vx_carry = float(getattr(enemy, "aim_vx", -6.0))
    enemy.vy_carry = float(getattr(enemy, "aim_vy", 0.0))


def _update_warp_burst(enemy, width: int) -> None:
    phase = enemy.grunt_phase
    if phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
            enemy.entry_fx_timer = 28
        return
    if phase == "dive":
        _layer_depth_motion(enemy, 1.05, allow_retreat=False, y_sine=0.45)
        if enemy.rect.left < width - 180:
            enemy.grunt_phase = "burst"
        return
    if phase == "burst":
        _layer_depth_motion(enemy, 2.65, y_sine=0.65)
        return
    _layer_depth_motion(enemy, 1.35, y_sine=0.5)


def _update_hit_run(enemy, width: int, height: int) -> None:
    phase = enemy.grunt_phase
    if phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
            _apply_aim_once(enemy)
        return
    if phase == "dive":
        _apply_aim_once(enemy)
        _nudge_smooth(
            enemy,
            float(getattr(enemy, "vx_carry", -6)) * 0.9,
            float(getattr(enemy, "vy_carry", 0)) * 1.05,
        )
        if enemy.rect.left < int(width * 0.52):
            enemy.grunt_phase = "weave"
            enemy.hit_run_timer = 40
        return
    if phase == "weave":
        enemy.hit_run_timer -= 1
        _layer_depth_motion(enemy, 0.62, y_sine=0.75)
        if enemy.hit_run_timer <= 0:
            enemy.grunt_phase = "u_turn_exit"
        return
    if phase == "u_turn_exit":
        # 自機近辺で撃った後、右へ切り返して退場
        _init_grunt_smooth_pos(enemy)
        if enemy.rect.centerx < int(width * 0.78):
            _nudge_smooth(enemy, _spd(enemy, 2.15), -_spd(enemy, 0.12))
        else:
            enemy.grunt_phase = "right_exit"
        return
    if phase == "right_exit":
        _nudge_smooth(enemy, _spd(enemy, 2.6), 0.0)
        return
    _layer_depth_motion(enemy, 0.55, y_sine=0.45)


def _update_straight(enemy, width: int) -> None:
    if enemy.grunt_phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
            _apply_aim_once(enemy)
        return
    if hasattr(enemy, "vx_carry") and not getattr(enemy, "_straight_boost", False):
        _nudge_smooth(enemy, float(enemy.vx_carry) * 0.85, float(getattr(enemy, "vy_carry", 0)) * 0.5)
        _apply_y_sine(enemy, 0.4)
        if enemy.timer > 36:
            enemy._straight_boost = True
        return
    _layer_depth_motion(enemy, 0.92, y_sine=0.55)
    # 直線型でも周期的な小ダッシュで表情を付ける
    if (enemy.timer + getattr(enemy, "shot_offset", 0)) % 64 == 0:
        _nudge_smooth(enemy, -_spd(enemy, 1.25), random.uniform(-0.6, 0.6))


def _update_zigzag(enemy, width: int) -> None:
    if enemy.grunt_phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
        return
    _layer_depth_motion(enemy, 0.72, y_sine=0.35)
    enemy.zigzag_flip -= 1
    if enemy.zigzag_flip <= 0:
        enemy.zigzag_flip = random.randint(8, 14)
        enemy.zigzag_dir *= -1
    _nudge_smooth(enemy, 0.0, enemy.zigzag_dir * _spd(enemy, 0.32))
    if (enemy.timer + enemy.zigzag_flip) % 41 == 0:
        _nudge_smooth(enemy, -_spd(enemy, 0.8), enemy.zigzag_dir * _spd(enemy, 0.22))


def _update_sine(enemy, width: int) -> None:
    if enemy.grunt_phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
        return
    _layer_depth_motion(enemy, 1.05, y_sine=1.0)
    # サイン機はときどき振幅を変化させて同型感を減らす
    if enemy.timer % 72 == 0:
        enemy.sin_amp = max(26.0, min(98.0, float(enemy.sin_amp) + random.uniform(-12.0, 14.0)))


def _update_weave(enemy, width: int) -> None:
    if enemy.grunt_phase == "wait":
        enemy.grunt_wait -= 1
        if enemy.grunt_wait <= 0:
            enemy.grunt_phase = "dive"
        return
    _move_left(enemy, 0.76)
    _maybe_feint_x(enemy)
    _init_grunt_smooth_pos(enemy)
    from settings import GRUNT_MOVE_Y_LERP

    freq = float(enemy.sin_freq)
    target_y = (
        enemy.base_y
        + math.sin(enemy.timer * freq) * enemy.sin_amp
        + math.sin(enemy.timer * freq * 0.55 + 1.2) * (enemy.sin_amp * 0.35)
    )
    enemy._smooth_y += (target_y - enemy._smooth_y) * GRUNT_MOVE_Y_LERP
    enemy.rect.y = int(round(enemy._smooth_y))
    if enemy.timer % 58 == 0:
        _nudge_smooth(enemy, -_spd(enemy, 0.7), random.uniform(-1.0, 1.0))


def _update_pop_shot(enemy, width: int) -> None:
    _update_straight(enemy, width)
    enemy.needs_pop_shot = not getattr(enemy, "pop_shot_done", False)


def _update_formation_sine(enemy, width: int) -> None:
    # 編隊でも個体差の速度パルスを入れて金太郎飴化を防止
    pulse = 1.0 + math.sin(enemy.timer * 0.09 + enemy.formation_index * 0.8) * 0.18
    _move_left(enemy, 1.95 * pulse)
    idx = float(getattr(enemy, "formation_index", 0))
    ph = enemy.formation_phase + enemy.timer * enemy.sin_freq
    lane_lag = idx * 0.55
    enemy.rect.y = int(
        enemy.base_y + math.sin(ph + lane_lag) * enemy.sin_amp
    )


def _update_dash(enemy, width: int) -> None:
    phase = enemy.grunt_phase
    if phase == "dive":
        _apply_aim_once(enemy)
        lane = str(getattr(enemy, "spawn_lane", "mid"))
        if lane == "top":
            # 上段レーンは急降下ボム機動
            _nudge_smooth(enemy, -_spd(enemy, 0.95), _spd(enemy, 1.85))
            if enemy.timer % 20 == 0:
                enemy.dash_bomb_now = True
        else:
            _nudge_smooth(enemy, float(enemy.vx_carry) * 1.35, float(enemy.vy_carry) * 1.05)
        if enemy.timer > 24 or enemy.rect.left < int(width * 0.58):
            enemy.grunt_phase = "sweep"
        return
    _layer_depth_motion(enemy, 1.55, y_sine=0.75)
    if enemy.timer % 48 == 0:
        _nudge_smooth(enemy, -_spd(enemy, 1.05), random.uniform(-1.1, 1.1))


def _ace_play_bounds(width: int, height: int, enemy) -> tuple[float, float, float, float]:
    from settings import GRUNT_ACE_PLAY_X_MAX_INSET, GRUNT_ACE_PLAY_X_MIN_RATIO

    half_h = enemy.rect.height * 0.5
    y_min = half_h + 10.0
    y_max = float(height) - half_h - 10.0
    x_min = -float(enemy.rect.width) - 80.0
    x_max = float(width) - float(enemy.rect.width) - float(GRUNT_ACE_PLAY_X_MAX_INSET)
    return x_min, x_max, y_min, y_max


def _clamp_ace_pos(enemy, width: int, height: int) -> None:
    _init_grunt_smooth_pos(enemy)
    x_min, x_max, y_min, y_max = _ace_play_bounds(width, height, enemy)
    if enemy._smooth_x < x_min:
        enemy._smooth_x = x_min
        enemy.ace_zig_x_dir = 1
    elif enemy._smooth_x > x_max:
        enemy._smooth_x = x_max
        enemy.ace_zig_x_dir = -1
    if enemy._smooth_y < y_min:
        enemy._smooth_y = y_min
        enemy.ace_zig_y_dir = 1
    elif enemy._smooth_y > y_max:
        enemy._smooth_y = y_max
        enemy.ace_zig_y_dir = -1
    enemy.base_y = enemy._smooth_y
    enemy.rect.x = int(round(enemy._smooth_x))
    enemy.rect.centery = int(round(enemy._smooth_y))


def _ace_begin_zigzag_segment(enemy, width: int, height: int) -> None:
    from settings import GRUNT_ACE_ZIG_SEG_MAX, GRUNT_ACE_ZIG_SEG_MIN

    y_dir = int(getattr(enemy, "ace_zig_y_dir", 1))
    x_dir = int(getattr(enemy, "ace_zig_x_dir", -1))
    enemy.ace_zig_y_dir = -y_dir
    enemy.ace_zig_x_dir = -x_dir if random.random() < 0.62 else x_dir

    _init_grunt_smooth_pos(enemy)
    _, _, y_min, y_max = _ace_play_bounds(width, height, enemy)
    mid = (y_min + y_max) * 0.5
    if enemy._smooth_y < mid - 48:
        enemy.ace_zig_y_dir = 1
    elif enemy._smooth_y > mid + 48:
        enemy.ace_zig_y_dir = -1

    enemy.ace_zig_seg = random.randint(GRUNT_ACE_ZIG_SEG_MIN, GRUNT_ACE_ZIG_SEG_MAX)


def _update_ace_zigzag(enemy, width: int, height: int) -> None:
    from settings import (
        GRUNT_ACE_ZIG_DURATION,
        GRUNT_ACE_ZIG_PRE_SNIPE_FRAMES,
        GRUNT_ACE_ZIG_X_SPEED_MUL,
        GRUNT_ACE_ZIG_Y_SPEED_MUL,
    )

    enemy.ace_zig_timer = int(getattr(enemy, "ace_zig_timer", 0)) + 1
    seg = int(getattr(enemy, "ace_zig_seg", 0))
    if seg <= 0:
        _ace_begin_zigzag_segment(enemy, width, height)
        seg = int(enemy.ace_zig_seg)

    if seg == GRUNT_ACE_ZIG_PRE_SNIPE_FRAMES:
        enemy.ace_snipe_now = True

    vy_dir = int(getattr(enemy, "ace_zig_y_dir", 1))
    vx_dir = int(getattr(enemy, "ace_zig_x_dir", -1))
    _nudge_smooth(
        enemy,
        vx_dir * _spd(enemy, GRUNT_ACE_ZIG_X_SPEED_MUL),
        vy_dir * _spd(enemy, GRUNT_ACE_ZIG_Y_SPEED_MUL),
    )
    _nudge_smooth(enemy, -_spd(enemy, 0.32), 0.0)
    _clamp_ace_pos(enemy, width, height)
    enemy.ace_zig_seg = seg - 1

    if enemy.ace_zig_timer >= GRUNT_ACE_ZIG_DURATION:
        enemy.ace_phase = "exit"


def _special_play_bounds(width: int, height: int, enemy) -> tuple[float, float, float, float]:
    half_h = enemy.rect.height * 0.5
    y_min = half_h + 16.0
    y_max = float(height) - half_h - 16.0
    x_min = float(width) * 0.22
    x_max = float(width) * 0.82
    return x_min, x_max, y_min, y_max


def _clamp_special_pos(enemy, width: int, height: int) -> None:
    _init_grunt_smooth_pos(enemy)
    x_min, x_max, y_min, y_max = _special_play_bounds(width, height, enemy)
    enemy._smooth_x = max(x_min, min(x_max, enemy._smooth_x))
    enemy._smooth_y = max(y_min, min(y_max, enemy._smooth_y))
    enemy.base_y = enemy._smooth_y
    enemy.rect.x = int(round(enemy._smooth_x))
    enemy.rect.centery = int(round(enemy._smooth_y))


def _special_teleport(enemy, width: int, height: int) -> None:
    x_min, x_max, y_min, y_max = _special_play_bounds(width, height, enemy)
    _init_grunt_smooth_pos(enemy)
    enemy._smooth_x = random.uniform(x_min, x_max)
    enemy._smooth_y = random.uniform(y_min, y_max)
    enemy.rect.x = int(round(enemy._smooth_x))
    enemy.rect.centery = int(round(enemy._smooth_y))
    enemy.base_y = enemy._smooth_y


def _special_dodge_bullets(enemy, width: int, height: int) -> None:
    """接近中の敵弾から離れる。"""
    from game_runtime import RT

    cx = float(enemy.rect.centerx)
    cy = float(enemy.rect.centery)
    avoid_x = 0.0
    avoid_y = 0.0
    radius = float(GRUNT_SPECIAL_DODGE_RADIUS)
    radius_sq = radius * radius

    def _accumulate(bx: float, by: float, bvx: float, bvy: float) -> None:
        nonlocal avoid_x, avoid_y
        dx = cx - bx
        dy = cy - by
        dist_sq = dx * dx + dy * dy
        if dist_sq > radius_sq or dist_sq < 1.0:
            return
        dist = max(1.0, dist_sq**0.5)
        weight = (radius - dist) / radius
        if bvx * dx + bvy * dy > 0:
            weight *= 1.35
        avoid_x += (dx / dist) * weight
        avoid_y += (dy / dist) * weight

    g = RT.g()
    for eb in g.get("enemy_bullets", []):
        _accumulate(
            float(eb.get("x", 0)),
            float(eb.get("y", 0)),
            float(eb.get("vx", 0)),
            float(eb.get("vy", 0)),
        )
    for el in g.get("enemy_lasers", []):
        _accumulate(
            float(getattr(el, "x", el.rect.centerx)),
            float(getattr(el, "y", el.rect.centery)),
            float(getattr(el, "vx", 0)),
            float(getattr(el, "vy", 0)),
        )

    if abs(avoid_x) + abs(avoid_y) < 0.05:
        return
    mag = (avoid_x * avoid_x + avoid_y * avoid_y) ** 0.5
    mul = GRUNT_SPECIAL_DODGE_STRENGTH * _spd(enemy, 0.42)
    _nudge_smooth(enemy, (avoid_x / mag) * mul, (avoid_y / mag) * mul)
    _clamp_special_pos(enemy, width, height)


def _update_special(enemy, width: int, height: int) -> None:
    phase = getattr(enemy, "special_phase", "enter")

    if phase == "enter":
        _nudge_smooth(enemy, -_spd(enemy, 1.15), 0.0)
        _special_dodge_bullets(enemy, width, height)
        _clamp_special_pos(enemy, width, height)
        if enemy.rect.left < int(width * 0.72):
            enemy.special_phase = "active"
            enemy.special_warp_cd = random.randint(
                GRUNT_SPECIAL_ACTIVE_WARP_CD_MIN, GRUNT_SPECIAL_ACTIVE_WARP_CD_MAX
            )
        return

    if phase == "active":
        _special_dodge_bullets(enemy, width, height)
        _nudge_smooth(enemy, -_spd(enemy, 0.18), math.sin(enemy.timer * 0.11) * 0.35)
        _clamp_special_pos(enemy, width, height)
        enemy.special_warp_cd = int(getattr(enemy, "special_warp_cd", 0)) - 1
        if enemy.special_warp_cd <= 0:
            enemy.special_phase = "warp"
            enemy.special_warp_timer = int(GRUNT_SPECIAL_WARP_FRAMES)
            enemy.entry_fx_timer = int(GRUNT_SPECIAL_WARP_FRAMES)
        return

    if phase == "warp":
        enemy.special_warp_timer = int(getattr(enemy, "special_warp_timer", 0)) - 1
        enemy.entry_fx_timer = max(int(getattr(enemy, "entry_fx_timer", 0)), enemy.special_warp_timer)
        mid = int(GRUNT_SPECIAL_WARP_FRAMES) // 2
        if enemy.special_warp_timer == mid:
            _special_teleport(enemy, width, height)
        if enemy.special_warp_timer <= 0:
            enemy.special_warps_done = int(getattr(enemy, "special_warps_done", 0)) + 1
            if enemy.special_warps_done >= int(GRUNT_SPECIAL_WARP_COUNT):
                enemy.special_phase = "exit"
            else:
                enemy.special_phase = "active"
                enemy.special_warp_cd = random.randint(
                    GRUNT_SPECIAL_ACTIVE_WARP_CD_MIN, GRUNT_SPECIAL_ACTIVE_WARP_CD_MAX
                )
        return

    if phase == "exit":
        _nudge_smooth(enemy, _spd(enemy, 2.75), 0.0)
        _clamp_y(enemy, height)
        return

    _nudge_smooth(enemy, -_spd(enemy, 0.5), 0.0)
    _clamp_special_pos(enemy, width, height)


def _update_ace(enemy, width: int, height: int) -> None:
    from grunt_ace_profiles import update_ace_by_profile

    update_ace_by_profile(enemy, width, height)


def draw_grunt_entry_fx(screen, enemy) -> None:
    t = int(getattr(enemy, "entry_fx_timer", 0))
    if t <= 0:
        return
    enemy.entry_fx_timer = t - 1
    cx, cy = enemy.rect.centerx, enemy.rect.centery
    pulse = 8 + (t % 6)
    alpha = min(200, 40 + t * 8)
    ring = pygame.Surface((pulse * 4, pulse * 4), pygame.SRCALPHA)
    pygame.draw.circle(ring, (100, 220, 255, alpha), (pulse * 2, pulse * 2), pulse, 2)
    screen.blit(ring, (cx - pulse * 2, cy - pulse * 2))
    shield = pygame.Surface((enemy.rect.width + 16, enemy.rect.height + 16), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shield,
        (80, 200, 255, min(120, 30 + t * 6)),
        shield.get_rect(),
        2,
    )
    screen.blit(
        shield,
        (enemy.rect.x - 8, enemy.rect.y - 8),
    )


def grunt_should_remove(enemy, width: int) -> bool:
    if getattr(enemy, "grunt_behavior", None) == BEH_SPECIAL:
        if getattr(enemy, "special_phase", "") == "exit":
            return enemy.rect.left > width + enemy.rect.width
        return False
    if getattr(enemy, "grunt_behavior", None) == BEH_ACE:
        if getattr(enemy, "ace_phase", "") == "exit":
            return enemy.rect.right < -48
    return enemy.rect.right < 0 or enemy.rect.left > width + enemy.rect.width


def spawn_death_scatter(enemy, bspd: float) -> None:
    if not getattr(enemy, "death_scatter", True):
        return
    from enemy_bullets import spawn_enemy_bullet

    n = int(getattr(enemy, "death_scatter_count", 8))
    cx, cy = enemy.rect.centerx, enemy.rect.centery
    for i in range(n):
        ang = math.radians(i * (360 / n) + random.uniform(-8, 8))
        spawn_enemy_bullet(
            x=float(cx),
            y=float(cy),
            vx=math.cos(ang) * bspd * random.uniform(0.5, 0.9),
            vy=math.sin(ang) * bspd * random.uniform(0.5, 0.9),
            image_type="normal",
        )


def make_death_ghost(enemy) -> dict:
    return {
        "rect": enemy.rect.copy(),
        "timer": 14,
        "mask_w": max(40, enemy.rect.width // 2),
        "mask_h": max(30, enemy.rect.height // 2),
    }


def _grunt_shot_interval(base_frames: int, diff) -> int:
    from settings import GRUNT_SHOOT_INTERVAL_MUL

    diff_mul = float(getattr(diff, "grunt_shoot_interval_mul", 1.0))
    return max(12, int(base_frames * GRUNT_SHOOT_INTERVAL_MUL * diff_mul))


def _spawn_grunt_bullet(**kwargs) -> None:
    from enemy_bullets import spawn_enemy_bullet
    from settings import GRUNT_BULLET_INDESTRUCTIBLE, GRUNT_BULLET_LIFE_FRAMES

    if GRUNT_BULLET_INDESTRUCTIBLE:
        kwargs["indestructible"] = True
    kwargs.setdefault("life", GRUNT_BULLET_LIFE_FRAMES)
    spawn_enemy_bullet(**kwargs)


def _spawn_snipe_bullet(cx: int, cy: int, speed: float, speed_mul: float = 1.0) -> None:
    from game_loop.resources import frame_core

    pl = frame_core().player
    dx = float(pl.rect.centerx - cx)
    dy = float(pl.rect.centery - cy)
    dist = max(1.0, math.hypot(dx, dy))
    spd = max(0.1, float(speed) * float(speed_mul))
    _spawn_grunt_bullet(
        x=cx,
        y=cy,
        vx=(dx / dist) * spd,
        vy=(dy / dist) * spd,
        image_type="normal",
    )


def _spawn_snipe_bullet_for_diff(cx: int, cy: int, speed: float, diff, speed_mul: float = 1.0) -> None:
    """NORMAL: 高速＋中速の2発。他難易度は従来どおり1発。"""
    from settings import GRUNT_SNIPE_SPEED_MUL

    if diff.name == "NORMAL" and getattr(diff, "enemy_pattern_normal", False):
        fast = float(getattr(diff, "enemy_bullet_fast_mul", 1.0))
        mid = float(getattr(diff, "enemy_bullet_mid_mul", 1.0))
        _spawn_snipe_bullet(cx, cy, speed, GRUNT_SNIPE_SPEED_MUL * speed_mul * fast)
        _spawn_snipe_bullet(
            cx,
            cy + random.randint(-12, 12),
            speed,
            GRUNT_SNIPE_SPEED_MUL * speed_mul * mid,
        )
        return
    _spawn_snipe_bullet(cx, cy, speed, GRUNT_SNIPE_SPEED_MUL * speed_mul)


def try_grunt_shoot(enemy, diff, width: int, height: int) -> None:
    if getattr(enemy, "grunt_behavior", None) == BEH_SPECIAL:
        return
    if grunt_invulnerable(enemy):
        return
    # 画面端でも撃てるように閾値を緩和（必ずスナイプさせる）
    if enemy.rect.right < width - 240 or enemy.rect.left < 40:
        return

    from settings import GRUNT_BULLET_SPEED_MUL, GRUNT_SNIPE_SPEED_MUL

    grunt_spd = float(getattr(diff, "grunt_bullet_spd_scale", 1.0))
    bspd = float(diff.enemy_bullet_spd) * GRUNT_BULLET_SPEED_MUL * grunt_spd
    cx = enemy.rect.centerx
    cy = enemy.rect.centery
    beh = enemy.grunt_behavior
    t = enemy.timer + getattr(enemy, "shot_offset", 0)

    if getattr(enemy, "needs_pop_shot", False) and not enemy.pop_shot_done:
        enemy.pop_shot_done = True
        enemy.needs_pop_shot = False
        _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff)
        return

    if beh == BEH_HIT_RUN and enemy.grunt_phase == "weave":
        if t % _grunt_shot_interval(38, diff) == 0:
            _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff, 1.1)
        return
    if beh == BEH_HIT_RUN and enemy.grunt_phase in ("u_turn_exit", "right_exit"):
        if t % _grunt_shot_interval(30, diff) == 0:
            _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff, 1.15)
        return

    if beh in (BEH_DASH, BEH_FORMATION_SINE) and enemy.grunt_phase in ("dive", "sweep"):
        if t % _grunt_shot_interval(52, diff) == 0:
            _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff)
        if beh == BEH_DASH and getattr(enemy, "dash_bomb_now", False):
            enemy.dash_bomb_now = False
            _spawn_grunt_bullet(
                x=cx,
                y=cy,
                vx=-bspd * 0.2,
                vy=bspd * 1.25,
                image_type="normal",
            )
        return

    if beh == BEH_WARP_BURST and enemy.grunt_phase == "burst":
        if t % _grunt_shot_interval(45, diff) == 0:
            _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff, 1.05)
        return

    if beh == BEH_ACE:
        from grunt_ace_profiles import try_ace_shoot_by_profile

        if try_ace_shoot_by_profile(enemy, diff, width, height, bspd):
            return

    # 非エースは最終的に必ずスナイプ射撃（挙動に依らないフォールバック）
    interval = _grunt_shot_interval(52, diff)
    if enemy.grunt_phase in ("dive", "burst", "weave", "exit", "u_turn_exit", "right_exit", "sweep"):
        if t % interval == 0:
            _spawn_snipe_bullet_for_diff(cx, cy, bspd, diff)
