# game_bootstrap.py — pygame 初期化と RT 用 namespace の構築

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from assets_loader import install_assets, load_all_assets, load_sound, set_window_icon
from audio import install_sfx, load_all_sfx
from config_manager import ConfigManager
from debug_flags import apply_play_debug_setup
from game_config_ui import install_config_ui
from game_constants import GAME_TITLE, install_game_constants
from game_input_device import init_joystick, refresh_input
from game_registry import install_game_registry
from game_runtime import RT
from game_state import AppState, PlayState, install_play_state
from hiscore import load_hiscore
from messages import BubbleMessage
from player import Player
from screen_modes import SPLASH, install_screen_modes
from splash_factory import create_splash
from title_cheat import TitleCheat

import render_ui
from assets_loader import get_asset_path
from game_layout import install_layout
from settings import FPS, PLAY_HEIGHT, PLAY_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH


@dataclass
class GameBootstrap:
    app: AppState
    play: PlayState
    player: Player
    config_mgr: ConfigManager
    clock: pygame.time.Clock
    screen: pygame.Surface


def bootstrap(namespace: dict) -> GameBootstrap:
    """main の globals() を初期化し、GameBootstrap を返す。"""
    install_layout(namespace)
    namespace.setdefault("FPS", FPS)

    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)
    clock = pygame.time.Clock()
    namespace["screen"] = screen
    namespace["clock"] = clock

    from platform_web import is_web

    if is_web():
        from web_loader import paint_boot_screen

        paint_boot_screen(screen, "Loading graphics (1-5 min first time)...", 12)

    install_screen_modes(namespace)
    install_game_constants(namespace)

    config_mgr = ConfigManager()
    install_config_ui(namespace, config_mgr)

    install_assets(namespace, load_all_assets(PLAY_WIDTH, PLAY_HEIGHT, boot_screen=screen if is_web() else None))

    if is_web():
        paint_boot_screen(screen, "効果音を読み込んでいます…", 78, font_path=namespace.get("noto_font_path"))

    set_window_icon()
    install_sfx(namespace, load_all_sfx(load_sound))

    if is_web():
        from web_loader import hide_html_loader, paint_boot_screen

        paint_boot_screen(screen, "起動準備中…", 100, font_path=namespace.get("noto_font_path"))
        hide_html_loader()

    render_ui.configure(
        namespace["font"],
        namespace["font2"],
        namespace["font_hud_sm"],
        namespace["hud_font"],
        namespace["hp_bar_font"],
        namespace["big_font"],
        namespace["life_icon_img"],
    )
    install_game_registry(namespace)

    app = AppState.create(SPLASH)
    app.hi_score = load_hiscore()
    app.install_to(namespace)

    joystick = init_joystick()
    refresh_input(namespace, joystick, namespace["_c"])

    namespace["_bubble"] = BubbleMessage()
    namespace["get_asset_path"] = get_asset_path
    namespace["splash_logo"] = create_splash(
        get_asset_path,
        PLAY_WIDTH,
        PLAY_HEIGHT,
        font_path=namespace["noto_font_path"],
        screen_w=SCREEN_WIDTH,
        screen_h=SCREEN_HEIGHT,
    )
    namespace["title_cheat"] = TitleCheat()
    namespace["_title_cheat_ctrl_prev"] = None

    player = Player(
        namespace["player_images"],
        namespace["bullet_img"],
        namespace["laser_img"],
        namespace["player_shield_bar_img"],
    )
    player.invincible_timer = 0
    namespace["player"] = player

    play = PlayState()
    install_play_state(namespace, play)

    def reset_game() -> None:
        play.reset(player, namespace["diff"], PLAY_HEIGHT)
        apply_play_debug_setup(play, namespace["diff"])
        play.install_to(namespace)
        if play.boss_warning:
            pygame.display.set_caption(
                f"{GAME_TITLE}  [DEBUG: BOSS{play.boss_cycle + 1}]"
            )
        else:
            pygame.display.set_caption(GAME_TITLE)

    namespace["reset_game"] = reset_game

    from game_loop.title_flow import (
        poll_title_cheat_controller,
        poll_title_cheat_stick,
        start_game_from_title,
        title_cheat_dir_from_key,
    )

    namespace["_poll_title_cheat_controller"] = poll_title_cheat_controller
    namespace["_poll_title_cheat_stick"] = poll_title_cheat_stick
    namespace["_title_cheat_dir_from_key"] = title_cheat_dir_from_key
    namespace["_start_game_from_title"] = lambda: start_game_from_title(reset_game)

    RT.bind(namespace)

    return GameBootstrap(
        app=app,
        play=play,
        player=player,
        config_mgr=config_mgr,
        clock=clock,
        screen=screen,
    )
