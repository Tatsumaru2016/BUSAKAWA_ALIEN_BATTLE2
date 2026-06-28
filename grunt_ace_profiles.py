# grunt_ace_profiles.py — エース4機: タイプ固定の移動・攻撃

from __future__ import annotations

import math
import random

from settings import (
    ENEMY_TYPE_ACE_FIRST,
    GRUNT_ACE_BOMBER_BOMB_COUNT,
    GRUNT_ACE_BOMBER_BOMB_SPEED_Y,
    GRUNT_ACE_BOMBER_SPEED_MUL,
    GRUNT_ACE_EXIT_SPEED_MUL,
    GRUNT_ACE_SNIPE_SPEED_MUL,
    GRUNT_ACE_ZIG_PRE_SNIPE_FRAMES,
    GRUNT_ACE_ZIG_SEG_MAX,
    GRUNT_ACE_ZIG_SEG_MIN,
    GRUNT_ACE_ZIG_X_SPEED_MUL,
    GRUNT_ACE_ZIG_Y_SPEED_MUL,
    PLAY_TOP_MARGIN,
    ace_style_for_type,
    is_enemy_ace_type,
)

# enemy_ace01〜04（type 8〜11）と1:1
ACE_STYLE_ZIGZAG = "zigzag"        # 01: ジグザグ＋曲がり前スナイプ
ACE_STYLE_DASH = "dash"            # 02: 自機方向ダッシュ＋扇撃ち→左退場
ACE_STYLE_SINE_SPRAY = "sine_spray"  # 03: 大振幅サイン＋5way拡散→左退場
ACE_STYLE_BOMBER_RUN = "bomber_run"  # 04: 上部高速通過＋爆弾投下（旧ホバー）


def init_ace_profile(enemy) -> None:
    """エース機の ace_style / フェーズを機体タイプで初期化。"""
    style = ace_style_for_type(int(enemy.type))
    enemy.ace_style = style
    enemy.ace_phase = "enter"
    enemy.ace_snipe_now = False
    enemy.ace_attack_now = False
    enemy.ace_fight_timer = 0

    if style == ACE_STYLE_ZIGZAG:
        enemy.ace_zig_timer = 0
        enemy.ace_zig_seg = 0
        enemy.ace_zig_y_dir = random.choice([-1, 1])
        enemy.ace_zig_x_dir = random.choice([-1, 1])
    elif style == ACE_STYLE_DASH:
        enemy.dash_timer = 0
        enemy.aim_applied = False
    elif style == ACE_STYLE_SINE_SPRAY:
        enemy.sin_amp = random.uniform(88, 108)
        enemy.sin_freq = random.uniform(0.072, 0.095)
        enemy.ace_spray_cd = 36
    elif style == ACE_STYLE_BOMBER_RUN:
        enemy.ace_bomb_xs = []
        enemy.ace_bombs_dropped = 0
        enemy.ace_run_y = 0


def _gb():
    import grunt_behavior as gb

    return gb


def _spd(enemy, mul: float) -> float:
    return _gb()._spd(enemy, mul)


def _nudge(enemy, dx: float, dy: float) -> None:
    _gb()._nudge_smooth(enemy, dx, dy)


def _clamp_ace(enemy, width: int, height: int) -> None:
    _gb()._clamp_ace_pos(enemy, width, height)


def _clamp_y(enemy, height: int) -> None:
    _gb()._clamp_y(enemy, height)


def _move_left(enemy, mul: float) -> None:
    _gb()._move_left(enemy, mul)


def _apply_y_sine(enemy, scale: float = 1.0) -> None:
    _gb()._apply_y_sine(enemy, scale)


def _apply_aim_once(enemy) -> None:
    _gb()._apply_aim_once(enemy)


def _grunt_shot_interval(base: int, diff) -> int:
    return _gb()._grunt_shot_interval(base, diff)


def _spawn_snipe(cx: int, cy: int, speed: float, diff, mul: float = 1.0) -> None:
    _gb()._spawn_snipe_bullet_for_diff(cx, cy, speed, diff, mul)


def _spawn_bullet(**kwargs) -> None:
    _gb()._spawn_grunt_bullet(**kwargs)


def _aimed_burst(cx: int, cy: int, bspd: float, angles_deg: tuple[float, ...], speed_mul: float = 1.0) -> None:
    spd = bspd * speed_mul
    for deg in angles_deg:
        rad = math.radians(deg)
        _spawn_bullet(
            x=cx,
            y=cy,
            vx=math.cos(rad) * spd,
            vy=math.sin(rad) * spd,
            image_type="normal",
        )


def _ace_fast_exit(enemy, height: int) -> None:
    _nudge(enemy, -_spd(enemy, GRUNT_ACE_EXIT_SPEED_MUL), 0.0)
    _clamp_y(enemy, height)


def _ace_begin_exit(enemy, height: int) -> None:
    enemy.ace_phase = "exit"
    _ace_fast_exit(enemy, height)


def _aimed_at_player(cx: int, cy: int, bspd: float, spread_deg: float = 0.0, speed_mul: float = 1.0) -> None:
    from game_loop.resources import frame_core

    pl = frame_core().player
    dx = pl.rect.centerx - cx
    dy = pl.rect.centery - cy
    base = math.degrees(math.atan2(dy, dx))
    _aimed_burst(cx, cy, bspd, (base + spread_deg,), speed_mul)


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


def _update_ace_zigzag_style(enemy, width: int, height: int) -> None:
    phase = enemy.ace_phase
    if phase == "enter":
        _nudge(enemy, -_spd(enemy, 1.85), 0.0)
        _clamp_ace(enemy, width, height)
        if enemy.rect.left < width - 200:
            enemy.ace_phase = "zigzag"
            enemy.ace_zig_timer = 0
            enemy.ace_zig_seg = random.randint(GRUNT_ACE_ZIG_SEG_MIN, GRUNT_ACE_ZIG_SEG_MAX)
        return
    if phase == "zigzag":
        _gb()._update_ace_zigzag(enemy, width, height)
        return
    if phase == "exit":
        _ace_fast_exit(enemy, height)
        return
    _nudge(enemy, -_spd(enemy, 1.45), 0.0)
    _clamp_ace(enemy, width, height)


def _update_ace_dash_style(enemy, width: int, height: int) -> None:
    phase = enemy.ace_phase
    if phase == "enter":
        _nudge(enemy, -_spd(enemy, 1.75), 0.0)
        _clamp_ace(enemy, width, height)
        if enemy.rect.left < int(width * 0.72):
            enemy.ace_phase = "dash"
            enemy.dash_timer = 0
            _apply_aim_once(enemy)
        return
    if phase == "dash":
        enemy.dash_timer = int(getattr(enemy, "dash_timer", 0)) + 1
        _nudge(enemy, float(getattr(enemy, "vx_carry", -5.5)) * 1.35, float(getattr(enemy, "vy_carry", 0)) * 1.35)
        _nudge(enemy, -_spd(enemy, 0.55), 0.0)
        _clamp_ace(enemy, width, height)
        if enemy.dash_timer >= 28:
            enemy.ace_attack_now = True
        return
    if phase == "exit":
        _ace_fast_exit(enemy, height)
        return


def _update_ace_sine_spray_style(enemy, width: int, height: int) -> None:
    phase = enemy.ace_phase
    if phase == "enter":
        _nudge(enemy, -_spd(enemy, 1.7), 0.0)
        _clamp_ace(enemy, width, height)
        if enemy.rect.left < int(width * 0.68):
            enemy.ace_phase = "sweep"
            enemy.ace_fight_timer = 0
            enemy.ace_spray_cd = 18
        return
    if phase == "sweep":
        enemy.ace_fight_timer = int(getattr(enemy, "ace_fight_timer", 0)) + 1
        pulse = 1.0 + math.sin(enemy.timer * 0.1) * 0.14
        _move_left(enemy, 1.25 * pulse)
        ph = float(getattr(enemy, "formation_phase", 0.0)) + enemy.timer * float(enemy.sin_freq)
        enemy.rect.y = int(enemy.base_y + math.sin(ph) * float(enemy.sin_amp))
        _clamp_ace(enemy, width, height)
        cd = int(getattr(enemy, "ace_spray_cd", 0)) - 1
        enemy.ace_spray_cd = cd
        if cd <= 0:
            enemy.ace_attack_now = True
        return
    if phase == "exit":
        _ace_fast_exit(enemy, height)
        return


def _update_ace_bomber_run_style(enemy, width: int, height: int) -> None:
    """画面上部を右→左へ高速通過し、エクストラ型爆弾を多めに投下。"""
    from enemy_bullets import (
        _striker_bomb_drop_x_positions,
        spawn_extra_striker_bomb,
    )

    phase = enemy.ace_phase
    run_y = int(getattr(enemy, "ace_run_y", 0) or (PLAY_TOP_MARGIN + enemy.rect.height // 2))

    if phase == "enter":
        enemy.ace_run_y = PLAY_TOP_MARGIN + enemy.rect.height // 2
        enemy.rect.centery = enemy.ace_run_y
        enemy.rect.left = width + enemy.rect.width
        enemy.ace_bomb_xs = _striker_bomb_drop_x_positions(
            width, GRUNT_ACE_BOMBER_BOMB_COUNT
        )
        enemy.ace_bombs_dropped = 0
        enemy.ace_phase = "bomb_run"
        return

    if phase == "bomb_run":
        enemy.rect.centery = run_y
        _nudge(enemy, -_spd(enemy, GRUNT_ACE_BOMBER_SPEED_MUL), 0.0)
        bomb_xs = list(getattr(enemy, "ace_bomb_xs", None) or [])
        dropped = int(getattr(enemy, "ace_bombs_dropped", 0) or 0)
        drop_y = float(enemy.rect.bottom - 6)
        while dropped < len(bomb_xs) and float(enemy.rect.centerx) <= float(bomb_xs[dropped]):
            spawn_extra_striker_bomb(
                float(enemy.rect.centerx),
                drop_y,
                speed_y=GRUNT_ACE_BOMBER_BOMB_SPEED_Y,
            )
            dropped += 1
        enemy.ace_bombs_dropped = dropped
        if dropped >= len(bomb_xs) and enemy.rect.right < int(width * 0.08):
            enemy.ace_phase = "exit"
        elif enemy.rect.right < -enemy.rect.width:
            enemy.ace_phase = "exit"
        return

    if phase == "exit":
        enemy.rect.centery = run_y
        _ace_fast_exit(enemy, height)
        return


def update_ace_by_profile(enemy, width: int, height: int) -> None:
    style = getattr(enemy, "ace_style", ACE_STYLE_ZIGZAG)
    if style == ACE_STYLE_DASH:
        _update_ace_dash_style(enemy, width, height)
    elif style == ACE_STYLE_SINE_SPRAY:
        _update_ace_sine_spray_style(enemy, width, height)
    elif style == ACE_STYLE_BOMBER_RUN:
        _update_ace_bomber_run_style(enemy, width, height)
    else:
        _update_ace_zigzag_style(enemy, width, height)


# ---------------------------------------------------------------------------
# 攻撃
# ---------------------------------------------------------------------------


def try_ace_shoot_by_profile(
    enemy, diff, width: int, height: int, bspd: float
) -> bool:
    """エース射撃を処理したら True。"""
    if not is_enemy_ace_type(int(enemy.type)):
        return False

    style = getattr(enemy, "ace_style", ace_style_for_type(int(enemy.type)))
    cx = enemy.rect.centerx
    cy = enemy.rect.centery
    t = enemy.timer + getattr(enemy, "shot_offset", 0)
    phase = getattr(enemy, "ace_phase", "enter")

    if style == ACE_STYLE_ZIGZAG:
        if not getattr(enemy, "ace_snipe_now", False):
            return True
        enemy.ace_snipe_now = False
        if phase not in ("zigzag", "enter"):
            return True
        _aimed_at_player(cx, cy, bspd * GRUNT_ACE_SNIPE_SPEED_MUL)
        return True

    if style == ACE_STYLE_BOMBER_RUN:
        return True

    if style == ACE_STYLE_DASH:
        if getattr(enemy, "ace_attack_now", False):
            enemy.ace_attack_now = False
            from game_loop.resources import frame_core

            pl = frame_core().player
            base = math.degrees(
                math.atan2(pl.rect.centery - cy, pl.rect.centerx - cx)
            )
            _aimed_burst(
                cx,
                cy,
                bspd,
                (base - 20.0, base, base + 20.0),
                GRUNT_ACE_SNIPE_SPEED_MUL * 0.95,
            )
            _ace_begin_exit(enemy, height)
            return True
        return True

    if style == ACE_STYLE_SINE_SPRAY:
        if getattr(enemy, "ace_attack_now", False):
            enemy.ace_attack_now = False
            from game_loop.resources import frame_core

            pl = frame_core().player
            base = math.degrees(
                math.atan2(pl.rect.centery - cy, pl.rect.centerx - cx)
            )
            _aimed_burst(
                cx,
                cy,
                bspd,
                tuple(base - 24.0 + i * 12.0 for i in range(5)),
                GRUNT_ACE_SNIPE_SPEED_MUL * 0.88,
            )
            _ace_begin_exit(enemy, height)
            return True
        return True

    return False
