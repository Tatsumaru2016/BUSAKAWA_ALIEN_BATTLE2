# boss5_shield.py — HP10%以下: ボス前方（左）の破壊可能隕石盾

# ボス.rect.left / centery からの相対オフセット（左＝前方）
# 縦長2列：内列（ボス寄り）＋外列（プレイヤー側）
SHIELD_COL_INNER_X = -88
SHIELD_COL_OUTER_X = -142
SHIELD_ROW_STEP = 48          # 縦方向の間隔
SHIELD_EXTRA_ABOVE = 36       # ボス上端より上へ延長
SHIELD_EXTRA_BELOW = 36       # ボス下端より下へ延長

SHIELD_METEOR_HP = 25
SHIELD_RESPAWN_FRAMES = 60 * 5   # 全破壊後、再展開まで
SHIELD_HIT_RADIUS = 26


def init_boss5_shield_attrs(boss):
    boss.b5_shield_initialized = False
    boss.b5_shield_stashed = False
    boss.b5_shield_cache = []
    boss.b5_shield_respawn_cd = 0
    boss.b5_shield_had_active = False


def _shield_count(meteors, boss):
    n = sum(1 for m in meteors if m.get("b5_shield"))
    if getattr(boss, "b5_shield_stashed", False):
        n += len(getattr(boss, "b5_shield_cache", []))
    return n


def _shield_layout_for_boss(boss):
    """ボスの高さに合わせた縦長の隕石壁（2列）。"""
    top_y = (boss.rect.top - boss.rect.centery) - SHIELD_EXTRA_ABOVE
    bot_y = (boss.rect.bottom - boss.rect.centery) + SHIELD_EXTRA_BELOW
    rows = []
    y = top_y
    while y <= bot_y:
        rows.append(int(y))
        y += SHIELD_ROW_STEP
    if len(rows) < 6:
        rows = list(range(-140, 141, SHIELD_ROW_STEP))
    layout = []
    for oy in rows:
        layout.append((SHIELD_COL_INNER_X, oy))
    for oy in rows:
        layout.append((SHIELD_COL_OUTER_X, oy))
    return layout


def _make_shield_meteor(boss, off_x, off_y, slot_id):
    return {
        "x": float(boss.rect.left + off_x),
        "y": float(boss.rect.centery + off_y),
        "vx": 0.0,
        "vy": 0.0,
        "angle": 0.0,
        "b5_shield": True,
        "shield_slot": slot_id,
        "shield_off_x": float(off_x),
        "shield_off_y": float(off_y),
        "hp": SHIELD_METEOR_HP,
        "shield_max_hp": SHIELD_METEOR_HP,
    }


def spawn_boss5_meteor_shield(boss, meteors):
    """ボス左前方に縦長の隕石盾（2列）を展開。"""
    for i, (ox, oy) in enumerate(_shield_layout_for_boss(boss)):
        meteors.append(_make_shield_meteor(boss, ox, oy, i))
    boss.b5_shield_had_active = True


def stash_boss5_shield(boss, meteors):
    """突進中: 盾を一時退避（リストから外す）。"""
    if getattr(boss, "b5_shield_stashed", False):
        return
    cache = []
    for m in list(meteors):
        if m.get("b5_shield"):
            cache.append(m)
            meteors.remove(m)
    boss.b5_shield_cache = cache
    boss.b5_shield_stashed = bool(cache)


def restore_boss5_shield(boss, meteors):
    """突進終了後: 盾を復帰。"""
    if not getattr(boss, "b5_shield_stashed", False):
        return
    for m in boss.b5_shield_cache:
        m["vx"] = 0.0
        m["vy"] = 0.0
        m["x"] = float(boss.rect.left + m["shield_off_x"])
        m["y"] = float(boss.rect.centery + m["shield_off_y"])
        meteors.append(m)
    boss.b5_shield_cache = []
    boss.b5_shield_stashed = False


def sync_boss5_shield_positions(boss, meteors):
    for m in meteors:
        if not m.get("b5_shield"):
            continue
        m["x"] = float(boss.rect.left + m["shield_off_x"])
        m["y"] = float(boss.rect.centery + m["shield_off_y"])
        m["vx"] = 0.0
        m["vy"] = 0.0


def clear_boss5_meteor_shield(boss, meteors):
    meteors[:] = [m for m in meteors if not m.get("b5_shield")]
    boss.b5_shield_cache = []
    boss.b5_shield_stashed = False
    boss.b5_shield_respawn_cd = 0
    boss.b5_shield_had_active = False


def shield_meteor_rect(m):
    import pygame
    r = int(m.get("shield_radius", SHIELD_HIT_RADIUS))
    return pygame.Rect(0, 0, r * 2, r * 2).move(
        int(m["x"]) - r, int(m["y"]) - r,
    )


def shield_meteor_blocks_bullet(bullet, meteor) -> bool:
    """プレイヤー弾が隕石盾の描画ピクセルに当たったか（矩形より厳密）。"""
    from meteors import meteor_draw_surface
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
        import math

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


def manage_boss5_meteor_shield(boss, meteors, is_dying_hp):
    """毎フレーム: 瀕死時の隕石盾・突進連動・再展開。"""
    if not hasattr(boss, "b5_shield_initialized"):
        init_boss5_shield_attrs(boss)

    if not is_dying_hp:
        if _shield_count(meteors, boss) > 0 or getattr(boss, "b5_shield_stashed", False):
            clear_boss5_meteor_shield(boss, meteors)
        return

    rush_busy = getattr(boss, "b5_rush_state", "idle") in ("charge", "wait", "return")
    if rush_busy:
        stash_boss5_shield(boss, meteors)
        return

    restore_boss5_shield(boss, meteors)
    sync_boss5_shield_positions(boss, meteors)

    count = _shield_count(meteors, boss)

    if not boss.b5_shield_initialized:
        boss.b5_shield_initialized = True
        spawn_boss5_meteor_shield(boss, meteors)
        boss.b5_shield_respawn_cd = SHIELD_RESPAWN_FRAMES
        return

    if count > 0:
        boss.b5_shield_had_active = True
        boss.b5_shield_respawn_cd = SHIELD_RESPAWN_FRAMES
        return

    if boss.b5_shield_had_active:
        boss.b5_shield_respawn_cd = max(0, boss.b5_shield_respawn_cd - 1)
        if boss.b5_shield_respawn_cd <= 0:
            spawn_boss5_meteor_shield(boss, meteors)
