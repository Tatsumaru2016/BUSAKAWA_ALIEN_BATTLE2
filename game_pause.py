# game_pause.py — プレイ中の一時停止

from __future__ import annotations

import pygame

from audio_focus import is_focus_audio_suppressed
from screen_modes import EXTRA_PLAY, PLAY

if False:  # TYPE_CHECKING
    from game_state import PlayState


def is_gameplay_paused(play) -> bool:
    return bool(getattr(play, "game_paused", False))


def gameplay_freeze_active(play, state: int) -> bool:
    return state in (PLAY, EXTRA_PLAY) and is_gameplay_paused(play)


def set_game_paused(play, paused: bool) -> None:
    was = is_gameplay_paused(play)
    play.set("game_paused", paused)
    if was == paused:
        return
    try:
        if paused:
            pygame.mixer.music.pause()
        elif not is_focus_audio_suppressed():
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass
            from audio import ensure_music_playing

            ensure_music_playing()
    except Exception:
        pass


def toggle_game_pause(play) -> bool:
    set_game_paused(play, not is_gameplay_paused(play))
    return is_gameplay_paused(play)


def draw_pause_overlay(surf, big_font) -> None:
    sw, sh = surf.get_size()
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surf.blit(overlay, (0, 0))
    if (pygame.time.get_ticks() // 480) % 2 == 0:
        text = "PAUSE"
        shadow = big_font.render(text, True, (0, 0, 0))
        main = big_font.render(text, True, (255, 220, 0))
        rect = main.get_rect(center=(sw // 2, sh // 2))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surf.blit(shadow, rect.move(dx, dy))
        surf.blit(main, rect)


def handle_play_pause_event(event, g: dict) -> bool:
    """PLAY / EXTRA_PLAY のポーズ・スコア確定 ENTER。処理したら True。"""
    state = g["state"]
    if state not in (PLAY, EXTRA_PLAY):
        return False

    play = g["play"]
    KEY_BINDINGS = g["KEY_BINDINGS"]
    _c = g["_c"]

    if play.boss_score_tally.active and play.boss_score_tally.require_enter:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            play.boss_score_tally.confirm_enter()
            return True
        if (
            event.type == pygame.JOYBUTTONDOWN
            and event.button == _c.get("confirm", 0)
        ):
            play.boss_score_tally.confirm_enter()
            return True

    pause_key = KEY_BINDINGS.get("pause", pygame.K_q)
    pause_btn = _c.get("pause", 7)
    if event.type == pygame.KEYDOWN and event.key == pause_key:
        toggle_game_pause(play)
        return True
    if event.type == pygame.JOYBUTTONDOWN and event.button == pause_btn:
        toggle_game_pause(play)
        return True
    return False
