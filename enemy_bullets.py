# enemy_bullets.py — 敵弾の生成・更新・描画

import math
import random

import pygame

from bullet import Bullet
from explosion import Explosion, ExtraStrikerBombExplosion
from game_runtime import RT
from homing_bullet import update_homing_bullet
from settings import (
    BOSS5_ENEMY_LASER_LENGTH,
    BOSS5_LASER_SPEED_SCALE,
    ENEMY_BULLET_LIFE_FRAMES,
    ENEMY_BULLET_MIN_SPEED,
    PLAYER_MAX_WEAPON_LEVEL,
    RED,
    WHITE,
)


def g():
    return RT.g()


def _b1_ground_max_len():
    return g()["HEIGHT"] // 2


def eb_v(eb, key, default=0.0):
    return float(eb.get(key, default))


# 寿命で消さず、攻撃エンティティとして life を使う attack_type
_BOSS_BULLET_ENTITY_ATTACKS = frozenset({
    "b3_ufo_fleet",
    "b1_ground_tentacle",
    "b1_tentacle_curtain",
    "b1_diagonal_ripple",
    "b1_sidewinder",
    "b2_fish_swarm",
    "extra_striker",
    "extra_robot_homing_charge",
})


_HOMING_IMAGE_TYPES = frozenset({
    "homing",
    "boss_homing",
    "boss1_homing",
    "boss2_homing",
    "boss3_homing",
    "turret_homing",
    "ripple_homing",
})


def is_homing_enemy_bullet(eb: dict) -> bool:
    """追尾弾（homing フラグまたは専用 image_type）。"""
    if eb.get("homing"):
        return True
    return eb.get("image_type", "") in _HOMING_IMAGE_TYPES


def enemy_bullet_destructible_by_player(eb: dict) -> bool:
    """自機弾で撃破できる敵弾か。"""
    if eb.get("indestructible"):
        return False
    if eb.get("destructible"):
        return True
    if eb.get("attack_type") == "b1_diagonal_ripple":
        return True
    return is_homing_enemy_bullet(eb)


def _boss_bullet_keeps_life(bullet: dict) -> bool:
    if bullet.get("bullet_life"):
        return True
    return bullet.get("attack_type") in _BOSS_BULLET_ENTITY_ATTACKS


def _apply_boss_bullet_offscreen_rule(bullet: dict) -> None:
    """ボス弾: 追尾のみ life、その他は offscreen_only。"""
    if not bullet.get("is_boss_bullet"):
        return
    if _boss_bullet_keeps_life(bullet):
        return
    if is_homing_enemy_bullet(bullet):
        bullet.pop("offscreen_only", None)
        if "life" not in bullet:
            bullet["life"] = int(
                bullet.get("bullet_life", ENEMY_BULLET_LIFE_FRAMES)
            )
        return
    bullet["offscreen_only"] = True
    bullet.pop("life", None)


def _clamp_enemy_bullet_speed(eb: dict, max_spd: float) -> None:
    vx = float(eb.get("vx", 0))
    vy = float(eb.get("vy", 0))
    spd = math.hypot(vx, vy)
    cap = float(max_spd)
    if spd <= cap or spd < 0.01:
        return
    scale = cap / spd
    eb["vx"] = vx * scale
    eb["vy"] = vy * scale


def finalize_boss_enemy_bullet(eb: dict) -> dict:
    """難易度スケールを適用してからリストへ追加する直前処理。"""
    eb.setdefault("is_boss_bullet", True)
    g()["diff"].scale_bullet(eb)
    _apply_boss_bullet_offscreen_rule(eb)
    return eb


def append_boss_enemy_bullet(eb: dict) -> dict:
    g()["enemy_bullets"].append(finalize_boss_enemy_bullet(eb))
    return eb


def spawn_enemy_bullet(**kwargs):
    bullet = {
        "vx": 0.0,
        "vy": 0.0,
        "homing": False,
        "is_boss_bullet": False,
        "image_type": "normal",
        "hp": 1,
    }
    bullet.update(kwargs)
    if not bullet.get("allow_zero_velocity") and abs(eb_v(bullet, "vx")) + abs(eb_v(bullet, "vy")) < 0.01:
        bullet["vx"] = -4.0
    intended_vx = eb_v(bullet, "vx")
    # 難易度による弾速スケール適用
    g()["diff"].scale_bullet(bullet)

    # ★ 最低速度保証: スクロール速度より遅い合成速度は補正
    vx = eb_v(bullet, "vx")
    vy = eb_v(bullet, "vy")
    if bullet.get("is_boss_bullet", False) and intended_vx < -0.01 and vx > 0:
        vx = -abs(vx)
        bullet["vx"] = vx
    spd = math.hypot(vx, vy)
    min_spd = (
        g()["diff"].enemy_bullet_min_speed()
        if not bullet.get("is_boss_bullet", False)
        else ENEMY_BULLET_MIN_SPEED
    )
    if (
        not bullet.get("is_boss_bullet", False)
        and spd < min_spd
        and spd > 0.01
    ):
        scale = min_spd / spd
        bullet["vx"] = vx * scale
        bullet["vy"] = vy * scale
    elif spd < 0.01 and not bullet.get("allow_zero_velocity"):
        bullet["vx"] = -min_spd
        bullet["vy"] = 0.0

    _apply_boss_bullet_offscreen_rule(bullet)

    # 寿命は追尾弾のみ（明示 life / 攻撃エンティティを除く）
    if (
        not bullet.get("is_boss_bullet")
        and is_homing_enemy_bullet(bullet)
        and "life" not in bullet
        and not bullet.get("offscreen_only")
    ):
        bullet["life"] = ENEMY_BULLET_LIFE_FRAMES

    g()["enemy_bullets"].append(bullet)
    return bullet


def spawn_boss4_strip_sniper_bullet(
    x: float,
    y: float,
    px: float,
    py: float,
    *,
    from_top: bool,
    speed: float = 12.5,
) -> dict:
    """ボス4上下帯: プレイ座標で自機へ直進スナイプ（方向を帯種別で補正）。"""
    if g()["diff"].name == "EASY":
        speed *= 0.88
    fx, fy = float(x), float(y)
    dx = float(px) - fx
    dy = float(py) - fy
    if from_top:
        if dy <= 4.0:
            fy = min(fy, float(py) - 28.0)
            dy = float(py) - fy
        dy = max(dy, 12.0)
    else:
        if dy >= -4.0:
            fy = max(fy, float(py) + 28.0)
            dy = float(py) - fy
        dy = min(dy, -12.0)
    dist = max(1.0, math.hypot(dx, dy))
    dir_x = dx / dist
    dir_y = dy / dist
    eb = spawn_enemy_bullet(
        x=fx,
        y=fy,
        vx=dir_x * speed,
        vy=dir_y * speed,
        homing=False,
        is_boss_bullet=True,
        image_type="boss4_turret_bullet",
        special_attack=True,
    )
    # scale_bullet 後も自機方向を維持
    spd = max(ENEMY_BULLET_MIN_SPEED, math.hypot(eb_v(eb, "vx"), eb_v(eb, "vy")))
    eb["vx"] = dir_x * spd
    eb["vy"] = dir_y * spd
    eb["boss4_strip_sniper"] = True
    eb["boss4_strip_from_top"] = from_top
    return eb


def spawn_enemy_laser(x, y, vx, vy, speed=14.0, life=120, laser_length=None, laser_variant="red"):
    """敵レーザー。上下で反射する。variant: red / giant_orange など。"""
    laser = Bullet(x, y, g()["laser_img"], damage=1, is_laser=True, laser_variant=laser_variant, speed=speed)
    laser.vx = float(vx)
    laser.vy = float(vy)
    laser.life = life
    laser.bounce_count = 0
    if laser_length is not None:
        laser.laser_length = laser_length
    g()["enemy_lasers"].append(laser)
    return laser


def _b1_ground_tentacle_palette(eb) -> dict:
    colors = eb.get("tentacle_colors")
    if isinstance(colors, dict):
        return colors
    return {
        "outer": (30, 140, 210),
        "inner": (100, 220, 255),
        "base": (70, 200, 255),
        "tip": (210, 255, 255),
    }


def b1_ground_tentacle_count() -> int:
    return sum(
        1
        for eb in g()["enemy_bullets"]
        if eb.get("attack_type") == "b1_ground_tentacle" and eb.get("life", 0) > 0
    )


# 地面触手（Boss1 HP50%以下）
B1_GROUND_TENTACLE_COUNT = 3
B1_GROUND_TENTACLE_BOSS_GAP = 140
B1_GROUND_TENTACLE_MIN_SPACING = 88
B1_GROUND_TENTACLE_LEN_MIN = 80
B1_GROUND_TENTACLE_PLAYER_CLEAR_Y = 58  # 自機中心からの縦余白（触手先端が入らない）


def pick_b1_ground_tentacle_xs(boss, width: int, count: int = B1_GROUND_TENTACLE_COUNT) -> list[float]:
    """中央より左のみ・ボス直左除外・count 本の X を重ならないよう分割配置。"""
    x_min = int(width * 0.10)
    x_cap = int(width * 0.46)
    boss_cap = int(boss.rect.left) - B1_GROUND_TENTACLE_BOSS_GAP
    x_max = max(x_min + 72, min(x_cap, boss_cap))
    span = float(x_max - x_min)
    if span <= 0 or count <= 0:
        return [float(x_min)] * max(1, count)
    chunk = span / float(count)
    if chunk < B1_GROUND_TENTACLE_MIN_SPACING * 0.85:
        return [x_min + chunk * (i + 0.5) for i in range(count)]
    xs: list[float] = []
    for i in range(count):
        lo = x_min + i * chunk + 6.0
        hi = x_min + (i + 1) * chunk - 6.0
        xs.append(random.uniform(lo, max(lo + 1.0, hi)))
    return xs


def _b1_ground_tentacle_len_bounds(y: float, from_top: bool) -> tuple[float, float]:
    """触手長さの [最小, 最大]。中心（自機付近）まで伸びない。"""
    height = float(g()["HEIGHT"])
    top_m = float(g().get("PLAY_TOP_MARGIN", 12))
    lo = float(B1_GROUND_TENTACLE_LEN_MIN)
    hard = float(_b1_ground_max_len())
    player = g().get("player")
    if player is not None:
        py = float(player.rect.centery)
        clear = float(B1_GROUND_TENTACLE_PLAYER_CLEAR_Y)
        if from_top:
            cap = (py - clear) - float(y)
        else:
            cap = float(y) - (py + clear)
    else:
        cap = hard
    cap = min(hard, cap, height * 0.36)
    if from_top:
        cap = min(cap, height * 0.52 - float(y))
    else:
        cap = min(cap, float(y) - top_m - 36.0)
    hi = max(lo, cap)
    return lo, hi


def b1_ground_tentacle_retract_all() -> None:
    """特殊攻撃終了時に地面触手を縮めて消す。"""
    for eb in g()["enemy_bullets"]:
        if eb.get("attack_type") == "b1_ground_tentacle":
            eb["state"] = "retract"


def _b1_purge_legacy_curtain_tentacles() -> None:
    """旧カーテン触手（ボス直左の浮遊表示）を除去。"""
    bullets = g()["enemy_bullets"]
    for eb in bullets[:]:
        if eb.get("attack_type") == "b1_tentacle_curtain":
            bullets.remove(eb)


def spawn_b1_ground_tentacle(
    x,
    *,
    from_top: bool = False,
    tentacle_colors=None,
    boss=None,
):
    """ボス1: 中央左エリアから上／下へ伸びる触手（ボス直左は不可）。"""
    kwargs = {}
    if tentacle_colors is not None:
        kwargs["tentacle_colors"] = tentacle_colors
    width = int(g()["WIDTH"])
    x_min = int(width * 0.10)
    x_cap = int(width * 0.46)
    if boss is not None:
        x_cap = min(x_cap, int(boss.rect.left) - B1_GROUND_TENTACLE_BOSS_GAP)
    x = max(float(x_min), min(float(x), float(max(x_min + 8, x_cap))))
    height = float(g()["HEIGHT"])
    top_m = float(g().get("PLAY_TOP_MARGIN", 36))
    if from_top:
        # 根元は HUD（プレイ領域上端）境界付近
        y = top_m + random.uniform(8.0, 16.0)
    else:
        y = height - 14.0
    len_lo, len_hi = _b1_ground_tentacle_len_bounds(y, from_top)
    tentacle_len_max = random.uniform(len_lo, len_hi)
    spawn_enemy_bullet(
        x=float(x),
        y=float(y),
        vx=0.0,
        vy=0.0,
        allow_zero_velocity=True,
        is_boss_bullet=True,
        image_type="boss1_bullet",
        special_attack=True,
        attack_type="b1_ground_tentacle",
        b1_from_top=bool(from_top),
        spawn_anchor_x=float(x),
        tentacle_len=0.0,
        tentacle_len_max=float(tentacle_len_max),
        tentacle_grow=random.uniform(5.0, 7.0),
        wave_phase=random.random() * math.tau,
        wave_amp=random.randint(14, 26),
        hold_at_max_frames=38,
        tentacle_retract=16.0,
        state="extend",
        life=130,
        **kwargs,
    )


def _b1_ground_tentacle_sway(eb, timer: int, t: float) -> float:
    """触手の横揺れ。ボス側（+X）へ大きく伸びないよう上限。"""
    phase = eb.get("wave_phase", 0.0)
    amp = float(eb.get("wave_amp", 18))
    sway = math.sin(timer * 0.12 + phase + t * 5.2) * amp
    anchor = float(eb.get("spawn_anchor_x", eb["x"]))
    return min(sway, max(0.0, anchor + 12.0 - float(eb["x"])))


def spawn_b1_ground_tentacle_wave(boss, *, tentacle_colors=None) -> None:
    """上下から合計3本。X は重ならず、長さはランダム（中心／自機帯には届かない）。"""
    _b1_purge_legacy_curtain_tentacles()
    width = int(g()["WIDTH"])
    xs = pick_b1_ground_tentacle_xs(boss, width, B1_GROUND_TENTACLE_COUNT)
    origins = [True, False, random.choice((True, False))]
    random.shuffle(origins)
    for tx, from_top in zip(xs, origins):
        spawn_b1_ground_tentacle(
            tx,
            from_top=from_top,
            tentacle_colors=tentacle_colors,
            boss=boss,
        )


def spawn_boss2_fish_swarm(boss, count=3):
    """ボス2 HP25%以下: 上・中・下レーンに1匹ずつ、サインカーブで左へ。"""
    del count  # 常に3匹（レーン各1）
    play_h = float(g()["HEIGHT"])
    fish_hp = 2
    fish_vx = -9.2
    sine_amp = 54.0
    sine_omega = 0.105
    lanes_y = (
        play_h * 0.22,
        play_h * 0.50,
        play_h * 0.78,
    )
    spawn_x = (
        float(boss.rect.left - 44),
        float(boss.rect.left - 72),
        float(boss.rect.left - 100),
    )
    for lane_i, lane_y in enumerate(lanes_y):
        spawn_enemy_bullet(
            x=spawn_x[lane_i],
            y=float(lane_y),
            vx=fish_vx,
            vy=0.0,
            is_boss_bullet=False,
            image_type="boss2_fish",
            special_attack=False,
            attack_type="b2_fish_swarm",
            hp=fish_hp,
            life=320,
            sine_lane_y=float(lane_y),
            sine_amp=sine_amp,
            sine_omega=sine_omega,
            sine_phase=lane_i * (math.tau / 3.0),
            fish_timer=0,
        )


def spawn_boss3_giant_laser(boss, player):
    """ボス3 HP25%以下: ボス左端から左へ伸びる巨大ビーム（根元固定・弱追尾）。"""
    if g()["laser_warning_sound"]:
        g()["laser_warning_sound"].play()
    ax = float(boss.rect.left - 16)
    ay = float(boss.rect.centery)
    dx = float(player.rect.centerx) - ax
    dy = float(player.rect.centery) - ay
    angle = math.atan2(dy, max(1.0, abs(dx)))
    angle = max(math.radians(158), min(math.radians(202), angle))
    laser = Bullet(
        int(ax), int(ay), g()["laser_img"],
        damage=1, is_laser=True, laser_variant="giant_orange", speed=0,
    )
    laser.vx = 0.0
    laser.vy = 0.0
    scale = max(0.52, float(g()["diff"].bullet_spd_scale))
    laser.life = max(110, int(120 / scale))
    laser.bounce_count = 0
    laser.laser_length = 960
    laser.beam_no_bounce = True
    laser.beam_from_anchor = True
    laser.beam_track_boss = True
    laser.beam_angle = angle
    laser.angle = angle
    g()["enemy_lasers"].append(laser)
    return laser

def _beam_length_to_left_offscreen(
    ax: float,
    ay: float,
    angle: float,
    *,
    margin: float = 200.0,
) -> int:
    """根本（ax,ay）から角度方向に左画面外までのビーム描画長。"""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    height = g()["HEIGHT"]
    dists: list[float] = []
    if cos_a < -0.01:
        dists.append((ax + margin) / abs(cos_a))
    if sin_a < -0.01:
        dists.append((ay + margin) / abs(sin_a))
    elif sin_a > 0.01:
        dists.append((height + margin - ay) / sin_a)
    if not dists:
        return int(g()["WIDTH"]) + 400
    return int(max(dists)) + 96


def _draw_extra_beam_orb_bullet(screen: pygame.Surface, cx: int, cy: int) -> None:
    """ビーム弾: 充填エフェクトと同系統の紫球体。"""
    pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.02)
    r_outer = int(15 * pulse)
    pygame.draw.circle(screen, (90, 20, 160), (cx, cy), r_outer)
    pygame.draw.circle(screen, (140, 40, 220), (cx, cy), int(11 * pulse))
    pygame.draw.circle(screen, (200, 90, 255), (cx, cy), 8)
    pygame.draw.circle(screen, (230, 160, 255), (cx, cy), 5)
    pygame.draw.circle(screen, (255, 230, 255), (cx, cy), 2)


EXTRA_MOVING_BEAM_LENGTH = 72

# ビーム砲（紫球）: 難易度スケール後の上限（EASY 第一・第二形態が速すぎる対策）
BEAM_ORB_SPEED_CAP_BY_DIFF = {
    "EASY": 7.0,
    "NORMAL": 10.0,
    "HARD": 12.0,
    "NIGHTMARE": 15.0,
}

# エクストラボス バルカン（第一形態タンク機関砲・第二形態頭部）: スケール後上限
EXTRA_VULCAN_BULLET_SPEED_CAP_BY_DIFF = {
    "EASY": 7.0,
    "NORMAL": 10.0,
    "HARD": 12.0,
    "NIGHTMARE": 15.0,
}


def _apply_extra_vulcan_speed_cap(eb: dict) -> None:
    cap = EXTRA_VULCAN_BULLET_SPEED_CAP_BY_DIFF.get(g()["diff"].name)
    if cap is not None:
        _clamp_enemy_bullet_speed(eb, cap)


def _extra_boss_bullet_life(
    x: float,
    y: float,
    vx: float,
    vy: float,
    width: int,
    height: int,
) -> int:
    """エクストラ弾: 画面外に出たらすぐ消えるよう余計な寿命を付けない。"""
    return _vulcan_life_until_offscreen(
        x, y, vx, vy, width, height, margin=36.0,
    )


def spawn_extra_beam_orb_shot(
    mx: float,
    my: float,
    player,
    *,
    speed: float = 12.0,
) -> dict:
    """エクストラボス: ビーム弾（自機狙いの紫球体・単発）。"""
    dx = float(player.rect.centerx) - float(mx)
    dy = float(player.rect.centery) - float(my)
    angle = math.atan2(dy, dx)
    spd = float(speed)
    vx = math.cos(angle) * spd
    vy = math.sin(angle) * spd
    bullet = spawn_enemy_bullet(
        x=float(mx),
        y=float(my),
        vx=vx,
        vy=vy,
        homing=False,
        is_boss_bullet=True,
        image_type="extra_beam_orb",
    )
    bullet["extra_beam_orb"] = True
    bullet["offscreen_only"] = True
    bullet.pop("life", None)
    cap = BEAM_ORB_SPEED_CAP_BY_DIFF.get(g()["diff"].name)
    if cap is not None:
        _clamp_enemy_bullet_speed(bullet, cap)
    return bullet


def spawn_extra_tank_machine_gun(
    x: float,
    y: float,
    player,
    *,
    speed: float = 11.0,
    bullets: int = 3,
    spread_rad: float = 0.07,
) -> None:
    """エクストラボス第一形態: 機関砲（黄色弾・自機狙い）。"""
    dx = float(player.rect.centerx) - float(x)
    dy = float(player.rect.centery) - float(y)
    base = math.atan2(dy, dx)

    width = g()["WIDTH"]
    height = g()["HEIGHT"]
    for i in range(bullets):
        off = (i - (bullets - 1) / 2.0) * spread_rad
        ang = base + off
        vx = math.cos(ang) * float(speed)
        vy = math.sin(ang) * float(speed)
        life = _extra_boss_bullet_life(x, y, vx, vy, width, height)
        eb = spawn_enemy_bullet(
            x=float(x),
            y=float(y),
            vx=vx,
            vy=vy,
            homing=False,
            is_boss_bullet=True,
            image_type="extra_vulcan",
            offscreen_only=True,
        )
        _apply_extra_vulcan_speed_cap(eb)


# ストライカー爆弾：落下途中ランダム爆発 → explosion_zako×3（弾拡散なし・各爆発に当たり）
STRIKER_BOMB_FUSE_MIN = 22
STRIKER_BOMB_FUSE_MAX = 92
STRIKER_BOMB_BURST_COUNT = 3
STRIKER_BOMB_BURST_OFFSET_X = 58
STRIKER_BOMB_BURST_OFFSET_Y = 46
STRIKER_BOMB_BURST_SCALE_MIN = 0.82
STRIKER_BOMB_BURST_SCALE_MAX = 1.18


def _striker_bomb_fuse_frames(y: float, speed_y: float) -> int:
    """落下途中でランダムに起爆するまでのフレーム数。"""
    height = float(g()["HEIGHT"])
    fall_frames = int(max(STRIKER_BOMB_FUSE_MIN + 4, (height - y) / max(2.0, speed_y)))
    fuse_hi = min(STRIKER_BOMB_FUSE_MAX, max(STRIKER_BOMB_FUSE_MIN + 1, fall_frames - 10))
    return random.randint(STRIKER_BOMB_FUSE_MIN, fuse_hi)


def _striker_bomb_burst_positions(cx: float, cy: float) -> list[tuple[float, float, float]]:
    """起爆点付近にランダム配置した3爆発の (x, y, scale_mul)。"""
    out: list[tuple[float, float, float]] = []
    for _ in range(STRIKER_BOMB_BURST_COUNT):
        ox = random.uniform(-STRIKER_BOMB_BURST_OFFSET_X, STRIKER_BOMB_BURST_OFFSET_X)
        oy = random.uniform(-STRIKER_BOMB_BURST_OFFSET_Y, STRIKER_BOMB_BURST_OFFSET_Y)
        scale = random.uniform(STRIKER_BOMB_BURST_SCALE_MIN, STRIKER_BOMB_BURST_SCALE_MAX)
        out.append((float(cx) + ox, float(cy) + oy, scale))
    return out


def detonate_extra_striker_bomb(x: float, y: float) -> None:
    """爆弾空中爆発：explosion_zako をランダム3つ（弾拡散なし・各爆発に当たり）。"""
    sfx = g().get("explosion_sound")
    if sfx is not None:
        try:
            sfx.play()
        except Exception:
            pass
    zako = g().get("explosion_zako_img") or g().get("meteor_zako_explosion_img")
    explosions = g()["explosions"]
    if zako is not None:
        for bx, by, scale_mul in _striker_bomb_burst_positions(float(x), float(y)):
            explosions.append(
                ExtraStrikerBombExplosion(bx, by, zako, scale_mul=scale_mul)
            )
    else:
        explosions.append(Explosion(float(x), float(y), big=False))


def _striker_bomb_drop_x_positions(width: int, count: int = 5) -> list[float]:
    """右→左へ移動する戦闘機が通過するX（右側から順に投下）。"""
    if count <= 1:
        return [float(width) * 0.5]
    ratios = [0.84 - i * (0.68 / (count - 1)) for i in range(count)]
    return [float(width) * r for r in ratios]


def spawn_extra_striker_bomb(
    x: float,
    y: float,
    *,
    speed_y: float = 7.8,
    is_boss_bullet: bool = False,
) -> dict:
    """ストライカー戦闘機から投下する爆弾（真下・途中ランダム爆発）。"""
    height = g()["HEIGHT"]
    life = int(height / max(2.0, speed_y)) + 48
    eb = spawn_enemy_bullet(
        x=float(x),
        y=float(y),
        vx=0.0,
        vy=float(speed_y),
        homing=False,
        is_boss_bullet=is_boss_bullet,
        image_type="extra_striker_bomb",
        life=life,
    )
    eb["attack_type"] = "extra_striker_bomb"
    eb["striker_fuse"] = _striker_bomb_fuse_frames(float(y), float(speed_y))
    return eb


def spawn_extra_striker_fighter(
    *,
    top_margin: float = 42.0,
    speed: float = 11.0,
    bomb_count: int = 5,
) -> dict:
    """第二形態: 最上部で右端→左端へ直進し、通過中に爆弾を投下。"""
    width = g()["WIDTH"]
    img = g().get("extra_tank_striker_img")
    half_w = float((img.get_width() if img else 80) * 0.5)
    half_h = float((img.get_height() if img else 32) * 0.5)
    gy = float(top_margin) + half_h
    gx = float(width) + half_w + 12.0
    bomb_xs = _striker_bomb_drop_x_positions(width, bomb_count)
    eb = spawn_enemy_bullet(
        x=gx,
        y=gy,
        vx=-abs(float(speed)),
        vy=0.0,
        homing=False,
        is_boss_bullet=True,
        image_type="extra_tank_striker",
        attack_type="extra_striker",
        life=900,
    )
    eb["striker_bomb_xs"] = bomb_xs
    eb["striker_bombs_dropped"] = 0
    eb["striker_bomb_drop_y"] = gy + half_h * 0.35
    eb["hp"] = 5
    eb["destructible"] = True
    return eb


def spawn_extra_robot_homing_charge(x: float, y: float) -> dict:
    """第二形態: 左縦5の待機弾（並び完了まで静止）。"""
    eb = spawn_enemy_bullet(
        x=float(x),
        y=float(y),
        vx=0.0,
        vy=0.0,
        homing=False,
        is_boss_bullet=True,
        image_type="boss3_bullet",
        allow_zero_velocity=True,
        life=240,
    )
    eb["extra_robot_homing_charge"] = True
    return eb


def spawn_extra_robot_homing_snipe(
    x: float,
    y: float,
    player,
    *,
    speed: float = 12.5,
) -> dict:
    """エクストラボス第二形態: 左縦列から自機へスナイプ（直進・boss3_bullet）。"""
    hx = float(x)
    hy = float(y)
    dx = float(player.rect.centerx) - hx
    dy = float(player.rect.centery) - hy
    dist = max(1.0, math.hypot(dx, dy))
    spd = float(speed)
    vx = dx / dist * spd
    vy = dy / dist * spd
    eb = spawn_enemy_bullet(
        x=hx,
        y=hy,
        vx=vx,
        vy=vy,
        homing=False,
        is_boss_bullet=True,
        image_type="boss3_bullet",
        offscreen_only=True,
    )
    eb["extra_robot_homing_snipe"] = True
    return eb


def spawn_extra_tank_homing_bullet(
    x: float,
    y: float,
    *,
    speed: float = 5.8,
    life: int = 95,
) -> dict:
    """エクストラボス第一形態: boss3_bullet ホーミング弾。"""
    eb = spawn_enemy_bullet(
        x=float(x),
        y=float(y),
        vx=-abs(float(speed)),
        vy=0.0,
        homing=True,
        is_boss_bullet=True,
        image_type="boss3_bullet",
        life=int(life),
    )
    eb["extra_tank_homing"] = True
    eb["destructible"] = True
    return eb


def spawn_extra_purple_shot(x, y, angle_rad, speed=10.5, life=None):
    """エクストラボス: ボス中心などからの細紫ショット（左場外まで）。"""
    spd = float(speed)
    vx = math.cos(angle_rad) * spd
    vy = math.sin(angle_rad) * spd
    if life is None:
        life = _life_until_left_offscreen(x, y, vx, vy)
    laser_len = min(720, max(200, int(spd * life * 0.5)))
    laser = spawn_enemy_laser(
        int(x),
        int(y),
        vx,
        vy,
        speed=spd,
        life=life,
        laser_length=laser_len,
        laser_variant="purple_thin",
    )
    laser.beam_no_bounce = True
    laser.beam_from_anchor = True
    laser.angle = angle_rad
    laser.extra_purple_shot = True
    return laser


EXTRA_VULCAN_BODY_R = 8
EXTRA_VULCAN_AURA_WIDTH = 2
EXTRA_VULCAN_DRAW_SIZE = (EXTRA_VULCAN_BODY_R + EXTRA_VULCAN_AURA_WIDTH) * 2 + 2


def _draw_extra_vulcan_bullet(surf: pygame.Surface, cx: int, cy: int) -> None:
    """水色ベース弾＋シアンオーラ（第一形態機関砲・第二形態バルカン・爆弾破片）。"""
    r = EXTRA_VULCAN_BODY_R
    pygame.draw.circle(surf, (18, 95, 140), (cx, cy), r)
    pygame.draw.circle(surf, (55, 185, 245), (cx, cy), r - 2)
    pygame.draw.circle(surf, (175, 240, 255), (cx, cy), r - 5)
    pygame.draw.circle(
        surf,
        (30, 150, 210),
        (cx, cy),
        r + 1,
        EXTRA_VULCAN_AURA_WIDTH,
    )


def _vulcan_life_until_offscreen(
    x: float,
    y: float,
    vx: float,
    vy: float,
    width: int,
    height: int,
    *,
    margin: float = 200.0,
) -> int:
    """直進弾がプレイ領域外へ出るまでの寿命（フレーム）。"""
    life = 0
    if vx < -0.01:
        life = max(life, int((x + margin) / abs(vx)))
    elif vx > 0.01:
        life = max(life, int((width + margin - x) / vx))
    if vy < -0.01:
        life = max(life, int((y + margin) / abs(vy)))
    elif vy > 0.01:
        life = max(life, int((height + margin - y) / vy))
    return max(36, life + 16)


def _life_until_left_offscreen(
    x: float,
    y: float,
    vx: float,
    vy: float,
    *,
    margin: float = 160.0,
) -> int:
    """左方向へ飛ぶレーザーが画面左場外へ出るまでの寿命（フレーム）。"""
    life = 0
    if vx < -0.01:
        life = max(life, int((x + margin) / abs(vx)))
    if vy < -0.01:
        height = g()["HEIGHT"]
        life = max(life, int((y + margin) / abs(vy)))
    elif vy > 0.01:
        height = g()["HEIGHT"]
        life = max(life, int((height + margin - y) / vy))
    return max(48, life + 16)


def _scaled_boss_laser_velocity(vx: float, vy: float) -> tuple[float, float]:
    eb = {"vx": float(vx), "vy": float(vy), "is_boss_bullet": True}
    g()["diff"].scale_bullet(eb)
    return float(eb["vx"]), float(eb["vy"])


def spawn_extra_vulcan_snipe(hx, hy, player, speed=12.0):
    """エクストラボス: 頭部バルカン（第二形態・自機スナイプ）。"""
    dx = float(player.rect.centerx) - hx
    dy = float(player.rect.centery) - hy
    angle = math.atan2(dy, dx)
    spd = float(speed)
    vx = math.cos(angle) * spd
    vy = math.sin(angle) * spd
    eb = spawn_enemy_bullet(
        x=float(hx),
        y=float(hy),
        vx=vx,
        vy=vy,
        homing=False,
        is_boss_bullet=True,
        image_type="extra_vulcan",
        offscreen_only=True,
    )
    _apply_extra_vulcan_speed_cap(eb)
    return eb


def spawn_extra_shockwave_crescent(
    boss,
    player,
    lane_index: int,
    *,
    ground_margin: float = 52.0,
    speed: float = 11.5,
) -> "Bullet":
    """HP25%以下: 地面を這う三日月型レーザー（左方向）。"""
    height = g()["HEIGHT"]
    width = g()["WIDTH"]
    lane_y = (-22, 0, 22)
    gy = float(height - ground_margin) + lane_y[lane_index % 3]
    gx = float(boss.rect.centerx)
    angle = math.radians(178.0 + lane_index * 2.5)
    spd = float(speed)
    vx = math.cos(angle) * spd
    vy = math.sin(angle) * spd
    life = _life_until_left_offscreen(gx, gy, vx, vy)
    beam_len = _beam_length_to_left_offscreen(gx, gy, angle)
    laser = spawn_enemy_laser(
        int(gx),
        int(gy),
        vx,
        vy,
        speed=spd,
        life=life,
        laser_length=beam_len,
        laser_variant="purple_ground_crescent",
    )
    laser.beam_no_bounce = True
    laser.beam_from_anchor = True
    laser.angle = angle
    laser.crescent_bulge = 38.0 + lane_index * 4.0
    return laser


EXTRA_BEAM_CUTTER_LANE_Y = (0.24, 0.50, 0.76)


def spawn_extra_beam_cutter(
    boss,
    *,
    lane_index: int = 0,
    speed: float = 27.0,
) -> dict:
    """エクストラボス: ビームカッター（上中下レーン・左へ直進）。"""
    height = float(g()["HEIGHT"])
    lanes = EXTRA_BEAM_CUTTER_LANE_Y
    gy = height * lanes[int(lane_index) % len(lanes)]
    gx = float(boss.rect.right) - 8.0
    eb = spawn_enemy_bullet(
        x=gx,
        y=gy,
        vx=-abs(float(speed)),
        vy=0.0,
        homing=False,
        is_boss_bullet=True,
        image_type="extra_beam_cutter",
    )
    eb["extra_beam_cutter"] = True
    eb["beam_cutter_lane"] = int(lane_index) % len(lanes)
    eb["offscreen_only"] = True
    eb.pop("life", None)
    return eb


def spawn_extra_funnel_snipe_beam(fx, fy, player, speed=12.0, life=None):
    """ファンネル口から自機狙いの細紫レーザー（左場外まで）。"""
    width = g()["WIDTH"]
    dx = float(player.rect.centerx) - fx
    dy = float(player.rect.centery) - fy
    angle = math.atan2(dy, dx)
    spd = float(speed)
    vx = math.cos(angle) * spd
    vy = math.sin(angle) * spd
    if life is None:
        life = _life_until_left_offscreen(fx, fy, vx, vy, margin=48.0)
    laser = spawn_enemy_laser(
        int(fx),
        int(fy),
        vx,
        vy,
        speed=spd,
        life=life,
        laser_length=EXTRA_MOVING_BEAM_LENGTH,
        laser_variant="purple_thin",
    )
    laser.beam_no_bounce = True
    laser.beam_from_anchor = True
    laser.angle = angle
    laser.extra_funnel_snipe = True
    return laser


def spawn_boss5_red_laser(x, y, angle_rad, speed=13.0, life=None):
    """ボス5用: 半分の長さ・やや低速の赤レーザー（左場外まで寿命を確保）。"""
    spd = speed * BOSS5_LASER_SPEED_SCALE
    vx = math.cos(angle_rad) * spd
    vy = math.sin(angle_rad) * spd
    vx, vy = _scaled_boss_laser_velocity(vx, vy)
    if life is None:
        life = _life_until_left_offscreen(float(x), float(y), vx, vy)
    else:
        life = max(int(life), _life_until_left_offscreen(float(x), float(y), vx, vy))
    return spawn_enemy_laser(
        x, y,
        vx,
        vy,
        life=life,
        laser_length=BOSS5_ENEMY_LASER_LENGTH,
    )
def spawn_boss5_ripple(x, y, vy=0.0, vx=-5.5, radius=8, radius_max=112, radius_grow=0.95):
    """左へ飛びながら小さく始まり徐々に大きくなるリップル。"""
    append_boss_enemy_bullet({
        "x": float(x), "y": float(y),
        "vx": float(vx), "vy": float(vy),
        "homing": False, "is_boss_bullet": True,
        "image_type": "ripple",
        "force_leftward": True,
        "radius": float(radius),
        "radius_max": float(radius_max),
        "radius_grow": float(radius_grow),
        "hp": 1,
    })


def spawn_boss2_player_ripple(x, y, speed_scale=1.0, extra=0):
    """ボス2: プレイヤーへサイン波の緩急をつけて接近するリップル。"""
    b2_speed = g()["diff"].scale_boss_scalar_speed(
        6.6 * float(speed_scale) + float(extra) * 0.25,
    )
    append_boss_enemy_bullet({
        "x": float(x),
        "y": float(y),
        "vx": 0.0,
        "vy": 0.0,
        "homing": False,
        "is_boss_bullet": True,
        "image_type": "ripple",
        "attack_type": "b2_player_ripple",
        "b2_speed": b2_speed,
        "b2_phase": random.uniform(0, math.tau),
        "b2_freq": random.uniform(0.11, 0.16),
        "b2_sway": random.uniform(1.0, 1.8),
        "radius": 14.0 + extra * 2,
        "radius_max": 92.0 + extra * 14,
        "radius_grow": 0.88,
        "hp": 1,
    })


def update_b2_player_ripple(eb, player_dead: bool) -> None:
    """自機方向へ進み、速度を sin で緩急＋わずかな蛇行。"""
    if player_dead:
        eb["vx"] = eb_v(eb, "vx", -6.0) * 0.98 - 0.15
        eb["vy"] = eb_v(eb, "vy") * 0.98
        return
    player = g()["player"]
    dx = player.rect.centerx - eb["x"]
    dy = player.rect.centery - eb["y"]
    dist = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist
    phase = float(eb.get("b2_phase", 0.0)) + float(eb.get("b2_freq", 0.13))
    eb["b2_phase"] = phase
    pulse = 0.62 + 0.38 * math.sin(phase)
    spd = float(eb.get("b2_speed", 6.6)) * pulse
    sway = float(eb.get("b2_sway", 1.4)) * math.sin(phase * 1.65)
    px, py = -uy, ux
    eb["vx"] = ux * spd + px * sway
    eb["vy"] = uy * spd + py * sway


B1_DIAGONAL_RIPPLE_HP = 20
B1_DIAGONAL_RIPPLE_FUSE_MIN = 72
B1_DIAGONAL_RIPPLE_FUSE_MAX = 150
B1_DIAGONAL_RIPPLE_BURST_DIRS = 8
B1_DIAGONAL_RIPPLE_BURST_SPEED = 6.2


def b1_diagonal_ripple_count() -> int:
    return sum(
        1
        for eb in g()["enemy_bullets"]
        if eb.get("attack_type") == "b1_diagonal_ripple"
    )


def b1_diagonal_ripple_on_screen() -> bool:
    return b1_diagonal_ripple_count() > 0


def burst_b1_diagonal_ripple(x: float, y: float, *, is_low_hp: bool = False) -> None:
    """反射泡破裂：8方向にボス1弾を飛ばす（画面外まで）。"""
    sfx = g().get("ripple_sound") or g().get("explosion_sound")
    if sfx is not None:
        try:
            sfx.play()
        except Exception:
            pass
    g()["explosions"].append(Explosion(float(x), float(y), big=False))
    spd = B1_DIAGONAL_RIPPLE_BURST_SPEED + (0.5 if is_low_hp else 0.0)
    for i in range(B1_DIAGONAL_RIPPLE_BURST_DIRS):
        ang = i * math.tau / B1_DIAGONAL_RIPPLE_BURST_DIRS
        vx = math.cos(ang) * spd
        vy = math.sin(ang) * spd
        append_boss_enemy_bullet({
            "x": float(x),
            "y": float(y),
            "vx": vx,
            "vy": vy,
            "homing": False,
            "is_boss_bullet": True,
            "image_type": "boss1_bullet",
            "b1_ripple_burst_shard": True,
        })


def _spawn_b1_diagonal_ripple_one(
    x,
    y,
    *,
    upward: bool,
    is_low_hp: bool = False,
    elev_deg: float | None = None,
    fuse_frames: int | None = None,
) -> None:
    """45°/60°で上下いずれかへ発射する反射泡1発。"""
    if elev_deg is None:
        elev_deg = random.choice((45.0, 60.0))
    if fuse_frames is None:
        fuse_frames = random.randint(
            B1_DIAGONAL_RIPPLE_FUSE_MIN,
            B1_DIAGONAL_RIPPLE_FUSE_MAX,
        )
    rad = math.radians(elev_deg)
    spd = 5.4 if is_low_hp else 4.9
    vx = -math.cos(rad) * spd
    vy = -math.sin(rad) * spd if upward else math.sin(rad) * spd
    append_boss_enemy_bullet({
        "x": float(x),
        "y": float(y),
        "vx": vx,
        "vy": vy,
        "homing": False,
        "is_boss_bullet": True,
        "image_type": "ripple",
        "attack_type": "b1_diagonal_ripple",
        "force_leftward": True,
        "radius": 40.0,
        "radius_max": 40.0,
        "radius_grow": 0.0,
        "hp": B1_DIAGONAL_RIPPLE_HP,
        "b1_upward": bool(upward),
        "b1_is_low_hp": bool(is_low_hp),
        "fuse_timer": int(fuse_frames),
    })


def spawn_b1_diagonal_ripple(x, y, *, is_low_hp: bool = False, upward: bool | None = None):
    """互換: 1発のみ（上下ランダム）。"""
    if upward is None:
        upward = random.choice((True, False))
    _spawn_b1_diagonal_ripple_one(x, y, upward=upward, is_low_hp=is_low_hp)


def spawn_b1_diagonal_ripple_pair(x, y, *, is_low_hp: bool = False) -> None:
    """上下同時2発。各45°/60°ランダム・破裂までの時間も個別ランダム。"""
    if b1_diagonal_ripple_on_screen():
        return
    for upward in (True, False):
        _spawn_b1_diagonal_ripple_one(x, y, upward=upward, is_low_hp=is_low_hp)


def spawn_b1_diagonal_ripple_alternate(_boss, x, y, *, is_low_hp: bool = False) -> None:
    """反射泡: 上下2発同時・45°/60°ランダム・一定時間後8方向破裂。"""
    spawn_b1_diagonal_ripple_pair(x, y, is_low_hp=is_low_hp)


B1_CURTAIN_COLORS = {
    "outer": (30, 140, 210),
    "inner": (100, 220, 255),
    "base": (70, 200, 255),
    "tip": (210, 255, 255),
}


def _b1_curtain_points(eb) -> list[tuple[int, int]]:
    """ボス左：上/下アンカーから中心 Y へ伸びる防御触手。"""
    length = max(0, int(eb.get("tentacle_len", 0)))
    if length < 2:
        length = 2
    timer = eb.get("special_timer", 0)
    phase = eb.get("wave_phase", 0.0)
    amp = eb.get("wave_amp", 10)
    ax = float(eb["x"])
    ay = float(eb["y"])
    side = eb.get("curtain_side", "top")
    points = []
    segments = 14
    for i in range(segments + 1):
        t = i / segments
        if side == "top":
            y = ay + length * t
        else:
            y = ay - length * t
        x = ax + math.sin(timer * 0.11 + phase + t * 4.8) * amp
        points.append((int(x), int(y)))
    return points


def spawn_b1_tentacle_curtain_shield(boss) -> None:
    """ボス1特殊：左端の上・下から中心へ伸びる防御触手（被弾で縮む）。"""
    bx = float(boss.rect.left - 32)
    cy = float(boss.rect.centery)
    top_y = float(boss.rect.top + int(boss.rect.height * 0.14))
    bot_y = float(boss.rect.bottom - int(boss.rect.height * 0.14))
    grow = 5.0 if boss.hp > boss.max_hp * 0.5 else 6.2
    for side, ay in (("top", top_y), ("bottom", bot_y)):
        max_len = max(40.0, abs(cy - ay))
        spawn_enemy_bullet(
            x=bx,
            y=ay,
            vx=0.0,
            vy=0.0,
            is_boss_bullet=True,
            image_type="boss1_bullet",
            special_attack=True,
            attack_type="b1_tentacle_curtain",
            curtain_side=side,
            meet_y=cy,
            tentacle_len=0.0,
            tentacle_len_max=max_len,
            tentacle_grow=grow,
            tentacle_retract=16.0,
            state="extend",
            hp=22,
            max_hp=22,
            life=600,
            wave_phase=random.random() * math.tau,
            wave_amp=random.randint(8, 14),
        )


def b1_tentacle_curtain_retract_all() -> None:
    for eb in g()["enemy_bullets"]:
        if eb.get("attack_type") == "b1_tentacle_curtain":
            eb["state"] = "retract"


def enemy_bullet_sprite_for(eb):
    image_type = eb.get("image_type", "normal")
    if image_type == "turret_homing":
        img = g().get("turret_bullet_img")
        if img is not None:
            return img
    if image_type == "extra_vulcan":
        return g().get("enemy_bullet_img") or g().get("boss_bullet_img")
    if image_type == "extra_tank_striker":
        img = g().get("extra_tank_striker_img")
        if img is not None:
            return img
    if image_type in ("extra_tank_striker_missile", "extra_striker_bomb"):
        img = g().get("extra_tank_striker_missile_img")
        if img is not None:
            return img
    if image_type in g()["boss_specific_bullet_imgs"]:
        return g()["boss_specific_bullet_imgs"][image_type]
    if image_type == "boss3_ufo":
        return g()["boss3_ufo_img"]
    if image_type == "boss2_fish":
        return g()["boss2_fish_img"]
    if image_type == "boss01":
        return g()["boss_bullet_img_01"]
    if image_type == "boss02":
        return g()["boss_bullet_img_02"]
    if image_type == "boss03":
        return g()["boss_bullet_img_03"]
    if image_type in ("homing", "boss_homing"):
        if eb.get("is_boss_bullet", False) or image_type == "boss_homing":
            return g().get("homing_bullet_img") or g()["enemy_bullet_img"]
        return g().get("grunt_homing_bullet_img") or g()["enemy_bullet_img"]
    if image_type == "boss":
        return g()["boss_bullet_img"]
    return g()["enemy_bullet_img"]

def _tentacle_points_on_surface(eb, ox: int, oy: int) -> list[tuple[int, int]]:
    attack_type = eb.get("attack_type")
    timer = eb.get("special_timer", 0)
    length = int(eb.get("tentacle_len", 0))
    from_ground = attack_type == "b1_ground_tentacle"
    from_top = bool(eb.get("b1_from_top", False))
    if attack_type == "b1_tentacle_curtain":
        points = _b1_curtain_points(eb)
        return [(px - ox, py - oy) for px, py in points]
    segments = 14
    phase = eb.get("wave_phase", 0.0)
    amp = eb.get("wave_amp", 18)
    length = int(eb.get("tentacle_len", 0))
    points = []
    for i in range(segments + 1):
        t = i / segments
        if from_ground:
            y = eb["y"] + length * t if from_top else eb["y"] - length * t
            x = eb["x"] + _b1_ground_tentacle_sway(eb, timer, t)
        else:
            y = eb["y"] + length * t
            x = eb["x"] + math.sin(timer * 0.12 + phase + t * 5.2) * amp
        points.append((int(x) - ox, int(y) - oy))
    return points


def _draw_tentacle_on_surface(surf: pygame.Surface, eb, rect: pygame.Rect) -> None:
    attack_type = eb.get("attack_type")
    points = _tentacle_points_on_surface(eb, rect.left, rect.top)
    if len(points) < 2:
        return
    if attack_type in ("b1_ground_tentacle", "b1_tentacle_curtain"):
        pal = (
            _b1_ground_tentacle_palette(eb)
            if attack_type == "b1_ground_tentacle"
            else B1_CURTAIN_COLORS
        )
        pygame.draw.lines(surf, (*pal["outer"], 255), False, points, 18)
        pygame.draw.lines(surf, (*pal["inner"], 240), False, points, 8)
        base_pt = points[0] if points else (0, 0)
        pygame.draw.circle(surf, (*pal["base"], 255), base_pt, 14)
        if attack_type == "b1_tentacle_curtain" and len(points) > 2:
            tip = points[-1]
            pygame.draw.circle(surf, (*pal["tip"], 255), tip, 10)
    else:
        pygame.draw.lines(surf, (255, 255, 255, 255), False, points, 8)
        pygame.draw.lines(surf, (255, 255, 255, 240), False, points, 3)


def enemy_bullet_visual_for_hit(eb) -> tuple[pygame.Surface | None, pygame.Rect | None]:
    """当たり判定用: 実際に描画している見た目のサーフェスと Rect。"""
    attack_type = eb.get("attack_type")
    image_type = eb.get("image_type", "normal")

    if attack_type in ("b1_tentacle_curtain", "b1_ground_tentacle"):
        length = int(eb.get("tentacle_len", 0))
        if length < 4:
            return None, None
        rect = enemy_bullet_hit_rect(eb)
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        _draw_tentacle_on_surface(surf, eb, rect)
        return surf, rect

    if attack_type == "b1_diagonal_ripple":
        ripple = g().get("boss1_ripple_img", g()["boss_ripple_base_img"])
        rect = ripple.get_rect(center=(int(eb["x"]), int(eb["y"])))
        return ripple, rect
    if image_type in ("ripple", "ripple_homing"):
        radius = int(eb.get("radius", 15))
        diameter = max(8, radius * 2)
        ripple = pygame.transform.scale(g()["boss_ripple_base_img"], (diameter, diameter))
        rect = ripple.get_rect(center=(int(eb["x"]), int(eb["y"])))
        return ripple, rect

    if image_type == "extra_vulcan":
        sz = EXTRA_VULCAN_DRAW_SIZE
        rect = pygame.Rect(0, 0, sz, sz)
        rect.center = (int(eb["x"]), int(eb["y"]))
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        _draw_extra_vulcan_bullet(surf, sz // 2, sz // 2)
        return surf, rect

    if image_type in ("extra_tank_striker", "extra_tank_striker_missile", "extra_striker_bomb"):
        b_img = enemy_bullet_sprite_for(eb)
        if b_img is None:
            return None, None
        if image_type == "extra_striker_bomb":
            rect = b_img.get_rect(midtop=(int(eb["x"]), int(eb["y"])))
        else:
            rect = b_img.get_rect(center=(int(eb["x"]), int(eb["y"])))
        return b_img, rect

    if image_type == "extra_beam_cutter":
        img = g().get("extra_beam_cutter_img")
        if img is None:
            return None, None
        dest = img.get_rect(midright=(int(eb["x"]), int(eb["y"])))
        return img, dest

    if image_type == "extra_beam_orb":
        rect = pygame.Rect(0, 0, 32, 32)
        rect.center = (int(eb["x"]), int(eb["y"]))
        surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        _draw_extra_beam_orb_bullet(surf, 16, 16)
        return surf, rect

    b_img = enemy_bullet_sprite_for(eb)
    rect = b_img.get_rect(center=(int(eb["x"]), int(eb["y"])))
    return b_img, rect


def enemy_bullet_hit_rect(eb):
    image_type = eb.get("image_type", "normal")
    attack_type = eb.get("attack_type")
    if attack_type == "b1_tentacle_curtain":
        height = max(8, int(eb.get("tentacle_len", 0)))
        rect = pygame.Rect(0, 0, 36, height)
        if eb.get("curtain_side", "top") == "top":
            rect.midtop = (int(eb["x"]), int(eb["y"]))
        else:
            rect.midbottom = (int(eb["x"]), int(eb["y"]))
    elif attack_type == "b1_ground_tentacle":
        height = max(12, int(eb.get("tentacle_len", 0)))
        rect = pygame.Rect(0, 0, 56, height)
        if eb.get("b1_from_top"):
            rect.midtop = (int(eb["x"]), int(eb["y"]))
        else:
            rect.midbottom = (int(eb["x"]), int(eb["y"]))
    elif attack_type == "b1_diagonal_ripple":
        rect = pygame.Rect(0, 0, 80, 80)
        rect.center = (int(eb["x"]), int(eb["y"]))
    elif image_type in ("ripple", "ripple_homing"):
        size = int(eb.get("radius", 15) * 1.6)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(eb["x"]), int(eb["y"]))
    elif image_type == "extra_vulcan":
        sz = max(18, EXTRA_VULCAN_DRAW_SIZE - 2)
        rect = pygame.Rect(0, 0, sz, sz)
        rect.center = (int(eb["x"]), int(eb["y"]))
    elif image_type in ("extra_tank_striker", "extra_tank_striker_missile", "extra_striker_bomb"):
        b_img = enemy_bullet_sprite_for(eb)
        if b_img is None:
            rect = pygame.Rect(0, 0, 24, 24)
            if image_type == "extra_striker_bomb":
                rect.midtop = (int(eb["x"]), int(eb["y"]))
            else:
                rect.center = (int(eb["x"]), int(eb["y"]))
        else:
            if image_type == "extra_striker_bomb":
                rect = b_img.get_rect(midtop=(int(eb["x"]), int(eb["y"])))
            else:
                rect = b_img.get_rect(center=(int(eb["x"]), int(eb["y"])))
            rect.inflate_ip(-max(6, rect.width // 6), -max(4, rect.height // 5))
    elif image_type == "extra_beam_cutter":
        img = g().get("extra_beam_cutter_img")
        if img is None:
            rect = pygame.Rect(0, 0, 24, 24)
            rect.midright = (int(eb["x"]), int(eb["y"]))
        else:
            rect = img.get_rect(midright=(int(eb["x"]), int(eb["y"])))
            rect.inflate_ip(-max(8, rect.width // 8), -max(6, rect.height // 6))
    elif image_type == "extra_beam_orb":
        rect = pygame.Rect(0, 0, 26, 26)
        rect.center = (int(eb["x"]), int(eb["y"]))
    elif image_type == "boss2_fish":
        b_img = enemy_bullet_sprite_for(eb)
        rect = b_img.get_rect(center=(int(eb["x"]), int(eb["y"])))
        rect.inflate_ip(-36, -18)
    else:
        b_img = enemy_bullet_sprite_for(eb)
        rect = pygame.Rect(0, 0, max(4, b_img.get_width() - 6), max(4, b_img.get_height() - 6))
        rect.center = (int(eb["x"]), int(eb["y"]))
    return rect
def enemy_bullet_special_motion(eb, player_dead, player=None):
    """Update velocity / timers. Returns True if the bullet was removed."""
    attack_type = eb.get("attack_type")
    if attack_type == "b2_fish_swarm":
        eb["fish_timer"] = int(eb.get("fish_timer", 0)) + 1
        t = float(eb["fish_timer"])
        eb["x"] = float(eb.get("x", 0)) + eb_v(eb, "vx")
        eb["y"] = float(eb.get("sine_lane_y", eb.get("y", 0))) + math.sin(
            t * float(eb.get("sine_omega", 0.105)) + float(eb.get("sine_phase", 0.0))
        ) * float(eb.get("sine_amp", 54.0))
        eb["vy"] = 0.0
        eb["freeze_timer"] = 1
        return False

    if attack_type == "b1_tentacle_curtain":
        eb["special_timer"] = eb.get("special_timer", 0) + 1
        cur_len = float(eb.get("tentacle_len", 0))
        max_len = float(eb.get("tentacle_len_max", 120))
        retract_spd = float(eb.get("tentacle_retract", 16.0))
        if eb.get("state") == "retract":
            eb["tentacle_len"] = max(0.0, cur_len - retract_spd)
            if eb["tentacle_len"] <= 0:
                eb["life"] = 0
            eb["freeze_timer"] = 1
            return False
        grow = float(eb.get("tentacle_grow", 5.0))
        if cur_len < max_len:
            eb["tentacle_len"] = min(max_len, cur_len + grow)
        eb["freeze_timer"] = 1
        return False

    if attack_type == "b1_ground_tentacle":
        eb["special_timer"] = eb.get("special_timer", 0) + 1
        cur_len = float(eb.get("tentacle_len", 0))
        max_len = float(eb.get("tentacle_len_max", _b1_ground_max_len()))
        retract_spd = float(eb.get("tentacle_retract", 16.0))
        if eb.get("state") == "retract":
            eb["tentacle_len"] = max(0.0, cur_len - retract_spd)
            if eb["tentacle_len"] <= 0:
                eb["life"] = 0
            eb["freeze_timer"] = 1
            return False
        grow = float(eb.get("tentacle_grow", 6.0))
        if cur_len < max_len:
            eb["tentacle_len"] = min(max_len, cur_len + grow)
        else:
            hold_max = int(eb.get("hold_at_max_frames", 38))
            eb["hold_timer"] = eb.get("hold_timer", 0) + 1
            if eb["hold_timer"] > hold_max:
                eb["life"] = min(eb.get("life", 1), max(0, eb["life"] - 10))
        eb["freeze_timer"] = 1
        return False

    if attack_type == "b3_ufo_fleet":
        eb["special_timer"] = eb.get("special_timer", 0) + 1
        timer = eb["special_timer"]
        if timer <= 24:
            target_x = eb.get("target_x", eb["x"])
            target_y = eb.get("target_y", eb["y"])
            eb["x"] += (target_x - eb["x"]) * 0.22
            eb["y"] += (target_y - eb["y"]) * 0.22
        elif timer <= eb.get("hold_frames", 105):
            eb["x"] = eb.get("target_x", eb["x"]) + math.sin(timer * 0.12 + eb.get("wave_phase", 0.0)) * 8
            eb["y"] = eb.get("target_y", eb["y"]) + math.sin(timer * 0.08 + eb.get("wave_phase", 0.0)) * 5
            if timer in eb.get("fire_frames", (34, 58, 82)) and not g()["player_dead"]:
                dx = player.rect.centerx - eb["x"]
                dy = player.rect.centery - eb["y"]
                dist = max(1.0, math.hypot(dx, dy))
                spd = 7.2
                spawn_enemy_bullet(
                    x=eb["x"] - 24,
                    y=eb["y"],
                    vx=(dx / dist) * spd,
                    vy=(dy / dist) * spd,
                    is_boss_bullet=True,
                    image_type="boss3_bullet",
                    special_attack=True,
                )
        else:
            eb["x"] += 9.0
            eb["y"] += math.sin(timer * 0.18 + eb.get("wave_phase", 0.0)) * 2.0
        eb["freeze_timer"] = 1
        return False

    if attack_type == "extra_striker_bomb":
        eb["y"] = float(eb.get("y", 0)) + eb_v(eb, "vy")
        fuse = int(eb.get("striker_fuse", 0)) - 1
        eb["striker_fuse"] = fuse
        ground_y = float(g()["HEIGHT"]) - 48.0
        if fuse <= 0 or float(eb["y"]) >= ground_y:
            detonate_extra_striker_bomb(float(eb["x"]), float(eb["y"]))
            if eb in g()["enemy_bullets"]:
                g()["enemy_bullets"].remove(eb)
            return True
        eb["freeze_timer"] = 1
        return False

    if attack_type == "extra_striker":
        eb["x"] = eb.get("x", 0) + eb_v(eb, "vx")
        drop_xs = list(eb.get("striker_bomb_xs") or [])
        dropped = int(eb.get("striker_bombs_dropped", 0) or 0)
        drop_y = float(eb.get("striker_bomb_drop_y", eb.get("y", 0)))
        while dropped < len(drop_xs) and float(eb["x"]) <= drop_xs[dropped]:
            spawn_extra_striker_bomb(float(eb["x"]), drop_y)
            dropped += 1
            sfx = g().get("shot_sound")
            if sfx is not None:
                try:
                    sfx.play()
                except Exception:
                    pass
        eb["striker_bombs_dropped"] = dropped
        img = g().get("extra_tank_striker_img")
        half_w = float((img.get_width() if img else 80) * 0.55)
        if float(eb["x"]) + half_w < -48.0:
            eb["life"] = 0
        eb["freeze_timer"] = 1
        return False

    if attack_type == "b1_sidewinder":
        eb["special_timer"] = eb.get("special_timer", 0) + 1
        timer = eb["special_timer"]
        phase = eb.get("wave_phase", 0.0)
        amp = eb.get("wave_amp", 3.8)
        eb["vx"] = -abs(eb.get("base_vx", 5.2))
        eb["vy"] = math.sin(timer * 0.16 + phase) * amp
        if timer > 42 and not g()["player_dead"]:
            dy = player.rect.centery - eb["y"]
            dist = max(1.0, abs(dy))
            eb["vy"] = eb["vy"] * 0.84 + (dy / dist) * 2.9 * 0.16
        return False

    if attack_type == "b3_orbit_lance":
        eb["special_timer"] = eb.get("special_timer", 0) + 1
        timer = eb["special_timer"]
        if timer <= eb.get("orbit_frames", 48):
            angle = eb.get("orbit_angle", 0.0) + timer * eb.get("orbit_speed", 0.10)
            radius = eb.get("orbit_radius", 74)
            eb["x"] = eb.get("orbit_cx", eb["x"]) + math.cos(angle) * radius
            eb["y"] = eb.get("orbit_cy", eb["y"]) + math.sin(angle) * radius
            eb["vx"] = 0.0
            eb["vy"] = 0.0
            eb["freeze_timer"] = 1
        elif timer == eb.get("orbit_frames", 48) + eb.get("launch_delay", 0):
            if not g()["player_dead"]:
                dx = player.rect.centerx - eb["x"]
                dy = player.rect.centery - eb["y"]
                base = math.atan2(dy, dx)
            else:
                base = math.pi
            base += math.radians(eb.get("launch_angle_offset", 0))
            spd = eb.get("launch_speed", 8.4)
            eb["vx"] = math.cos(base) * spd
            eb["vy"] = math.sin(base) * spd
        return False

    if eb.get("speed_type") == "brake":
        timer = eb.get("action_timer", 0)
        cruise_vx = eb.get("cruise_vx", eb_v(eb, "vx", -5.5))
        cruise_vy = eb.get("cruise_vy", eb_v(eb, "vy"))
        if timer > 0:
            eb["action_timer"] = timer - 1
            eb["vx"] = cruise_vx
            eb["vy"] = cruise_vy
        else:
            eb["vx"] = -1.5
            eb["vy"] = 0.0
        return False

    if eb.get("speed_type") == "accel":
        timer = eb.get("action_timer", 0)
        cruise_vx = eb.get("cruise_vx", -2.0)
        cruise_vy = eb.get("cruise_vy", 0.0)
        if timer > 0:
            eb["action_timer"] = timer - 1
            eb["vx"] = cruise_vx
            eb["vy"] = cruise_vy
        else:
            eb["vx"] = -10.0
            eb["vy"] = 0.0
        return False

    if eb.get("mine"):
        mine_timer = eb.get("mine_timer", 0)
        if mine_timer > 0:
            eb["mine_timer"] = mine_timer - 1
            eb["vx"] = eb_v(eb, "vx") * 0.90
            eb["vy"] = eb_v(eb, "vy") * 0.90
            return False
        g()["explosion_sound"].play()
        g()["explosions"].append(Explosion(eb["x"], eb["y"], big=False))
        for a in range(0, 360, 90):
            rad = math.radians(a)
            append_boss_enemy_bullet({
                "x": eb["x"], "y": eb["y"],
                "vx": math.cos(rad) * 3.5, "vy": math.sin(rad) * 3.5,
                "homing": False, "is_boss_bullet": True, "image_type": "boss", "hp": 1,
                "life": ENEMY_BULLET_LIFE_FRAMES,  # 子弾に寿命を設定（画面外200px判定のみに頼らない）
            })
        if eb in g()["enemy_bullets"]:
            g()["enemy_bullets"].remove(eb)
        return True

    if (eb.get("homing") or eb.get("image_type") == "homing") and not g()["player_dead"]:
        dx = player.rect.centerx - eb["x"]
        dy = player.rect.centery - eb["y"]
        dist = max(1, math.hypot(dx, dy))
        # 近距離（120px以内）では追尾を緩めて回避猶予を確保
        base_steer = 3.2 if eb.get("is_boss_bullet") else 2.8
        if g()["diff"].name == "NORMAL":
            base_steer *= 0.82
        proximity_factor = min(1.0, dist / 120.0)
        steer = base_steer * (0.45 + 0.55 * proximity_factor)
        eb["vx"] = (eb_v(eb, "vx") * 0.95) + ((dx / dist) * steer * 0.05)
        eb["vy"] = (eb_v(eb, "vy") * 0.95) + ((dy / dist) * steer * 0.05)

    return False

def move_enemy_bullet(eb):
    if eb.get("freeze_timer", 0) > 0:
        eb["freeze_timer"] -= 1
        return

    vx = eb_v(eb, "vx")
    vy = eb_v(eb, "vy")
    if (
        not eb.get("is_boss_bullet")
        and not eb.get("speed_type")
        and eb.get("image_type") not in ("ripple", "ripple_homing")
        and math.hypot(vx, vy) < 0.35
    ):
        vx, vy = -4.0, 0.0
        eb["vx"] = vx
        eb["vy"] = vy

    eb["x"] = eb.get("x", 0) + vx
    eb["y"] = eb.get("y", 0) + vy

def enemy_bullet_bounce_vertical(eb) -> None:
    """上下プレイ領域端で vy を反転（ボス1斜めリップル用・何度でも反射）。"""
    margin = 14
    r = 40 if eb.get("attack_type") == "b1_diagonal_ripple" else max(6, int(eb.get("radius", 12)))
    top = margin + r
    bottom = g()["HEIGHT"] - margin - r
    if eb["y"] < top:
        eb["y"] = float(top)
        eb["vy"] = abs(eb_v(eb, "vy"))
    elif eb["y"] > bottom:
        eb["y"] = float(bottom)
        eb["vy"] = -abs(eb_v(eb, "vy"))


def enemy_bullet_bounce(eb):
    if eb.get("attack_type") == "b1_diagonal_ripple":
        enemy_bullet_bounce_vertical(eb)
        return
    if not eb.get("bounce"):
        return
    if eb["y"] <= 15:
        eb["y"] = 16
        if eb.get("bounce_count", 0) < 1:
            eb["vy"] = abs(eb_v(eb, "vy"))
            eb["bounce_count"] = eb.get("bounce_count", 0) + 1
        else:
            eb["bounce"] = False
    elif eb["y"] >= g()["HEIGHT"] - 15:
        eb["y"] = g()["HEIGHT"] - 16
        if eb.get("bounce_count", 0) < 1:
            eb["vy"] = -abs(eb_v(eb, "vy"))
            eb["bounce_count"] = eb.get("bounce_count", 0) + 1
        else:
            eb["bounce"] = False

def draw_enemy_bullet_sprite(eb):
    screen = g()["screen"]
    image_type = eb.get("image_type", "normal")
    attack_type = eb.get("attack_type")
    if attack_type in ("b1_tentacle_curtain", "b1_ground_tentacle"):
        timer = eb.get("special_timer", 0)
        length = int(eb.get("tentacle_len", 0))
        if length < 4 and attack_type == "b1_ground_tentacle":
            return
        length = int(eb.get("tentacle_len", 0))
        if attack_type == "b1_ground_tentacle" and length < 4:
            return
        if attack_type == "b1_tentacle_curtain" and length < 4:
            return
        if attack_type == "b1_tentacle_curtain":
            points = _b1_curtain_points(eb)
            pal = B1_CURTAIN_COLORS
        else:
            segments = 14
            points = []
            phase = eb.get("wave_phase", 0.0)
            amp = eb.get("wave_amp", 18)
            from_top = bool(eb.get("b1_from_top", False))
            for i in range(segments + 1):
                t = i / segments
                y = eb["y"] + length * t if from_top else eb["y"] - length * t
                x = eb["x"] + _b1_ground_tentacle_sway(eb, timer, t)
                points.append((int(x), int(y)))
            pal = _b1_ground_tentacle_palette(eb)
        if len(points) >= 2:
            pygame.draw.lines(screen, pal["outer"], False, points, 18)
            pygame.draw.lines(screen, pal["inner"], False, points, 8)
            pygame.draw.circle(screen, pal["base"], points[0], 14)
            for p in points[2::4]:
                pygame.draw.circle(screen, pal["tip"], p, 8)
        return

    if image_type == "extra_vulcan":
        _draw_extra_vulcan_bullet(screen, int(eb["x"]), int(eb["y"]))
        return

    if image_type in ("extra_tank_striker", "extra_tank_striker_missile", "extra_striker_bomb"):
        img = enemy_bullet_sprite_for(eb)
        if img is not None:
            if image_type == "extra_striker_bomb":
                dest = img.get_rect(midtop=(int(eb["x"]), int(eb["y"])))
            else:
                dest = img.get_rect(center=(int(eb["x"]), int(eb["y"])))
            screen.blit(img, dest)
        return

    if image_type == "extra_beam_cutter":
        img = g().get("extra_beam_cutter_img")
        if img is not None:
            dest = img.get_rect(midright=(int(eb["x"]), int(eb["y"])))
            screen.blit(img, dest)
        return

    if image_type == "extra_beam_orb":
        _draw_extra_beam_orb_bullet(screen, int(eb["x"]), int(eb["y"]))
        return

    if image_type == "ripple":
        if eb.get("attack_type") == "b1_diagonal_ripple":
            ripple = g().get("boss1_ripple_img", g()["boss_ripple_base_img"]).copy()
            ripple.fill((120, 240, 255), special_flags=pygame.BLEND_RGBA_MULT)
            g()["screen"].blit(ripple, ripple.get_rect(center=(int(eb["x"]), int(eb["y"]))))
            return
        radius = eb.get("radius", 15)
        max_r = eb.get("radius_max", 95)
        grow = eb.get("radius_grow", 1.2)
        if radius < max_r:
            eb["radius"] = radius + grow
        current_diameter = max(4, int(eb["radius"] * 2))
        scaled_ripple = pygame.transform.scale(g()["boss_ripple_base_img"], (current_diameter, current_diameter))
        g()["screen"].blit(scaled_ripple, scaled_ripple.get_rect(center=(int(eb["x"]), int(eb["y"]))))
        return

    if image_type == "ripple_homing":
        radius = eb.get("radius", 15)
        max_r = eb.get("radius_max", 130)
        grow = eb.get("radius_grow", 1.4)
        if radius < max_r:
            eb["radius"] = radius + grow
        current_diameter = int(eb["radius"] * 2)
        pulsing_ripple = g()["boss_ripple_base_img"].copy()
        if (pygame.time.get_ticks() // 100) % 2 == 0:
            pulsing_ripple.fill((255, 50, 50), special_flags=pygame.BLEND_RGBA_MULT)
        scaled_ripple = pygame.transform.scale(pulsing_ripple, (current_diameter, current_diameter))
        g()["screen"].blit(scaled_ripple, scaled_ripple.get_rect(center=(int(eb["x"]), int(eb["y"]))))
        return

    b_img = enemy_bullet_sprite_for(eb)
    if image_type == "boss2_fish":
        fish_rect = b_img.get_rect(center=(int(eb["x"]), int(eb["y"])))
        g()["screen"].blit(b_img, fish_rect)
        return

    if eb.get("special_attack") and image_type != "boss2_fish":
        pulse = 1.0 + 0.18 * math.sin(pygame.time.get_ticks() * 0.018)
        glow_r = int(max(b_img.get_width(), b_img.get_height()) * 0.72 * pulse)
        glow_color = (120, 220, 255) if image_type == "boss1_bullet" else (255, 120, 80)
        if image_type == "boss3_ufo":
            glow_color = (120, 180, 255)
        if image_type == "boss4_turret_bullet":
            glow_color = (200, 255, 120)
        pygame.draw.circle(screen, glow_color, (int(eb["x"]), int(eb["y"])), glow_r, 2)
        pygame.draw.circle(screen, WHITE, (int(eb["x"]), int(eb["y"])), max(4, glow_r // 3), 1)
    g()["screen"].blit(b_img, b_img.get_rect(center=(int(eb["x"]), int(eb["y"]))))

def update_ripple_homing_velocity(eb, player_dead):
    player = g()["player"]
    if not player_dead:
        dx = player.rect.centerx - eb["x"]
        dy = player.rect.centery - eb["y"]
        dist = max(1, math.hypot(dx, dy))
        # 左方向を保ちつつYのみプレイヤーへ寄せる
        target_vx = -abs(eb.get("base_vx", 5.5))
        eb["vx"] = (eb_v(eb, "vx") * 0.92) + (target_vx * 0.08)
        eb["vy"] = (eb_v(eb, "vy") * 0.94) + ((dy / dist) * 4.5 * 0.06)


def _extra_beam_cutter_offscreen(eb, width: int) -> bool:
    """ビームカッター全体が左画面外へ出たら除去（基準点=midright）。"""
    img = g().get("extra_beam_cutter_img")
    w = float(img.get_width() if img else 182)
    x = float(eb.get("x", 0))
    return x - w < -64.0 or x > width + 80.0


def _extra_boss_bullet_offscreen(eb, width: int, height: int) -> bool:
    """紫球体・バルカン・ビームカッター・戦闘機は画面外に出たら即除去。"""
    image_type = eb.get("image_type", "normal")
    if image_type == "extra_tank_striker":
        img = g().get("extra_tank_striker_img")
        half_w = float((img.get_width() if img else 80) * 0.55)
        x = float(eb.get("x", 0))
        return x + half_w < -48.0 or x - half_w > width + 80.0
    if image_type in ("extra_tank_striker_missile", "extra_striker_bomb"):
        margin = 28
        x = float(eb.get("x", 0))
        y = float(eb.get("y", 0))
        return (
            x < -margin
            or x > width + margin
            or y < -margin
            or y > height + margin
        )
    if image_type == "extra_beam_cutter":
        return _extra_beam_cutter_offscreen(eb, width)
    if image_type not in (
        "extra_beam_orb",
        "extra_vulcan",
        "extra_tank_striker_missile",
        "extra_striker_bomb",
        "boss3_bullet",
    ):
        return False
    if image_type == "boss3_bullet" and not (
        eb.get("extra_tank_homing") or eb.get("extra_robot_homing_snipe")
    ):
        return False
    margin = 36 if image_type == "boss3_bullet" else 28
    x = float(eb.get("x", 0))
    y = float(eb.get("y", 0))
    return (
        x < -margin
        or x > width + margin
        or y < -margin
        or y > height + margin
    )


def update_enemy_bullets_frame(state, player_dead, player, diff, boss_fight_timer):
    """1フレーム分の敵弾更新・描画・プレイヤー当たり。"""
    enemy_bullets = g()["enemy_bullets"]
    width = g()["WIDTH"]
    height = g()["HEIGHT"]
    ending = g().get("ENDING", 3)

    for eb in enemy_bullets[:]:
        image_type = eb.get("image_type", "normal")

        if _extra_boss_bullet_offscreen(eb, width, height):
            if eb in enemy_bullets:
                enemy_bullets.remove(eb)
            continue

        if eb.get("extra_robot_homing_charge"):
            continue

        if "life" in eb and not eb.get("offscreen_only"):
            eb["life"] -= 1
            if eb["life"] <= 0:
                if eb in enemy_bullets:
                    enemy_bullets.remove(eb)
                continue

        if eb.get("homing"):
            update_homing_bullet(eb, player, diff, boss_fight_timer)

        if eb.get("attack_type") == "b1_diagonal_ripple":
            fuse = int(eb.get("fuse_timer", 0)) - 1
            eb["fuse_timer"] = fuse
            if fuse <= 0:
                burst_b1_diagonal_ripple(
                    eb["x"],
                    eb["y"],
                    is_low_hp=bool(eb.get("b1_is_low_hp", False)),
                )
                if eb in enemy_bullets:
                    enemy_bullets.remove(eb)
                continue
            move_enemy_bullet(eb)
            if eb_v(eb, "vx") > -0.05:
                floor = diff.boss_bullet_speed_floor()
                eb["vx"] = -max(abs(eb_v(eb, "vx")), floor)
            enemy_bullet_bounce_vertical(eb)
        elif eb.get("attack_type") == "b2_player_ripple":
            update_b2_player_ripple(eb, player_dead)
            move_enemy_bullet(eb)
        elif eb.get("attack_type") in ("b1_ground_tentacle", "b1_tentacle_curtain"):
            enemy_bullet_special_motion(eb, player_dead, player)
        elif eb.get("attack_type"):
            if enemy_bullet_special_motion(eb, player_dead, player):
                continue
            move_enemy_bullet(eb)
            enemy_bullet_bounce(eb)
        elif image_type == "ripple_homing":
            update_ripple_homing_velocity(eb, player_dead)
            move_enemy_bullet(eb)
        elif image_type == "ripple":
            move_enemy_bullet(eb)
        elif image_type == "extra_beam_cutter":
            move_enemy_bullet(eb)
        else:
            if enemy_bullet_special_motion(eb, player_dead, player):
                continue
            move_enemy_bullet(eb)
            enemy_bullet_bounce(eb)

        if state != ending:
            draw_enemy_bullet_sprite(eb)

        if not player_dead and player.invincible_timer == 0:
            play = g().get("play")
            boss = play.boss if play is not None else None
            if play is not None and (
                getattr(play, "extra_victory_active", False)
                or (
                    boss is not None
                    and boss.boss_type == 6
                    and boss.hp <= 0
                )
            ):
                pass
            else:
                from combat import apply_player_hit, enemy_bullet_hits_player_sprite

                if image_type == "extra_beam_cutter":
                    hit_rect = enemy_bullet_hit_rect(eb)
                    if not hit_rect.colliderect(pygame.Rect(0, 0, width, height)):
                        pass
                    elif enemy_bullet_hits_player_sprite(player, eb):
                        apply_player_hit(hit_kind="grunt")
                        if eb in enemy_bullets:
                            enemy_bullets.remove(eb)
                        continue
                elif image_type in (
                    "extra_beam_orb",
                    "extra_vulcan",
                    "extra_tank_striker",
                    "extra_tank_striker_missile",
                    "extra_striker_bomb",
                ):
                    bx = float(eb.get("x", 0))
                    by = float(eb.get("y", 0))
                    if bx < 0 or bx > width or by < 0 or by > height:
                        pass
                    elif enemy_bullet_hits_player_sprite(player, eb):
                        apply_player_hit(hit_kind="grunt")
                        if eb in enemy_bullets:
                            enemy_bullets.remove(eb)
                        continue
                elif enemy_bullet_hits_player_sprite(player, eb):
                    apply_player_hit(hit_kind="grunt")
                    if eb in enemy_bullets:
                        enemy_bullets.remove(eb)
                    continue

        if eb["x"] < -200 or eb["x"] > width + 200 or eb["y"] < -200 or eb["y"] > height + 200:
            if eb in enemy_bullets:
                enemy_bullets.remove(eb)
