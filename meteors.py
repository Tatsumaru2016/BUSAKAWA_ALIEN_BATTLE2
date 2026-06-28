# meteors.py — 隕石の生成・衝突・更新

import math
import random

import pygame

from explosion import Explosion, MeteorZakoExplosion
from game_runtime import RT
from boss5_attack_patterns import update_fleet_meteor
from boss5_shield import manage_boss5_meteor_shield


def g():
    return RT.g()


# 破壊不可の大型隕石（2・3枚目）: 左へ進み続け、場外まで
CRUISER_MIN_LEFT_VX = 3.6
CRUISER_OFF_LEFT = -160
CRUISER_OFF_RIGHT_PAD = 520
CRUISER_OFF_Y = 120

# 画面内配置の静止障害物（4枚目）
OBSTACLE_HP_BY_DIFF = {
    "EASY": 3,
    "NORMAL": 4,
    "HARD": 5,
    "NIGHTMARE": 6,
}
OBSTACLE_MAX_ON_SCREEN = 2
OBSTACLE_SPAWN_CYCLE = {1: 420, 2: 360, 3: 300, 4: 260}
OBSTACLE_HIT_RADIUS = 34

# ボス5が発射する小隕石（隕石盾をすり抜け・画面外まで長く飛ぶ）
BOSS5_FIRED_SMALL_SPEED_MIN = 3.0
BOSS5_FIRED_SMALL_SPEED_MAX = 12.0
BOSS5_FIRED_SMALL_OFF_LEFT = -400
BOSS5_FIRED_SMALL_OFF_RIGHT = 560
BOSS5_FIRED_SMALL_OFF_Y = 160

METEOR_COLLIDE_RADIUS = 34
METEOR_SMALL_COLLIDE_RADIUS = 18
METEOR_FRAGMENT_LIFE = 90
METEOR_FRAGMENT_HP = 1
METEOR_SMALL_HP = 1


def _is_small_meteor(m) -> bool:
    return bool(m.get("fragment") or m.get("small"))


def _is_field_obstacle(m) -> bool:
    return bool(m.get("field_obstacle"))


def _is_cruiser_meteor(m) -> bool:
    """大型・破壊不可・移動（艦隊／通常発射）。"""
    if _is_small_meteor(m) or _is_field_obstacle(m) or m.get("b5_shield"):
        return False
    return bool(m.get("indestructible"))


def _is_destructible_meteor(m) -> bool:
    if m.get("b5_shield") or m.get("indestructible"):
        return False
    if _is_field_obstacle(m):
        return True
    if m.get("fragment") or m.get("small"):
        return True
    return False


def _is_boss5_fired_small(m) -> bool:
    return bool(m.get("small") and m.get("passes_b5_shield") and not m.get("fragment"))


def _enforce_cruiser_drift(m) -> None:
    """破壊不可隕石は減速・停止せず左方向へ進み続ける。"""
    if not _is_cruiser_meteor(m):
        return
    vx = float(m["vx"])
    vy = float(m["vy"])
    if vx > -CRUISER_MIN_LEFT_VX:
        spd = max(CRUISER_MIN_LEFT_VX, math.hypot(vx, vy))
        if abs(vy) < 0.15:
            vy = random.choice((-1.2, 1.2))
        ratio = abs(vy) / max(abs(vy), 0.01)
        m["vx"] = -math.sqrt(max(spd * spd - vy * vy, CRUISER_MIN_LEFT_VX ** 2))
        m["vy"] = vy * ratio if abs(vy) > 0.15 else vy
    m["angle"] = math.atan2(float(m["vy"]), float(m["vx"]))


def spawn_boss5_meteor():
    """ボス5: 右から直線で飛ぶ小隕石（破壊可能・盾をすり抜ける）。"""
    y = random.randint(90, g()["HEIGHT"] - 90)
    ang = math.pi + random.uniform(-0.35, 0.35)
    spd = random.uniform(BOSS5_FIRED_SMALL_SPEED_MIN, BOSS5_FIRED_SMALL_SPEED_MAX)
    g()["meteors"].append({
        "x": float(g()["WIDTH"] + 50),
        "y": float(y),
        "vx": math.cos(ang) * spd,
        "vy": math.sin(ang) * spd,
        "angle": ang,
        "small": True,
        "passes_b5_shield": True,
        "hp": METEOR_SMALL_HP,
    })


def spawn_boss5_cruiser_meteor_entry(
    x,
    y,
    angle,
    speed,
    *,
    fleet: bool = False,
    homing_strength: float = 0.0,
    formation_id: int = 0,
) -> dict:
    """破壊不可の大型隕石（必ず場外まで）。"""
    entry = {
        "x": float(x),
        "y": float(y),
        "vx": math.cos(angle) * speed,
        "vy": math.sin(angle) * speed,
        "angle": angle,
        "indestructible": True,
    }
    if fleet:
        entry["fleet"] = True
        entry["formation_id"] = formation_id
        entry["homing_strength"] = homing_strength
        entry["homing_active"] = False
        entry["life"] = 900
    return entry


def spawn_boss5_field_obstacle(meteors, width: int, height: int, diff) -> None:
    """静止障害物（4枚目）: 難易度別耐久。"""
    diff_name = getattr(diff, "name", "NORMAL")
    hp = OBSTACLE_HP_BY_DIFF.get(diff_name, 4)
    margin_x = 72
    margin_y = 100
    x = float(random.randint(margin_x, max(margin_x + 1, width - margin_x)))
    y = float(random.randint(margin_y, max(margin_y + 1, height - margin_y)))
    meteors.append({
        "x": x,
        "y": y,
        "vx": 0.0,
        "vy": 0.0,
        "angle": 0.0,
        "field_obstacle": True,
        "hp": hp,
        "max_hp": hp,
    })


def tick_boss5_field_obstacles(boss, meteors, diff, width: int, height: int, b5_phase: int) -> None:
    """定期的に画面内へ静止障害物を配置。"""
    cd = int(getattr(boss, "b5_obstacle_cd", 0))
    if cd > 0:
        boss.b5_obstacle_cd = cd - 1
        return
    on_screen = sum(1 for m in meteors if m.get("field_obstacle"))
    if on_screen >= OBSTACLE_MAX_ON_SCREEN:
        return
    spawn_boss5_field_obstacle(meteors, width, height, diff)
    boss.b5_obstacle_cd = OBSTACLE_SPAWN_CYCLE.get(b5_phase, 360)


def _meteor_collision_radius(m):
    if _is_field_obstacle(m):
        return OBSTACLE_HIT_RADIUS
    if _is_small_meteor(m):
        return METEOR_SMALL_COLLIDE_RADIUS
    return METEOR_COLLIDE_RADIUS


def meteor_draw_surface(m):
    """隕石描画サーフェス（当たり判定と blit で共通）。"""
    if _is_field_obstacle(m):
        img = g().get("meteor_obstacle_img")
        if img is not None:
            return img
    if _is_small_meteor(m):
        return g()["meteor_small_img"]
    scale = m.get("scale", 1.0)
    if scale >= 0.999:
        return g()["meteor_img"]
    sw = max(8, int(g()["meteor_img"].get_width() * scale))
    sh = max(8, int(g()["meteor_img"].get_height() * scale))
    return pygame.transform.smoothscale(g()["meteor_img"], (sw, sh))


_meteor_draw_surface = meteor_draw_surface


def meteor_blocks_player_bullet(bullet, meteor) -> bool:
    """プレイヤー弾が破壊可能隕石の描画ピクセルに当たったか。"""
    if not _is_destructible_meteor(meteor):
        return False
    from combat import (
        BULLET_MASK_CACHE,
        METEOR_MASK_CACHE,
        laser_segment_hits_sprite_mask,
        masks_overlap_at,
        surface_mask,
    )

    surf = meteor_draw_surface(meteor)
    m_rect = surf.get_rect(center=(int(meteor["x"]), int(meteor["y"])))
    m_mask = surface_mask(surf, METEOR_MASK_CACHE, threshold=160)
    if getattr(bullet, "is_laser", False):
        cx = bullet.rect.centerx
        cy = bullet.rect.centery
        length = getattr(bullet, "laser_length", 120)
        cos_a = math.cos(bullet.angle)
        sin_a = math.sin(bullet.angle)
        if getattr(bullet, "beam_from_anchor", False):
            x1, y1 = float(cx), float(cy)
            x2 = cx + cos_a * length
            y2 = cy + sin_a * length
        else:
            half = length / 2
            x1 = cx - cos_a * half
            y1 = cy - sin_a * half
            x2 = cx + cos_a * half
            y2 = cy + sin_a * half
        return laser_segment_hits_sprite_mask(surf, m_rect, x1, y1, x2, y2)
    b_mask = surface_mask(bullet.image, BULLET_MASK_CACHE)
    return masks_overlap_at(b_mask, bullet.rect, m_mask, m_rect)


def append_meteor_collision_explosion(explosions, x: float, y: float) -> None:
    zako = g().get("meteor_zako_explosion_img")
    if zako is not None:
        explosions.append(MeteorZakoExplosion(x, y, zako))
    else:
        explosions.append(Explosion(int(x), int(y), big=False))


def spawn_meteor_fragments(meteors, x, y):
    """隕石衝突時: 破片を8方向付近へ（破壊可能）。"""
    for i in range(8):
        ang = i * math.tau / 8 + random.uniform(-0.2, 0.2)
        spd = random.uniform(3.8, 6.8)
        meteors.append({
            "x": float(x),
            "y": float(y),
            "vx": math.cos(ang) * spd,
            "vy": math.sin(ang) * spd,
            "angle": ang,
            "fragment": True,
            "small": True,
            "hp": METEOR_FRAGMENT_HP,
            "life": METEOR_FRAGMENT_LIFE,
        })


def _meteor_pair_collides(a, b) -> bool:
    """破壊不可の大型隕石同士のみ衝突。"""
    return _is_cruiser_meteor(a) and _is_cruiser_meteor(b)


def process_meteor_collisions(meteors, explosions):
    """大型隕石同士 → zako爆発 + 破片。"""
    remove_idx = set()
    for i in range(len(meteors)):
        if i in remove_idx:
            continue
        a = meteors[i]
        if not _is_cruiser_meteor(a):
            continue
        for j in range(i + 1, len(meteors)):
            if j in remove_idx:
                continue
            b = meteors[j]
            if not _meteor_pair_collides(a, b):
                continue
            dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if dist >= _meteor_collision_radius(a) + _meteor_collision_radius(b):
                continue
            cx = (a["x"] + b["x"]) * 0.5
            cy = (a["y"] + b["y"]) * 0.5
            sfx = g().get("boss5_meteo1_sound")
            if sfx is not None:
                try:
                    sfx.play()
                except Exception:
                    pass
            append_meteor_collision_explosion(explosions, cx, cy)
            spawn_meteor_fragments(meteors, cx, cy)
            remove_idx.add(i)
            remove_idx.add(j)
            break
    for idx in sorted(remove_idx, reverse=True):
        meteors.pop(idx)


def update_meteors_frame(state, player_dead, player, boss_active, boss):
    """1フレーム分の隕石移動・衝突・描画・プレイヤー当たり。"""
    meteors = g()["meteors"]
    explosions = g()["explosions"]
    screen = g()["screen"]
    width = g()["WIDTH"]
    height = g()["HEIGHT"]
    ending = g().get("ENDING", 3)

    if boss_active and boss and boss.boss_type == 5:
        _b5_dying = boss.hp <= boss.max_hp * 0.10
        manage_boss5_meteor_shield(boss, meteors, _b5_dying)
        if not _b5_dying and boss.b5_charge_phase == 0:
            if boss.hp <= boss.max_hp * 0.10:
                b5_phase = 4
            elif boss.hp <= boss.max_hp * 0.25:
                b5_phase = 3
            elif boss.hp <= boss.max_hp * 0.5:
                b5_phase = 2
            else:
                b5_phase = 1
            tick_boss5_field_obstacles(
                boss, meteors, g()["diff"], width, height, b5_phase
            )

    for m in meteors[:]:
        if m.get("b5_shield") or _is_field_obstacle(m):
            if m.get("b5_shield"):
                continue
        else:
            m["x"] += m["vx"]
            m["y"] += m["vy"]

        if m.get("fragment"):
            m["life"] = m.get("life", METEOR_FRAGMENT_LIFE) - 1
            if m["life"] <= 0:
                if m in meteors:
                    meteors.remove(m)
                continue

        if m.get("fleet"):
            alive = update_fleet_meteor(m, player if not player_dead else None, width)
            _enforce_cruiser_drift(m)
            if not alive:
                if m in meteors:
                    meteors.remove(m)
                continue
        elif _is_cruiser_meteor(m):
            _enforce_cruiser_drift(m)

    if meteors:
        process_meteor_collisions(meteors, explosions)

    for m in meteors[:]:
        _m_img = meteor_draw_surface(m)
        if state != ending:
            screen.blit(_m_img, _m_img.get_rect(center=(int(m["x"]), int(m["y"]))))

        m_rect = _m_img.get_rect(center=(int(m["x"]), int(m["y"])))
        if not player_dead and player.invincible_timer == 0:
            from combat import apply_player_hit, meteor_sprite_hits_player_sprite

            if meteor_sprite_hits_player_sprite(player, _m_img, m_rect):
                apply_player_hit(hit_kind="meteor")
                if m in meteors and not _is_cruiser_meteor(m):
                    meteors.remove(m)
                continue

        if m.get("b5_shield") or _is_field_obstacle(m):
            continue
        if _is_boss5_fired_small(m):
            off_left = BOSS5_FIRED_SMALL_OFF_LEFT
            off_right = width + BOSS5_FIRED_SMALL_OFF_RIGHT
            off_y = BOSS5_FIRED_SMALL_OFF_Y
        elif _is_cruiser_meteor(m):
            off_left = CRUISER_OFF_LEFT
            off_right = width + CRUISER_OFF_RIGHT_PAD
            off_y = CRUISER_OFF_Y
        else:
            off_left, off_right, off_y = -120, width + 120, 80
        if (
            m["x"] < off_left
            or m["x"] > off_right
            or m["y"] < -off_y
            or m["y"] > height + off_y
        ):
            if m in meteors:
                meteors.remove(m)
