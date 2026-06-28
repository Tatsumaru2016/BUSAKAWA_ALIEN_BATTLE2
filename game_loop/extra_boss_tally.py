# game_loop/extra_boss_tally.py — エクストラボス撃破スコア確定

from __future__ import annotations

import random

from explosion import Explosion
from game_loop.resources import frame_core_with_app, ui_message
from game_runtime import RT
from score_system import TALLY_HOLD_FRAMES_EXTRA


def finish_extra_boss_score_tally(bonus_total: int) -> None:
    play = frame_core_with_app().play
    play.set("score", play.score + bonus_total)
    play.boss_score_tally.reset()
    play.set("extra_victory_phase", "bubbles")
    play.set("extra_victory_timer", 0)
    play.set("extra_victory_dialogue_step", 0)
    play.set("extra_victory_bubble_wait", 30)
    ui_message().bubble.clear()


def start_extra_boss_score_tally(play) -> None:
    """中央整列後: 本編ボスと同様のスコア確定演出。"""
    if play.boss_score_tally.active:
        return

    g = RT.g()
    diff = g["diff"]
    hit_bank = int(getattr(play, "extra_victory_hit_bank", 0) or 0)
    play.score_chain.boss_hit_bank = 0
    play.set("_tally_last_line", -1)

    rect = getattr(play, "extra_victory_boss_rect", None)
    if rect is not None:
        for _ in range(15):
            play.explosions.append(
                Explosion(
                    rect.centerx + random.randint(-100, 100),
                    rect.top + random.randint(0, rect.height),
                    big=True,
                )
            )

    play.boss_score_tally.start(
        diff,
        6,
        hit_bank,
        bool(getattr(play, "extra_victory_no_damage", False)),
        int(getattr(play, "extra_victory_fight_frames", 0) or 0),
        play.lives,
        play.score_chain.multiplier(),
        is_final=False,
        on_finish=finish_extra_boss_score_tally,
        hold_frames=TALLY_HOLD_FRAMES_EXTRA,
        require_enter=False,
        show_enter_prompt=False,
    )
    play.set("extra_victory_phase", "tally")
