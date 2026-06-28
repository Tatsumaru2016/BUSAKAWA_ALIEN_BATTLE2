# game_layout.py — ウィンドウ全体とプレイ領域（HUD は描画のみ・枠画像なし）

from __future__ import annotations

import pygame

from ui_bars import draw_glossy_panel

# プレイフィールド
PLAY_WIDTH = 1280
PLAY_HEIGHT = 760
PLAY_SCREEN_SIZE = (PLAY_WIDTH, PLAY_HEIGHT)

SCREEN_WIDTH = 1300
HUD_HEIGHT = 48
HUD_PAD_X = 12
HUD_PAD_Y = 6

# ボス HP（play_screen 座標）
BOSS_HP_BAR_X = 440
BOSS_HP_BAR_Y = 20
BOSS_HP_BAR_W = 500
BOSS_HP_BAR_H = 36
BOSS_GRAVITY_GAP = 4
BOSS_GRAVITY_W = 300
BOSS_GRAVITY_H = 6

PLAY_TOP_MARGIN = 12

SCREEN_HEIGHT = HUD_HEIGHT + PLAY_HEIGHT
PLAY_ORIGIN_X = (SCREEN_WIDTH - PLAY_WIDTH) // 2
PLAY_ORIGIN_Y = HUD_HEIGHT
PLAY_SIDE_GUTTER = PLAY_ORIGIN_X

WIDTH = PLAY_WIDTH
HEIGHT = PLAY_HEIGHT

_PLAY_BORDER = (48, 62, 88)
_PLAY_FILL = (6, 8, 14)


def hud_content_rect() -> pygame.Rect:
    """上部ステータス（文字・バー）の配置領域。"""
    return pygame.Rect(
        HUD_PAD_X,
        HUD_PAD_Y,
        SCREEN_WIDTH - HUD_PAD_X * 2,
        HUD_HEIGHT - HUD_PAD_Y * 2,
    )


def boss_hp_bar_rect() -> pygame.Rect:
    return pygame.Rect(BOSS_HP_BAR_X, BOSS_HP_BAR_Y, BOSS_HP_BAR_W, BOSS_HP_BAR_H)


def boss_hp_gravity_rect() -> pygame.Rect:
    r = boss_hp_bar_rect()
    gx = r.x + (r.width - BOSS_GRAVITY_W) // 2
    return pygame.Rect(gx, r.bottom + BOSS_GRAVITY_GAP, BOSS_GRAVITY_W, BOSS_GRAVITY_H)


def install_layout(namespace: dict) -> None:
    namespace["PLAY_WIDTH"] = PLAY_WIDTH
    namespace["PLAY_HEIGHT"] = PLAY_HEIGHT
    namespace["PLAY_SCREEN_SIZE"] = PLAY_SCREEN_SIZE
    namespace["HUD_HEIGHT"] = HUD_HEIGHT
    namespace["HUD_PAD_X"] = HUD_PAD_X
    namespace["HUD_PAD_Y"] = HUD_PAD_Y
    namespace["BOSS_HP_BAR_X"] = BOSS_HP_BAR_X
    namespace["BOSS_HP_BAR_Y"] = BOSS_HP_BAR_Y
    namespace["BOSS_HP_BAR_W"] = BOSS_HP_BAR_W
    namespace["BOSS_HP_BAR_H"] = BOSS_HP_BAR_H
    namespace["SCREEN_WIDTH"] = SCREEN_WIDTH
    namespace["SCREEN_HEIGHT"] = SCREEN_HEIGHT
    namespace["PLAY_SIDE_GUTTER"] = PLAY_SIDE_GUTTER
    namespace["PLAY_ORIGIN_X"] = PLAY_ORIGIN_X
    namespace["PLAY_ORIGIN_Y"] = PLAY_ORIGIN_Y
    namespace["PLAY_TOP_MARGIN"] = PLAY_TOP_MARGIN
    namespace["WIDTH"] = PLAY_WIDTH
    namespace["HEIGHT"] = PLAY_HEIGHT


def draw_hud_bar(full_screen: pygame.Surface) -> None:
    """上部 HUD 帯（艶付きパネル）のみ。"""
    sw, _sh = full_screen.get_size()
    draw_glossy_panel(
        full_screen, 0, 0, sw, HUD_HEIGHT, (55, 75, 110), fill_alpha=100
    )


def draw_frame_chrome(full_screen: pygame.Surface) -> None:
    """上部 HUD 帯とプレイ領域の枠。"""
    draw_hud_bar(full_screen)

    pr = play_rect()
    pygame.draw.rect(full_screen, _PLAY_FILL, pr)
    pygame.draw.rect(full_screen, _PLAY_BORDER, pr, 2)


def play_rect() -> pygame.Rect:
    return pygame.Rect(PLAY_ORIGIN_X, PLAY_ORIGIN_Y, PLAY_WIDTH, PLAY_HEIGHT)


def prepare_play_screen_surface(
    img: pygame.Surface, size: tuple[int, int] = PLAY_SCREEN_SIZE
) -> pygame.Surface:
    """全面UI用: 1280×760 原寸ならそのまま、違うときだけスケール。"""
    img = img.convert_alpha()
    if img.get_size() != size:
        return pygame.transform.smoothscale(img, size)
    return img


def blit_play_screen_image(
    full_screen: pygame.Surface, img: pygame.Surface | None
) -> None:
    """1280×760 想定の画像をプレイ領域（左右10px・HUD下）に描画。"""
    if img is None:
        return
    dest = play_rect()
    surf = img
    if surf.get_size() != (dest.width, dest.height):
        surf = pygame.transform.smoothscale(surf, (dest.width, dest.height))
    full_screen.blit(surf, dest.topleft)


def blit_full_window_image(
    full_screen: pygame.Surface, img: pygame.Surface | None
) -> None:
    """1280×760 素材をウィンドウ全体 (SCREEN_WIDTH×SCREEN_HEIGHT) にフィット。"""
    if img is None:
        return
    sw, sh = full_screen.get_size()
    surf = img
    if surf.get_size() != (sw, sh):
        surf = pygame.transform.smoothscale(surf, (sw, sh))
    full_screen.blit(surf, (0, 0))


def activate_play_view(namespace: dict) -> None:
    full = namespace["screen"]
    namespace["full_screen"] = full
    namespace["screen"] = full.subsurface(play_rect())
    namespace["_play_surface_active"] = True


def deactivate_play_view(namespace: dict) -> None:
    if namespace.get("_play_surface_active") and "full_screen" in namespace:
        namespace["screen"] = namespace["full_screen"]
    namespace["_play_surface_active"] = False
