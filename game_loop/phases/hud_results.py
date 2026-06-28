# game_loop/phases/hud_results.py — HUD・ゲームオーバー・エンディング・画面シェイク

import pygame

from audio import BGM_GAMEOVER, play_bgm, set_sfx_muted
from game_flow import should_mute_sfx
from assets_loader import CYAN, WHITE, YELLOW
from game_constants import GAME_TITLE
from game_loop.resources import frame_core_with_app, hud_result_assets
from game_runtime import RT
from game_layout import blit_full_window_image, boss_hp_bar_rect, boss_hp_gravity_rect
from render_ui import (
    draw_custom_hp_bar,
    draw_gravity_indicator,
    draw_text_with_shadow,
    draw_top_status_bar,
)
from score_system import (
    chain_multiplier_maxed,
    draw_chain_combo_callout,
    draw_chain_milestone_flash,
)
from render_ui import chain_hud_panel_rect
from screen_handlers.menus import TITLE_DIFF_MARGIN_RIGHT, TITLE_DIFF_MARGIN_TOP
from ending_extra_dive import draw_extra_dive_enter_prompt
from screen_handlers.ending_menu import draw_ending_extra_menu, draw_ending_stats
from extra_boss_victory import is_extra_ending_cinematic
from screen_modes import ENDING, ENDING_EXTRA_DIVE, EXTRA_PLAY, GAMEOVER, PLAY
from boss5_attack_patterns import get_gravity_screen_shake
from game_pause import draw_pause_overlay, is_gameplay_paused
from render_ui import key_label, pad_label


def run_hud_results_phase() -> None:
    g = RT.g()
    core = frame_core_with_app()
    play = core.play
    state = core.state
    set_sfx_muted(should_mute_sfx(play, state))
    app = core.app
    player = core.player
    play_screen = g["screen"]
    full_screen = g.get("full_screen", play_screen)
    diff = core.diff
    WIDTH = core.width
    HEIGHT = core.height
    SCREEN_W = g.get("SCREEN_WIDTH", WIDTH)
    SCREEN_H = g.get("SCREEN_HEIGHT", HEIGHT)
    hud = hud_result_assets()
    score = play.score
    hi_score = app.hi_score
    score_chain = play.score_chain
    boss_score_tally = play.boss_score_tally
    boss = play.boss
    boss_active = play.boss_active
    boss_shield_hp = play.boss_shield_hp
    boss_shield_max = play.boss_shield_max
    player_dead = play.player_dead
    lives = play.lives
    revive_timer = play.revive_timer
    gameover_timer = play.gameover_timer
    ems_flash_timer = play.ems_flash_timer
    _ending_sfx_timer = play._ending_sfx_timer
    _ending_screen_sfx_played = play._ending_screen_sfx_played

    font = hud.font
    font_hud_sm = hud.font_hud_sm
    big_font = hud.big_font
    gameover_img = hud.gameover_img
    ending_img = hud.ending_img
    ending_screen_sound = hud.ending_screen_sound
    title_cheat = hud.title_cheat
    paused = is_gameplay_paused(play)

    if ems_flash_timer > 0 and not paused:
        play.set("ems_flash_timer", ems_flash_timer - 1)
        alpha = int(180 * ems_flash_timer / 30)
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((0, 200, 255, alpha))
        play_screen.blit(flash, (0, 0))

    if state not in (ENDING, ENDING_EXTRA_DIVE):
        if state == EXTRA_PLAY:
            pygame.display.set_caption(f"{GAME_TITLE}  [EXTRA]")
        else:
            pygame.display.set_caption(f"{GAME_TITLE}  [{diff.name}]")
        score_mult = score_chain.multiplier()
        milestone = score_chain.pop_chain_milestone()
        if milestone is not None:
            g["chain_milestone_sound"].play()

        boss_bank = None
        boss_cap = 0
        if state == PLAY and boss_active and boss and score_chain.boss_hit_cap > 0:
            boss_bank = score_chain.boss_hit_bank
            boss_cap = score_chain.boss_hit_cap

        extra_gallery = is_extra_ending_cinematic(play)
        if g.get("_play_surface_active") and not boss_score_tally.active and not extra_gallery:
            draw_top_status_bar(
                full_screen,
                score,
                score_mult,
                lives,
                player.weapon_level,
                diff,
                float(getattr(player, "laser_gauge", 0.0)),
                float(getattr(player, "speed_gauge", 0.0)),
                score_chain.chain,
                score_chain.timer,
                score_mult,
                boss_bank=boss_bank,
                boss_cap=boss_cap,
            )

        if score_chain.chain_flash_timer > 0:
            draw_chain_milestone_flash(
                full_screen,
                score_chain.chain_flash_timer,
                chain_hud_panel_rect(boss_row=boss_cap > 0 and boss_bank is not None),
            )

        if (
            state in (PLAY, EXTRA_PLAY)
            and not boss_active
            and not boss_score_tally.active
            and not play.b5_death_active
        ):
            chain = score_chain.chain
            chain_callout_visible = chain > 0 and (
                not chain_multiplier_maxed(chain)
                or score_chain.chain_max_callout_timer > 0
            )
            if chain_callout_visible:
                draw_chain_combo_callout(
                    play_screen,
                    chain,
                    center=(WIDTH // 2, 72),
                    chain_pop_timer=score_chain.chain_pop_timer,
                    chain_flash_timer=score_chain.chain_flash_timer,
                    chain_max_callout_timer=score_chain.chain_max_callout_timer,
                    big_font=big_font,
                )

        if boss_score_tally.active:
            boss_score_tally.draw(full_screen, font, font_hud_sm, font, big_font)

    if (
        boss_active
        and boss
        and state not in (ENDING, ENDING_EXTRA_DIVE)
        and not boss_score_tally.active
        and not play.b5_death_active
    ):
        hp_r = boss_hp_bar_rect()
        if boss_shield_hp > 0 and boss_shield_max > 0:
            draw_custom_hp_bar(
                play_screen,
                hp_r.x,
                hp_r.y,
                hp_r.width,
                hp_r.height,
                boss_shield_hp,
                boss_shield_max,
                has_shield=True,
            )
        else:
            draw_custom_hp_bar(
                play_screen,
                hp_r.x,
                hp_r.y,
                hp_r.width,
                hp_r.height,
                boss.hp,
                boss.max_hp,
                has_shield=False,
            )
        if boss.boss_type == 5:
            from boss5_attack_patterns import get_gravity_hud_indicator

            grav_ind = get_gravity_hud_indicator(boss)
            if grav_ind is not None:
                gr = boss_hp_gravity_rect()
                draw_gravity_indicator(
                    play_screen,
                    gr.x,
                    gr.y,
                    gr.width,
                    gr.height,
                    grav_ind[0],
                    grav_ind[1],
                )

    if state in (PLAY, EXTRA_PLAY) and play.boss_warning:
        from boss_spawn import draw_boss_warning_overlay

        draw_boss_warning_overlay(play_screen, play, g.get("warning_img"))

    if (
        state in (PLAY, EXTRA_PLAY)
        and player_dead
        and lives <= 0
        and revive_timer == 0
        and not paused
    ):
        play.set("gameover_timer", gameover_timer - 1)
        if gameover_timer <= 0:
            play_bgm(BGM_GAMEOVER)
            title_cheat.reset_all()
            app.set_screen_mode(GAMEOVER)

    if state == GAMEOVER:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        full_screen.blit(overlay, (0, 0))
        full_screen.blit(
            gameover_img,
            gameover_img.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 10)),
        )
        diff_w = font.size(diff.name)[0]
        draw_text_with_shadow(
            full_screen, diff.name, font, diff.label_color,
            SCREEN_W - TITLE_DIFF_MARGIN_RIGHT - diff_w, TITLE_DIFF_MARGIN_TOP,
        )
        go_cy = SCREEN_H // 2 + 10
        if app.maybe_update_hiscore(score):
            draw_text_with_shadow(
                full_screen, "ハイスコア更新!", font, YELLOW,
                SCREEN_W // 2, go_cy + 150, is_center=True,
            )
        draw_text_with_shadow(
            full_screen, f"ハイスコア：{int(hi_score)}", font, CYAN,
            SCREEN_W // 2, go_cy + 188, is_center=True,
        )
        draw_text_with_shadow(
            full_screen, f"スコア：{int(score)}", big_font, YELLOW,
            SCREEN_W // 2, go_cy + 228, is_center=True,
        )
        draw_text_with_shadow(
            full_screen, "[タイトルに戻る]：ENTER / Button0", font, WHITE,
            SCREEN_W // 2, SCREEN_H - 44, is_center=True,
        )

    elif state == ENDING:
        if _ending_sfx_timer > 0:
            new_ending_sfx_timer = _ending_sfx_timer - 1
            play.set("_ending_sfx_timer", new_ending_sfx_timer)
            if new_ending_sfx_timer == 0 and not _ending_screen_sfx_played:
                ending_screen_sound.play()
                play.set("_ending_screen_sfx_played", True)
        sw, sh = SCREEN_W, SCREEN_H
        full_screen.fill((0, 0, 0))
        blit_full_window_image(full_screen, ending_img)
        hi_score_updated = app.maybe_update_hiscore(score)
        draw_ending_stats(
            full_screen,
            font,
            big_font,
            hi_score=app.hi_score,
            score=score,
            diff_name=diff.name,
            diff_color=diff.label_color,
            hi_score_updated=hi_score_updated,
        )
        draw_ending_extra_menu(
            full_screen,
            font,
            play.ending_menu_choice,
            sw,
            sh,
            extra_allowed=app.can_enter_extra_stage(diff.name),
        )

    elif state == ENDING_EXTRA_DIVE:
        from boss5_ending_flow import (
            draw_boss5_clear_epilogue,
            update_boss5_clear_epilogue,
        )
        from ending_extra_dive import draw_extra_dive_enter_prompt

        update_boss5_clear_epilogue(play, app)
        player_img = g["player_images"]["normal"]
        draw_boss5_clear_epilogue(
            play_screen,
            full_screen,
            play,
            player_img,
            font,
            font_hud_sm,
            font,
            big_font,
        )
        if (
            not getattr(play, "b5_clear_cinematic", False)
            and play.extra_dive_done
        ):
            draw_extra_dive_enter_prompt(full_screen, font, big_font, play)

    if (
        state == PLAY
        and boss_active
        and boss
        and boss.boss_type == 5
    ):
        gsx, gsy = get_gravity_screen_shake(boss)
        if gsx or gsy:
            shake_buf = play_screen.copy()
            play_screen.fill((10, 12, 20))
            play_screen.blit(shake_buf, (gsx, gsy))

    if paused and state in (PLAY, EXTRA_PLAY):
        kb = g.get("KEY_BINDINGS", {})
        pad = g.get("_c", {})
        pause_hint = f"[再開]：{key_label(kb.get('pause', 0))} / {pad_label(pad.get('pause', 7))}"
        draw_pause_overlay(full_screen, big_font)
        draw_text_with_shadow(
            full_screen,
            pause_hint,
            font,
            (190, 220, 255),
            SCREEN_W // 2,
            SCREEN_H // 2 + 48,
            is_center=True,
        )
