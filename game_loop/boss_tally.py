# game_loop/boss_tally.py — ボス撃破スコア確定

from __future__ import annotations

import random

from audio import BGM_ENDING, BGM_NORMAL, play_bgm
from explosion import Explosion
from game_constants import EMS_MAX
from game_loop.resources import frame_core, frame_core_with_app, title_flow_resources, ui_message
from game_runtime import RT
from game_state import AppState
from boss5_support import clear_boss5_support
from boss_spawn import clear_boss_warning
from screen_modes import ENDING


def advance_boss_slot_after_defeat(play) -> None:
    """撃破直後に次ボス用スロットへ進め、同一ボスへの誤WARNINGを防ぐ。"""
    clear_boss_warning(play)
    play.set("boss_cycle", play.boss_cycle + 1)
    play.set("boss_index", play.boss_index + 1)


def finish_boss_score_tally(bonus_total: int) -> None:
    core = frame_core_with_app()
    play = core.play
    app = core.app
    g = RT.g()
    _bubble = ui_message().bubble
    is_final = play.boss_score_tally.is_final
    boss_type = play.boss_score_tally.boss_type

    play.set("score", play.score + bonus_total)
    play.set("boss_fight_active", False)

    if is_final:
        if getattr(play, "b5_clear_cinematic", False):
            from boss5_ending_flow import begin_boss5_dive_after_tally

            begin_boss5_dive_after_tally(play, app)
            return
        play.boss_score_tally.reset()
        play.set("ending_delay_timer", 0)
        play.set("boss", None)
        play.enemy_bullets.clear()
        play.enemy_lasers.clear()
        play.bullets.clear()
        title_flow_resources().title_cheat.reset_all()
        app.record_hard_clear_if_applicable()
        if AppState.can_enter_extra_stage(app.diff.name):
            play.set("ending_menu_choice", 0)
        else:
            play.set("ending_menu_choice", 1)
        app.set_screen_mode(ENDING)
        play.set("_ending_sfx_timer", g["FPS"] * 3)
        play.set("_ending_screen_sfx_played", False)
        return

    play_bgm(BGM_NORMAL)
    if boss_type != 5:
        clear_boss5_support()
    boss_kill_key = f"boss_kill_{boss_type}"
    _bubble.show(boss_kill_key)
    if play.ems_count < EMS_MAX:
        play.set("ems_count", play.ems_count + 1)
    play.set("boss", None)


def start_boss_score_tally(boss_ref) -> None:
    core = frame_core_with_app()
    play = core.play
    app = core.app
    player = core.player
    bt = boss_ref.boss_type
    is_final = bt == 5

    play.enemies.clear()
    play.turrets.clear()
    play.power_items.clear()
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.bullets.clear()
    play.meteors.clear()

    if is_final and not getattr(play, "b5_clear_cinematic", False):
        for _ in range(30):
            play.explosions.append(
                Explosion(
                    boss_ref.rect.centerx + random.randint(-200, 200),
                    boss_ref.rect.centery + random.randint(-300, 300),
                    big=True,
                )
            )
    else:
        for _ in range(15):
            play.explosions.append(
                Explosion(
                    boss_ref.rect.centerx + random.randint(-100, 100),
                    boss_ref.rect.top + random.randint(0, boss_ref.rect.height),
                    big=True,
                )
            )

    hit_bank = play.score_chain.boss_hit_bank
    play.score_chain.boss_hit_bank = 0
    play.set("_tally_last_line", -1)
    # ボス撃破: レーザーゲージを満タンにする（爽快感を維持）
    try:
        from settings import LASER_GAUGE_MAX

        player.laser_gauge = float(LASER_GAUGE_MAX)
    except Exception:
        pass

    play.boss_score_tally.start(
        app.diff,
        bt,
        hit_bank,
        play.no_damage_since_boss,
        play.boss_fight_timer,
        play.lives,
        play.score_chain.multiplier(),
        is_final=is_final,
        on_finish=finish_boss_score_tally,
        require_enter=True,
        show_enter_prompt=True,
    )
    play.set("boss_active", False)
