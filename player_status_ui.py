# player_status_ui.py — 自機付近のゲージ／シールド／EMS（テキストなし）
#
# ブラケット配置:
#   上: レーザー（Lv5） / 自機直上: シールドバー / 下: スピード / 右: EMS
# バリア: 自機シルエット＋オーラ（描画のみ）

from __future__ import annotations

import pygame

from settings import (
    BRACKET_LASER_FILL,
    BRACKET_LASER_TRACK,
    BRACKET_SHIELD_TRACK,
    BRACKET_SPEED_FILL,
    BRACKET_SPEED_TRACK,
    LASER_GAUGE_MAX,
    PLAYER_COCKPIT_CENTER_U,
    PLAYER_COCKPIT_CENTER_V,
    PLAYER_COCKPIT_RADIUS_RATIO,
    PLAYER_MASK_ALPHA_THRESHOLD,
    PLAYER_MAX_WEAPON_LEVEL,
    PLAYER_SHIELD_AURA_GLOW,
    PLAYER_SHIELD_OUTLINE_PX,
    SPEED_GAUGE_MAX,
)
from ui_bars import draw_glossy_bar_horizontal

BRACKET_BAR_H = 7
BRACKET_BAR_W_RATIO = 0.58
BRACKET_TOP_GAP = 6
BRACKET_BOTTOM_GAP = 5
BRACKET_ARC_EXTRA = 12
BRACKET_ARC_PUSH_LEFT = 10
BRACKET_ARC_THICK = 6
_EMS_ORB_R = 4
_EMS_ORB_GAP = 2
_EMS_SIDE_GAP = 3

_ring_mask_cache: dict[tuple[int, int], tuple[pygame.mask.Mask, int]] = {}
_cockpit_mask_cache: dict[int, tuple[pygame.mask.Mask, pygame.Rect]] = {}
_aura_surf_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}


def shield_fill_color(ratio: float) -> tuple[int, int, int]:
    """シールド残量で色変化。"""
    ratio = max(0.0, min(1.0, ratio))
    if ratio <= 0.25:
        return (235, 55, 45)
    if ratio <= 0.50:
        return (255, 150, 45)
    if ratio <= 0.75:
        return (255, 220, 70)
    return (120, 245, 255)


def _body_mask_from_image(image: pygame.Surface) -> pygame.mask.Mask:
    return pygame.mask.from_surface(image, threshold=PLAYER_MASK_ALPHA_THRESHOLD)


def _mask_on_canvas(
    body: pygame.mask.Mask, canvas_pad: int, expand_r: int
) -> pygame.mask.Mask:
    mw, mh = body.get_size()
    cw, ch = mw + canvas_pad * 2, mh + canvas_pad * 2
    if expand_r <= 0:
        base = pygame.Mask((cw, ch))
        base.draw(body, (canvas_pad, canvas_pad))
        return base
    out = pygame.Mask((cw, ch))
    for dx in range(-expand_r, expand_r + 1):
        for dy in range(-expand_r, expand_r + 1):
            if dx * dx + dy * dy <= expand_r * expand_r:
                out.draw(body, (canvas_pad + dx, canvas_pad + dy))
    return out


def _shell_mask(
    body: pygame.mask.Mask, canvas_pad: int, inner_r: int, outer_r: int
) -> pygame.mask.Mask:
    if outer_r <= 0:
        return pygame.Mask((1, 1))
    outer = _mask_on_canvas(body, canvas_pad, outer_r)
    inner = (
        _mask_on_canvas(body, canvas_pad, inner_r)
        if inner_r > 0
        else _mask_on_canvas(body, canvas_pad, 0)
    )
    shell = outer.copy()
    shell.erase(inner, (0, 0))
    return shell


def _aura_draw_pad() -> int:
    glow = PLAYER_SHIELD_AURA_GLOW
    return max(PLAYER_SHIELD_OUTLINE_PX, *(r for r, _ in glow))


def player_shield_aura_rect(ship_rect: pygame.Rect) -> pygame.Rect:
    pad = _aura_draw_pad()
    return ship_rect.inflate(pad * 2, pad * 2)


def _ring_mask_for_image(image: pygame.Surface) -> tuple[pygame.mask.Mask, int]:
    key = (id(image), PLAYER_SHIELD_OUTLINE_PX)
    cached = _ring_mask_cache.get(key)
    if cached is not None:
        return cached
    body = _body_mask_from_image(image)
    pad = PLAYER_SHIELD_OUTLINE_PX
    ring = _shell_mask(body, pad, 0, pad)
    _ring_mask_cache[key] = (ring, pad)
    return ring, pad


def _aura_surface_for_image(
    image: pygame.Surface,
    color: tuple[int, int, int],
    *,
    outline_px: int | None = None,
    glow_layers: tuple[tuple[int, int], ...] | None = None,
) -> tuple[pygame.Surface, int]:
    outline = outline_px if outline_px is not None else PLAYER_SHIELD_OUTLINE_PX
    glow = glow_layers if glow_layers is not None else PLAYER_SHIELD_AURA_GLOW
    pad = max(outline, *(r for r, _ in glow)) if glow else outline
    key = (id(image), color[0], color[1], color[2], outline, glow)
    cached = _aura_surf_cache.get(key)
    if cached is not None:
        return cached, pad

    body = _body_mask_from_image(image)
    sw, sh = image.get_size()
    surf = pygame.Surface((sw + pad * 2, sh + pad * 2), pygame.SRCALPHA)

    for glow_r, alpha in glow:
        inner = max(0, glow_r - 2)
        band = _shell_mask(body, pad, inner, glow_r)
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        band.to_surface(
            layer,
            setcolor=(*color, alpha),
            unsetcolor=(0, 0, 0, 0),
        )
        surf.blit(layer, (0, 0))

    core = _shell_mask(body, pad, 0, outline)
    core_layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    core.to_surface(
        core_layer,
        setcolor=(*color, 235),
        unsetcolor=(0, 0, 0, 0),
    )
    surf.blit(core_layer, (0, 0))

    _aura_surf_cache[key] = surf
    return surf, pad


def draw_sprite_aura(
    screen: pygame.Surface,
    image: pygame.Surface,
    dest_rect: pygame.Rect,
    color: tuple[int, int, int],
    *,
    intensity: float = 1.0,
    outline_px: int | None = None,
    glow_layers: tuple[tuple[int, int], ...] | None = None,
) -> None:
    intensity = max(0.0, min(1.0, intensity))
    if intensity <= 0.001:
        return
    aura, pad = _aura_surface_for_image(
        image, color, outline_px=outline_px, glow_layers=glow_layers
    )
    if intensity < 0.999:
        aura = aura.copy()
        aura.set_alpha(int(255 * intensity))
    screen.blit(aura, (dest_rect.x - pad, dest_rect.y - pad))


def draw_player_shield_aura(
    screen: pygame.Surface, player, ratio: float
) -> None:
    ratio = max(0.0, min(1.0, ratio))
    color = shield_fill_color(ratio)
    aura, pad = _aura_surface_for_image(player.image, color)
    dest = (player.rect.x - pad, player.rect.y - pad)
    screen.blit(aura, dest)


def get_player_cockpit_hit(
    player,
) -> tuple[pygame.mask.Mask, pygame.Rect]:
    cache_key = id(player.image)
    cached = _cockpit_mask_cache.get(cache_key)
    if cached is not None:
        pr = player.rect
        mask, base = cached
        dest = base.copy()
        dest.center = (
            pr.left + int(pr.width * PLAYER_COCKPIT_CENTER_U),
            pr.top + int(pr.height * PLAYER_COCKPIT_CENTER_V),
        )
        return mask, dest

    body = _body_mask_from_image(player.image)
    pr = player.rect
    cx_rel = int(pr.width * PLAYER_COCKPIT_CENTER_U)
    cy_rel = int(pr.height * PLAYER_COCKPIT_CENTER_V)
    rad = max(4, int(min(pr.width, pr.height) * PLAYER_COCKPIT_RADIUS_RATIO))
    size = rad * 2 + 1
    cockpit = pygame.Mask((size, size), fill=False)
    center = rad
    for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
            if dx * dx + dy * dy > rad * rad:
                continue
            mx = cx_rel + dx
            my = cy_rel + dy
            if (
                0 <= mx < pr.width
                and 0 <= my < pr.height
                and body.get_at((mx, my))
            ):
                cockpit.set_at((center + dx, center + dy))
    if cockpit.count() == 0:
        fallback = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            fallback, (255, 255, 255, 255), (center, center), max(3, rad // 2)
        )
        cockpit = pygame.mask.from_surface(fallback)
    base_dest = pygame.Rect(0, 0, size, size)
    _cockpit_mask_cache[cache_key] = (cockpit, base_dest)
    dest = base_dest.copy()
    dest.center = (pr.left + cx_rel, pr.top + cy_rel)
    return cockpit, dest


def get_player_shield_aura_hit(
    player,
) -> tuple[pygame.mask.Mask, pygame.Rect] | None:
    if float(getattr(player, "shield_meter", 0.0)) <= 0.001:
        return None
    ring, pad = _ring_mask_for_image(player.image)
    dest = pygame.Rect(
        player.rect.x - pad,
        player.rect.y - pad,
        ring.get_size()[0],
        ring.get_size()[1],
    )
    return ring, dest


def _bar_width(ship_rect: pygame.Rect) -> int:
    return max(28, int(ship_rect.width * BRACKET_BAR_W_RATIO))


def _shield_bar_rect(ship_rect: pygame.Rect) -> pygame.Rect:
    bar_w = _bar_width(ship_rect)
    x = ship_rect.centerx - bar_w // 2
    y = ship_rect.top - BRACKET_BAR_H - BRACKET_TOP_GAP
    return pygame.Rect(x, y, bar_w, BRACKET_BAR_H)


def _laser_bar_rect(ship_rect: pygame.Rect) -> pygame.Rect:
    bar_w = _bar_width(ship_rect)
    x = ship_rect.centerx - bar_w // 2
    y = ship_rect.bottom + BRACKET_BOTTOM_GAP
    return pygame.Rect(x, y, bar_w, BRACKET_BAR_H)


def _draw_bracket_laser_bar(screen: pygame.Surface, ship_rect: pygame.Rect, player) -> None:
    wl = int(getattr(player, "weapon_level", 1))
    if wl < PLAYER_MAX_WEAPON_LEVEL:
        return
    lg = float(getattr(player, "laser_gauge", 0.0))
    ratio = max(0.0, min(1.0, lg / max(1.0, float(LASER_GAUGE_MAX))))
    bar = _laser_bar_rect(ship_rect)
    laser_sel = getattr(player, "fire_mode", "normal") == "laser"
    # 下段（レーザー）は蛍光緑
    fill = (90, 255, 95) if laser_sel else (70, 200, 80)
    track = (34, 78, 38)
    border = (180, 255, 170) if laser_sel else (110, 170, 100)
    draw_glossy_bar_horizontal(
        screen,
        bar.x,
        bar.y,
        bar.width,
        bar.height,
        ratio,
        fill,
        track,
        border,
    )


def _draw_bracket_shield_bar(screen: pygame.Surface, ship_rect: pygame.Rect, player) -> None:
    meter = float(getattr(player, "shield_meter", 0.0))
    ratio = max(0.0, min(1.0, meter))
    bar = _shield_bar_rect(ship_rect)
    fill = shield_fill_color(ratio)
    track = BRACKET_SHIELD_TRACK
    border = (255, 230, 130) if ratio > 0.25 else (175, 150, 80)
    draw_glossy_bar_horizontal(
        screen,
        bar.x,
        bar.y,
        bar.width,
        bar.height,
        ratio,
        fill,
        track,
        border,
    )


def _draw_bracket_speed_vertical(screen: pygame.Surface, ship_rect: pygame.Rect, ratio: float) -> None:
    ratio = max(0.0, min(1.0, ratio))
    h = max(30, int(ship_rect.height * 0.86))
    w = 8
    x = ship_rect.left - BRACKET_ARC_PUSH_LEFT - w - 6
    y = ship_rect.centery - h // 2
    draw_glossy_bar_horizontal(
        screen,
        x,
        y,
        w,
        h,
        1.0,
        BRACKET_SPEED_TRACK,
        BRACKET_SPEED_TRACK,
        (80, 140, 170),
    )
    fill_h = max(1, int(h * ratio))
    fy = y + h - fill_h
    draw_glossy_bar_horizontal(
        screen,
        x + 1,
        fy,
        max(1, w - 2),
        fill_h,
        1.0,
        (80, 230, 255),
        (80, 230, 255),
        (170, 255, 255),
    )


def _ems_orb_colors(ems_count: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    # EMSは水色系
    return (80, 220, 255), (190, 250, 255)


def _draw_bracket_ems_dots(
    screen: pygame.Surface,
    speed_bar: pygame.Rect,
    ems_count: int,
    ems_max: int,
) -> None:
    """スピードバー左横に EMS ドット（隙間狭め）。"""
    n = max(1, ems_max)
    fill_col, border_col = _ems_orb_colors(ems_count)
    total_w = n * (_EMS_ORB_R * 2) + (n - 1) * _EMS_ORB_GAP
    x0 = speed_bar.left - _EMS_SIDE_GAP - total_w + _EMS_ORB_R
    cy = speed_bar.centery
    for i in range(n):
        ox = x0 + i * (_EMS_ORB_R * 2 + _EMS_ORB_GAP)
        if i < ems_count:
            pygame.draw.circle(screen, fill_col, (ox, cy), _EMS_ORB_R)
            pygame.draw.circle(screen, border_col, (ox, cy), _EMS_ORB_R, 1)
            pygame.draw.circle(
                screen, (235, 255, 255), (ox - 1, cy - 1), max(1, _EMS_ORB_R // 2)
            )
        else:
            pygame.draw.circle(screen, (55, 68, 88), (ox, cy), _EMS_ORB_R, 1)


def draw_player_bracket_back(screen: pygame.Surface, player) -> None:
    """機体左: 縦バーのスピードゲージ（自機より下に描画）。"""
    sg = float(getattr(player, "speed_gauge", 0.0))
    ratio = max(0.0, min(1.0, sg / max(1.0, float(SPEED_GAUGE_MAX))))
    _draw_bracket_speed_vertical(screen, player.rect, ratio)


def draw_player_bracket_front(
    screen: pygame.Surface, player, ems_count: int, ems_max: int
) -> None:
    """上:シールド / 下:レーザー / EMS（自機より上に描画）。"""
    r = player.rect
    laser_bar = _laser_bar_rect(r)
    _draw_bracket_shield_bar(screen, r, player)
    _draw_bracket_laser_bar(screen, r, player)
    _draw_bracket_ems_dots(screen, laser_bar, ems_count, ems_max)


def draw_player_bracket_gauges(
    screen: pygame.Surface, player, ems_count: int, ems_max: int
) -> None:
    draw_player_bracket_back(screen, player)
    draw_player_bracket_front(screen, player, ems_count, ems_max)


def draw_player_near_status(screen, player, ems_count: int, ems_max: int) -> None:
    draw_player_bracket_gauges(screen, player, ems_count, ems_max)
