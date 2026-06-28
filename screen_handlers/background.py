from game_flow import is_final_gameover_play
from game_layout import play_rect
from game_runtime import RT
from render_ui import draw_scroll
from screen_modes import ENDING, ENDING_EXTRA_DIVE, EXTRA_PLAY, GAMEOVER, PLAY
from extra_stage_bg import draw_extra_play_background


def update_title_background() -> None:
    """タイトル画面: タイトル画像の背面で通常ステージ背景をスクロール。"""
    g = RT.g()
    play = g["play"]
    screen = g["screen"]
    origin = play_rect().topleft
    play.update(
        far_x=draw_scroll(screen, g["bg_far"], play.far_x, 1, origin=origin),
        mid_x=draw_scroll(screen, g["bg_mid"], play.mid_x, 2, origin=origin),
        front_x=draw_scroll(screen, g["bg_front"], play.front_x, 5, origin=origin),
    )


def _should_scroll_play_bg(play, state) -> bool:
    if (
        state in (ENDING, EXTRA_PLAY)
        or play.ending_delay_timer > 0
        or play.b5_death_active
    ):
        return False
    if (
        state == GAMEOVER
        or play.boss_score_tally.active
        or is_final_gameover_play(play, state)
    ):
        return True
    if play.boss_active and play.boss:
        return False
    return True


def update_play_background() -> None:
    g = RT.g()
    play = g["play"]
    screen = g["screen"]
    state = g["state"]
    if g.get("extra_bg_mode"):
        if state == EXTRA_PLAY:
            draw_extra_play_background(screen)
        else:
            play.update(
                extra_far_x=draw_scroll(screen, g["extra_bg_far"], play.extra_far_x, 1),
                extra_mid_x=draw_scroll(screen, g["extra_bg_mid"], play.extra_mid_x, 2),
                extra_front_x=draw_scroll(
                    screen, g["extra_bg_front"], play.extra_front_x, 4
                ),
            )
    elif g["boss5_bg_mode"]:
        play.update(
            boss5_far_x=draw_scroll(screen, g["boss5_bg_far"], play.boss5_far_x, 1),
            boss5_mid_x=draw_scroll(screen, g["boss5_bg_mid"], play.boss5_mid_x, 2),
            boss5_front_x=draw_scroll(screen, g["boss5_bg_front"], play.boss5_front_x, 4),
        )
    elif state == ENDING:
        screen.blit(g["bg_far"], (play.far_x, 0))
        screen.blit(g["bg_far"], (play.far_x + g["bg_far"].get_width(), 0))
        screen.blit(g["bg_mid"], (play.mid_x, 0))
        screen.blit(g["bg_mid"], (play.mid_x + g["bg_mid"].get_width(), 0))
        screen.blit(g["bg_front"], (play.front_x, 0))
        screen.blit(g["bg_front"], (play.front_x + g["bg_front"].get_width(), 0))
    elif _should_scroll_play_bg(play, state):
        play.update(
            far_x=draw_scroll(screen, g["bg_far"], play.far_x, 1),
            mid_x=draw_scroll(screen, g["bg_mid"], play.mid_x, 2),
            front_x=draw_scroll(screen, g["bg_front"], play.front_x, 5),
        )
    else:
        screen.blit(g["bg_far"], (play.far_x, 0))
        screen.blit(g["bg_far"], (play.far_x + g["bg_far"].get_width(), 0))
        screen.blit(g["bg_mid"], (play.mid_x, 0))
        screen.blit(g["bg_mid"], (play.mid_x + g["bg_mid"].get_width(), 0))
        screen.blit(g["bg_front"], (play.front_x, 0))
        screen.blit(g["bg_front"], (play.front_x + g["bg_front"].get_width(), 0))
