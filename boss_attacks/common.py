"""Boss attacks (Phase 3)."""

import math
import random

import pygame

from game_runtime import RT
from enemy_bullets import (
    spawn_enemy_bullet,
    spawn_b1_ground_tentacle,
    spawn_boss2_fish_swarm,
    spawn_boss2_player_ripple,
    spawn_boss3_giant_laser,
    spawn_boss5_red_laser,
    spawn_boss5_ripple,
)
from meteors import spawn_boss5_meteor
from combat import apply_player_hit
from explosion import Explosion
from item_drops import roll_boss_supply_item_type
from powerup import PowerItem
from settings import BOSS_SUPPLY_INTERVAL_MAX, BOSS_SUPPLY_INTERVAL_MIN


def g():
    return RT.g()


def boss_special_alert_pulse(frames: int = 50) -> None:
    """自機付近の「！」表示タイマーを延長（play とグローバルを同期）。"""
    play = RT.play()
    play.set(
        "_boss_special_alert_timer",
        max(int(play._boss_special_alert_timer), int(frames)),
    )


def draw_boss_special_alert_icon(screen, player, timer: int) -> None:
    """自機付近の「！」を描画（タイマーは減算しない）。"""
    if timer <= 0:
        return
    from settings import PLAY_TOP_MARGIN, WIDTH, HEIGHT

    alert_alpha = 255 if timer > 10 else int(255 * timer / 10)
    alert_visible = True
    if timer > 20 and (timer // 4) % 2 == 0:
        alert_visible = False
    if not alert_visible:
        return
    top_m = PLAY_TOP_MARGIN
    ax = max(top_m, min(WIDTH - top_m, player.rect.centerx + 24))
    ay = max(top_m, min(HEIGHT - top_m, player.rect.top - 44))
    alert_bg = pygame.Surface((34, 34), pygame.SRCALPHA)
    pygame.draw.circle(alert_bg, (200, 0, 0, alert_alpha), (17, 17), 17)
    pygame.draw.circle(
        alert_bg,
        (255, 80, 80, min(255, alert_alpha + 60)),
        (17, 17),
        17,
        2,
    )
    screen.blit(alert_bg, (ax - 9, ay - 9))
    font = pygame.font.SysFont("Yu Gothic,Meiryo,msgothic,Arial", 20, bold=True)
    alert_surf = font.render("!", True, (255, 255, 255))
    alert_surf.set_alpha(alert_alpha)
    alert_rect = alert_surf.get_rect(center=(ax + 8, ay + 8))
    screen.blit(alert_surf, alert_rect)


def flush_boss4_tentacle_message_ui(play, screen, player, bubble) -> None:
    """触手開始フレームで吹き出し・！を同フレーム描画（player_input より後の更新用）。"""
    if play is None or not getattr(play, "_b4_tentacle_ui_flush", False):
        return
    play._b4_tentacle_ui_flush = False
    bubble.update_and_draw(screen, player.rect)
    draw_boss_special_alert_icon(
        screen, player, int(getattr(play, "_boss_special_alert_timer", 0) or 0),
    )


def boss_easy_mode() -> bool:
    return g()["diff"].name == "EASY"


def boss_easy_bullet_count(n: int, *, minimum: int = 1) -> int:
    """EASY: ボス攻撃の弾数を約38%減（boss_easy_bullet_count_mul）。"""
    count = int(n)
    if not boss_easy_mode():
        return max(minimum, count)
    mul = float(getattr(g()["diff"], "boss_easy_bullet_count_mul", 0.80))
    return max(minimum, int(round(count * mul)))


def boss_easy_pick_sequence(seq):
    """EASY: 列の要素数を弾数係数に合わせて間引く（両端を残して間引く）。"""
    items = tuple(seq)
    if not boss_easy_mode() or len(items) <= 1:
        return items
    want = boss_easy_bullet_count(len(items))
    if want >= len(items):
        return items
    if want == 1:
        return (items[len(items) // 2],)
    return tuple(items[int(round(i * (len(items) - 1) / (want - 1)))] for i in range(want))


def boss_hp_stage(boss, fight_timer=0, diff_name="NORMAL"):
    ratio = boss.hp / max(1, boss.max_hp)
    # 時間経過でステージを強制昇格\uff08難易度別�09
    if diff_name == "EASY":
        force_mid  = fight_timer >= 600    # 10秒
        force_last = fight_timer >= 1200   # 20秒
    elif diff_name == "NORMAL":
        force_mid  = fight_timer >= 960    # 16秒
        force_last = fight_timer >= 1980   # 33秒
    elif diff_name == "HARD":
        force_mid  = fight_timer >= 1200   # 20秒
        force_last = fight_timer >= 2400   # 40秒
    else:  # NIGHTMARE（旧HARD相当）
        force_mid  = fight_timer >= 1200
        force_last = fight_timer >= 2400
    # ボス1〜3: HP25%で最終段階（特殊攻撃は boss2/3 側で個別管理）
    last_ratio = 0.25 if getattr(boss, "boss_type", 5) <= 3 else 0.15
    if ratio <= last_ratio or force_last:
        return "last"
    if ratio <= 0.5 or force_mid:
        return "mid"
    return "high"


# ボス1〜3: HP段階ごとに通常弾幕の組み合わせを大きく切り替え
BOSS13_ATTACK_MIXES: dict[int, dict[str, tuple[str, ...]]] = {
    1: {
        "high": ("aim_fan", "spiral"),
        "mid": ("ring", "accel_lanes"),
        "last": ("spiral", "ring", "accel_lanes"),
    },
    2: {
        "high": ("aim_fan", "spiral"),
        "mid": ("ring", "spiral"),
        "last": ("spiral", "ring", "aim_fan"),
    },
    3: {
        "high": ("aim_fan", "ring"),
        "mid": ("spiral", "accel_lanes"),
        "last": ("ring", "spiral", "aim_fan"),
    },
}


def pick_boss13_attack_mix(boss_type: int, stage: str) -> tuple[str, ...]:
    table = BOSS13_ATTACK_MIXES.get(int(boss_type), {})
    return table.get(stage, table.get("high", ("aim_fan", "spiral")))


def boss_attack_pool(boss_type):
    # ボス4は main 内の専用弾幕（b4_spiral）のみ。mix はボス1〜3・5用。
    if boss_type in (1, 3):
        return ("aim_fan", "ring", "spiral", "accel_lanes")
    if boss_type == 2:
        # accel_lanes / boss2_homing / ripple_wave 廃止
        return ("aim_fan", "ring", "spiral")
    return ("laser_fan", "dual_spiral", "ripple_wave", "homing", "meteor", "ring", "sweep_laser")

BOSS_ATTACK_CATEGORY = {
    "aim_fan": "direct",
    "laser_fan": "direct",
    "ring": "area",
    "spiral": "area",
    "dual_spiral": "area",
    "homing": "pressure",
    "accel_lanes": "pressure",
    "ripple_wave": "pressure",
    "meteor": "gimmick",
    "sweep_laser": "gimmick",
}

def boss_attack_pick_count(boss_type):
    if boss_type <= 3:
        return 2
    return 4

def pick_boss_attack_mix(boss_type, stage: str = "high"):
    if int(boss_type) <= 3:
        return pick_boss13_attack_mix(boss_type, stage)
    pool = list(boss_attack_pool(boss_type))
    count = min(boss_attack_pick_count(boss_type), len(pool))
    grouped = {}
    for pattern in pool:
        grouped.setdefault(BOSS_ATTACK_CATEGORY.get(pattern, "misc"), []).append(pattern)

    preferred = ["direct", "area", "pressure", "gimmick"]
    if boss_type == 5:
        preferred = ["direct", "area", "pressure", "gimmick"]

    # ボス1・3は追尾なし。他ボスは homing を mix に必ず含める。
    if boss_type in (1, 3):
        chosen = ["aim_fan"]
    else:
        chosen = ["homing"]

    for cat in preferred:
        candidates = [p for p in grouped.get(cat, []) if p not in chosen]
        if candidates and len(chosen) < count:
            chosen.append(random.choice(candidates))

    remaining = [p for p in pool if p not in chosen]
    while len(chosen) < count and remaining:
        pick = random.choice(remaining)
        chosen.append(pick)
        remaining.remove(pick)
    random.shuffle(chosen)
    return chosen

def ensure_boss_attack_mix(boss):
    stage = boss_hp_stage(boss, g()["boss_fight_timer"], g()["diff"].name)
    if getattr(boss, "attack_mix_stage", None) == stage:
        return
    boss.attack_mix_stage = stage
    boss.attack_mix = pick_boss_attack_mix(boss.boss_type, stage)
    boss.attack_stage_timer = 0
    boss.spiral_angle = random.random() * math.tau
    boss.spiral_angle2 = boss.spiral_angle + math.pi

def boss_fire_point(boss):
    if boss.boss_type in (4, 5):
        return boss.rect.left + 20, boss.rect.centery
    return boss.rect.left, boss.rect.centery

def boss_stage_tuning(stage):
    if stage == "last":
        return 0.66, 1.28, 2
    if stage == "mid":
        return 0.82, 1.12, 1
    return 1.0, 1.0, 0


def boss13_pattern_interval(boss, base: int, stage: str) -> int:
    """ボス1〜3の mid/last: 間隔はやや短く（弾数は extra で抑える）。"""
    if boss.boss_type > 3:
        return base
    if stage == "mid":
        return max(5, int(base * 0.90))
    if stage == "last":
        return max(5, int(base * 0.78))
    return base


def boss13_pattern_extra(boss, stage: str) -> int:
    if boss.boss_type > 3:
        return 0
    if stage == "mid":
        return 0
    if stage == "last":
        return 1
    return 0


def _boss2_radial_density_relax(stage: str) -> bool:
    """ボス2: シールド破壊後〜HP50%付近（high/mid）の放射系をやや疎に。"""
    return stage in ("high", "mid")


def _boss3_radial_relax_level(boss) -> str | None:
    """ボス3: 放射系（ring/spiral）の緩和段階。None=なし。"""
    if boss.boss_type != 3:
        return None
    diff = g()["diff"].name
    if diff == "NORMAL":
        return "normal"
    if diff in ("HARD", "NIGHTMARE"):
        return "mild"
    return None


def boss_interval(base, stage):
    interval_scale, _, _ = boss_stage_tuning(stage)
    return max(4, int(base * interval_scale * g()["diff"].boss_fire_interval))

def boss_aim_angle(x, y):
    return math.atan2(g()["player"].rect.centery - y, g()["player"].rect.centerx - x)

def boss_pattern_velocity(boss, stage, vx, vy):
    # high段階でvxが右向き（>-0.35）の弾を強制的に左方向へ補正する。
    # これはring/spiralで後方に逃げる弾を「プレイヤー側へ誘導」する意図的な仕様。
    # mid/lastでは適用しない（HP低下時はプレイヤーに有利な弾が出てもよい）。
    if boss.boss_type <= 4 and stage == "high" and vx > -0.35:
        vx = -max(4.6, abs(vx))
        vy += random.uniform(-0.8, 0.8)
    return vx, vy

def boss_bullet_type(boss_type, homing=False):
    if boss_type in (1, 2, 3, 4):
        return f"boss{boss_type}_{'homing' if homing else 'bullet'}"
    return "boss_homing" if homing else "boss01"


# ボス2ホーミング: 口から渦状に大量発射・速度5分の3・自機弾で撃破可能
B2_HOMING_SPEED_MULT = 3 / 5
B2_MOUTH_U = 0.10
B2_MOUTH_V = 0.50
B2_VORTEX_ANGLE_STEP = 0.38
B2_VORTEX_RADIUS_GROW = 2.4
B2_VORTEX_SWIRL = 1.35


def boss2_mouth_point(boss):
    """ボス2スプライト左端付近（口）の発射原点。"""
    r = boss.rect
    return (
        r.left + int(r.width * B2_MOUTH_U),
        r.top + int(r.height * B2_MOUTH_V),
    )


def b2_homing_vortex_burst_len(stage, extra):
    """破壊可能ホーミング泡 — 旧仕様の約半分（フレーム数は維持、1fあたり発射を半減）。"""
    if stage == "last":
        return 30 + extra * 2, 2
    if stage == "mid":
        return 24 + extra, 2
    return 15 + extra, 2


def spawn_boss_homing_bullet(
    boss,
    x,
    y,
    off=0,
    speed_scale=1.0,
    extra=0,
    *,
    vx=None,
    vy=None,
):
    if vx is None:
        homing_vx = -3.2 * speed_scale
        if boss.boss_type == 1:
            homing_vx *= 0.88
        elif boss.boss_type == 2:
            homing_vx *= B2_HOMING_SPEED_MULT
        vx = homing_vx
        vy = 0.0
    eb = spawn_enemy_bullet(
        x=x,
        y=y + off,
        vx=vx,
        vy=vy,
        is_boss_bullet=True,
        image_type=boss_bullet_type(boss.boss_type, homing=True),
        homing=True,
    )
    eb["destructible"] = True
    return eb


def _ensure_b2_vortex_state(boss):
    if not hasattr(boss, "b2_vortex_burst_left"):
        boss.b2_vortex_burst_left = 0
        boss.b2_vortex_angle = 0.0
        boss.b2_vortex_spawn_idx = 0


def start_boss2_homing_vortex(boss, stage, extra):
    _ensure_b2_vortex_state(boss)
    frames, _ = b2_homing_vortex_burst_len(stage, extra)
    boss.b2_vortex_burst_left = frames
    boss.b2_vortex_angle = random.random() * math.tau
    boss.b2_vortex_spawn_idx = 0


def tick_boss2_homing_vortex(boss, speed_scale, extra, stage):
    """渦状バーストの1フレーム分を口から発射。"""
    if getattr(boss, "b2_vortex_burst_left", 0) <= 0:
        return
    _ensure_b2_vortex_state(boss)
    _, per_frame = b2_homing_vortex_burst_len(stage, extra)
    mouth_x, mouth_y = boss2_mouth_point(boss)
    base_speed = 3.2 * speed_scale * B2_HOMING_SPEED_MULT

    for i in range(boss_easy_bullet_count(per_frame)):
        idx = boss.b2_vortex_spawn_idx
        arm = (idx % 2) * math.pi
        spiral_r = 6.0 + (idx % 18) * B2_VORTEX_RADIUS_GROW
        angle = boss.b2_vortex_angle + arm + i * 0.22
        sx = mouth_x + math.cos(angle) * spiral_r
        sy = mouth_y + math.sin(angle) * spiral_r * 0.62
        tangent = angle + math.pi / 2
        vx = -base_speed * 0.9 + math.cos(tangent) * B2_VORTEX_SWIRL * speed_scale
        vy = math.sin(tangent) * B2_VORTEX_SWIRL * speed_scale * 1.15
        spawn_boss_homing_bullet(
            boss, sx, sy, 0, speed_scale, extra, vx=vx, vy=vy
        )
        boss.b2_vortex_spawn_idx += 1

    boss.b2_vortex_angle += B2_VORTEX_ANGLE_STEP
    boss.b2_vortex_burst_left -= 1


def spawn_boss2_snipe(x, y, speed_scale, extra):
    rad = boss_aim_angle(x, y)
    spd = (7.8 + extra * 0.4) * speed_scale
    spawn_enemy_bullet(
        x=x, y=y,
        vx=math.cos(rad) * spd,
        vy=math.sin(rad) * spd,
        is_boss_bullet=True, image_type=boss_bullet_type(2),
    )


def _roll_boss_supply_interval() -> int:
    return random.randint(BOSS_SUPPLY_INTERVAL_MIN, BOSS_SUPPLY_INTERVAL_MAX)


def update_boss_supply_drop(boss):
    if not hasattr(boss, "supply_timer"):
        boss.supply_timer = 0
        boss.next_supply_time = _roll_boss_supply_interval()
    boss.supply_timer += 1
    if boss.supply_timer < boss.next_supply_time:
        return
    boss.supply_timer = 0
    boss.next_supply_time = _roll_boss_supply_interval()
    item_type = roll_boss_supply_item_type(g()["player"])
    img = {
        "weapon": g()["power_weapon_img"],
        "laser_charge": g()["power_laser_charge_img"],
        "shield": g()["power_shield_img"],
        "speed": g()["power_speed_img"],
        "1up": g()["power_1up_img"],
    }[item_type]
    g()["power_items"].append(PowerItem(g()["WIDTH"] + 40, random.randint(90, g()["HEIGHT"] - 90), item_type, img))

def run_boss_attack_mix(boss):
    ensure_boss_attack_mix(boss)
    stage = boss_hp_stage(boss, g()["boss_fight_timer"], g()["diff"].name)
    _, speed_scale, extra = boss_stage_tuning(stage)
    x, y = boss_fire_point(boss)
    t = boss.shot_timer
    boss.attack_stage_timer = getattr(boss, "attack_stage_timer", 0) + 1
    # lastステージで螺旋回転速度を1.35倍に強化（arms=3と組み合わせて圧力増加）
    spiral_speed_scale = 1.35 if stage == "last" else 1.0
    boss.spiral_angle = getattr(boss, "spiral_angle", 0.0) + (0.055 + extra * 0.025) * spiral_speed_scale
    boss.spiral_angle2 = getattr(boss, "spiral_angle2", math.pi) - (0.052 + extra * 0.022) * spiral_speed_scale

    b13x = boss13_pattern_extra(boss, stage)
    for pattern in getattr(boss, "attack_mix", ()):
        if pattern == "aim_fan":
            aim_base = boss13_pattern_interval(boss, 58 - boss.boss_type * 4, stage)
            if t % boss_interval(aim_base, stage) == 0:
                base = boss_aim_angle(x, y)
                spread = 18 + extra * 8 + boss.boss_type * 2 + b13x * 4
                if boss.boss_type == 1:
                    count = boss_easy_bullet_count(5 + b13x)
                else:
                    count = boss_easy_bullet_count(3 + extra * 2 + b13x)
                for i in range(count):
                    off = -spread + (spread * 2 * i / max(1, count - 1))
                    rad = base + math.radians(off)
                    vx = math.cos(rad) * (5.4 + boss.boss_type * 0.35) * speed_scale
                    vy = math.sin(rad) * (5.4 + boss.boss_type * 0.35) * speed_scale
                    vx, vy = boss_pattern_velocity(boss, stage, vx, vy)
                    spawn_enemy_bullet(
                        x=x, y=y,
                        vx=vx,
                        vy=vy,
                        is_boss_bullet=True, image_type=boss_bullet_type(boss.boss_type),
                    )
        elif pattern == "ring":
            ring_base = boss13_pattern_interval(boss, 105, stage)
            if boss.boss_type == 2 and _boss2_radial_density_relax(stage):
                ring_base = int(ring_base * 1.30)
            elif (b3_relax := _boss3_radial_relax_level(boss)):
                ring_mul = 1.22 if b3_relax == "normal" else 1.12
                ring_base = int(ring_base * ring_mul)
            if t % boss_interval(ring_base, stage) == 0:
                count = 8 + extra * 4 + b13x * 2 + (2 if boss.boss_type >= 4 else 0)
                if boss.boss_type == 2 and _boss2_radial_density_relax(stage):
                    count = max(5, count - 3 - b13x)
                elif (b3_relax := _boss3_radial_relax_level(boss)):
                    drop = (2 if b3_relax == "normal" else 1) + b13x
                    count = max(6 if b3_relax == "normal" else 7, count - drop)
                count = boss_easy_bullet_count(count)
                offset = (t * 1.7) % 360
                for i in range(count):
                    rad = math.radians(offset + i * 360 / count)
                    vx = math.cos(rad) * (4.4 + extra * 0.45) * speed_scale
                    vy = math.sin(rad) * (4.4 + extra * 0.45) * speed_scale
                    vx, vy = boss_pattern_velocity(boss, stage, vx, vy)
                    spawn_enemy_bullet(
                        x=x,
                        y=y,
                        vx=vx,
                        vy=vy,
                        is_boss_bullet=True,
                        image_type=boss_bullet_type(boss.boss_type),
                        bounce=(boss.boss_type == 4 and i % 2 == 0),
                        bounce_count=0,
                    )
        elif pattern == "spiral":
            spiral_base = boss13_pattern_interval(boss, 18, stage)
            if boss.boss_type == 2 and _boss2_radial_density_relax(stage):
                spiral_base = int(spiral_base * 1.22)
            elif (b3_relax := _boss3_radial_relax_level(boss)):
                spiral_mul = 1.18 if b3_relax == "normal" else 1.10
                spiral_base = int(spiral_base * spiral_mul)
            if t % boss_interval(spiral_base, stage) == 0:
                arms = 2
                if boss.boss_type <= 3 and stage == "last":
                    arms = 3
                if _boss3_radial_relax_level(boss) == "normal" and stage == "last":
                    arms = 2
                arms = boss_easy_bullet_count(arms)
                for i in range(arms):
                    rad = boss.spiral_angle + i * math.tau / arms
                    vx = math.cos(rad) * (4.7 + extra * 0.5) * speed_scale
                    vy = math.sin(rad) * (4.7 + extra * 0.5) * speed_scale
                    vx, vy = boss_pattern_velocity(boss, stage, vx, vy)
                    spawn_enemy_bullet(
                        x=x, y=y,
                        vx=vx,
                        vy=vy,
                        is_boss_bullet=True, image_type=boss_bullet_type(boss.boss_type),
                    )
        elif pattern == "homing":
            if boss.boss_type in (2, 3):
                pass
            homing_base = boss13_pattern_interval(boss, 92, stage)
            if t % boss_interval(homing_base, stage) == 0:
                if boss.boss_type == 2:
                    pass
                else:
                    offsets = (-60, 60) if stage != "last" else (-85, 0, 85)
                    for off in boss_easy_pick_sequence(offsets):
                        spawn_boss_homing_bullet(boss, x, y, off, speed_scale, extra)
        elif pattern == "accel_lanes":
            if boss.boss_type == 2:
                continue
            lane_base = boss13_pattern_interval(boss, 118, stage)
            if t % boss_interval(lane_base, stage) == 0:
                lane_shift = random.randint(-45, 45)
                if boss.boss_type <= 3 and stage == "mid":
                    lanes = (120, 280, 440, 600)
                elif stage == "last":
                    lanes = (100, 250, 400, 550)
                else:
                    lanes = (130, 360, 590)
                rush_vx = -3.2 if boss.boss_type <= 3 and stage == "last" else -2.4
                rush_timer = 16 if boss.boss_type <= 3 and stage != "high" else 22
                for lane_y in boss_easy_pick_sequence(lanes):
                    lane_y = max(45, min(g()["HEIGHT"] - 45, lane_y + lane_shift))
                    spawn_enemy_bullet(
                        x=x, y=lane_y,
                        vx=rush_vx, vy=0,
                        is_boss_bullet=True, image_type=boss_bullet_type(boss.boss_type),
                        speed_type="accel", action_timer=rush_timer,
                        cruise_vx=rush_vx, cruise_vy=0,
                    )
        elif pattern == "laser_fan":
            if t % boss_interval(62, stage) == 0:
                base = boss_aim_angle(x, y)
                angles = (-24, 24) if stage == "high" else (-30, 0, 30)
                if stage == "last":
                    angles = (-36, -12, 12, 36)
                g()["laser_warning_sound"].play()
                for off in boss_easy_pick_sequence(angles):
                    spawn_boss5_red_laser(x, y, base + math.radians(off), speed=10.5 * speed_scale, life=145)
        elif pattern == "dual_spiral":
            if t % boss_interval(16, stage) == 0:
                for angle in (boss.spiral_angle, boss.spiral_angle2):
                    for i in range(boss_easy_bullet_count(2)):
                        rad = angle + i * math.pi
                        spawn_enemy_bullet(
                            x=x, y=y,
                            vx=math.cos(rad) * (5.0 + extra * 0.45) * speed_scale,
                            vy=math.sin(rad) * (5.0 + extra * 0.45) * speed_scale,
                            is_boss_bullet=True, image_type="boss01",
                        )
        elif pattern == "ripple_wave":
            ripple_base = boss13_pattern_interval(boss, 92, stage)
            ripple_phase = 28 if stage == "high" else 24 if stage == "mid" else 16
            if t % boss_interval(ripple_base, stage) == ripple_phase:
                g()["ripple_sound"].play()
                if boss.boss_type == 2:
                    mx, my = boss2_mouth_point(boss)
                    spawn_boss2_player_ripple(mx, my, speed_scale, extra)
                    if stage == "last" and not boss_easy_mode():
                        spawn_boss2_player_ripple(
                            mx, my + random.choice((-60, 60)), speed_scale, extra
                        )
                else:
                    offsets = (0,) if stage == "high" else (-55, 55) if stage == "mid" else (-80, 0, 80)
                    for off in boss_easy_pick_sequence(offsets):
                        dy = g()["player"].rect.centery - (y + off)
                        vy = (dy / max(1, abs(dy))) * (2.4 + extra * 0.35)
                        spawn_boss5_ripple(
                            x, y + off, vy=vy, vx=-5.4 * speed_scale,
                            radius=18 + extra * 3, radius_max=115 + extra * 20,
                        )
        elif pattern == "meteor":
            if t % boss_interval(85, stage) == 0:
                spawn_boss5_meteor()
                if stage == "last" and not boss_easy_mode():
                    spawn_boss5_meteor()
        elif pattern == "sweep_laser":
            sweep_interval = boss_interval(150, stage)
            sweep_t = t % sweep_interval
            sweep_frames = boss_easy_pick_sequence((20, 28, 36, 44, 52))
            if sweep_t in sweep_frames:
                sweep = (sweep_t - 20) / 32.0
                for sign in boss_easy_pick_sequence((-1, 1)):
                    spawn_boss5_red_laser(
                        x, y,
                        math.pi + sign * sweep * math.radians(58 + extra * 12),
                        speed=9.6 * speed_scale,
                    )
def boss_mix_blockers(boss):
    """run_boss_attack_mix を止める条件。"""
    b4_tentacle = False
    if boss.boss_type == 4:
        from boss_attacks.boss4_kraken import _b4_any_tentacle_active

        b4_tentacle = _b4_any_tentacle_active(boss)
    b2_charge = (
        boss.boss_type == 2
        and getattr(boss, "b2_charge_state", "idle") in ("charge", "wait", "return")
    )
    b3_burst = (
        boss.boss_type == 3
        and getattr(boss, "b3_sp_state", "idle") == "burst"
    )
    return b4_tentacle, b2_charge, b3_burst
