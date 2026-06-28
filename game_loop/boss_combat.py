# game_loop/boss_combat.py — ボス戦更新・描画・攻撃

from __future__ import annotations

import math

import pygame

from audio import reset_boss5_hp_bgm
from boss5_attack_patterns import (
    get_gravity_boss_purple_flash_alpha,
    is_b5_rush_active,
    run_boss5_attacks,
)
from boss5_support import clear_boss5_support
from boss5_update import (
    blit_boss5,
    boss5_body_image,
    b5_rush_aura_intensity,
    draw_b5_rush_red_aura,
    get_b5_rush_charge_shake,
    spawn_boss5_meteor_custom,
    sync_boss5_body_sprite,
)
from boss_attacks import (
    draw_boss1,
    draw_boss3,
    draw_boss4,
    player_hits_boss4_screen_overlays,
    draw_boss_special_fx,
    sync_boss1_body_sprite,
    sync_boss3_body_sprite,
    draw_boss2,
    sync_boss2_body_sprite,
    update_boss2_charge_movement,
    update_boss_attacks,
    update_boss_sin_movement,
)
from combat import apply_player_hit, player_hits_boss_body
from explosion import Explosion
from game_loop.boss5_rush import update_boss5_rush
from boss5_death import (
    B5_VICTORY_FRAMES,
    draw_boss5_death,
    finish_boss5_death_sequence,
    start_boss5_death,
    update_boss5_death,
)
from game_loop.boss_tally import advance_boss_slot_after_defeat, start_boss_score_tally
from game_loop.resources import frame_core_with_app
from enemy_bullets import (
    spawn_boss5_red_laser,
    spawn_boss5_ripple,
    spawn_enemy_bullet,
)
from game_loop.resources import (
    boss_combat_images,
    boss_combat_sfx,
    frame_core,
    ui_message,
)
from game_runtime import RT
from meteors import spawn_boss5_meteor
from screen_modes import ENDING, EXTRA_PLAY
from settings import WHITE


def run_boss_combat_phase() -> None:
    core = frame_core()
    if core.state == EXTRA_PLAY:
        return
    play = core.play
    player = core.player
    screen = core.screen
    diff = core.diff
    state = core.state
    WIDTH = core.width
    HEIGHT = core.height
    imgs = boss_combat_images()
    sfx = boss_combat_sfx()
    bubble = ui_message().bubble
    player_dead = play.player_dead
    boss = play.boss
    boss_active = play.boss_active
    boss_fight_active = play.boss_fight_active
    boss_fight_timer = play.boss_fight_timer
    boss_shield_hp = play.boss_shield_hp
    boss_shield_grace_timer = play.boss_shield_grace_timer
    boss_score_tally = play.boss_score_tally
    _boss_special_alert_timer = play._boss_special_alert_timer

    # ボス1〜4: 撃破後の派手な爆発演出（1秒）— boss クリア後も進行
    if int(getattr(play, "_boss_defeat_fx_type", 0)) in (1, 2, 3, 4):
        fx_timer = int(getattr(play, "_boss_defeat_fx_timer", 0))
        fx_rect = getattr(play, "_boss_defeat_fx_rect", None)
        if fx_timer > 0 and fx_rect is not None:
            # 連続爆発を重ねて派手さを出す
            burst_n = 3 if fx_timer > 30 else 2
            for _ in range(burst_n):
                play.explosions.append(
                    Explosion(
                        int(fx_rect.centerx + math.sin((60 - fx_timer) * 0.6) * 24 + (pygame.time.get_ticks() % 37) - 18),
                        int(fx_rect.centery + (pygame.time.get_ticks() % 29) - 14),
                        big=True,
                    )
                )
            if fx_timer % 8 == 0:
                explosion_sound = sfx.explosion_sound
                explosion_sound.play()
            # 追加SE: 演出中は汎用演出音を重ね、シールド被弾音とは混同させない
            if fx_timer % 16 == 0:
                try:
                    launch = RT.g().get("launch_sound")
                    if launch is not None:
                        launch.play()
                except Exception:
                    pass
            play.set("_boss_defeat_fx_timer", fx_timer - 1)
            return
        if fx_timer <= 0 and fx_rect is not None:
            # 1sec経過後にタリーへ遷移
            class _BossRef:
                pass

            boss_ref = _BossRef()
            boss_ref.boss_type = int(getattr(play, "_boss_defeat_fx_type", 1))
            boss_ref.rect = fx_rect.copy()
            play.set("_boss_defeat_fx_type", 0)
            play.set("_boss_defeat_fx_rect", None)
            clear_boss5_support()
            reset_boss5_hp_bgm()
            start_boss_score_tally(boss_ref)
            return

    if not boss_active or not boss:
        return

    if play.b5_death_active:
        draw_boss5_death(screen, play)
        if update_boss5_death(play):
            core_app = frame_core_with_app()
            finish_boss5_death_sequence(core_app.play, core_app.app)
        return

    if (
        play.boss_score_tally.active
        or play.ending_delay_timer > 0
        or state == ENDING
    ):
        return

    bullets = play.bullets
    enemy_bullets = play.enemy_bullets
    enemy_lasers = play.enemy_lasers
    meteors = play.meteors
    explosions = play.explosions
    midboss5_images = imgs.midboss5_images
    boss_shield_img = imgs.boss_shield_img
    boss_shield_img2 = imgs.boss_shield_img2
    _bubble = bubble
    _boss_special_alert_ref = play._boss_special_alert_ref
    explosion_sound = sfx.explosion_sound
    laser_warning_sound = sfx.laser_warning_sound
    ripple_sound = sfx.ripple_sound
    boss_special_alert_sound = sfx.boss_special_alert_sound
    boss5_gravity_sound = sfx.boss5_gravity_sound
    boss5_meteo3_sound = sfx.boss5_meteo3_sound
    if boss.boss_type == 2:
        update_boss2_charge_movement(boss)

    if boss.boss_type == 1:
        sync_boss1_body_sprite(boss)

    if boss.boss_type == 2:
        sync_boss2_body_sprite(boss)

    if boss.boss_type == 3:
        sync_boss3_body_sprite(boss)

    if boss.boss_type == 5:
        sync_boss5_body_sprite(boss, midboss5_images)

    if boss.boss_type == 5 and boss.hp > 0:
        update_boss5_rush(boss, player, player_dead, WIDTH, HEIGHT)

    b2_charge_active = (
        boss.boss_type == 2
        and getattr(boss, "b2_charge_state", "idle") in ("charge", "wait", "return")
    )
    b5_rush_active = boss.boss_type == 5 and is_b5_rush_active(boss)
    if not b2_charge_active and not b5_rush_active:
        boss.update()

    if boss_fight_active:
        play.set("boss_fight_timer", boss_fight_timer + 1)
        boss_fight_timer = play.boss_fight_timer

    update_boss_sin_movement(boss, b2_charge_active)

    is_low_hp = False
    is_critical_hp = False
    is_dying_hp = False

    if state != ENDING:
        if diff.name == "EASY":
            force_low_f, force_crit_f = 600, 1200
        elif diff.name == "NORMAL":
            force_low_f, force_crit_f = 960, 1980
        elif diff.name == "HARD":
            force_low_f, force_crit_f = 1200, 2400
        else:  # NIGHTMARE
            force_low_f, force_crit_f = 1200, 2400
        phase_force_low = boss_fight_timer >= force_low_f
        phase_force_critical = boss_fight_timer >= force_crit_f
        is_low_hp = (boss.hp <= boss.max_hp * 0.5) or phase_force_low
        is_critical_hp = (boss.hp <= boss.max_hp * 0.25) or phase_force_critical
        is_dying_hp = boss.hp <= boss.max_hp * 0.10

        if boss.boss_type == 4:
            draw_boss4(boss)
        elif boss.boss_type == 5:
            flash_t = int(getattr(boss, "b5_rush_flash_timer", 0))
            rush_red = flash_t > 0 or is_b5_rush_active(boss)
            shake = get_b5_rush_charge_shake(boss) if flash_t > 0 else (0, 0)
            b5_img = boss5_body_image(boss, midboss5_images)
            if rush_red:
                b5_img = midboss5_images.get("normal", b5_img)
            b5_draw_rect, b5_draw_surf = blit_boss5(
                screen,
                boss,
                b5_img,
                shake_xy=shake,
            )
            aura_i = b5_rush_aura_intensity(boss)
            if aura_i > 0:
                draw_b5_rush_red_aura(
                    screen,
                    b5_draw_surf,
                    b5_draw_rect,
                    intensity=aura_i,
                    boss=boss,
                )
            if not rush_red:
                grav_purple_a = get_gravity_boss_purple_flash_alpha(boss)
                if grav_purple_a > 0:
                    gp_flash = pygame.Surface(
                        (b5_draw_rect.width, b5_draw_rect.height), pygame.SRCALPHA
                    )
                    gp_flash.fill((55, 0, 95, grav_purple_a))
                    screen.blit(gp_flash, b5_draw_rect.topleft)
        elif boss.boss_type == 1:
            draw_boss1(screen, boss)
        elif boss.boss_type == 2:
            draw_boss2(screen, boss)
        elif boss.boss_type == 3:
            draw_boss3(screen, boss)
        else:
            boss.draw(screen)

        draw_boss_special_fx(boss, is_low_hp)

        if (
            boss.boss_type == 5
            and not is_b5_rush_active(boss)
            and getattr(boss, "b5_phase", 1) != 3
        ):
            b5_cp2 = getattr(boss, "b5_charge_phase", 0)
            b5_pt2 = getattr(boss, "b5_phase_timer", 0)
            if b5_cp2 == 1:
                prog2 = min(1.0, b5_pt2 / 60.0)
                pulse2 = int(20 + prog2 * 40 + math.sin(pygame.time.get_ticks() * 0.18) * 8)
                b5_fx = boss.rect.left + 20
                b5_fy = boss.rect.centery
                pygame.draw.circle(screen, (60, 20, 200), (b5_fx, b5_fy), pulse2 + 12, 3)
                pygame.draw.circle(screen, (180, 60, 255), (b5_fx, b5_fy), pulse2 + 4, 3)
                pygame.draw.circle(screen, WHITE, (b5_fx, b5_fy), max(4, pulse2 // 3))

        if boss_shield_hp > 0:
            if boss.boss_type > 3:
                screen.blit(boss_shield_img2, (boss.rect.left - 30, 0))
            else:
                screen.blit(boss_shield_img, (boss.rect.left - 30, boss.rect.top))

    if state != ENDING and boss.hp > 0:
        boss.shot_timer += 1

        if not hasattr(boss, "_grace_init"):
            boss._grace_init = True

        play.set("boss_shield_grace_timer", max(0, boss_shield_grace_timer - 1))
        boss_shield_grace_timer = play.boss_shield_grace_timer
        if boss_shield_grace_timer > 0:
            if boss_shield_grace_timer % 10 < 5:
                need_h = max(1, int(boss.rect.height))
                flash = getattr(play, "_boss_grace_flash", None)
                if (
                    flash is None
                    or flash.get_width() != 60
                    or flash.get_height() != need_h
                ):
                    flash = pygame.Surface((60, need_h), pygame.SRCALPHA)
                    flash.fill((255, 255, 100, 60))
                    play._boss_grace_flash = flash
                screen.blit(flash, (boss.rect.left - 30, boss.rect.top))
            grace_skip = True
        else:
            grace_skip = False

        update_boss_attacks(
            boss,
            grace_skip=grace_skip,
            is_low_hp=is_low_hp,
            is_critical_hp=is_critical_hp,
        )

        if boss.boss_type == 4:
            from boss_attacks.common import flush_boss4_tentacle_message_ui

            flush_boss4_tentacle_message_ui(play, screen, player, _bubble)

        if boss.boss_type == 5 and boss.hp > 0 and not grace_skip:
            b5_fire_x = boss.rect.left + 20
            b5_fire_y = boss.rect.centery
            _boss_special_alert_ref[0] = _boss_special_alert_timer
            run_boss5_attacks(
                boss, screen, player, player_dead,
                diff, meteors, enemy_bullets, enemy_lasers,
                explosions, b5_fire_x, b5_fire_y,
                is_low_hp, is_critical_hp, is_dying_hp,
                _bubble, _boss_special_alert_ref,
                laser_warning_sound, ripple_sound, boss_special_alert_sound,
                spawn_enemy_bullet, spawn_boss5_red_laser, spawn_boss5_ripple,
                spawn_boss5_meteor, spawn_boss5_meteor_custom,
                apply_player_hit,
                WIDTH, HEIGHT,
            )
            play.set("_boss_special_alert_timer", _boss_special_alert_ref[0])

            grav_now = getattr(boss, "b5_gravity_state", "idle")
            if grav_now == "active" and getattr(boss, "_sfx_prev_gravity", None) != "active":
                boss5_gravity_sound.play()
            boss._sfx_prev_gravity = grav_now

            rush_now = getattr(boss, "b5_rush_state", "idle")
            if rush_now == "charge" and getattr(boss, "_sfx_prev_rush", None) != "charge":
                boss5_meteo3_sound.play()
            boss._sfx_prev_rush = rush_now

    if boss.hp <= 0 and not boss_score_tally.active and not play.b5_death_active:
        bullets.clear()
        enemy_bullets.clear()
        enemy_lasers.clear()
        meteors.clear()
        if boss.boss_type == 5:
            if play.b5_victory_timer < 0:
                play.set("b5_victory_timer", B5_VICTORY_FRAMES)
                explosion_sound.play()
                _bubble.show("boss_kill_5")
            elif play.b5_victory_timer > 0:
                play.set("b5_victory_timer", play.b5_victory_timer - 1)
            else:
                start_boss5_death(play, boss, midboss5_images, diff)
        else:
            # ボス1〜4は即タリーに入らず、爆発演出→1秒待ちで継続
            if boss.boss_type in (1, 2, 3, 4):
                play.set("_boss_defeat_fx_type", int(boss.boss_type))
                play.set("_boss_defeat_fx_timer", 60)  # 1sec
                play.set("_boss_defeat_fx_rect", boss.rect.copy())
                advance_boss_slot_after_defeat(play)
                play.set("boss_active", False)
                play.set("boss", None)
                explosion_sound.play()
                # 開始SE: 破壊感を重ねる（シールド系音は使わない）
                try:
                    ripple = RT.g().get("ripple_sound")
                    if ripple is not None:
                        ripple.play()
                except Exception:
                    pass
            else:
                clear_boss5_support()
                reset_boss5_hp_bgm()
                explosion_sound.play()
                advance_boss_slot_after_defeat(play)
                start_boss_score_tally(boss)
    elif not player_dead and player.invincible_timer == 0:
        # ボス5突進の当たりは charge 中の update_boss5_rush のみ（復帰テレポで経路判定が走るのを防ぐ）
        if not (boss.boss_type == 5 and is_b5_rush_active(boss)):
            hit_boss = player_hits_boss_body(player, boss)
            if boss.boss_type == 4 and not hit_boss:
                hit_boss = player_hits_boss4_screen_overlays(player, boss)
            if hit_boss:
                apply_player_hit(hit_kind="boss")
