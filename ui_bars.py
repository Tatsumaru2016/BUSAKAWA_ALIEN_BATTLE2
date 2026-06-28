# ui_bars.py — ゲーム内バー／インジケーター（緩い角丸＋艶）

from __future__ import annotations

import math

import pygame


def gentle_radius(width: int, height: int) -> int:
    """控えめな角丸（細いバーでも少し丸める）。"""
    if height <= 3:
        return 2
    if height <= 6:
        return max(3, height // 2)
    return max(4, min(10, height // 2, width // 6))


def _brighten(rgb: tuple[int, int, int], amount: int = 60) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in rgb[:3])


def _darken(rgb: tuple[int, int, int], amount: int = 40) -> tuple[int, int, int]:
    return tuple(max(0, c - amount) for c in rgb[:3])


def draw_glossy_bar_horizontal(
    surf: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    ratio: float,
    fill_rgb: tuple[int, int, int],
    track_rgb: tuple[int, int, int],
    border_rgb: tuple[int, int, int] | None = None,
) -> None:
    """横方向の艶付きバー（左から充填）。"""
    if width <= 0 or height <= 0:
        return
    ratio = max(0.0, min(1.0, ratio))
    r = gentle_radius(width, height)

    pygame.draw.rect(surf, track_rgb, (x, y, width, height), border_radius=r)

    fw = max(1, int(width * ratio)) if ratio > 0.001 else 0
    if fw > 0:
        old_clip = surf.get_clip()
        surf.set_clip(pygame.Rect(x, y, fw, height))
        pygame.draw.rect(surf, fill_rgb, (x, y, width, height), border_radius=r)

        gloss_h = max(1, height // 3)
        gloss = pygame.Surface((width, gloss_h), pygame.SRCALPHA)
        gloss.fill((*_brighten(fill_rgb, 75), 110))
        surf.blit(gloss, (x, y))

        shade_h = max(1, height // 4)
        shade = pygame.Surface((width, shade_h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 45))
        surf.blit(shade, (x, y + height - shade_h))

        surf.set_clip(old_clip)

    if border_rgb is not None:
        pygame.draw.rect(surf, border_rgb, (x, y, width, height), 1, border_radius=r)


def draw_glossy_arc_gauge(
    surf: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    thickness: int,
    ratio: float,
    fill_rgb: tuple[int, int, int],
    track_rgb: tuple[int, int, int],
    border_rgb: tuple[int, int, int] | None = None,
    *,
    start_angle: float | None = None,
    span_angle: float | None = None,
    fill_from_end: bool = False,
) -> None:
    """艶付き円弧ゲージ（自機後方のシールド用）。"""
    if radius <= 0 or thickness <= 0:
        return
    ratio = max(0.0, min(1.0, ratio))
    cx, cy = center
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = (cx, cy)
    start = start_angle if start_angle is not None else 3 * math.pi / 2
    span = span_angle if span_angle is not None else math.pi
    end_full = start + span
    if fill_from_end:
        start_fill = end_full - span * ratio
        end_fill = end_full
    else:
        start_fill = start
        end_fill = start + span * ratio

    pygame.draw.arc(surf, track_rgb, rect, start, end_full, thickness)
    if ratio > 0.001:
        pygame.draw.arc(surf, fill_rgb, rect, start_fill, end_fill, thickness)
    if border_rgb is not None:
        pygame.draw.arc(surf, border_rgb, rect, start, end_full, max(1, thickness - 2))


def draw_glossy_panel(
    surf: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    border_rgb: tuple[int, int, int],
    fill_alpha: int = 72,
) -> None:
    """半透明パネル＋緩い角丸枠（艶のある上辺ハイライト）。"""
    r = gentle_radius(width, height)
    bg = pygame.Surface((width, height), pygame.SRCALPHA)
    bg.fill((12, 16, 24, fill_alpha))
    surf.blit(bg, (x, y))

    gloss = pygame.Surface((width, max(2, height // 4)), pygame.SRCALPHA)
    gloss.fill((255, 255, 255, 28))
    clip = pygame.Rect(x, y, width, height)
    old = surf.get_clip()
    surf.set_clip(clip)
    surf.blit(gloss, (x, y))
    surf.set_clip(old)

    pygame.draw.rect(surf, border_rgb, (x, y, width, height), 1, border_radius=r)


def draw_glossy_pip(
    surf: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    active: bool,
    active_rgb: tuple[int, int, int] = (245, 197, 24),
    inactive_rgb: tuple[int, int, int] = (42, 42, 52),
) -> None:
    """武器LVなどの小さな艶付きインジケーター。"""
    if active:
        draw_glossy_bar_horizontal(
            surf,
            x,
            y,
            width,
            height,
            1.0,
            active_rgb,
            _darken(active_rgb, 50),
            _brighten(active_rgb, 30),
        )
    else:
        draw_glossy_bar_horizontal(
            surf,
            x,
            y,
            width,
            height,
            0.0,
            inactive_rgb,
            inactive_rgb,
            (58, 62, 78),
        )


def draw_glossy_slot(
    surf: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    fill_rgb: tuple[int, int, int],
    *,
    filled: bool,
) -> None:
    """ボスHPなどの分割スロット。"""
    empty_rgb = (38, 42, 54)
    if filled:
        draw_glossy_bar_horizontal(
            surf,
            x,
            y,
            width,
            height,
            1.0,
            fill_rgb,
            _darken(fill_rgb, 55),
            _brighten(fill_rgb, 25),
        )
    else:
        draw_glossy_bar_horizontal(
            surf, x, y, width, height, 0.0, empty_rgb, empty_rgb, (52, 58, 72)
        )
