import pygame

from audio import BGM_TITLE, play_bgm, set_sfx_muted, stop_bgm
from debug_flags import (
    boss_type_from_key,
    clear_boss_skip_queue,
    extra_skip_from_key,
    queue_boss_skip,
    queue_extra_skip,
)
from explosion import Explosion
from game_config_ui import CONFIG_KEY_ITEMS, CONFIG_PAD_ITEMS
from game_input_device import refresh_input
from game_runtime import RT
from ending_extra_dive import go_to_difficulty_select, start_ending_extra_dive
from extra_boss import ems_clear_extra_vulcan_bullets
from game_pause import handle_play_pause_event
from player_fire_mode import toggle_fire_mode
from extra_stage import begin_extra_stage
from screen_modes import (
    CONFIG,
    DIFFICULTY_SELECT,
    ENDING,
    ENDING_EXTRA_DIVE,
    GAMEOVER,
    NEW_SCREEN,
    NEW_SCREEN2,
    NOTICE,
    EXTRA_PLAY,
    PLAY,
    SPLASH,
    TITLE,
)


def handle_event(event: pygame.event.Event) -> None:
    g = RT.g()
    state = g["state"]
    app = g["app"]
    play = g["play"]
    player = g["player"]
    _c = g["_c"]
    _config = g["_config"]
    config_mgr = g["config_mgr"]
    KEY_BINDINGS = g["KEY_BINDINGS"]
    title_cheat = g["title_cheat"]
    difficulty_select_sound = g["difficulty_select_sound"]
    difficulty_confirm_sound = g["difficulty_confirm_sound"]
    ems_use_sound = g["ems_use_sound"]
    _bubble = g["_bubble"]
    diff = app.diff

    if state == SPLASH:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            g["splash_logo"].stop_audio()
            app.set_screen_mode(NOTICE)
    elif state == NOTICE:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            app.set_screen_mode(NEW_SCREEN)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            app.set_screen_mode(NEW_SCREEN)
    elif state == NEW_SCREEN:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            app.set_screen_mode(NEW_SCREEN2)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            app.set_screen_mode(NEW_SCREEN2)
    elif state == NEW_SCREEN2:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            app.set_screen_mode(DIFFICULTY_SELECT)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            app.set_screen_mode(DIFFICULTY_SELECT)
    elif state == DIFFICULTY_SELECT:
        def _confirm_difficulty_if_unlocked() -> bool:
            if app.is_selected_difficulty_unlocked():
                difficulty_confirm_sound.play()
                play_bgm(BGM_TITLE)
                title_cheat.reset_sequence()
                app.set_screen_mode(TITLE)
                return True
            difficulty_select_sound.play()
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                app.nudge_difficulty_cursor(-1)
                difficulty_select_sound.play()
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                app.nudge_difficulty_cursor(1)
                difficulty_select_sound.play()
            elif event.key == pygame.K_RETURN:
                _confirm_difficulty_if_unlocked()
        elif event.type == pygame.JOYAXISMOTION:
            _axis_val = event.value
            _is_nav_axis = event.axis == _c["axis_x"] or event.axis == _c["axis_y"]
            if _is_nav_axis:
                if _axis_val < -_c["deadzone"]:
                    app.nudge_difficulty_cursor(-1)
                    difficulty_select_sound.play()
                elif _axis_val > _c["deadzone"]:
                    app.nudge_difficulty_cursor(1)
                    difficulty_select_sound.play()
        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value[0], event.value[1]
            _nav = hx if hx != 0 else (-hy if hy != 0 else 0)
            if _nav < 0:
                app.nudge_difficulty_cursor(-1)
                difficulty_select_sound.play()
            elif _nav > 0:
                app.nudge_difficulty_cursor(1)
                difficulty_select_sound.play()
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            _confirm_difficulty_if_unlocked()
    elif state == TITLE:
        if event.type == pygame.KEYDOWN:
            _cheat_dir = g["_title_cheat_dir_from_key"](event.key)
            if _cheat_dir is not None:
                if title_cheat.feed(_cheat_dir):
                    g["title_cheat_sound"].play()
            elif event.key == pygame.K_RETURN:
                clear_boss_skip_queue()
                g["_start_game_from_title"]()
            elif extra_skip_from_key(event.key):
                clear_boss_skip_queue()
                queue_extra_skip()
                g["_start_game_from_title"]()
            else:
                _skip_boss = boss_type_from_key(event.key)
                if _skip_boss is not None:
                    queue_boss_skip(_skip_boss)
                    g["_start_game_from_title"]()
                elif event.key == pygame.K_c:
                    stop_bgm()
                    title_cheat.reset_sequence()
                    app.set_screen_mode(CONFIG)
                elif event.key == pygame.K_ESCAPE:
                    stop_bgm()
                    title_cheat.reset_sequence()
                    app.set_screen_mode(DIFFICULTY_SELECT)
        elif event.type == pygame.KEYUP:
            _cheat_dir = g["_title_cheat_dir_from_key"](event.key)
            if _cheat_dir is not None:
                title_cheat.release_direction()
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            clear_boss_skip_queue()
            g["_start_game_from_title"]()
        elif event.type == pygame.JOYBUTTONDOWN and event.button == 2:
            stop_bgm()
            title_cheat.reset_sequence()
            app.set_screen_mode(CONFIG)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["cancel"]:
            stop_bgm()
            title_cheat.reset_sequence()
            app.set_screen_mode(DIFFICULTY_SELECT)
        elif event.type == pygame.JOYHATMOTION:
            from title_cheat import cardinal_from_bools

            hx, hy = int(event.value[0]), int(event.value[1])
            cur = cardinal_from_bools(hy > 0, hy < 0, hx < 0, hx > 0)
            prev = g.get("_title_cheat_ctrl_prev")
            if cur != prev:
                if cur is not None and title_cheat.feed(cur):
                    g["title_cheat_sound"].play()
                elif cur is None:
                    title_cheat.release_direction()
                g["_title_cheat_ctrl_prev"] = cur
    elif state == CONFIG:
        items = CONFIG_KEY_ITEMS if _config["mode"] == "keyboard" else CONFIG_PAD_ITEMS
        if _config["waiting"] is not None:
            if _config["mode"] == "keyboard":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        _config["waiting"] = None
                    else:
                        config_mgr.set_key_binding(_config["waiting"], event.key)
                        KEY_BINDINGS[_config["waiting"]] = event.key
                        _config["waiting"] = None
            else:
                if event.type == pygame.JOYBUTTONDOWN:
                    config_mgr.set_controller_button(_config["waiting"], event.button)
                    _c[_config["waiting"]] = event.button
                    from game_input import install_input_to_namespace

                    install_input_to_namespace(g, g.get("_joystick"), _c)
                    _config["waiting"] = None
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    _config["waiting"] = None
        else:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_bgm(BGM_TITLE)
                    title_cheat.reset_sequence()
                    app.set_screen_mode(TITLE)
                elif event.key == pygame.K_TAB:
                    _config["mode"] = "controller" if _config["mode"] == "keyboard" else "keyboard"
                    _config["cursor"] = 0
                elif event.key == pygame.K_r:
                    config_mgr.reset_to_default()
                    g["_c"] = config_mgr.get_controller()
                    g["KEY_BINDINGS"] = config_mgr.get_all_key_bindings()
                    refresh_input(g, g.get("_joystick"), g["_c"])
                    _config["cursor"] = 0
                elif event.key in (pygame.K_UP, pygame.K_w):
                    _config["cursor"] = (_config["cursor"] - 1) % len(items)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    _config["cursor"] = (_config["cursor"] + 1) % len(items)
                elif event.key == pygame.K_RETURN:
                    _config["waiting"] = items[_config["cursor"]][0]
            elif event.type == pygame.JOYHATMOTION:
                hy = event.value[1]
                if hy > 0:
                    _config["cursor"] = (_config["cursor"] - 1) % len(items)
                elif hy < 0:
                    _config["cursor"] = (_config["cursor"] + 1) % len(items)
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == _c.get("cancel", 1):
                    play_bgm(BGM_TITLE)
                    title_cheat.reset_sequence()
                    app.set_screen_mode(TITLE)
                elif event.button == _c.get("confirm", 0):
                    _config["waiting"] = items[_config["cursor"]][0]

    elif state == PLAY:
        if handle_play_pause_event(event, g):
            return
        _weapon_mode_key = KEY_BINDINGS.get("weapon_mode")
        _weapon_mode_btn = _c.get("weapon_mode", 2)
        if (
            not play.player_dead
            and not play.game_paused
            and play.ending_delay_timer == 0
            and not play.boss_score_tally.active
            and not play.b5_death_active
        ):
            if (
                event.type == pygame.KEYDOWN
                and _weapon_mode_key is not None
                and event.key == _weapon_mode_key
            ):
                toggle_fire_mode(player, _bubble)
            elif (
                event.type == pygame.JOYBUTTONDOWN
                and event.button == _weapon_mode_btn
            ):
                toggle_fire_mode(player, _bubble)
        _ems_triggered = False
        if event.type == pygame.KEYDOWN and event.key == KEY_BINDINGS["ems"]:
            _ems_triggered = True
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c.get("ems", 3):
            _ems_triggered = True
        if (
            _ems_triggered
            and not play.player_dead
            and not play.game_paused
            and play.ending_delay_timer == 0
            and not play.boss_score_tally.active
            and not play.b5_death_active
        ):
            if play.ems_count > 0:
                play.set("ems_count", play.ems_count - 1)
                play.set("ems_flash_timer", 30)
                ems_use_sound.play()
                _bubble.show("ems_use")
                for _e in play.enemies[:]:
                    play.explosions.append(
                        Explosion(_e.rect.centerx, _e.rect.centery, big=False)
                    )
                    play.add_score(play.score_chain.score_ems_kill(diff))
                    play.add_kill()
                play.enemies.clear()
                play.enemy_bullets.clear()
                play.enemy_lasers.clear()
                play.meteors[:] = [m for m in play.meteors if m.get("b5_shield")]
            else:
                _bubble.show("ems_empty")

    elif state == EXTRA_PLAY:
        if handle_play_pause_event(event, g):
            return
        _weapon_mode_key = KEY_BINDINGS.get("weapon_mode")
        _weapon_mode_btn = _c.get("weapon_mode", 2)
        if (
            not play.player_dead
            and not play.game_paused
            and not play.boss_score_tally.active
            and not getattr(play, "extra_victory_active", False)
        ):
            if event.type == pygame.KEYDOWN and _weapon_mode_key is not None and event.key == _weapon_mode_key:
                toggle_fire_mode(player, _bubble)
            elif event.type == pygame.JOYBUTTONDOWN and event.button == _weapon_mode_btn:
                toggle_fire_mode(player, _bubble)
        _ems_triggered = False
        if event.type == pygame.KEYDOWN and event.key == KEY_BINDINGS["ems"]:
            _ems_triggered = True
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c.get("ems", 3):
            _ems_triggered = True
        if (
            _ems_triggered
            and not play.player_dead
            and not play.game_paused
            and not play.boss_score_tally.active
            and not getattr(play, "extra_victory_active", False)
        ):
            if play.ems_count > 0:
                cleared = ems_clear_extra_vulcan_bullets(play, diff)
                if cleared > 0:
                    play.set("ems_count", play.ems_count - 1)
                    play.set("ems_flash_timer", 30)
                    ems_use_sound.play()
                    _bubble.show("ems_use")
            else:
                _bubble.show("ems_empty")

    elif state == GAMEOVER:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            go_to_difficulty_select(app, play, title_cheat)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            go_to_difficulty_select(app, play, title_cheat)

    elif state == ENDING:
        extra_ok = app.can_enter_extra_stage(diff.name)

        def _ending_confirm() -> None:
            if extra_ok and play.ending_menu_choice == 0:
                start_ending_extra_dive(play, app)
            else:
                go_to_difficulty_select(app, play, title_cheat)

        if event.type == pygame.KEYDOWN:
            if extra_ok and event.key in (pygame.K_UP, pygame.K_w):
                play.set("ending_menu_choice", 0)
                difficulty_select_sound.play()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                play.set("ending_menu_choice", 1)
                difficulty_select_sound.play()
            elif event.key == pygame.K_RETURN:
                _ending_confirm()
            elif event.key == pygame.K_ESCAPE:
                go_to_difficulty_select(app, play, title_cheat)
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == _c["confirm"]:
                _ending_confirm()
            elif event.button == _c.get("cancel", 1):
                go_to_difficulty_select(app, play, title_cheat)
        elif event.type == pygame.JOYHATMOTION:
            _hy = event.value[1]
            if extra_ok and _hy > 0:
                play.set("ending_menu_choice", 0)
                difficulty_select_sound.play()
            elif _hy < 0:
                play.set("ending_menu_choice", 1)
                difficulty_select_sound.play()

    elif state == ENDING_EXTRA_DIVE:
        if play.boss_score_tally.active and play.boss_score_tally.require_enter:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                play.boss_score_tally.confirm_enter()
            elif (
                event.type == pygame.JOYBUTTONDOWN
                and event.button == _c.get("confirm", 0)
            ):
                play.boss_score_tally.confirm_enter()
            return
        if getattr(play, "b5_clear_cinematic", False):
            return
        if not play.extra_dive_done:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            begin_extra_stage(play, app)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == _c["confirm"]:
            begin_extra_stage(play, app)
