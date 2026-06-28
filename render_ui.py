# render_ui.py — HUD・テキスト・背景スクロール描画

import math

import pygame

from assets_loader import (
    BLACK,
    CYAN,
    DARK_ORANGE,
    LIGHT_BLUE,
    ORANGE,
)
from ui_bars import (
    draw_glossy_bar_horizontal,
    draw_glossy_panel,
    draw_glossy_pip,
    draw_glossy_slot,
    gentle_radius,
)

_font = None
_font2 = None
_font_hud_sm = None
_hud_font = None
_hp_bar_font = None
_big_font = None
_life_icon_img = None
HUD_LIFE_ICON_SIZE = (25, 25)


def configure(font, font2, font_hud_sm, hud_font, hp_bar_font, big_font, life_icon_img):
    global _font, _font2, _font_hud_sm, _hud_font, _hp_bar_font, _big_font, _life_icon_img
    _font = font
    _font2 = font2
    _font_hud_sm = font_hud_sm
    _hud_font = hud_font
    _hp_bar_font = hp_bar_font
    _big_font = big_font
    _life_icon_img = life_icon_img


def draw_text_with_shadow(surf, text, text_font, color, x, y, is_center=False):
    text_surface = text_font.render(text, True, color)
    shadow_surface = text_font.render(text, True, BLACK)

    rect = text_surface.get_rect()
    if is_center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx != 0 or dy != 0:
                surf.blit(shadow_surface, (rect.x + dx, rect.y + dy))

    surf.blit(text_surface, rect)


def key_label(key_code):
    try:
        name = pygame.key.name(key_code)
    except Exception:
        name = str(key_code)
    return name.upper()


def pad_label(button_id):
    return f"Button {button_id}"


def draw_scroll(screen, image, x, speed, origin=(0, 0)):
    ox, oy = origin
    width = image.get_width()
    screen.blit(image, (ox + x, oy))
    screen.blit(image, (ox + x + width, oy))
    x -= speed
    if x <= -width:
        x = 0
    return x


def _scale_surface_to_height(src: pygame.Surface, max_h: int) -> pygame.Surface:
    if src.get_height() <= max_h:
        return src
    scale = max_h / src.get_height()
    w = max(1, int(src.get_width() * scale))
    return pygame.transform.smoothscale(src, (w, max_h))


def _fit_surface_to_height(src: pygame.Surface, target_h: int) -> pygame.Surface:
    """高さを target_h に合わせる（拡大・縮小どちらも）。"""
    if target_h <= 0:
        return src
    if src.get_height() == target_h:
        return src
    scale = target_h / src.get_height()
    w = max(1, int(src.get_width() * scale))
    return pygame.transform.smoothscale(src, (w, target_h))


def _blit_vcenter(
    surf: pygame.Surface, image: pygame.Surface, x: int, band_y: int, band_h: int
) -> int:
    y = band_y + (band_h - image.get_height()) // 2
    surf.blit(image, (x, y))
    return x + image.get_width()


def _draw_hud_row_panel(surf, x, y, w, h, border_rgb, fill_alpha=72):
    draw_glossy_panel(surf, x, y, w, h, border_rgb, fill_alpha=fill_alpha)


def chain_hud_panel_rect(boss_row: bool = False):
    """上部HUD・連鎖表示パネルの矩形（draw_top_status_bar と一致）。"""
    from game_layout import hud_content_rect

    content = hud_content_rect()
    chain_w = 132
    boss_w = 148 if boss_row else 0
    panel_y = content.y + 2
    panel_h = content.height - 4
    chain_x = content.right - chain_w - (boss_w + 8 if boss_row else 0)
    return pygame.Rect(chain_x, panel_y, chain_w, panel_h)


def _draw_chain_row(
    surf, chain, timer, chain_mult, font_sm, x, y, w, h
) -> None:
    from score_system import CHAIN_MAX_FRAMES

    _draw_hud_row_panel(surf, x, y, w, h, (55, 75, 110))
    cy = y + (h - font_sm.get_height()) // 2 - 2
    surf.blit(font_sm.render("連鎖", True, (120, 180, 255)), (x + 5, cy))
    surf.blit(
        font_sm.render(str(chain), True, (255, 255, 255) if chain else (90, 90, 95)),
        (x + 44, cy),
    )
    mc = (255, 210, 60) if chain_mult > 1 else (150, 150, 160)
    surf.blit(font_sm.render(f"x{chain_mult}", True, mc), (x + 66, cy))
    bar_x, bar_y, bar_w, bar_h = x + 5, y + h - 7, w - 10, 5
    ratio = (
        max(0.0, min(1.0, timer / CHAIN_MAX_FRAMES))
        if chain > 0 and CHAIN_MAX_FRAMES > 0
        else 0.0
    )
    fill_col = (255, 200, 40) if ratio > 0.35 else (255, 90, 60)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (30, 35, 50), (70, 80, 100)
    )


def _draw_boss_pts_row(
    surf, bank, cap, font_sm, x, y, w, h
) -> None:
    _draw_hud_row_panel(surf, x, y, w, h, (140, 90, 50))
    cy = y + (h - font_sm.get_height()) // 2 - 2
    amt = font_sm.render(f"{bank:,}", True, (255, 245, 200))
    surf.blit(amt, (x + 6, cy))
    cap_s = font_sm.render(f"/{cap // 1000}k" if cap >= 10000 else f"/{cap:,}", True, (140, 130, 120))
    surf.blit(cap_s, (x + 6 + amt.get_width() + 4, cy))
    bar_x, bar_y, bar_w, bar_h = x + 5, y + h - 7, w - 10, 5
    ratio = max(0.0, min(1.0, bank / cap))
    fill_col = (255, 160, 50) if ratio < 0.95 else (255, 220, 100)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (40, 30, 25), (100, 70, 40)
    )


def draw_top_status_bar(
    surf,
    score,
    score_multiplier,
    lives,
    weapon_level,
    diff,
    laser_gauge: float = 0.0,
    speed_gauge: float = 0.0,
    chain=0,
    chain_timer=0,
    chain_mult=1,
    boss_bank: int | None = None,
    boss_cap: int = 0,
) -> None:
    """上部 HUD: 左=難易度・残機・武器 / 中央=SCORE / 右=連鎖・ボスバンク。"""
    from game_layout import HUD_HEIGHT, hud_content_rect

    content = hud_content_rect()
    score_band_h = HUD_HEIGHT - 2
    score_lbl_h = HUD_HEIGHT - 8
    gap_item = 22
    row_h = content.height
    row_y = content.y
    cy = row_y + row_h // 2
    sw = content.right
    lbl_font = _font2 if _font2 is not None else _font_hud_sm
    boss_row = boss_cap > 0 and boss_bank is not None

    pip_h = max(10, row_h - 20)
    pip_y = cy - pip_h // 2
    pip_gap = 4
    pip_w_w = 22
    lives_icon_slots = 5
    lives_overflow_reserved_w = lbl_font.render("+99", True, (190, 190, 190)).get_width()
    icon_w_target, icon_h_target = HUD_LIFE_ICON_SIZE
    lives_icon_step = icon_w_target + 4
    life_icon = pygame.transform.smoothscale(
        _life_icon_img, HUD_LIFE_ICON_SIZE
    )
    icon_h = icon_h_target
    def _lbl(text: str, px: int, color=(120, 180, 255)) -> int:
        s = lbl_font.render(text, True, color)
        surf.blit(s, (px, cy - s.get_height() // 2))
        return s.get_width()

    # --- 左クラスタ（各項目に間隔）---
    x = content.left
    diff_img = _scale_surface_to_height(
        lbl_font.render(diff.name, True, diff.label_color),
        min(score_lbl_h + 4, content.height - 4),
    )
    x = _blit_vcenter(surf, diff_img, x, content.y, content.height) + gap_item

    lw = _lbl("残機", x)
    icon_x0 = x + lw + 8
    icon_y = cy - icon_h // 2
    shown = min(lives, lives_icon_slots)
    for i in range(shown):
        surf.blit(life_icon, (icon_x0 + i * lives_icon_step, icon_y))
    overflow_x = icon_x0 + lives_icon_slots * lives_icon_step
    if lives > lives_icon_slots:
        over = lbl_font.render(f"+{lives - lives_icon_slots}", True, (190, 190, 190))
        surf.blit(over, (overflow_x, cy - over.get_height() // 2))
    # SCORE 位置が残機数でずれないよう、5枠＋オーバー表示分は常に確保
    x = overflow_x + lives_overflow_reserved_w + gap_item

    lw = _lbl("武器", x)
    bx0 = x + lw + 8
    for i in range(5):
        bx = bx0 + i * (pip_w_w + pip_gap)
        draw_glossy_pip(
            surf, bx, pip_y, pip_w_w, pip_h, active=(i < weapon_level)
        )
    left_end = bx0 + 5 * (pip_w_w + pip_gap)

    # --- ゲージ（レーザー／スピード）横並び・HUD 1行に収める ---
    try:
        from settings import LASER_GAUGE_MAX, SPEED_GAUGE_MAX

        gauge_font = _font_hud_sm if _font_hud_sm is not None else lbl_font
        gauge_w = 92
        gauge_h = max(5, min(8, row_h - 10))
        gx = left_end + 6
        gy = cy - gauge_h // 2
        lr = max(0.0, min(1.0, float(laser_gauge) / max(1.0, float(LASER_GAUGE_MAX))))
        sr = max(0.0, min(1.0, float(speed_gauge) / max(1.0, float(SPEED_GAUGE_MAX))))
        lab_col = (170, 210, 240)
        ltxt = gauge_font.render("LASER", True, lab_col)
        stxt = gauge_font.render("SPEED", True, lab_col)
        lbl_gap = 5
        pair_gap = 14

        lx = gx
        surf.blit(ltxt, (lx, cy - ltxt.get_height() // 2))
        bx = lx + ltxt.get_width() + lbl_gap
        draw_glossy_bar_horizontal(
            surf, bx, gy, gauge_w, gauge_h, lr,
            (110, 235, 255), (45, 75, 95), (90, 160, 200),
        )

        sx = bx + gauge_w + pair_gap
        surf.blit(stxt, (sx, cy - stxt.get_height() // 2))
        bx2 = sx + stxt.get_width() + lbl_gap
        draw_glossy_bar_horizontal(
            surf, bx2, gy, gauge_w, gauge_h, sr,
            (255, 200, 100), (70, 50, 35), (120, 90, 50),
        )
        left_end = bx2 + gauge_w
    except Exception:
        pass

    # --- 中央 SCORE（HUD帯の高さいっぱい）---
    sc_lbl = _fit_surface_to_height(
        lbl_font.render("SCORE", True, (120, 180, 255)), score_lbl_h
    )
    num_img = _fit_surface_to_height(
        _hud_font.render(f"{int(score)}", True, (255, 255, 255)), score_band_h
    )
    mult_surf = None
    if score_multiplier > 1:
        mult_surf = _fit_surface_to_height(
            lbl_font.render(f"x{score_multiplier}", True, (255, 210, 0)),
            score_band_h,
        )
    # 桁が増えても右へ伸びる（左端は武器列の終わりで固定）
    score_x = left_end + 20
    hud_cy = HUD_HEIGHT // 2
    surf.blit(sc_lbl, (score_x, hud_cy - sc_lbl.get_height() // 2))
    nx = score_x + sc_lbl.get_width() + 4
    surf.blit(num_img, (nx, hud_cy - num_img.get_height() // 2))
    if mult_surf is not None:
        surf.blit(
            mult_surf,
            (nx + num_img.get_width() + 3, hud_cy - mult_surf.get_height() // 2),
        )

    # --- 右: 連鎖・ボス（テキストラベルなし・数値のみ）---
    chain_w = 132
    boss_w = 148 if boss_row else 0
    panel_y = content.y + 2
    panel_h = content.height - 4
    chain_x = content.right - chain_w - (boss_w + 8 if boss_row else 0)
    _draw_chain_row(surf, chain, chain_timer, chain_mult, lbl_font, chain_x, panel_y, chain_w, panel_h)
    if boss_row:
        _draw_boss_pts_row(
            surf, boss_bank, boss_cap, lbl_font,
            content.right - boss_w, panel_y, boss_w, panel_h,
        )


def draw_gravity_indicator(
    surf: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    fill_ratio: float,
    mode: str,
) -> None:
    """重力攻撃の残り／警戒をボスHP下のバーで表示（テキストなし）。"""
    fill_ratio = max(0.0, min(1.0, fill_ratio))
    if mode == "warn":
        fill_col = (170, 70, 240)
    elif fill_ratio > 0.35:
        fill_col = (190, 90, 255)
    else:
        fill_col = (255, 70, 140)
    draw_glossy_bar_horizontal(
        surf,
        x,
        y,
        width,
        height,
        fill_ratio,
        fill_col,
        (36, 22, 52),
        (110, 70, 150),
    )


def _boss_hp_colors(ratio: float, has_shield: bool) -> tuple:
    """(スロット塗り, HPラベル色, MAXラベル色)"""
    if has_shield:
        return (70, 195, 255), (140, 235, 255), (100, 210, 245)
    if ratio <= 0.25:
        return (235, 45, 45), (255, 90, 90), (255, 140, 140)
    if ratio <= 0.50:
        return (255, 150, 35), (255, 200, 80), DARK_ORANGE
    return ORANGE, ORANGE, DARK_ORANGE


def _draw_boss_shield_hp_frame(
    surf: pygame.Surface, x: int, y: int, width: int, height: int
) -> None:
    """シールド中: 水色の外枠＋角飾り＋ゆるいパルス（画像オーバーレイなし）。"""
    rect = pygame.Rect(x, y, width, height)
    rad = gentle_radius(width, height)
    t = pygame.time.get_ticks() * 0.0045
    pulse = 0.62 + 0.38 * (0.5 + 0.5 * math.sin(t))

    pad = 4
    glow = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    glow_r = rad + 2
    pygame.draw.rect(
        glow,
        (30, 160, 240, int(42 * pulse)),
        glow.get_rect(),
        border_radius=glow_r,
    )
    surf.blit(glow, (x - pad, y - pad))

    pygame.draw.rect(surf, (55, 190, 250), rect, 3, border_radius=rad)
    pygame.draw.rect(
        surf, (120, 235, 255), rect.inflate(-4, -4), 1, border_radius=max(2, rad - 1)
    )

    arm = max(8, min(18, width // 14))
    thick = max(2, height // 12)
    accent = (190, 245, 255)
    pygame.draw.rect(surf, accent, (x, y, arm, thick))
    pygame.draw.rect(surf, accent, (x, y, thick, arm))
    pygame.draw.rect(surf, accent, (x + width - arm, y, arm, thick))
    pygame.draw.rect(surf, accent, (x + width - thick, y, thick, arm))
    pygame.draw.rect(surf, accent, (x, y + height - thick, arm, thick))
    pygame.draw.rect(surf, accent, (x, y + height - arm, thick, arm))
    pygame.draw.rect(surf, accent, (x + width - arm, y + height - thick, arm, thick))
    pygame.draw.rect(surf, accent, (x + width - thick, y + height - arm, thick, arm))

    scan = pygame.Surface((width, height), pygame.SRCALPHA)
    step = max(14, width // 22)
    for i in range(0, width, step):
        pygame.draw.line(
            scan,
            (140, 230, 255, int(22 * pulse)),
            (i, 2),
            (i, height - 3),
            1,
        )
    surf.blit(scan, rect.topleft)


def draw_custom_hp_bar(
    surf,
    x,
    y,
    width,
    height,
    current_hp,
    max_hp,
    has_shield=False,
):
    ratio = max(0.0, min(1.0, current_hp / max(max_hp, 1)))
    fill_color, _, _ = _boss_hp_colors(ratio, has_shield)
    if has_shield:
        border = (45, 95, 130)
        panel_fill = 88
    else:
        border = (70, 78, 98)
        panel_fill = 90

    draw_glossy_panel(surf, x, y, width, height, border, fill_alpha=panel_fill)

    slot_w = (width - 12) // 10
    slot_h = height - 10
    slot_y = y + 5
    filled_slots = int(ratio * 10 + 0.999)

    for i in range(10):
        sx = x + 10 + i * slot_w
        draw_glossy_slot(
            surf,
            sx,
            slot_y,
            max(2, slot_w - 2),
            slot_h,
            fill_color,
            filled=(i < filled_slots),
        )

    if has_shield:
        _draw_boss_shield_hp_frame(surf, x, y, width, height)
