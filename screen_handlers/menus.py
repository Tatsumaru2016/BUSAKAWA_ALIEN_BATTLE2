import pygame

from game_layout import blit_full_window_image, play_rect
from screen_handlers.background import update_title_background
from game_progress import is_nightmare_unlocked
from settings import DifficultyConfig
from game_config_ui import CONFIG_KEY_ITEMS, CONFIG_PAD_ITEMS
from debug_flags import DEBUG_BOSS_SKIP, DEBUG_EXTRA_SKIP
from game_runtime import RT
from render_ui import draw_text_with_shadow, key_label, pad_label
from screen_modes import CONFIG, DIFFICULTY_SELECT, TITLE

# タイトル UI 余白
TITLE_DIFF_MARGIN_RIGHT = 24
TITLE_DIFF_MARGIN_TOP = 12
TITLE_HI_SCORE_MARGIN_TOP = 24
# diff_select_bg 上の「難易度選択」タイトル直下（濃い帯内）
DIFF_SELECT_UNLOCK_HINT_Y_RATIO = 0.155
DIFF_SELECT_UNLOCK_HINT_GAP = 22


def _draw_title_difficulty(screen, diff, font) -> None:
    label = diff.name
    text_w = font.size(label)[0]
    x = screen.get_width() - TITLE_DIFF_MARGIN_RIGHT - text_w
    y = TITLE_DIFF_MARGIN_TOP
    draw_text_with_shadow(screen, label, font, diff.label_color, x, y)


def draw_menu_screen() -> bool:
    """難易度選択 / タイトル / コンフィグ。continue すべきなら True。"""
    g = RT.g()
    state = g["state"]
    screen = g["screen"]
    app = g["app"]
    diff = app.diff
    WIDTH = g.get("SCREEN_WIDTH", g["WIDTH"])
    HEIGHT = g.get("SCREEN_HEIGHT", g["HEIGHT"])
    _g = g["_g"]
    hi_score = app.hi_score

    if state == DIFFICULTY_SELECT:
        if g["diff_select_bg"]:
            blit_full_window_image(screen, g["diff_select_bg"])
        else:
            screen.fill((0, 0, 0))

        order = DifficultyConfig.ORDER
        diff_imgs = g["diff_imgs"]
        progress = app.progress
        nightmare_unlocked = is_nightmare_unlocked(progress)
        _has_any_img = any(diff_imgs.get(n, {}).get("on") for n in order)

        # 解放条件メッセージを「3行分」下に寄せる（フォントの行サイズ基準）
        _unlock_line_h = (
            g["font"].get_linesize()
            if hasattr(g["font"], "get_linesize")
            else g["font"].get_height()
        )
        unlock_hint_y = (
            int(HEIGHT * DIFF_SELECT_UNLOCK_HINT_Y_RATIO)
            + DIFF_SELECT_UNLOCK_HINT_GAP
            + _unlock_line_h * 2
        )

        if _has_any_img:
            if not nightmare_unlocked:
                draw_text_with_shadow(
                    screen,
                    "NIGHTMARE: HARDクリアで解放",
                    g["font"],
                    (200, 120, 120),
                    WIDTH // 2,
                    unlock_hint_y,
                    is_center=True,
                )
            _total_items = len(order)
            _gap = 16
            _widths = []
            for name in order:
                _img_tmp = diff_imgs.get(name, {}).get("on") or diff_imgs.get(name, {}).get("off")
                _widths.append(_img_tmp.get_width() if _img_tmp else 0)
            _block_w = sum(_widths) + _gap * (_total_items - 1)
            _left_x = (WIDTH - _block_w) // 2
            _cursor_x = _left_x
            for i, name in enumerate(order):
                is_sel = i == _g["cursor"]
                locked = name == "NIGHTMARE" and not nightmare_unlocked
                _img = diff_imgs.get(name, {}).get("on" if is_sel else "off")
                if _img is None:
                    _img = diff_imgs.get(name, {}).get("off" if is_sel else "on")
                if _img is None:
                    _cursor_x += _widths[i] + _gap
                    continue
                _rect = _img.get_rect(centery=HEIGHT // 2 - 15, x=_cursor_x)
                if locked:
                    dim = _img.copy()
                    dim.set_alpha(110)
                    screen.blit(dim, _rect)
                else:
                    screen.blit(_img, _rect)
                if locked:
                    lock = g["font"].render("LOCK", True, (220, 80, 80))
                    screen.blit(
                        lock,
                        lock.get_rect(midtop=(_rect.centerx, _rect.bottom + 4)),
                    )
                _cursor_x += _img.get_width() + _gap
        else:
            descs = {
                "EASY": "体験用。弾幕・敵を大きく弱体化。",
                "NORMAL": "やさしめ。初めてのクリア向け。",
                "HARD": "標準的なチャレンジ。",
                "NIGHTMARE": "高難度。HARDクリアで選択可能。",
            }
            title_y = int(HEIGHT * DIFF_SELECT_UNLOCK_HINT_Y_RATIO)
            draw_text_with_shadow(
                screen, "難易度選択", g["big_font"], g["CYAN"],
                WIDTH // 2, title_y, is_center=True,
            )
            if not nightmare_unlocked:
                draw_text_with_shadow(
                    screen,
                    "NIGHTMARE: HARDクリアで解放",
                    g["font"],
                    (200, 120, 120),
                    WIDTH // 2,
                    title_y
                    + g["big_font"].get_height()
                    + DIFF_SELECT_UNLOCK_HINT_GAP
                    + _unlock_line_h * 2,
                    is_center=True,
                )
            for i, name in enumerate(order):
                preset = DifficultyConfig(name)
                y = HEIGHT // 2 - 60 + i * 72
                is_sel = i == _g["cursor"]
                locked = name == "NIGHTMARE" and not nightmare_unlocked
                bg_alpha = 180 if is_sel else 60
                bg_surf = pygame.Surface((560, 58), pygame.SRCALPHA)
                bg_surf.fill((40, 40, 60, bg_alpha))
                screen.blit(bg_surf, bg_surf.get_rect(center=(WIDTH // 2, y + 28)))
                col = preset.label_color
                if locked:
                    col = tuple(c // 2 for c in col)
                prefix = "> " if is_sel else "  "
                label = prefix + name + ("  [LOCK]" if locked else "")
                draw_text_with_shadow(
                    screen, label, g["big_font"], col, WIDTH // 2 - 220, y + 10,
                )
                draw_text_with_shadow(
                    screen, descs[name], g["font"],
                    (200, 200, 200) if not is_sel else g["WHITE"],
                    WIDTH // 2 + 30, y + 14,
                )

        draw_text_with_shadow(
            screen,
            "[難易度選択]：←→↑↓/ スティック←→↑↓  [決定]：ENTER / Button0",
            g["font"], (160, 160, 160), WIDTH // 2, HEIGHT - 70, is_center=True,
        )
        pygame.display.flip()
        return True

    if state == TITLE:
        update_title_background()
        if g["title_img"]:
            blit_full_window_image(screen, g["title_img"])
        _draw_title_difficulty(screen, diff, g["font"])
        pr = play_rect()
        title_enter_y = pr.bottom - 132
        if hi_score > 0:
            draw_text_with_shadow(
                screen, f"ハイスコア : {int(hi_score)}", g["font"], g["CYAN"],
                WIDTH // 2, TITLE_HI_SCORE_MARGIN_TOP, is_center=True,
            )
        if (pygame.time.get_ticks() // 480) % 2 == 0:
            draw_text_with_shadow(
                screen, "PRESS ENTER", g["big_font"], g["YELLOW"],
                pr.centerx, title_enter_y, is_center=True,
            )
        draw_text_with_shadow(
            screen, "ゲームパッド: Button0", g["font"], (210, 210, 210),
            pr.centerx, title_enter_y + 50, is_center=True,
        )
        draw_text_with_shadow(
            screen,
            "[キーボード・コントローラーコンフィグ] C / Button2",
            g["font2"], (175, 195, 220), pr.centerx, HEIGHT - 58, is_center=True,
        )
        draw_text_with_shadow(
            screen,
            "[難易度選択へ戻る] ESC / Button1",
            g["font2"], (140, 140, 140), pr.centerx, HEIGHT - 34, is_center=True,
        )
        if DEBUG_BOSS_SKIP or DEBUG_EXTRA_SKIP:
            hints = []
            if DEBUG_BOSS_SKIP:
                hints.append("[DEBUG] F8〜F12: ボス1〜5直撃")
            if DEBUG_EXTRA_SKIP:
                hints.append("F6: エクストラ直撃")
            draw_text_with_shadow(
                screen,
                "  ".join(hints),
                g["font2"],
                (255, 200, 120),
                pr.centerx,
                HEIGHT - 82,
                is_center=True,
            )
        pygame.display.flip()
        return True

    if state == CONFIG:
        _config = g["_config"]
        mode = _config["mode"]
        items = CONFIG_KEY_ITEMS if mode == "keyboard" else CONFIG_PAD_ITEMS
        bg = g["config_keyboard_bg"] if mode == "keyboard" else g["config_controller_bg"]
        if bg:
            blit_full_window_image(screen, bg)
        else:
            screen.fill((10, 12, 20))
        title = "キーボード" if mode == "keyboard" else "コントローラー/ゲームパッド"
        draw_text_with_shadow(screen, title, g["big_font"], g["CYAN"], WIDTH // 2, 90, is_center=True)
        if _config["waiting"] is not None:
            draw_text_with_shadow(
                screen, "入力待ち...", g["font"], g["YELLOW"], WIDTH // 2, 195, is_center=True,
            )

        start_y = 250
        KEY_BINDINGS = g["KEY_BINDINGS"]
        _c = g["_c"]
        for i, (key, label) in enumerate(items):
            y = start_y + i * 58
            selected = i == _config["cursor"]
            col = g["YELLOW"] if selected else g["WHITE"]
            prefix = "> " if selected else "  "
            value = key_label(KEY_BINDINGS[key]) if mode == "keyboard" else pad_label(_c[key])
            draw_text_with_shadow(screen, prefix + label, g["font"], col, WIDTH // 2 - 250, y)
            draw_text_with_shadow(screen, value, g["font"], col, WIDTH // 2 + 120, y)
        draw_text_with_shadow(
            screen,
            "[変更対象選択]：↑↓←→  [決定]：ENTER/Button0  "
            "[キーボード/コントローラー切り替え]：TAB  [タイトルへ戻る]：ESC/Button1",
            g["font2"], g["WHITE"], WIDTH // 2, HEIGHT - 88, is_center=True,
        )
        draw_text_with_shadow(
            screen,
            "変更したいキー/ボタンを選び、ENTER または Button0 で選択後に割り当てたいキー/ボタンを押してください",
            g["font2"], (190, 220, 255), WIDTH // 2, HEIGHT - 48, is_center=True,
        )
        pygame.display.flip()
        return True

    return False
