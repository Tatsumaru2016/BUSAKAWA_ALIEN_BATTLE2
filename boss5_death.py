# boss5_death.py — ボス5撃破: 勝利演出 → 沈黙 → スコア確定 → 吸い込み → エンディング

from __future__ import annotations

import pygame

from boss5_support import clear_boss5_support
from boss5_update import b5_rush_draw_surface, boss5_body_image, sync_boss5_body_sprite
from boss5_ending_flow import begin_boss5_post_death_epilogue

B5_VICTORY_FRAMES = 120
B5_DEATH_FADE_FRAMES = 120
B5_DEATH_HOLD_FRAMES = 240
B5_DEATH_AMBIENT_INTERVAL = 72


def _scale_to_match(src: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    if src.get_size() == size:
        return src
    return pygame.transform.smoothscale(src, size)


def blend_boss5_defeat(
    color_surf: pygame.Surface, dead_surf: pygame.Surface, t: float
) -> pygame.Surface:
    """t=0 カラー / t=1 白黒撃破画像。"""
    t = max(0.0, min(1.0, t))
    if t <= 0.0:
        return color_surf
    if t >= 1.0:
        return dead_surf
    size = dead_surf.get_size()
    color = _scale_to_match(color_surf, size)
    out = dead_surf.copy()
    overlay = color.copy()
    overlay.set_alpha(int(255 * (1.0 - t)))
    out.blit(overlay, (0, 0))
    return out


def start_boss5_death(play, boss, midboss5_images, diff) -> None:
    from audio import reset_boss5_hp_bgm

    clear_boss5_support()
    reset_boss5_hp_bgm()

    sync_boss5_body_sprite(boss, midboss5_images)
    color_img = boss5_body_image(boss, midboss5_images)
    color_surf, draw_rect = b5_rush_draw_surface(boss, color_img)
    dead = midboss5_images.get("defeat") or midboss5_images["normal"]
    dead_surf = _scale_to_match(dead, color_surf.get_size())

    play.enemies.clear()
    play.turrets.clear()
    play.power_items.clear()
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.bullets.clear()
    play.meteors.clear()

    play.set("b5_death_from_surface", color_surf)
    play.set("b5_death_dead_surface", dead_surf)
    play.set("b5_death_draw_rect", draw_rect.copy())
    play.set("b5_death_timer", 0)
    play.set("b5_death_active", True)
    play.set("b5_death_silence_played", False)
    play.set("b5_death_pending_bonus", 0)
    play.set("boss_active", True)
    play.set("boss_shield_hp", 0)
    play.set("b5_victory_timer", -1)

    try:
        pygame.mixer.music.fadeout(3000)
    except Exception:
        pass
    from audio import invalidate_bgm_state

    invalidate_bgm_state()


def update_boss5_death(play) -> bool:
    """1フレーム進行。シーケンス完了で True。"""
    if not play.b5_death_active:
        return False

    from game_runtime import RT

    g = RT.g()
    t = play.b5_death_timer
    if t == 0 and not play.b5_death_silence_played:
        play.set("b5_death_silence_played", True)
        sfx = g.get("boss5_silence_sound")
        if sfx is not None:
            try:
                sfx.play()
            except Exception:
                pass

    if t >= B5_DEATH_FADE_FRAMES:
        hold_t = t - B5_DEATH_FADE_FRAMES
        if hold_t > 0 and hold_t % B5_DEATH_AMBIENT_INTERVAL == 0:
            ambient = g.get("boss5_gravity_sound")
            if ambient is not None:
                try:
                    ambient.play()
                except Exception:
                    pass

    play.set("b5_death_timer", t + 1)
    return play.b5_death_timer >= B5_DEATH_FADE_FRAMES + B5_DEATH_HOLD_FRAMES


def draw_boss5_death(screen, play) -> None:
    if not play.b5_death_active:
        return
    color_surf = play.b5_death_from_surface
    dead_surf = play.b5_death_dead_surface
    rect = play.b5_death_draw_rect
    if color_surf is None or dead_surf is None or rect is None:
        return
    t = play.b5_death_timer
    if t < B5_DEATH_FADE_FRAMES:
        blend_t = t / max(1, B5_DEATH_FADE_FRAMES)
        img = blend_boss5_defeat(color_surf, dead_surf, blend_t)
    else:
        img = dead_surf
    screen.blit(img, rect.topleft)


def finish_boss5_death_sequence(play, app) -> None:
    from game_runtime import RT

    g = RT.g()
    play.set("b5_death_active", False)
    play.set("b5_death_from_surface", None)
    play.set("b5_death_dead_surface", None)
    play.set("b5_death_draw_rect", None)
    dead_img = g["midboss5_images"].get("defeat") or g["midboss5_images"]["normal"]
    begin_boss5_post_death_epilogue(play, app, g["player"], dead_img)
