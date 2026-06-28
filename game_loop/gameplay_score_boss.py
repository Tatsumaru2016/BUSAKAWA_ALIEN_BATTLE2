# game_loop/gameplay_score_boss.py — スコアチェイン・ボス警告

from __future__ import annotations

import boss_spawn
from boss_spawn import BOSS_WARNING_DURATION_FRAMES, play_boss_warning_sfx
from game_loop.resources import frame_core, score_boss_bundle, ui_message
from game_runtime import RT
from screen_modes import ENDING, ENDING_EXTRA_DIVE, EXTRA_PLAY, GAMEOVER, PLAY


def _should_start_boss_warning(play, diff) -> bool:
    boss_kills = diff.boss_kills
    if play.boss_score_tally.active or play.b5_death_active:
        return False
    if int(getattr(play, "_boss_defeat_fx_type", 0)) in (1, 2, 3, 4):
        return False
    return (
        play.boss_index < len(boss_kills)
        and play.kill_count >= boss_kills[play.boss_index]
        and not play.boss_active
        and play.boss is None
        and not play.boss_warning
    )


def _tick_boss_warning_screen(
    play,
    screen,
    g,
    *,
    warning_img,
    warning_sound,
    diff,
    player,
    boss_cycle: int,
    bubble,
) -> None:
    """警告表示を1フレーム進める（タイマーは play から都度読む）。"""
    timer = int(play.boss_warning_timer) + 1
    play.set("boss_warning_timer", timer)

    if timer == 1:
        bubble.show("boss_warning")
        boss_spawn.on_boss_warning_first_frame(play, boss_cycle + 1)
    elif timer % 45 == 0 and timer < BOSS_WARNING_DURATION_FRAMES:
        play_boss_warning_sfx(g, warning_sound, with_launch=False)

    if timer >= BOSS_WARNING_DURATION_FRAMES:
        boss_spawn.activate_boss_after_warning(
            play,
            boss_cycle + 1,
            diff,
            player,
            screen.get_width(),
            screen.get_height(),
        )


def run_gameplay_score_boss_phase() -> None:
    g = RT.g()
    core = frame_core()
    play = core.play
    screen = core.screen
    player = core.player
    diff = core.diff
    state = core.state
    assets = score_boss_bundle()
    bubble = ui_message().bubble
    player_dead = play.player_dead
    ending_delay_timer = play.ending_delay_timer
    boss_score_tally = play.boss_score_tally
    boss_cycle = play.boss_cycle

    score_chain = play.score_chain
    score_tick_sound = assets.score_tick_sound
    warning_img = assets.warning_img
    warning_sound = assets.warning_sound
    _bubble = bubble

    gameplay_paused = boss_score_tally.active or play.b5_death_active
    g["_gameplay_paused"] = gameplay_paused

    tally_states = (PLAY, EXTRA_PLAY)
    epilogue_phase = getattr(play, "b5_epilogue_phase", "")
    if state == ENDING_EXTRA_DIVE and (
        boss_score_tally.active or epilogue_phase == "tally"
    ):
        tally_states = (PLAY, EXTRA_PLAY, ENDING_EXTRA_DIVE)

    if state in tally_states:
        if boss_score_tally.active:
            if boss_score_tally.line_index != play._tally_last_line:
                play.set("_tally_last_line", boss_score_tally.line_index)
                if play._tally_last_line > 0:
                    score_tick_sound.play()
            boss_score_tally.update()

    if state == GAMEOVER:
        return

    blocked = (
        player_dead
        or ending_delay_timer != 0
        or play.b5_death_active
        or state == ENDING
        or (
            state == ENDING_EXTRA_DIVE
            and epilogue_phase not in ("tally", "dive", "fade")
        )
    )

    tick_kw = dict(
        play=play,
        screen=screen,
        g=g,
        warning_img=warning_img,
        warning_sound=warning_sound,
        diff=diff,
        player=player,
        boss_cycle=boss_cycle,
        bubble=_bubble,
    )

    # 表示中の警告はスコア確定中でも進行（開始直後フレームの取りこぼし防止）
    if play.boss_warning and not blocked:
        _tick_boss_warning_screen(**tick_kw)
        return

    # スコア確定中に条件を満たした場合は、確定後に警告を出す
    if getattr(play, "boss_warning_pending", False) and not gameplay_paused and not blocked:
        play.set("boss_warning_pending", False)
        if _should_start_boss_warning(play, diff):
            boss_spawn.begin_boss_warning(play, boss_cycle + 1)
            _tick_boss_warning_screen(**tick_kw)
        return

    if blocked or gameplay_paused:
        if _should_start_boss_warning(play, diff) and gameplay_paused and not blocked:
            play.set("boss_warning_pending", True)
        return

    if _should_start_boss_warning(play, diff):
        boss_spawn.begin_boss_warning(play, boss_cycle + 1)
        _tick_boss_warning_screen(**tick_kw)
