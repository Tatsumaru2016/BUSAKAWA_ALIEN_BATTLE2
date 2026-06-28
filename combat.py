# combat.py — 当たり判定と被弾処理

import math

import pygame

from explosion import Explosion
from game_runtime import RT
from settings import (
    BOSS5_LASER_DAMAGE_MUL,
    ENTITY_MASK_ALPHA_THRESHOLD,
    PLAYER_MASK_ALPHA_THRESHOLD,
    PLAYER_SHIELD_LOSS_BOSS,
    PLAYER_SHIELD_LOSS_GRUNT,
    PLAYER_SHIELD_LOSS_METEOR,
)


def g():
    return RT.g()


def bullet_damage_to_boss(bullet, boss) -> int:
    """ボス5のみレーザー弾ダメージを倍化（常時レーザー不可の補正）。"""
    dmg = int(getattr(bullet, "damage", 1))
    if (
        boss is not None
        and getattr(boss, "boss_type", None) == 5
        and getattr(bullet, "is_laser", False)
    ):
        dmg *= BOSS5_LASER_DAMAGE_MUL
    return dmg


BOSS_MASK_CACHE = {}
B5_RUSH_MASK_CACHE = {}
BULLET_MASK_CACHE = {}
PLAYER_MASK_CACHE = {}
ENEMY_MASK_CACHE = {}
TURRET_MASK_CACHE = {}
ENEMY_BULLET_MASK_CACHE = {}
METEOR_MASK_CACHE = {}
SPRITE_MASK_CACHE = {}

def surface_mask(surface, cache, *, threshold: int = 127):
    key = (id(surface), threshold)
    mask = cache.get(key)
    if mask is None:
        mask = pygame.mask.from_surface(surface, threshold=threshold)
        cache[key] = mask
    return mask


def entity_mask(
    surface: pygame.Surface,
    cache: dict,
    *,
    threshold: int = ENTITY_MASK_ALPHA_THRESHOLD,
) -> pygame.mask.Mask:
    return surface_mask(surface, cache, threshold=threshold)


def _bullet_laser_endpoints(bullet) -> tuple[float, float, float, float]:
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
    return x1, y1, x2, y2


def laser_hits_mask(
    mask: pygame.mask.Mask,
    dest: pygame.Rect,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    mw, mh = mask.get_size()
    length = math.hypot(x2 - x1, y2 - y1)
    samples = max(8, int(length / 6) + 1)
    for i in range(samples):
        t = i / max(1, samples - 1)
        px = x1 + (x2 - x1) * t
        py = y1 + (y2 - y1) * t
        mx = int(px) - dest.left
        my = int(py) - dest.top
        if 0 <= mx < mw and 0 <= my < mh and mask.get_at((mx, my)):
            return True
    return False


def bullet_hits_sprite_mask(
    bullet,
    surf: pygame.Surface,
    dest: pygame.Rect,
    *,
    mask_cache: dict = SPRITE_MASK_CACHE,
) -> bool:
    """自機弾がスプライトの不透明ピクセルに当たるか。"""
    if not bullet.rect.colliderect(dest):
        return False
    target_mask = entity_mask(surf, mask_cache)
    if getattr(bullet, "is_laser", False):
        x1, y1, x2, y2 = _bullet_laser_endpoints(bullet)
        return laser_hits_mask(target_mask, dest, x1, y1, x2, y2)
    bullet_mask = surface_mask(bullet.image, BULLET_MASK_CACHE, threshold=127)
    offset = (dest.left - bullet.rect.left, dest.top - bullet.rect.top)
    return bullet_mask.overlap(target_mask, offset) is not None


def bullet_hits_enemy_sprite(bullet, enemy) -> bool:
    return bullet_hits_sprite_mask(
        bullet, enemy.image, enemy.rect, mask_cache=ENEMY_MASK_CACHE
    )


def bullet_hits_turret_sprite(bullet, turret: dict) -> bool:
    return bullet_hits_sprite_mask(
        bullet, turret["image"], turret["rect"], mask_cache=TURRET_MASK_CACHE
    )


def bullet_hits_enemy_bullet_visual(bullet, eb) -> bool:
    from enemy_bullets import enemy_bullet_visual_for_hit

    surf, dest = enemy_bullet_visual_for_hit(eb)
    if surf is None or dest is None:
        return False
    return bullet_hits_sprite_mask(
        bullet, surf, dest, mask_cache=ENEMY_BULLET_MASK_CACHE
    )


def pickup_hits_player(player, item) -> bool:
    """アイテム取得判定: アイテムのBOXが自機RECTと接触したら取得。"""
    return bool(item.rect.colliderect(player.rect))


def enemy_body_hits_player(player, enemy) -> bool:
    return sprite_hits_player(player, enemy.image, enemy.rect)


def filled_circle_hits_player(
    player, cx: int, cy: int, radius: int, *, threshold: int = 160
) -> bool:
    r = max(1, radius)
    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 255, 255, 255), (r, r), r)
    dest = surf.get_rect(center=(cx, cy))
    mask = pygame.mask.from_surface(surf, threshold=threshold)
    return other_hits_player_masks(player, mask, dest)


def _boss_mask_dest(boss) -> tuple[pygame.mask.Mask, pygame.Rect]:
    """スプライトマスクと描画位置（rect 中心合わせ）。"""
    surf = boss.image
    boss_mask = surface_mask(surf, BOSS_MASK_CACHE)
    mw, mh = boss_mask.get_size()
    dest = pygame.Rect(0, 0, mw, mh)
    dest.center = boss.rect.center
    return boss_mask, dest


def bullet_hits_boss_visible_pixels(bullet, boss):
    boss_mask, dest = _boss_mask_dest(boss)
    if getattr(bullet, "is_laser", False):
        if abs(bullet.vx) + abs(bullet.vy) > 0.1:
            bullet.angle = math.atan2(bullet.vy, bullet.vx)
        length = getattr(bullet, "laser_length", 120)
        half = length / 2
        cos_a = math.cos(bullet.angle)
        sin_a = math.sin(bullet.angle)
        cx = bullet.rect.centerx
        cy = bullet.rect.centery
        samples = max(10, int(length / 6))
        for i in range(samples):
            t = i / max(1, samples - 1)
            px = cx - cos_a * half + cos_a * length * t
            py = cy - sin_a * half + sin_a * length * t
            mx = int(px) - dest.left
            my = int(py) - dest.top
            if (
                0 <= mx < dest.width
                and 0 <= my < dest.height
                and boss_mask.get_at((mx, my))
            ):
                return True
        return False

    bullet_mask = surface_mask(bullet.image, BULLET_MASK_CACHE)
    offset = (bullet.rect.left - dest.left, bullet.rect.top - dest.top)
    return boss_mask.overlap(bullet_mask, offset) is not None

def player_sprite_mask(player):
    """自機スプライトの不透明ピクセルマスク（描画と同じ image）。"""
    return surface_mask(
        player.image, PLAYER_MASK_CACHE, threshold=PLAYER_MASK_ALPHA_THRESHOLD
    )


def player_shield_active(player) -> bool:
    return float(getattr(player, "shield_meter", 0.0)) > 0.001


def player_collision_rect(player) -> pygame.Rect:
    """当たり範囲: シールド時はオーラ、なし時はコックピット。"""
    from player_status_ui import get_player_cockpit_hit, get_player_shield_aura_hit

    if player_shield_active(player):
        hit = get_player_shield_aura_hit(player)
        if hit is not None:
            return hit[1]
    return get_player_cockpit_hit(player)[1]


def player_hit_mask_parts(player) -> list[tuple[pygame.mask.Mask, pygame.Rect]]:
    """当たり: シールドあり→オーラ / なし→コックピットのみ。"""
    from player_status_ui import get_player_cockpit_hit, get_player_shield_aura_hit

    if player_shield_active(player):
        hit = get_player_shield_aura_hit(player)
        if hit is not None:
            return [hit]
        return []
    mask, rect = get_player_cockpit_hit(player)
    return [(mask, rect)]


def _point_on_mask(px: float, py: float, mask: pygame.mask.Mask, rect: pygame.Rect) -> bool:
    mx = int(px) - rect.left
    my = int(py) - rect.top
    mw, mh = mask.get_size()
    if 0 <= mx < mw and 0 <= my < mh:
        return bool(mask.get_at((mx, my)))
    return False


def player_point_opaque(px: float, py: float, player) -> bool:
    for mask, rect in player_hit_mask_parts(player):
        if _point_on_mask(px, py, mask, rect):
            return True
    return False


def rect_hits_player_sprite(player, rect: pygame.Rect) -> bool:
    """矩形と自機＋シールドの重なり（不透明部分のみ）。"""
    bounds = player_collision_rect(player)
    inter = rect.clip(bounds)
    if inter.width <= 0 or inter.height <= 0:
        return False
    step = max(3, min(inter.width, inter.height) // 8)
    for x in range(inter.left, inter.right + 1, step):
        for y in range(inter.top, inter.bottom + 1, step):
            if player_point_opaque(x, y, player):
                return True
    return False


def other_hits_player_masks(
    player, other_mask: pygame.mask.Mask, other_rect: pygame.Rect
) -> bool:
    for pm, pr in player_hit_mask_parts(player):
        if masks_overlap_at(pm, pr, other_mask, other_rect):
            return True
    return False


def masks_overlap_at(mask_a, rect_a, mask_b, rect_b) -> bool:
    offset = (rect_b.left - rect_a.left, rect_b.top - rect_a.top)
    return mask_a.overlap(mask_b, offset) is not None


def sprite_hits_player(player, surf: pygame.Surface, dest: pygame.Rect) -> bool:
    """相手スプライトの不透明ピクセルがプレイヤー当たりに触れるか。"""
    if not dest.colliderect(player_collision_rect(player)):
        return False
    other_mask = entity_mask(surf, SPRITE_MASK_CACHE)
    return other_hits_player_masks(player, other_mask, dest)


def sprite_hits_player_sprite(player, surf, dest: pygame.Rect) -> bool:
    return sprite_hits_player(player, surf, dest)


def laser_segment_hits_sprite_mask(
    surf: pygame.Surface, dest: pygame.Rect, x1, y1, x2, y2
) -> bool:
    """線分がスプライト不透明ピクセルに触れるか。"""
    mask = entity_mask(surf, SPRITE_MASK_CACHE)
    return laser_hits_mask(mask, dest, x1, y1, x2, y2)


def laser_segment_hits_player_sprite(player, x1, y1, x2, y2) -> bool:
    bounds = player_collision_rect(player)
    if not bounds.collidepoint(x1, y1) and not bounds.collidepoint(x2, y2):
        seg_rect = pygame.Rect(
            int(min(x1, x2)),
            int(min(y1, y2)),
            max(1, int(abs(x2 - x1))),
            max(1, int(abs(y2 - y1))),
        )
        if not seg_rect.colliderect(bounds):
            return False
    length = math.hypot(x2 - x1, y2 - y1)
    samples = max(8, int(length / 6) + 1)
    for i in range(samples):
        t = i / max(1, samples - 1)
        px = x1 + (x2 - x1) * t
        py = y1 + (y2 - y1) * t
        if player_point_opaque(px, py, player):
            return True
    return False


def enemy_bullet_hits_player_sprite(player, eb) -> bool:
    from enemy_bullets import enemy_bullet_visual_for_hit

    surf, dest = enemy_bullet_visual_for_hit(eb)
    if surf is None or dest is None:
        return False
    if not dest.colliderect(player_collision_rect(player)):
        return False
    b_mask = entity_mask(surf, ENEMY_BULLET_MASK_CACHE)
    return other_hits_player_masks(player, b_mask, dest)


def enemy_laser_hazard_active_in_play(
    laser, width: int, height: int, *, margin: int = 8,
) -> bool:
    """レーザー本体・線分がプレイ領域外なら当たり判定しない（左端遅延被弾防止）。"""
    if not getattr(laser, "is_laser", False):
        return True
    cx, cy = laser.rect.centerx, laser.rect.centery
    if cx < -margin or cx > width + margin or cy < -margin or cy > height + margin:
        return False
    if getattr(laser, "beam_from_anchor", False):
        x1, y1, x2, y2 = _bullet_laser_endpoints(laser)
        if max(x1, x2) < -margin or min(x1, x2) > width + margin:
            return False
        if max(y1, y2) < -margin or min(y1, y2) > height + margin:
            return False
    return True


def enemy_laser_hits_player_sprite(player, laser) -> bool:
    if not laser.is_laser:
        return sprite_hits_player(player, laser.image, laser.rect)
    x1, y1, x2, y2 = _bullet_laser_endpoints(laser)
    return laser_segment_hits_player_sprite(player, x1, y1, x2, y2)


def zako_explosion_hits_player_sprite(player, explosion) -> bool:
    """explosion_zako 系の表示スプライトと自機のマスク当たり。"""
    pair = explosion.display_surface_and_rect()
    if pair is None:
        return False
    surf, rect = pair
    return sprite_hits_player(player, surf, rect)


def meteor_sprite_hits_player_sprite(player, meteor_surf, meteor_rect: pygame.Rect) -> bool:
    if not meteor_rect.colliderect(player_collision_rect(player)):
        return False
    m_mask = entity_mask(meteor_surf, METEOR_MASK_CACHE)
    return other_hits_player_masks(player, m_mask, meteor_rect)


def player_hit_by_b5_rush(player, boss) -> bool:
    """ボス5突進：縮小回転スプライトのマスク判定＋移動経路サンプル。"""
    if getattr(boss, "b5_rush_state", "idle") != "charge":
        return False
    if not getattr(boss, "b5_rush_scaled", False):
        return False
    from boss5_update import b5_rush_draw_surface

    images = g().get("midboss5_images") or {}
    rush_image = images.get("normal") or boss.image
    surf, dest = b5_rush_draw_surface(boss, rush_image)
    rush_mask = entity_mask(surf, SPRITE_MASK_CACHE)
    pc = player_collision_rect(player)
    if dest.colliderect(pc) and other_hits_player_masks(player, rush_mask, dest):
        return True

    prev = getattr(boss, "b5_rush_prev_center", None)
    if prev is None:
        return False
    cx, cy = boss.rect.centerx, boss.rect.centery
    dist = math.hypot(cx - prev[0], cy - prev[1])
    if dist < 1.0:
        return False
    steps = min(8, max(2, int(dist // 12) + 1))
    for i in range(1, steps):
        t = i / steps
        sx = int(prev[0] + (cx - prev[0]) * t)
        sy = int(prev[1] + (cy - prev[1]) * t)
        dest_step = dest.copy()
        dest_step.center = (sx, sy)
        if not dest_step.colliderect(pc):
            continue
        if other_hits_player_masks(player, rush_mask, dest_step):
            return True
    return False


def player_hits_boss_body(player, boss):
    """自機当たり（不透明）とボス見た目のマスク重なり。"""
    if boss.boss_type == 5 and getattr(boss, "b5_rush_scaled", False):
        return player_hit_by_b5_rush(player, boss)
    boss_mask = entity_mask(boss.image, BOSS_MASK_CACHE)
    for pm, pr in player_hit_mask_parts(player):
        if masks_overlap_at(pm, pr, boss_mask, boss.rect):
            return True
    return False

def _shield_loss_for_hit(hit_kind: str) -> float:
    if hit_kind == "boss":
        return PLAYER_SHIELD_LOSS_BOSS
    if hit_kind == "meteor":
        return PLAYER_SHIELD_LOSS_METEOR
    return PLAYER_SHIELD_LOSS_GRUNT


def apply_player_hit(hit_kind: str = "grunt"):
    """自機が被弾したときの共通処理（シールドメーター優先）。"""
    rt = g()
    play = rt["play"]
    player = rt["player"]
    play.score_chain.break_chain()
    meter = float(getattr(player, "shield_meter", 0.0))
    if meter > 0.001:
        loss = _shield_loss_for_hit(hit_kind)
        player.shield_meter = max(0.0, meter - loss)
        player.invincible_timer = 60
        if player.shield_meter <= 0.001:
            player.shield_meter = 0.0
            rt["player_shield_break_sound"].play()
            rt["_bubble"].show("shield_broken")
        else:
            rt["player_shield_hit_sound"].play()
            rt["_bubble"].show("shield_hit")
    else:
        play.set("player_dead", True)
        play.set("lives", play.lives - 1)
        play.set("revive_timer", 90)
        play.set("gameover_timer", 120)
        # 撃破時: レーザー／速度ゲージは空にする
        try:
            player.laser_gauge = 0.0
            player.speed_gauge = 0.0
        except Exception:
            pass
        if play.lives <= 0:
            from audio import BGM_GAMEOVER, play_bgm, set_sfx_muted

            set_sfx_muted(True)
            play_bgm(BGM_GAMEOVER)
        else:
            rt["explosion_sound"].play()
        rt["_bubble"].show("player_hit")
        if play.lives == 0:
            rt["_bubble"].show("last_life")
        for _ in range(10):
            play.explosions.append(
                Explosion(player.rect.centerx, player.rect.centery, big=True)
            )
