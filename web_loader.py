# web_loader.py — pygbag 起動時の HTML ローダー / ブート画面

from __future__ import annotations

import json
import sys

from platform_web import is_web


def _eval(js: str) -> None:
    if not is_web():
        return
    try:
        import platform

        platform.window.eval(js)
    except Exception:
        pass


def hide_html_loader() -> None:
    """HTML オーバーレイを消し canvas を表示する。"""
    if not is_web():
        return
    _eval("window.BABLoader && BABLoader.hide()")
    _eval(
        "document.querySelector('canvas.emscripten')"
        " && (document.querySelector('canvas.emscripten').style.visibility='visible')"
    )


def set_html_stage(msg: str, pct: float | None = None) -> None:
    if not is_web():
        return
    try:
        import platform

        el = platform.document.getElementById("bab-stage")
        if el:
            el.innerText = msg
    except Exception:
        _eval(f"window.BABLoader && BABLoader.setStage({json.dumps(msg, ensure_ascii=True)})")
    if pct is not None:
        _eval(f"window.BABLoader && BABLoader.setPercent({float(pct)})")


def paint_boot_screen(screen, msg: str, pct: float, *, font_path: str | None = None) -> None:
    """Web: pygame 画面に簡易プログレスを描画（HTML ローダーと同期）。"""
    if not is_web():
        return
    try:
        import pygame

        pct = max(0.0, min(100.0, float(pct)))
        screen.fill((6, 12, 24))
        w, h = screen.get_size()
        bar_w = min(420, max(200, w - 80))
        bar_h = 14
        x0 = (w - bar_w) // 2
        y0 = h // 2

        pygame.draw.rect(screen, (40, 62, 96), (x0, y0, bar_w, bar_h), border_radius=7)
        fill_w = max(0, int(bar_w * pct / 100.0))
        if fill_w:
            pygame.draw.rect(screen, (80, 220, 255), (x0, y0, fill_w, bar_h), border_radius=7)

        if font_path:
            try:
                font = pygame.font.Font(font_path, 22)
            except Exception:
                font = pygame.font.SysFont("sans-serif", 22)
        else:
            font = pygame.font.SysFont("sans-serif", 22)
        title = font.render("Busakawa Alien Battle 2", True, (120, 220, 255))
        line = font.render(msg, True, (210, 230, 255))
        pct_line = font.render(f"{int(pct)}%", True, (255, 213, 106))
        screen.blit(title, title.get_rect(center=(w // 2, y0 - 72)))
        screen.blit(line, line.get_rect(center=(w // 2, y0 - 32)))
        screen.blit(pct_line, pct_line.get_rect(center=(w // 2, y0 + 28)))
        pygame.display.flip()
    except Exception:
        pass
    set_html_stage(msg, pct)
