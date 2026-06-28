# extra_boss_victory.py — エクストラボス撃破演出

from __future__ import annotations

import math
import random

import pygame

from explosion import Explosion
from extra_stage_support import (
    all_support_exited,
    all_support_lineup_done,
    begin_victory_exit,
    begin_victory_lineup,
    deploy_victory_support_squad,
    update_extra_support_squad,
)
from game_runtime import RT

EXTRA_VICTORY_PLAYER_BATTLE_X = 120
EXTRA_VICTORY_POST_EXIT_WAIT_FRAMES = 120
EXTRA_ENDING_SLIDE_COUNT = 7
EXTRA_ENDING_SLIDE_FRAMES = 300
EXTRA_FIN_PRE_WAIT_FRAMES = 60
EXTRA_VICTORY_FOLLOW_OFFSET_X = 96
EXTRA_FIN_CHAR_DRAW_FRAMES = 52
EXTRA_FIN_POST_WAIT_FRAMES = 120
EXTRA_ENDING_FADE_FRAMES = 90
EXTRA_FIN_TEXT = "Fin"
EXTRA_FIN_MARGIN_RIGHT = 52
EXTRA_FIN_MARGIN_BOTTOM = 44
EXTRA_FIN_CHAR_GAP = 8
EXTRA_VICTORY_EXPLODE_FRAMES = 200
EXTRA_VICTORY_SUPPORT_SPAWN_T = 52
EXTRA_VICTORY_SUPPORT_STAGGER = 10
EXTRA_VICTORY_LINEUP_MAX_FRAMES = 220
EXTRA_VICTORY_BUBBLE_GAP = 95
EXTRA_VICTORY_PLAYER_LINEUP_SPEED = 2.8
VICTORY_CENTER_X_RATIO = 0.40
VICTORY_CENTER_Y_RATIO = 0.50

# (kind, variant_index, msg_index) — 支援機は各1回のみ
_VICTORY_DIALOGUE = []
for _v in range(5):
    _VICTORY_DIALOGUE.append(("support", _v, 0))
for _n in range(3):
    _VICTORY_DIALOGUE.append(("player", -1, _n))


def g():
    return RT.g()


def is_extra_victory_active(play) -> bool:
    return bool(getattr(play, "extra_victory_active", False))


def is_extra_victory_blocking(play) -> bool:
    """自機停止・射撃不可。"""
    return is_extra_victory_active(play)


def is_extra_ending_cinematic(play) -> bool:
    """スライド／Fin 表示中（UI・自機を隠す）。"""
    if not is_extra_victory_active(play):
        return False
    return getattr(play, "extra_victory_phase", "") in (
        "gallery",
        "fin_pre_wait",
        "fin_draw",
        "fin_post_wait",
        "fade_out",
    )


def init_extra_victory_state(play) -> None:
    play.set("extra_victory_active", False)
    play.set("extra_victory_phase", "")
    play.set("extra_victory_timer", 0)
    play.set("extra_victory_dialogue_step", 0)
    play.set("extra_victory_frozen_x", 0)
    play.set("extra_victory_frozen_y", 0)
    play.set("extra_victory_target_x", 0.0)
    play.set("extra_victory_target_y", 0.0)
    play.set("extra_victory_depart_x", float(EXTRA_VICTORY_PLAYER_BATTLE_X))
    play.set("extra_victory_depart_y", 0.0)
    play.set("extra_victory_bubble_wait", 0)
    play.set("extra_victory_boss_rect", None)
    play.set("extra_victory_flash_timer", 0)
    play.set("extra_victory_hit_bank", 0)
    play.set("extra_victory_no_damage", False)
    play.set("extra_victory_fight_frames", 0)
    play.set("extra_ending_slide_index", 0)
    play.set("extra_ending_bgm_started", False)
    play.set("extra_fin_char_index", 0)
    play.set("extra_fin_char_progress", 0.0)
    play.set("extra_victory_speech_variant", -1)
    play.set("extra_victory_depart_stuck", 0)


def clear_extra_victory(play) -> None:
    init_extra_victory_state(play)


def _init_victory_layout(play, player, width: int, height: int) -> None:
    tcx = float(width) * VICTORY_CENTER_X_RATIO
    tcy = float(height) * VICTORY_CENTER_Y_RATIO
    play.set("extra_victory_target_x", tcx)
    play.set("extra_victory_target_y", tcy)
    play.set("extra_victory_depart_x", float(EXTRA_VICTORY_PLAYER_BATTLE_X))
    play.set("extra_victory_depart_y", float(height) // 2)
    play.set("extra_victory_frozen_x", float(player.rect.centerx))
    play.set("extra_victory_frozen_y", float(player.rect.centery))


def _finish_extra_victory_to_difficulty(play) -> None:
    from ending_extra_dive import go_to_difficulty_select
    from extra_stage_support import clear_extra_support
    from game_loop.resources import frame_core_with_app, title_flow_resources

    clear_extra_support(play)
    clear_extra_victory(play)
    core = frame_core_with_app()
    core.app.record_hard_clear_if_applicable()
    go_to_difficulty_select(core.app, play, title_flow_resources().title_cheat)


def _blit_last_ending_slide(screen: pygame.Surface) -> None:
    slides = g().get("extra_ending_slides") or []
    if not slides:
        screen.fill((0, 0, 0))
        return
    from game_layout import blit_full_window_image

    last_idx = min(EXTRA_ENDING_SLIDE_COUNT - 1, len(slides) - 1)
    blit_full_window_image(screen, slides[last_idx])


def draw_extra_ending_slide(screen: pygame.Surface, play) -> None:
    slides = g().get("extra_ending_slides") or []
    idx = int(getattr(play, "extra_ending_slide_index", 0) or 0)
    if not slides:
        screen.fill((0, 0, 0))
        return
    if idx >= len(slides):
        idx = len(slides) - 1
    from game_layout import blit_full_window_image

    blit_full_window_image(screen, slides[idx])


def _fin_letter_surfaces(font) -> list[tuple[pygame.Surface, pygame.Surface]]:
    from assets_loader import BLACK, WHITE

    return [
        (font.render(ch, True, WHITE), font.render(ch, True, BLACK))
        for ch in EXTRA_FIN_TEXT
    ]


def _blit_fin_letter(
    screen: pygame.Surface,
    letter: pygame.Surface,
    shadow: pygame.Surface,
    x: int,
    y: int,
    progress: float,
    *,
    wobble_y: int = 0,
) -> None:
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0:
        return
    w, h = letter.get_size()
    clip_w = max(1, int(w * progress))
    clipped = letter.subsurface((0, 0, clip_w, h))
    clipped_shadow = shadow.subsurface((0, 0, clip_w, h))
    px, py = x, y + wobble_y
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        screen.blit(clipped_shadow, (px + dx, py + dy))
    screen.blit(clipped, (px, py))


def _fin_display_font():
    font = g().get("fin_script_font") or g().get("big_font")
    return font


def draw_extra_ending_fin(screen: pygame.Surface, play) -> None:
    """6枚目の上に、右下へ「Fin」を1文字ずつ筆記風に表示。"""
    _blit_last_ending_slide(screen)
    font = _fin_display_font()
    if font is None:
        return

    letters = _fin_letter_surfaces(font)
    if not letters:
        return

    char_idx = int(getattr(play, "extra_fin_char_index", 0) or 0)
    progress = float(getattr(play, "extra_fin_char_progress", 0.0) or 0.0)
    phase = getattr(play, "extra_victory_phase", "")
    if phase in ("fin_post_wait", "fade_out"):
        char_idx = len(EXTRA_FIN_TEXT)
        progress = 1.0
    elif phase == "fin_pre_wait":
        char_idx = 0
        progress = 0.0

    total_w = sum(s[0].get_width() for s in letters) + EXTRA_FIN_CHAR_GAP * (len(letters) - 1)
    base_x = screen.get_width() - EXTRA_FIN_MARGIN_RIGHT - total_w
    base_y = screen.get_height() - EXTRA_FIN_MARGIN_BOTTOM - letters[0][0].get_height()
    t = int(getattr(play, "extra_victory_timer", 0) or 0)

    cx = base_x
    for i, (letter, shadow) in enumerate(letters):
        if i < char_idx:
            _blit_fin_letter(screen, letter, shadow, cx, base_y, 1.0)
        elif i == char_idx and phase == "fin_draw":
            wobble = int(math.sin(t * 0.55) * 3) if progress < 1.0 else 0
            _blit_fin_letter(
                screen, letter, shadow, cx, base_y, progress, wobble_y=wobble,
            )
        cx += letter.get_width() + EXTRA_FIN_CHAR_GAP


def draw_extra_ending_fade_overlay(screen: pygame.Surface, play) -> None:
    """Fin表示の上から黒フェードアウト。"""
    t = int(getattr(play, "extra_victory_timer", 0) or 0)
    dur = max(1, EXTRA_ENDING_FADE_FRAMES)
    raw = min(1.0, t / float(dur))
    fade = raw * raw * (3.0 - 2.0 * raw)
    alpha = int(255 * fade)
    if alpha <= 0:
        return
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))


def start_extra_boss_victory(play, boss) -> None:
    if play.extra_victory_active:
        return
    from extra_boss import clear_extra_boss_combat_on_defeat

    clear_extra_boss_combat_on_defeat(play, boss)
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.meteors.clear()
    play.bullets.clear()

    play.set("extra_victory_active", True)
    play.set("extra_victory_phase", "explode")
    play.set("extra_victory_timer", 0)
    play.set("extra_victory_dialogue_step", 0)
    play.set("extra_victory_boss_rect", boss.rect.copy() if boss else None)
    play.set("extra_victory_flash_timer", 0)
    play.set("extra_victory_hit_bank", play.score_chain.boss_hit_bank)
    play.set("extra_victory_no_damage", play.no_damage_since_boss)
    play.set("extra_victory_fight_frames", play.boss_fight_timer)
    play.set("extra_ending_slide_index", 0)
    play.set("extra_ending_bgm_started", False)
    play.set("extra_fin_char_index", 0)
    play.set("extra_fin_char_progress", 0.0)
    play.set("extra_victory_speech_variant", -1)
    play.set("extra_victory_depart_stuck", 0)
    play.set("boss_fight_active", False)
    play.set("boss_shield_hp", 0)
    play.set("boss_shield_max", 0)
    play.set("boss_shield_grace_timer", 0)

    sfx = g().get("explosion_sound")
    if sfx is not None:
        try:
            sfx.play()
        except Exception:
            pass


def _boss_rect(play):
    return getattr(play, "extra_victory_boss_rect", None)


def _spawn_boss_explosion_burst(play, count: int, *, big_chance: float = 0.65) -> None:
    rect = _boss_rect(play)
    if rect is None:
        return
    explosions = play.explosions
    cx, cy = rect.centerx, rect.centery
    for _ in range(count):
        big = random.random() < big_chance
        rx = random.randint(-int(rect.width * 0.55), int(rect.width * 0.55))
        ry = random.randint(-int(rect.height * 0.45), int(rect.height * 0.45))
        explosions.append(Explosion(cx + rx, cy + ry, big=big))


def _update_victory_explosions(play, t: int) -> None:
    rect = _boss_rect(play)
    if rect is None:
        return

    if t % 3 == 0:
        _spawn_boss_explosion_burst(play, 2, big_chance=0.35)
    if t % 5 == 0:
        _spawn_boss_explosion_burst(play, 1, big_chance=0.8)

    for peak in (18, 42, 68, 98, 130, 165):
        if t == peak:
            _spawn_boss_explosion_burst(play, random.randint(6, 10), big_chance=0.85)
            play.set("extra_victory_flash_timer", 14)
            sfx = g().get("explosion_sound")
            if sfx is not None:
                try:
                    sfx.play()
                except Exception:
                    pass

    if t == EXTRA_VICTORY_SUPPORT_SPAWN_T + 20:
        _spawn_boss_explosion_burst(play, 8, big_chance=0.9)
        play.set("extra_victory_flash_timer", 18)


def _step_player_toward_point(
    play, player, tx: float, ty: float, speed: float,
) -> bool:
    dx = tx - player.rect.centerx
    dy = ty - player.rect.centery
    dist = math.hypot(dx, dy)
    if dist > 1.0:
        step = min(speed, dist)
        player.rect.centerx = int(player.rect.centerx + (dx / dist) * step)
        player.rect.centery = int(player.rect.centery + (dy / dist) * step)
        dist = math.hypot(tx - player.rect.centerx, ty - player.rect.centery)
    if dist <= 10.0:
        player.rect.centerx = int(tx)
        player.rect.centery = int(ty)
        return True
    return False


def _step_player_toward(play, player, speed: float) -> bool:
    tx = float(play.extra_victory_target_x)
    ty = float(play.extra_victory_target_y)
    return _step_player_toward_point(play, player, tx, ty, speed)


def _update_player_follow_support_exit(
    play, player, width: int, height: int,
) -> None:
    """支援機の退場に合わせ、自機は隊列の後方（左）から追従。"""
    from boss5_support import SUPPORT_SIZE

    squad = getattr(play, "extra_support_fighters", [])
    _, sh = SUPPORT_SIZE
    margin_y = sh * 0.5 + 48
    supports_gone = all_support_exited(play, width)
    speed = (
        EXTRA_VICTORY_PLAYER_LINEUP_SPEED * 2.4
        if supports_gone
        else EXTRA_VICTORY_PLAYER_LINEUP_SPEED
    )

    if supports_gone:
        tx = float(width) + 100.0
        ty = float(player.rect.centery)
    elif squad:
        active = [sf for sf in squad if sf.get("state") == "victory_exit"]
        if not active:
            active = squad
        tx = min(float(sf["x"]) for sf in active) - EXTRA_VICTORY_FOLLOW_OFFSET_X
        ty = sum(float(sf["y"]) for sf in active) / len(active)
    else:
        tx = float(width) + 100.0
        ty = float(player.rect.centery)

    ty = max(margin_y, min(float(height) - margin_y, ty))
    _step_player_toward_point(play, player, tx, ty, speed)


def _depart_sequence_done(play, player, width: int) -> bool:
    if not all_support_exited(play, width):
        return False
    if float(player.rect.left) >= float(width) + 16:
        return True
    if float(player.rect.right) >= float(width) - 6:
        stuck = int(getattr(play, "extra_victory_depart_stuck", 0) or 0) + 1
        play.set("extra_victory_depart_stuck", stuck)
        return stuck >= 45
    play.set("extra_victory_depart_stuck", 0)
    return False


def _sync_player_victory_pos(play, player) -> None:
    play.set("extra_victory_frozen_x", float(player.rect.centerx))
    play.set("extra_victory_frozen_y", float(player.rect.centery))


def _try_spawn_victory_support(play, player, t: int, width: int, height: int) -> None:
    if not play.extra_support_deployed:
        images = g().get("support_fighter_images") or []
        for variant in range(5):
            spawn_t = EXTRA_VICTORY_SUPPORT_SPAWN_T + variant * EXTRA_VICTORY_SUPPORT_STAGGER
            if t == spawn_t:
                deploy_victory_support_squad(
                    play,
                    images,
                    width,
                    height,
                    variant=variant,
                    arrive_sound=g().get("support_arrive_sound") if variant == 0 else None,
                )
                sfx = g().get("launch_sound") or g().get("support_arrive_sound")
                if sfx is not None:
                    try:
                        sfx.play()
                    except Exception:
                        pass


def _update_victory_support(
    play,
    player,
    *,
    victory_lineup: bool = False,
    victory_exit: bool = False,
) -> None:
    if not play.extra_support_deployed:
        return
    width = g()["WIDTH"]
    height = g()["HEIGHT"]
    update_extra_support_squad(
        play,
        player,
        False,
        None,
        play.bullets,
        g().get("bullet_img"),
        g().get("support_fighter_images") or [],
        None,
        width,
        height,
        g().get("Bullet") or __import__("bullet", fromlist=["Bullet"]).Bullet,
        victory_lineup=victory_lineup,
        victory_exit=victory_exit,
    )


def draw_extra_victory_fx(
    screen: pygame.Surface, play, t: int, *, layer: str = "over",
) -> None:
    """撃破フラッシュ・衝撃波。"""
    rect = _boss_rect(play)
    width, height = screen.get_size()

    if layer == "under":
        flash_t = play.extra_victory_flash_timer
        if flash_t > 0:
            alpha = min(220, 50 + flash_t * 16)
            flash = pygame.Surface((width, height), pygame.SRCALPHA)
            flash.fill((255, 230, 180, alpha))
            screen.blit(flash, (0, 0))
        return

    if rect is None:
        return

    cx, cy = rect.centerx, rect.centery
    for wave_start, max_r, color in (
        (10, 280, (255, 120, 60, 90)),
        (35, 340, (255, 200, 80, 70)),
        (70, 400, (200, 120, 255, 55)),
        (110, 460, (255, 255, 255, 40)),
        (145, 520, (255, 80, 40, 35)),
    ):
        age = t - wave_start
        if age < 0 or age > 52:
            continue
        radius = int(age * (max_r / 52))
        alpha = max(0, color[3] - age * 2)
        ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(
            ring,
            (color[0], color[1], color[2], alpha),
            (radius + 4, radius + 4),
            radius,
            max(2, 5 - age // 14),
        )
        screen.blit(ring, (cx - radius - 4, cy - radius - 4))

    flash_t = play.extra_victory_flash_timer
    if flash_t > 0:
        alpha = min(160, 30 + flash_t * 10)
        flash = pygame.Surface((width, height), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (0, 0))


def extra_victory_boss_draw_offset(play) -> tuple[int, int]:
    return (
        int(getattr(play, "_extra_victory_boss_shake_x", 0)),
        int(getattr(play, "_extra_victory_boss_shake_y", 0)),
    )


def draw_extra_victory_boss(screen: pygame.Surface, play, boss) -> None:
    if boss is None:
        return
    ox, oy = extra_victory_boss_draw_offset(play)
    t = play.extra_victory_timer
    alpha = 255
    if t > 120:
        alpha = max(0, 255 - (t - 120) * 4)
    if alpha <= 0:
        return
    img = boss.image
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    pos = boss.rect.copy()
    pos.x += ox
    pos.y += oy
    screen.blit(img, pos)


def _support_by_variant(play, variant: int):
    for sf in getattr(play, "extra_support_fighters", []):
        if sf.get("variant") == variant:
            return sf
    return None


def get_extra_victory_speech_anchor(play):
    """撃破後セリフ中: いま話している支援機に吹き出しを固定。"""
    if getattr(play, "extra_victory_phase", "") != "bubbles":
        return None
    variant = getattr(play, "extra_victory_speech_variant", -1)
    if variant < 0:
        return None
    sf = _support_by_variant(play, variant)
    if sf is None:
        return None
    from boss5_support import support_fighter_rect

    return support_fighter_rect(sf)


def _show_victory_bubble(play, kind: str, variant: int, msg_index: int) -> bool:
    """表示したら True。スキップしたら False。"""
    bubble = g().get("_bubble")
    if bubble is None:
        return False
    if kind == "player":
        play.set("extra_victory_speech_variant", -1)
        key = f"extra_clear_player_{msg_index + 1}"
        bubble.show(key, None, anchor_style="player")
        return True
    sf = _support_by_variant(play, variant)
    if sf is None:
        play.set("extra_victory_speech_variant", -1)
        return False
    from boss5_support import support_fighter_rect

    play.set("extra_victory_speech_variant", variant)
    key = f"extra_clear_support_{variant}_{msg_index + 1}"
    bubble.show(key, support_fighter_rect(sf), anchor_style="support_right")
    return True


def _player_lineup_done(play, player) -> bool:
    tx = float(play.extra_victory_target_x)
    ty = float(play.extra_victory_target_y)
    return math.hypot(tx - player.rect.centerx, ty - player.rect.centery) <= 10.0


def update_extra_boss_victory(play, player) -> None:
    if not play.extra_victory_active:
        return

    phase = play.extra_victory_phase
    play.set("extra_victory_timer", play.extra_victory_timer + 1)
    t = play.extra_victory_timer
    width = g()["WIDTH"]
    height = g()["HEIGHT"]

    if phase == "explode":
        if t == 1:
            _init_victory_layout(play, player, width, height)
        play.set(
            "_extra_victory_boss_shake_x",
            int(math.sin(t * 0.85) * min(14, 4 + t // 22)),
        )
        play.set("_extra_victory_boss_shake_y", int(math.sin(t * 0.62) * min(6, t // 40)))
        if play.extra_victory_flash_timer > 0:
            play.set("extra_victory_flash_timer", play.extra_victory_flash_timer - 1)
        _step_player_toward(play, player, EXTRA_VICTORY_PLAYER_LINEUP_SPEED)
        _sync_player_victory_pos(play, player)
        _update_victory_explosions(play, t)
        _try_spawn_victory_support(play, player, t, width, height)
        if t >= EXTRA_VICTORY_SUPPORT_SPAWN_T:
            begin_victory_lineup(play, width, height)
        _update_victory_support(play, player, victory_lineup=True)

        if t >= EXTRA_VICTORY_EXPLODE_FRAMES:
            play.set("extra_victory_phase", "lineup")
            play.set("extra_victory_timer", 0)
            begin_victory_lineup(play, width, height)
            play.set("boss_active", False)
            play.set("boss", None)
        return

    if phase == "lineup":
        _step_player_toward(play, player, EXTRA_VICTORY_PLAYER_LINEUP_SPEED)
        _sync_player_victory_pos(play, player)
        _update_victory_support(play, player, victory_lineup=True)
        player_done = _player_lineup_done(play, player)
        support_done = all_support_lineup_done(play)
        if (player_done and support_done) or t >= EXTRA_VICTORY_LINEUP_MAX_FRAMES:
            player.rect.centerx = int(play.extra_victory_target_x)
            player.rect.centery = int(play.extra_victory_target_y)
            _sync_player_victory_pos(play, player)
            play.set("extra_victory_timer", 0)
            from game_loop.extra_boss_tally import start_extra_boss_score_tally

            start_extra_boss_score_tally(play)
        return

    if phase == "tally":
        player.rect.centerx = int(play.extra_victory_target_x)
        player.rect.centery = int(play.extra_victory_target_y)
        _sync_player_victory_pos(play, player)
        _update_victory_support(play, player, victory_lineup=True)
        return

    if phase == "bubbles":
        if t == 1:
            bubble = g().get("_bubble")
            if bubble is not None:
                bubble.clear()
        player.rect.centerx = int(play.extra_victory_target_x)
        player.rect.centery = int(play.extra_victory_target_y)
        _sync_player_victory_pos(play, player)
        _update_victory_support(play, player, victory_lineup=True)
        step = play.extra_victory_dialogue_step
        wait = play.extra_victory_bubble_wait
        if wait > 0:
            play.set("extra_victory_bubble_wait", wait - 1)
        elif step < len(_VICTORY_DIALOGUE):
            kind, variant, msg_i = _VICTORY_DIALOGUE[step]
            if _show_victory_bubble(play, kind, variant, msg_i):
                play.set("extra_victory_dialogue_step", step + 1)
                play.set("extra_victory_bubble_wait", EXTRA_VICTORY_BUBBLE_GAP)
            else:
                play.set("extra_victory_dialogue_step", step + 1)
                play.set("extra_victory_bubble_wait", 0)
        else:
            play.set("extra_victory_speech_variant", -1)
            begin_victory_exit(play, width)
            play.set("extra_victory_phase", "depart")
            play.set("extra_victory_timer", 0)
            play.set("extra_victory_depart_stuck", 0)
        return

    if phase == "depart":
        _update_victory_support(play, player, victory_exit=True)
        _update_player_follow_support_exit(play, player, width, height)
        _sync_player_victory_pos(play, player)
        if _depart_sequence_done(play, player, width):
            from extra_stage_support import clear_extra_support

            clear_extra_support(play)
            play.set("extra_victory_phase", "post_exit_wait")
            play.set("extra_victory_timer", 0)
        return

    if phase == "post_exit_wait":
        t = play.extra_victory_timer
        if t >= EXTRA_VICTORY_POST_EXIT_WAIT_FRAMES:
            play.set("extra_victory_phase", "gallery")
            play.set("extra_victory_timer", 0)
            play.set("extra_ending_slide_index", 0)
        return

    if phase == "gallery":
        t = play.extra_victory_timer
        slide = int(getattr(play, "extra_ending_slide_index", 0) or 0)
        if slide == 0 and t == 1 and not play.extra_ending_bgm_started:
            from audio import BGM_ENDING, play_bgm

            play_bgm(BGM_ENDING)
            play.set("extra_ending_bgm_started", True)
        if t >= EXTRA_ENDING_SLIDE_FRAMES:
            slide += 1
            if slide >= EXTRA_ENDING_SLIDE_COUNT:
                play.set("extra_victory_phase", "fin_pre_wait")
                play.set("extra_victory_timer", 0)
                play.set(
                    "extra_ending_slide_index",
                    min(EXTRA_ENDING_SLIDE_COUNT - 1, len(g().get("extra_ending_slides") or []) - 1),
                )
                play.set("extra_fin_char_index", 0)
                play.set("extra_fin_char_progress", 0.0)
                return
            play.set("extra_ending_slide_index", slide)
            play.set("extra_victory_timer", 0)
        return

    if phase == "fin_pre_wait":
        if t >= EXTRA_FIN_PRE_WAIT_FRAMES:
            play.set("extra_victory_phase", "fin_draw")
            play.set("extra_victory_timer", 0)
            play.set("extra_fin_char_index", 0)
            play.set("extra_fin_char_progress", 0.0)
        return

    if phase == "fin_draw":
        char_idx = int(getattr(play, "extra_fin_char_index", 0) or 0)
        progress = min(1.0, t / float(EXTRA_FIN_CHAR_DRAW_FRAMES))
        play.set("extra_fin_char_progress", progress)
        if t >= EXTRA_FIN_CHAR_DRAW_FRAMES:
            char_idx += 1
            if char_idx >= len(EXTRA_FIN_TEXT):
                play.set("extra_victory_phase", "fin_post_wait")
                play.set("extra_victory_timer", 0)
                play.set("extra_fin_char_index", len(EXTRA_FIN_TEXT))
                play.set("extra_fin_char_progress", 1.0)
            else:
                play.set("extra_fin_char_index", char_idx)
                play.set("extra_victory_timer", 0)
                play.set("extra_fin_char_progress", 0.0)
        return

    if phase == "fin_post_wait":
        if t >= EXTRA_FIN_POST_WAIT_FRAMES:
            play.set("extra_victory_phase", "fade_out")
            play.set("extra_victory_timer", 0)
        return

    if phase == "fade_out":
        if t >= EXTRA_ENDING_FADE_FRAMES:
            _finish_extra_victory_to_difficulty(play)
        return


def try_extra_boss_defeat(play, boss) -> bool:
    if boss is None or boss.boss_type != 6:
        return False
    if play.extra_victory_active:
        return True
    if boss.hp > 0:
        return False
    boss.hp = 0
    from extra_boss import clear_extra_boss_combat_on_defeat

    clear_extra_boss_combat_on_defeat(play, boss)
    start_extra_boss_victory(play, boss)
    return True
