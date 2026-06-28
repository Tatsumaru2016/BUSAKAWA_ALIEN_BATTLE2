"""Boss attacks (Phase 3)."""

import math
import random

import pygame

from boss_attacks.common import boss_easy_bullet_count, boss_easy_pick_sequence
from combat import bullet_hits_sprite_mask, masks_overlap_at, player_hit_mask_parts
from settings import ENTITY_MASK_ALPHA_THRESHOLD
from game_runtime import RT
from enemy_bullets import (
    spawn_enemy_bullet,
    spawn_b1_ground_tentacle,
    spawn_boss2_fish_swarm,
    spawn_boss3_giant_laser,
    spawn_boss5_red_laser,
    spawn_boss5_ripple,
)
from meteors import spawn_boss5_meteor
from combat import apply_player_hit
from explosion import Explosion
from powerup import PowerItem


def g():
    return RT.g()


def _b4_fire_period(base: int) -> int:
    """EASY: 発射間隔を延ばして弾幕量を抑える。"""
    if g()["diff"].name == "EASY":
        return max(1, int(round(base * 1.45)))
    return base


def _b4_fire_due(at: int, period: int) -> bool:
    return at % _b4_fire_period(period) == 0


# 本体は上下帯の見た目右端に左辺を接続（幅は右にはみ出し可）
BOSS4_SPAWN_RIGHT_OVERFLOW = 300  # 弾幕当たり等のレガシー参照用
BOSS4_BODY_SEAM_OVERLAP = 4  # 帯と本体の継ぎ目をわずかに重ねる
BOSS4_OVERLAY_X_SHIFT = 200  # 上帯・下帯を右へ
BOSS4_BODY_LEFT_SHIFT = 200  # 本体のみ左へ（帯と重なって可）
# 触手の根元（midboss4_d 上・左に出る肉瘤の位置＝参照スクショ黄○）
BOSS4_TENTACLE_ROOT_X_DRAW = 0.094
BOSS4_TENTACLE_ROOT_X_HIT = 0.10
BOSS4_TENTACLE_ROOT_Y_RATIO = 0.380
BOSS4_TENTACLE_ROOT_OFFSET_X = -35  # 左へ（従来-100から+65）
BOSS4_TENTACLE_ROOT_OFFSET_Y = 182  # 下へ
BOSS4_FIRE_X_RATIO = 0.10
BOSS4_OVERLAY_MASK_CACHE: dict = {}
_BOSS4_MASK_CENTER_X: dict[int, float] = {}
_BOSS4_SCREEN_LAYOUT_KEY: tuple[int, int] | None = None
_BOSS4_SCREEN_LAYOUT: dict = {}
BOSS4_TENTACLE_WAVE_AMP = 78.0
BOSS4_TENTACLE_WAVE_FREQ = 0.052
BOSS4_TENTACLE_EXTEND_SPD = 10.5   # 本体
BOSS4_STRIP_TENTACLE_EXTEND_SPD = 7.5  # 上帯・下帯（伸びのみ遅め）
BOSS4_TENTACLE_RETRACT_SPD = 14.25
BOSS4_BODY_TENTACLE_IDLE_FRAMES = 480
BOSS4_STRIP_TENTACLE_IDLE_FRAMES = 600
BOSS4_BODY_IDLE_SWAP_FRAMES = 48
BOSS4_STRIP_SNIPER_SPEED = 12.5
BOSS4_STRIP_SNIPER_CD_MIN = 140
BOSS4_STRIP_SNIPER_CD_MAX = 260
# 弾幕: 1.0より大きいほど発射間隔が長い
BOSS4_BULLET_INTERVAL_MUL = 1.05


def _b4_bullet_interval(base: int) -> int:
    return max(1, int(round(base * BOSS4_BULLET_INTERVAL_MUL)))


def _b4_bullet_count(n: int) -> int:
    return boss_easy_bullet_count(n)


# ボス4弾幕 (120,255,120) に合わせた触手色（先端スプライトは使わない）
B4_TENTACLE_PALETTE = {
    "outline": (28, 62, 38),
    "shadow": (45, 105, 55),
    "body": (85, 195, 105),
    "core": (140, 255, 155),
    "glow": (175, 255, 190),
}


def _boss4_overlay_mask(surface: pygame.Surface) -> pygame.mask.Mask:
    key = (id(surface), ENTITY_MASK_ALPHA_THRESHOLD)
    cached = BOSS4_OVERLAY_MASK_CACHE.get(key)
    if cached is None:
        cached = pygame.mask.from_surface(surface, threshold=ENTITY_MASK_ALPHA_THRESHOLD)
        BOSS4_OVERLAY_MASK_CACHE[key] = cached
    return cached


def _boss4_overlay_visual_center_x(surf: pygame.Surface) -> float:
    """不透明領域の水平中心（マスク bbox は初回のみ計算）。"""
    cid = id(surf)
    cached = _BOSS4_MASK_CENTER_X.get(cid)
    if cached is not None:
        return cached
    mask = _boss4_overlay_mask(surf)
    rects = mask.get_bounding_rects()
    if not rects:
        cx = surf.get_width() * 0.5
    else:
        left = min(r.left for r in rects)
        right = max(r.right for r in rects)
        cx = (left + right) * 0.5
    _BOSS4_MASK_CENTER_X[cid] = cx
    return cx


def _boss4_overlay_left(surf: pygame.Surface, anchor_x: float) -> int:
    return int(round(anchor_x - _boss4_overlay_visual_center_x(surf)))


def _boss4_overlay_visual_right_edge(surf: pygame.Surface, anchor_x: float) -> int:
    """帯スプライトの不透明領域の右端（プレイ座標）。"""
    base_left = _boss4_overlay_left(surf, anchor_x) + BOSS4_OVERLAY_X_SHIFT
    rects = _boss4_overlay_mask(surf).get_bounding_rects()
    if not rects:
        return base_left + surf.get_width()
    return base_left + max(r.right for r in rects)


def _boss4_screen_layout() -> dict:
    """上下帯の rect / join_x を解像度ごとに1回だけ構築。"""
    global _BOSS4_SCREEN_LAYOUT_KEY, _BOSS4_SCREEN_LAYOUT
    play_w = int(g()["WIDTH"])
    play_h = int(g()["HEIGHT"])
    key = (play_w, play_h)
    if _BOSS4_SCREEN_LAYOUT_KEY == key:
        return _BOSS4_SCREEN_LAYOUT
    rt = g()
    top = rt.get("boss4_overlay_top_img")
    bot = rt.get("boss4_overlay_bottom_img")
    anchor_x = play_w * 0.5
    join_x = 0
    pairs: list[tuple[pygame.Surface, pygame.Rect]] = []
    top_pair = None
    bot_pair = None
    if top is not None:
        tx = _boss4_overlay_left(top, anchor_x) + BOSS4_OVERLAY_X_SHIFT
        tr = top.get_rect(topleft=(tx, 0))
        top_pair = (top, tr)
        pairs.append(top_pair)
        join_x = max(join_x, _boss4_overlay_visual_right_edge(top, anchor_x))
    if bot is not None:
        bx = _boss4_overlay_left(bot, anchor_x) + BOSS4_OVERLAY_X_SHIFT
        br = bot.get_rect(bottomleft=(bx, play_h))
        bot_pair = (bot, br)
        pairs.append(bot_pair)
        join_x = max(join_x, _boss4_overlay_visual_right_edge(bot, anchor_x))
    _BOSS4_SCREEN_LAYOUT = {
        "join_x": join_x,
        "pairs": pairs,
        "top_pair": top_pair,
        "bot_pair": bot_pair,
    }
    _BOSS4_SCREEN_LAYOUT_KEY = key
    return _BOSS4_SCREEN_LAYOUT


def _boss4_overlay_join_x(play_w: int) -> int:
    return int(_boss4_screen_layout()["join_x"])


def _boss4_play_layout() -> tuple[int, int, int, int, int]:
    """プレイ領域ローカル座標: top_h, bot_h, body_h, play_w, play_h。"""
    rt = g()
    top = rt.get("boss4_overlay_top_img")
    bot = rt.get("boss4_overlay_bottom_img")
    play_w = int(rt["WIDTH"])
    play_h = int(rt["HEIGHT"])
    top_h = top.get_height() if top is not None else 0
    bot_h = bot.get_height() if bot is not None else 0
    body_h = max(1, play_h)  # HUD下〜地面（プレイ高さ全体）
    return top_h, bot_h, body_h, play_w, play_h


def _boss4_build_strip_rects() -> tuple[
    tuple[pygame.Surface, pygame.Rect] | None,
    tuple[pygame.Surface, pygame.Rect] | None,
]:
    layout = _boss4_screen_layout()
    return layout["top_pair"], layout["bot_pair"]


def _boss4_overlay_pairs(boss=None) -> list[tuple[pygame.Surface, pygame.Rect]]:
    cached = None
    if boss is not None:
        cached = getattr(boss, "_b4_overlay_pairs", None)
    if cached:
        return cached
    return list(_boss4_screen_layout()["pairs"])


def boss4_overlay_rects(boss=None) -> list[tuple[pygame.Surface, pygame.Rect]]:
    """上帯→下帯の順（当たり判定・描画用）。"""
    return _boss4_overlay_pairs(boss)


def draw_boss4_screen_overlays(screen, boss=None) -> None:
    """ボス4本体の手前（背景側）に上下帯を描画。"""
    for surf, rect in boss4_overlay_rects(boss):
        screen.blit(surf, rect)


def _boss4_strip_fire_point(
    surf: pygame.Surface, rect: pygame.Rect, *, strip: str
) -> tuple[int, int]:
    """上帯=下端の砲口、下帯=上端の砲口。"""
    mask = _boss4_overlay_mask(surf)
    w, h = surf.get_size()
    from_top = strip == "top"
    if from_top:
        local_ys = (h - 8, h - 16, h - 26, h - 38)
    else:
        local_ys = (8, 16, 26, 38)
    for ly in local_ys:
        ly = max(0, min(h - 1, int(ly)))
        for lx in range(0, max(1, int(w * 0.58))):
            if mask.get_at((lx, ly)):
                return rect.left + lx, rect.top + ly
    if from_top:
        return rect.left + w // 4, rect.bottom - 8
    return rect.left + w // 4, rect.top + 8


def _boss4_fire_strip_sniper(boss) -> None:
    """上帯または下帯から自機へスナイプ弾1発。"""
    if g()["player_dead"]:
        return
    top_pair, bot_pair = _boss4_build_strip_rects()
    choices: list[tuple[str, pygame.Surface, pygame.Rect]] = []
    if top_pair is not None:
        choices.append(("top", top_pair[0], top_pair[1]))
    if bot_pair is not None:
        choices.append(("bottom", bot_pair[0], bot_pair[1]))
    if not choices:
        return
    strip, surf, rect = random.choice(choices)
    fx, fy = _boss4_strip_fire_point(surf, rect, strip=strip)
    player = g()["player"]
    from enemy_bullets import spawn_boss4_strip_sniper_bullet

    spawn_boss4_strip_sniper_bullet(
        fx,
        fy,
        float(player.rect.centerx),
        float(player.rect.centery),
        from_top=(strip == "top"),
        speed=BOSS4_STRIP_SNIPER_SPEED,
    )


def _b4_strip_tentacle_active(boss, slot: str) -> bool:
    return str(_b4_slot_get(boss, slot, "state")) in ("extend", "retract")


def _b4_any_strip_tentacle_active(boss) -> bool:
    return _b4_strip_tentacle_active(boss, "top") or _b4_strip_tentacle_active(
        boss, "bottom"
    )


def update_boss4_strip_sniper(boss) -> None:
    """上下帯触手が出ていない間は帯からスナイプ。"""
    sync_boss4_body_layout(boss)
    if _b4_any_strip_tentacle_active(boss):
        return
    if not hasattr(boss, "b4_strip_sniper_cd"):
        boss.b4_strip_sniper_cd = random.randint(
            _b4_fire_period(45), _b4_fire_period(BOSS4_STRIP_SNIPER_CD_MIN)
        )
        return
    cd = int(boss.b4_strip_sniper_cd or 0)
    if cd <= 0:
        _boss4_fire_strip_sniper(boss)
        boss.b4_strip_sniper_cd = random.randint(
            _b4_fire_period(BOSS4_STRIP_SNIPER_CD_MIN),
            _b4_fire_period(BOSS4_STRIP_SNIPER_CD_MAX),
        )
    else:
        boss.b4_strip_sniper_cd = cd - 1


def _bullet_laser_hits_rect(bullet, rect: pygame.Rect) -> bool:
    """レーザーと矩形の粗い当たり（シールド時の高速判定用）。"""
    if not bullet.rect.colliderect(rect.inflate(24, 24)):
        return False
    length = float(getattr(bullet, "laser_length", 120))
    half = length * 0.5
    if abs(bullet.vx) + abs(bullet.vy) > 0.1:
        angle = math.atan2(bullet.vy, bullet.vx)
    else:
        angle = float(getattr(bullet, "angle", 0.0))
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cx = bullet.rect.centerx
    cy = bullet.rect.centery
    samples = max(8, int(length / 8))
    for i in range(samples):
        t = i / max(1, samples - 1)
        px = cx - cos_a * half + cos_a * length * t
        py = cy - sin_a * half + sin_a * length * t
        if rect.collidepoint(int(px), int(py)):
            return True
    return False


def bullet_hits_boss4_shield_block(bullet, boss) -> bool:
    """シールド有効時: 本体＋上下帯を矩形のみで判定（マスク精査なし）。"""
    if bullet.rect.colliderect(boss.rect):
        return True
    if getattr(bullet, "is_laser", False):
        if _bullet_laser_hits_rect(bullet, boss.rect):
            return True
        for _surf, rect in _boss4_overlay_pairs(boss):
            if _bullet_laser_hits_rect(bullet, rect):
                return True
        return False
    for _surf, rect in _boss4_overlay_pairs(boss):
        if bullet.rect.colliderect(rect):
            return True
    return False


def bullet_hits_boss4_overlays(bullet, boss=None) -> bool:
    """上下帯の不透明ピクセルに自機弾が当たるか。"""
    for surf, rect in _boss4_overlay_pairs(boss):
        if not bullet.rect.colliderect(rect):
            continue
        if bullet_hits_sprite_mask(
            bullet, surf, rect, mask_cache=BOSS4_OVERLAY_MASK_CACHE
        ):
            return True
    return False


def _b4_slot_keys(slot: str) -> dict[str, str | None]:
    if slot == "body":
        return {
            "state": "arm_state",
            "timer": "arm_timer",
            "len": "tentacle_len",
            "target_x": None,
            "target_y": "tentacle_target_y",
        }
    prefix = "b4_top_" if slot == "top" else "b4_bot_"
    return {
        "state": f"{prefix}arm_state",
        "timer": f"{prefix}arm_timer",
        "len": f"{prefix}tentacle_len",
        "target_x": f"{prefix}target_x",
        "target_y": f"{prefix}target_y",
    }


def _b4_slot_get(boss, slot: str, field: str):
    key = _b4_slot_keys(slot)[field]
    if key is None:
        return None
    defaults = {
        "state": "idle",
        "timer": 0,
        "len": 0.0,
        "target_x": 0.0,
        "target_y": float(g()["HEIGHT"]) * 0.5,
    }
    return getattr(boss, key, defaults[field])


def _b4_slot_set(boss, slot: str, field: str, value) -> None:
    key = _b4_slot_keys(slot)[field]
    if key is not None:
        setattr(boss, key, value)


def _b4_strip_tentacle_root(strip: str) -> tuple[int, int] | None:
    """上帯=内側下端、下帯=内側上端（触手の根元）。"""
    top_pair, bot_pair = _boss4_build_strip_rects()
    if strip == "top":
        if top_pair is None:
            return None
        surf, rect = top_pair
    else:
        if bot_pair is None:
            return None
        surf, rect = bot_pair
    mask = _boss4_overlay_mask(surf)
    w, h = surf.get_size()
    from_top = strip == "top"
    if from_top:
        local_ys = (h - 8, h - 16, h - 26, h - 38)
    else:
        local_ys = (8, 16, 26, 38)
    for ly in local_ys:
        ly = max(0, min(h - 1, int(ly)))
        for lx in range(0, max(1, int(w * 0.58))):
            if mask.get_at((lx, ly)):
                return rect.left + lx, rect.top + ly
    if from_top:
        return rect.left + w // 4, rect.bottom - 8
    return rect.left + w // 4, rect.top + 8


def _b4_any_tentacle_active(boss) -> bool:
    for slot in ("body", "top", "bottom"):
        if _b4_slot_get(boss, slot, "state") in ("extend", "retract"):
            return True
    return False


def reset_boss4_tentacles(boss) -> None:
    """シールド破壊猶予中は攻撃更新が止まるため、触手を即 idle に戻す。"""
    for slot in ("body", "top", "bottom"):
        _b4_slot_set(boss, slot, "state", "idle")
        _b4_slot_set(boss, slot, "timer", 0)
        _b4_slot_set(boss, slot, "len", 0.0)
    boss._b4_body_bubble_once = False
    for slot in ("top", "bottom"):
        setattr(boss, f"_b4_{slot}_bubble_once", False)
    boss._b4_sync_timer = -1


def _boss4_shield_grace_active() -> bool:
    play = g().get("play")
    if play is None:
        return False
    return int(getattr(play, "boss_shield_grace_timer", 0) or 0) > 0


def _b4_tentacle_bubble_flag(slot: str) -> str:
    return "_b4_body_bubble_once" if slot == "body" else f"_b4_{slot}_bubble_once"


def _boss4_tentacle_alert_and_bubble(boss, slot: str = "body") -> None:
    """触手攻撃開始と同時: 画面アラート＋自機吹き出し（スロットごとに1回）。"""
    from boss_attacks.common import boss_special_alert_pulse

    flag = _b4_tentacle_bubble_flag(slot)
    if getattr(boss, flag, False):
        return
    setattr(boss, flag, True)
    boss_special_alert_pulse(50)
    g()["_bubble"].show("boss4_tentacle")
    play = g().get("play")
    if play is not None:
        play._b4_tentacle_ui_flush = True
    try:
        g()["boss_special_alert_sound"].play()
    except Exception:
        pass


def player_hits_boss4_screen_overlays(player, boss=None) -> bool:
    for surf, rect in boss4_overlay_rects(boss):
        if not rect.colliderect(player.rect):
            continue
        omask = _boss4_overlay_mask(surf)
        for pm, pr in player_hit_mask_parts(player):
            if masks_overlap_at(pm, pr, omask, rect):
                return True
    return False


def _b4_body_tentacle_sprite_active(boss) -> bool:
    """本体スプライト midboss4_f（触手攻撃ポーズ）を使う間。"""
    return _b4_slot_get(boss, "body", "state") in ("extend", "retract")


def _b4_tick_idle_body_frame(boss) -> None:
    if _b4_body_tentacle_sprite_active(boss):
        return
    t = int(getattr(boss, "b4_idle_swap_timer", 0)) + 1
    boss.b4_idle_swap_timer = t
    if t >= BOSS4_BODY_IDLE_SWAP_FRAMES:
        boss.b4_idle_swap_timer = 0
        boss.b4_idle_frame = 1 - int(getattr(boss, "b4_idle_frame", 0))


def _b4_body_frame_key(boss) -> str:
    if _b4_body_tentacle_sprite_active(boss):
        return "f"
    return "d" if int(getattr(boss, "b4_idle_frame", 0)) == 0 else "e"


def _b4_body_source_surface(frame_key: str) -> pygame.Surface:
    rt = g()
    keyed = rt.get(f"midboss4_body_{frame_key}")
    if keyed is not None:
        return keyed
    return rt.get("midboss4_body_src") or rt["midboss4_body_img"]


def sync_boss4_body_layout(boss) -> None:
    """通常: midboss4_d/e 交互。本体触手攻撃中: midboss4_f 固定。"""
    tick = int(getattr(boss, "shot_timer", -1))
    _b4_tick_idle_body_frame(boss)
    frame_key = _b4_body_frame_key(boss)
    if (
        getattr(boss, "_b4_sync_timer", -2) == tick
        and getattr(boss, "_b4_body_frame_key", "") == frame_key
    ):
        return
    boss._b4_sync_timer = tick
    boss._b4_body_frame_key = frame_key
    src = _b4_body_source_surface(frame_key)
    _top_h, _bot_h, body_h, play_w, _play_h = _boss4_play_layout()
    iw, ih = src.get_size()
    if ih <= 0:
        boss.image = src
        boss._b4_body_size = src.get_size()
    else:
        target_w = max(1, int(iw * body_h / ih))
        size_key = (frame_key, target_w, body_h)
        if getattr(boss, "_b4_body_size", None) != size_key:
            boss.image = pygame.transform.smoothscale(src, (target_w, body_h))
            boss._b4_body_size = size_key
    layout = _boss4_screen_layout()
    boss._b4_overlay_pairs = layout["pairs"]
    join_x = int(layout["join_x"])
    body_left = join_x - BOSS4_BODY_SEAM_OVERLAP - BOSS4_BODY_LEFT_SHIFT
    boss.rect = boss.image.get_rect(top=0, left=body_left)


def _boss4_tentacle_root(
    boss, slot: str = "body", *, for_hit: bool = False
) -> tuple[int, int]:
    if slot == "body":
        rx = BOSS4_TENTACLE_ROOT_X_HIT if for_hit else BOSS4_TENTACLE_ROOT_X_DRAW
        base_y = boss.rect.top + int(boss.rect.height * BOSS4_TENTACLE_ROOT_Y_RATIO)
        return (
            boss.rect.left + int(boss.rect.width * rx) + BOSS4_TENTACLE_ROOT_OFFSET_X,
            base_y + BOSS4_TENTACLE_ROOT_OFFSET_Y,
        )
    pt = _b4_strip_tentacle_root(slot)
    if pt is None:
        return 0, int(g()["HEIGHT"]) * 0.5
    return pt


def _boss4_tentacle_baseline(
    boss, slot: str = "body", *, for_hit: bool = False
) -> tuple[float, float, float, float, float]:
    root_x, root_y = _boss4_tentacle_root(boss, slot, for_hit=for_hit)
    root_x, root_y = float(root_x), float(root_y)
    if slot == "body":
        target_y = float(_b4_slot_get(boss, slot, "target_y") or root_y)
        dx = -max(1.0, root_x)
        dy = target_y - root_y
    else:
        target_x = float(_b4_slot_get(boss, slot, "target_x") or root_x)
        target_y = float(_b4_slot_get(boss, slot, "target_y") or root_y)
        dx = target_x - root_x
        dy = target_y - root_y
    dist = max(1.0, math.hypot(dx, dy))
    return root_x, root_y, dx / dist, dy / dist, dist


def _b4_tentacle_extend_cap(boss, slot: str) -> float:
    _, _, _, _, reach = _boss4_tentacle_baseline(boss, slot, for_hit=True)
    return min(reach, float(g()["WIDTH"]) - 80)


def _boss4_tentacle_point_at(
    boss, along: float, slot: str = "body", *, for_hit: bool = False
) -> tuple[int, int]:
    root_x, root_y, tx, ty, max_len = _boss4_tentacle_baseline(
        boss, slot, for_hit=for_hit
    )
    along = max(0.0, min(float(along), max_len))
    bx = root_x + tx * along
    by = root_y + ty * along
    nx, ny = ty, -tx
    progress = along / max(1.0, max_len)
    envelope = math.sin(progress * math.pi)
    arm_t = float(_b4_slot_get(boss, slot, "timer") or 0)
    wave = (
        math.sin(along * BOSS4_TENTACLE_WAVE_FREQ + arm_t * 0.18)
        * BOSS4_TENTACLE_WAVE_AMP
        * envelope
    )
    return int(bx + nx * wave), int(by + ny * wave)


def _boss4_tentacle_tip_pos(boss, slot: str = "body") -> tuple[int, int, float]:
    _, _, _, _, max_len = _boss4_tentacle_baseline(boss, slot, for_hit=True)
    length = float(_b4_slot_get(boss, slot, "len") or 0.0)
    tip_x, tip_y = _boss4_tentacle_point_at(boss, length, slot, for_hit=True)
    return tip_x, tip_y, max_len


def _boss4_tentacle_draw_points(boss, slot: str = "body") -> list[tuple[int, int]]:
    length = float(_b4_slot_get(boss, slot, "len") or 0.0)
    if length <= 1.0:
        rx, ry = _boss4_tentacle_root(boss, slot)
        return [(rx, ry)]
    segments = 14
    points: list[tuple[int, int]] = []
    for i in range(segments + 1):
        along = length * (i / segments)
        points.append(_boss4_tentacle_point_at(boss, along, slot))
    return points


def _draw_b4_tentacle_slot(boss, screen: pygame.Surface, slot: str) -> None:
    if _b4_slot_get(boss, slot, "state") not in ("extend", "retract"):
        return
    if float(_b4_slot_get(boss, slot, "len") or 0.0) <= 2.0:
        return
    pts = _boss4_tentacle_draw_points(boss, slot)
    if len(pts) < 2:
        return
    pal = B4_TENTACLE_PALETTE
    pygame.draw.lines(screen, pal["outline"], False, pts, 22)
    pygame.draw.lines(screen, pal["shadow"], False, pts, 14)
    pygame.draw.lines(screen, pal["body"], False, pts, 9)
    pygame.draw.lines(screen, pal["core"], False, pts, 4)
    tip_x, tip_y, _ = _boss4_tentacle_tip_pos(boss, slot)
    pygame.draw.circle(screen, pal["glow"], (tip_x, tip_y), 7)
    pygame.draw.circle(screen, pal["core"], (tip_x, tip_y), 3)


def draw_boss4_tentacle(boss, screen: pygame.Surface) -> None:
    """本体・上帯・下帯のベクター触手（本体は midboss4_f と併用）。"""
    if _boss4_shield_grace_active():
        return
    for slot in ("body", "top", "bottom"):
        _draw_b4_tentacle_slot(boss, screen, slot)


def _boss4_tentacle_hits_player(boss, slot: str = "body") -> bool:
    if g()["player_dead"] or g()["player"].invincible_timer != 0:
        return False
    tip_x, tip_y, _ = _boss4_tentacle_tip_pos(boss, slot)
    from combat import filled_circle_hits_player

    return filled_circle_hits_player(g()["player"], tip_x, tip_y, 24)


def _b4_init_strip_tentacles(boss) -> None:
    mid_x = int(g()["WIDTH"]) // 2
    mid_y = int(g()["HEIGHT"]) // 2
    for slot, timer_start in (("top", 0), ("bottom", 180)):
        if not hasattr(boss, _b4_slot_keys(slot)["state"]):
            _b4_slot_set(boss, slot, "state", "idle")
            _b4_slot_set(boss, slot, "timer", timer_start)
            _b4_slot_set(boss, slot, "len", 0.0)
            _b4_slot_set(boss, slot, "target_x", float(mid_x))
            _b4_slot_set(boss, slot, "target_y", float(mid_y))


def _b4_update_tentacle_slot(
    boss,
    slot: str,
    *,
    enabled: bool,
    idle_frames: int,
    play_warning: bool = False,
) -> None:
    if not enabled:
        _b4_slot_set(boss, slot, "state", "idle")
        _b4_slot_set(boss, slot, "len", 0.0)
        return

    extend_spd = (
        BOSS4_TENTACLE_EXTEND_SPD
        if slot == "body"
        else BOSS4_STRIP_TENTACLE_EXTEND_SPD
    )
    retract_spd = BOSS4_TENTACLE_RETRACT_SPD
    cap = _b4_tentacle_extend_cap(boss, slot)
    state = str(_b4_slot_get(boss, slot, "state"))
    timer = int(_b4_slot_get(boss, slot, "timer") or 0) + 1
    _b4_slot_set(boss, slot, "timer", timer)
    length = float(_b4_slot_get(boss, slot, "len") or 0.0)

    if state == "idle":
        if timer >= idle_frames:
            pl = g()["player"]
            if slot == "body":
                _b4_slot_set(boss, slot, "target_y", float(pl.rect.centery))
                if play_warning:
                    try:
                        g()["laser_warning_sound"].play()
                    except Exception:
                        pass
            else:
                _b4_slot_set(boss, slot, "target_x", float(pl.rect.centerx))
                _b4_slot_set(boss, slot, "target_y", float(pl.rect.centery))
            _boss4_tentacle_alert_and_bubble(boss, slot)
            _b4_slot_set(boss, slot, "state", "extend")
            _b4_slot_set(boss, slot, "timer", 0)
            _b4_slot_set(boss, slot, "len", 0.0)
    elif state == "extend":
        length = min(cap, length + extend_spd)
        _b4_slot_set(boss, slot, "len", length)
        if _boss4_tentacle_hits_player(boss, slot):
            apply_player_hit(hit_kind="boss")
        if length >= cap:
            _b4_slot_set(boss, slot, "state", "retract")
            _b4_slot_set(boss, slot, "timer", 0)
    elif state == "retract":
        _boss4_tentacle_alert_and_bubble(boss, slot)
        length = max(0.0, length - retract_spd)
        _b4_slot_set(boss, slot, "len", length)
        if length > 10 and _boss4_tentacle_hits_player(boss, slot):
            apply_player_hit(hit_kind="boss")
        if length <= 0.0:
            _b4_slot_set(boss, slot, "state", "idle")
            _b4_slot_set(boss, slot, "timer", 0)
            _b4_slot_set(boss, slot, "len", 0.0)
            setattr(boss, _b4_tentacle_bubble_flag(slot), False)


def draw_boss4(boss):
    screen = g()["screen"]
    sync_boss4_body_layout(boss)
    screen.blit(boss.image, boss.rect)
    draw_boss4_screen_overlays(screen, boss)
    draw_boss4_tentacle(boss, screen)


def update_boss4_special(boss, is_low_hp, is_critical_hp):
    if not hasattr(boss, "arm_state"):
        boss.arm_state = "idle"
        boss.arm_timer = 0
        boss.tentacle_len = 0.0
        boss.tentacle_target_y = g()["HEIGHT"] // 2
        boss._b4_body_bubble_once = False
    _b4_init_strip_tentacles(boss)
    sync_boss4_body_layout(boss)
    update_boss4_strip_sniper(boss)

    if is_low_hp and not getattr(boss, "_b4_body_tentacle_enabled", False):
        _b4_slot_set(boss, "body", "timer", 0)
        _b4_slot_set(boss, "body", "state", "idle")
        _b4_slot_set(boss, "body", "len", 0.0)
    boss._b4_body_tentacle_enabled = bool(is_low_hp)

    _b4_update_tentacle_slot(
        boss,
        "body",
        enabled=is_low_hp,
        idle_frames=BOSS4_BODY_TENTACLE_IDLE_FRAMES,
        play_warning=True,
    )
    _b4_update_tentacle_slot(
        boss,
        "top",
        enabled=is_critical_hp,
        idle_frames=BOSS4_STRIP_TENTACLE_IDLE_FRAMES,
    )
    _b4_update_tentacle_slot(
        boss,
        "bottom",
        enabled=is_critical_hp,
        idle_frames=BOSS4_STRIP_TENTACLE_IDLE_FRAMES,
    )

    if not hasattr(boss, "b4_atk_timer"):
        boss.b4_atk_timer = 0
    if not hasattr(boss, "b4_spiral"):
        boss.b4_spiral = 0.0
    boss.b4_atk_timer += 1
    at = boss.b4_atk_timer
    fire_x = boss.rect.left + int(boss.rect.width * BOSS4_FIRE_X_RATIO)
    fire_y = boss.rect.centery

    # 触手攻撃中（本体・上帯・下帯）でも弾幕は継続
    if not is_low_hp:
        boss.b4_spiral += 0.06
        if _b4_fire_due(at, _b4_bullet_interval(18)):
            for i in range(_b4_bullet_count(2)):
                rad = boss.b4_spiral + math.radians(i * 180)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad) * 4.5, vy=math.sin(rad) * 4.5,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(60)):
            dx = g()["player"].rect.centerx - fire_x
            dy = g()["player"].rect.centery - fire_y
            for _ang in boss_easy_pick_sequence((-20, 0, 20)):
                rad_d = math.atan2(dy, dx) + math.radians(_ang)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad_d) * 5.5, vy=math.sin(rad_d) * 5.5,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(110)):
            for y_pos in boss_easy_pick_sequence((160, 360, 560)):
                spawn_enemy_bullet(
                    x=fire_x, y=y_pos,
                    vx=-5.0, vy=0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
    elif is_low_hp and not is_critical_hp:
        boss.b4_spiral += 0.10
        if _b4_fire_due(at, _b4_bullet_interval(15)):
            for i in range(_b4_bullet_count(2)):
                rad = boss.b4_spiral + math.radians(i * 180)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad) * 5.5, vy=math.sin(rad) * 5.5,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(68)):
            dx = g()["player"].rect.centerx - fire_x
            dy = g()["player"].rect.centery - fire_y
            base = math.atan2(dy, dx)
            for _ang in boss_easy_pick_sequence((-30, 0, 30)):
                rad = base + math.radians(_ang)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad) * 6.0, vy=math.sin(rad) * 6.0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(105)):
            for off in boss_easy_pick_sequence((-80, 0, 80)):
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y + off,
                    vx=-5.0, vy=0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
    else:
        boss.b4_spiral += 0.15
        if _b4_fire_due(at, _b4_bullet_interval(11)):
            for i in range(_b4_bullet_count(2)):
                rad = boss.b4_spiral + math.radians(i * 180)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad) * 6.0, vy=math.sin(rad) * 6.0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(52)):
            dx = g()["player"].rect.centerx - fire_x
            dy = g()["player"].rect.centery - fire_y
            base = math.atan2(dy, dx)
            for _ang in boss_easy_pick_sequence((-22, 0, 22)):
                rad = base + math.radians(_ang)
                spawn_enemy_bullet(
                    x=fire_x, y=fire_y,
                    vx=math.cos(rad) * 7.0, vy=math.sin(rad) * 7.0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                )
        if _b4_fire_due(at, _b4_bullet_interval(95)):
            for y_pos in boss_easy_pick_sequence((160, 360, 560)):
                spawn_enemy_bullet(
                    x=fire_x, y=y_pos,
                    vx=-2.5, vy=0,
                    is_boss_bullet=True, image_type="boss4_bullet",
                    speed_type="accel", action_timer=20,
                    cruise_vx=-2.5, cruise_vy=0.0,
                )


