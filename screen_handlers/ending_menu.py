# screen_handlers/ending_menu.py — エンディング画面のエクストラ／難易度選択 UI

from __future__ import annotations

from render_ui import draw_text_with_shadow

# 下部メニューと重ならないようスコア類は画面上部
ENDING_HI_SCORE_NEW_Y = 16
ENDING_HI_SCORE_Y = 44
ENDING_SCORE_Y = 88
ENDING_DIFF_Y = 132


def draw_ending_stats(
    surf,
    font,
    big_font,
    *,
    hi_score: float,
    score: float,
    diff_name: str,
    diff_color: tuple[int, int, int],
    hi_score_updated: bool,
) -> None:
    sw = surf.get_width()
    cx = sw // 2
    if hi_score_updated:
        draw_text_with_shadow(
            surf, "ハイスコア更新!", font, (255, 220, 90),
            cx, ENDING_HI_SCORE_NEW_Y, is_center=True,
        )
    draw_text_with_shadow(
        surf, f"ハイスコア : {int(hi_score)}", font, (80, 255, 255),
        cx, ENDING_HI_SCORE_Y, is_center=True,
    )
    draw_text_with_shadow(
        surf, f"スコア : {int(score)}", big_font, (80, 255, 255),
        cx, ENDING_SCORE_Y, is_center=True,
    )
    draw_text_with_shadow(
        surf, f"難易度 : {diff_name}", font, diff_color,
        cx, ENDING_DIFF_Y, is_center=True,
    )


def draw_ending_extra_menu(
    surf,
    font,
    choice: int,
    sw: int,
    sh: int,
    *,
    extra_allowed: bool,
) -> None:
    cx = sw // 2
    y_title = sh - 56

    if extra_allowed:
        y_extra = sh - 108
        labels = (
            ("[エクストラステージへ]", 0),
            ("[難易度選択へ]", 1),
        )
        for text, idx in labels:
            y = y_extra if idx == 0 else y_title
            color = (255, 220, 90) if choice == idx else (175, 178, 190)
            draw_text_with_shadow(surf, text, font, color, cx, y, is_center=True)
        hint = font.render("↑↓ で選択　決定: ENTER / Button0", True, (130, 132, 145))
        surf.blit(hint, hint.get_rect(midtop=(cx, sh - 148)))
    else:
        draw_text_with_shadow(
            surf,
            "エクストラステージは NORMAL 以上で解放",
            font,
            (150, 155, 170),
            cx,
            sh - 108,
            is_center=True,
        )
        draw_text_with_shadow(
            surf, "[難易度選択へ]", font, (255, 220, 90), cx, y_title, is_center=True,
        )
        hint = font.render("決定: ENTER / Button0", True, (130, 132, 145))
        surf.blit(hint, hint.get_rect(midtop=(cx, sh - 148)))
