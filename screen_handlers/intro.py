import pygame

from game_layout import blit_full_window_image
from game_runtime import RT
from render_ui import draw_text_with_shadow
from screen_modes import NEW_SCREEN, NEW_SCREEN2, NOTICE, SPLASH


def draw_intro_screen() -> bool:
    """SPLASH / NOTICE / NEW_SCREEN* を描画。continue すべきなら True。"""
    g = RT.g()
    state = g["state"]
    screen = g["screen"]
    app = g["app"]
    WIDTH = g.get("SCREEN_WIDTH", g["WIDTH"])
    HEIGHT = g.get("SCREEN_HEIGHT", g["HEIGHT"])
    cx, cy = WIDTH // 2, HEIGHT // 2
    intro_msg_bottom = HEIGHT - 44
    if state == SPLASH:
        g["splash_logo"].update()
        g["splash_logo"].draw(screen)
        pygame.display.flip()
        if g["splash_logo"].finished:
            g["splash_logo"].stop_audio()
            app.set_screen_mode(NOTICE)
        return True

    if state == NOTICE:
        if g["notice_img"]:
            blit_full_window_image(screen, g["notice_img"])
        else:
            draw_text_with_shadow(
                screen, "INFORMATION", g["big_font"], g["CYAN"],
                cx, cy - 60, is_center=True,
            )
            draw_text_with_shadow(
                screen, "Please prepare assets/notice.png", g["font"], g["RED"],
                cx, cy + 20, is_center=True,
            )
        draw_text_with_shadow(
            screen, "[追加情報へ]：ENTER / Button0", g["font"], g["WHITE"],
            cx, intro_msg_bottom, is_center=True,
        )
        pygame.display.flip()
        return True

    if state == NEW_SCREEN:
        if g["next_screen_img"]:
            blit_full_window_image(screen, g["next_screen_img"])
        else:
            draw_text_with_shadow(
                screen, "PREPARATION SCREEN 1", g["big_font"], g["GREEN"],
                cx, cy - 60, is_center=True,
            )
            draw_text_with_shadow(
                screen, "Please prepare assets/next_screen.png", g["font"], g["YELLOW"],
                cx, cy + 20, is_center=True,
            )
        draw_text_with_shadow(
            screen, "[追加情報へ]：ENTER / Button0", g["font"], g["WHITE"],
            cx, intro_msg_bottom, is_center=True,
        )
        pygame.display.flip()
        return True

    if state == NEW_SCREEN2:
        if g["next_screen2_img"]:
            blit_full_window_image(screen, g["next_screen2_img"])
        else:
            draw_text_with_shadow(
                screen, "PREPARATION SCREEN 2", g["big_font"], g["GREEN"],
                cx, cy - 60, is_center=True,
            )
            draw_text_with_shadow(
                screen, "Please prepare assets/next_screen2.png", g["font"], g["YELLOW"],
                cx, cy + 20, is_center=True,
            )
        draw_text_with_shadow(
            screen, "[難易度選択へ]：ENTER / Button0", g["font"], g["WHITE"],
            cx, intro_msg_bottom, is_center=True,
        )
        pygame.display.flip()
        return True

    return False
