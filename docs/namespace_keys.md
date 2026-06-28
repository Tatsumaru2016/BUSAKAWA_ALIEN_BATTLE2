# RT.g() namespace キー一覧

`game_bootstrap.bootstrap(globals())` のあと `game_runtime.RT.bind(namespace)` により、サブモジュールは `RT.g()` で main と同じ dict を参照する。

機械可読なキー名リストはリポジトリ直下の [`namespace_catalog.py`](../namespace_catalog.py) にある。本ドキュメントは役割ごとの説明用。

## 初期化の流れ

1. `settings` — `WIDTH`, `HEIGHT`, `FPS` など
2. `install_screen_modes` — 画面モード定数（[`screen_modes.py`](../screen_modes.py)）
3. `install_game_constants` — `GAME_TITLE`, `SHOT_INTERVAL`, `EMS_MAX`
4. `install_config_ui` — `config_mgr`, `_c`, `KEY_BINDINGS`, `_config`, 設定画面項目
5. `install_assets` — 画像・フォント（[`assets_loader.load_all_assets`](../assets_loader.py)）
6. `install_sfx` — 効果音（[`audio.load_all_sfx`](../audio.py)）
7. `install_game_registry` — spawn / 描画ヘルパ（[`game_registry.py`](../game_registry.py)）
8. `AppState.install_to` — `app`, `_g`, `state`, `hi_score`, `diff`（`_g` 経由）
9. `refresh_input` — `_joystick`, `joy_*`
10. UI オブジェクト — `_bubble`, `splash_logo`, `title_cheat`, `player`, `PlayState.install_to`

## 画面モード（`screen_modes.py`）

| キー | 値 | 説明 |
|------|-----|------|
| `SPLASH` | -4 | 起動ロゴ |
| `NOTICE` | -1 | 注意画面 |
| `NEW_SCREEN` | -2 | 準備画面 1 |
| `NEW_SCREEN2` | -3 | 準備画面 2 |
| `TITLE` | 0 | タイトル |
| `PLAY` | 1 | プレイ中 |
| `GAMEOVER` | 2 | ゲームオーバー |
| `ENDING` | 3 | エンディング |
| `DIFFICULTY_SELECT` | 4 | 難易度選択 |
| `CONFIG` | 5 | キー/パッド設定 |
| `ENDING_EXTRA_PROMPT` | 6 | （予約）エクストラ前 |
| `EXTRA_PLAY` | 7 | （予約）エクストラプレイ |

実行時の現在モードは `state`（`AppState.set_screen_mode` で同期）。

## セッション・プレイ状態

| キー | 型 | 説明 |
|------|-----|------|
| `app` | `AppState` | 難易度カーソル・ハイスコア・画面遷移 |
| `_g` | `dict` | `app` 内の `diff` / `cursor`（難易度選択用） |
| `play` | `PlayState` | 1 プレイ分のリスト・ボス・スコア等 |
| `player` | `Player` | 自機インスタンス |
| `diff` | `DifficultyConfig` | 現在難易度（毎フレーム `app.diff` と同期） |
| `hi_score` | `int` | ハイスコア |
| `reset_game` | `callable` | プレイ再開 |

`PlayState.install_to` により、次の名前が **グローバルと `play` の両方** にミラーされる（`game_state.PLAY_STATE_FIELDS` 参照）:

`bullets`, `enemy_bullets`, `enemy_lasers`, `meteors`, `explosions`, `enemies`, `power_items`, `turrets`, `boss`, `boss_active`, `boss_warning`, `boss_warning_timer`, `boss_cycle`, `enemy_timer`, `turret_spawn_timer`, `score`, `boss_index`, `boss_shield_hp`, `boss_shield_grace_timer`, `kill_count`, `no_damage_since_boss`, `boss_fight_timer`, `boss_fight_active`, `player_dead`, `gameover_timer`, `player_explode_timer`, `ending_delay_timer`, `_ending_screen_sfx_played`, `_ending_sfx_timer`, `lives`, `revive_timer`, `_prev_lives`, `_shot_timer`, `ems_count`, `ems_flash_timer`, `_boss_special_alert_timer`, `boss_shield_max`, `_tally_last_line`, `far_x`, `mid_x`, `front_x`, `boss5_far_x`, `boss5_mid_x`, `boss5_front_x`, `boss5_bg_mode`, `score_chain`, `boss_score_tally`, `_boss_special_alert_ref`

## フレームローカル（プレイ専用）

| キー | 説明 |
|------|------|
| `_ticks` | `pygame.time.get_ticks()`（フレーム先頭で設定） |
| `_gameplay_paused` | ボス撃破スコア集計中はスポーン等を止める |

## 画像・フォント（`ASSET_IMAGE_AND_FONT_KEYS`）

`assets_loader.load_all_assets` が返すキー。代表例:

- 背景: `bg_far`, `bg_mid`, `bg_front`, `boss5_bg_*`
- UI: `title_img`, `warning_img`, `gameover_img`, `ending_img`, `diff_*`, `config_*_bg`
- 自機: `player_images`, `bullet_img`, `laser_img`, `shield_img`, `life_icon_img`
- 敵: `enemy_images`, `turret_*_img`, `enemy_bullet_img`, `homing_bullet_img`
- ボス: `midboss_img*`, `midboss4_body_img`, `midboss5_images`, `boss_shield_img*`, `boss_*_bullet*`, `boss3_ufo_img`, `boss2_fish_img`, `boss4_tentacle_tip_img`, `boss_ripple_base_img`, `meteor_img`
- パワーアップ: `power_weapon_img`, `power_shield_img`, `power_speed_img`, `power_1up_img`
- 支援機: `support_fighter_images`
- フォント: `font`, `font2`, `font_hud_sm`, `hud_font`, `hp_bar_font`, `big_font`, `noto_font_path`

色定数（`COLOR_KEYS`）: `WHITE`, `RED`, `GREEN`, `CYAN`, `YELLOW`, `ORANGE`, `DARK_ORANGE`, `BLUE`, `LIGHT_BLUE`, `GRAY`, `DARK_GRAY`, `BLACK`

## 効果音（`SFX_KEYS`）

| キー | 用途の目安 |
|------|------------|
| `shot_sound` | 自機射撃 |
| `explosion_sound` | 爆発全般 |
| `warning_sound` / `score_tick_sound` | ボス警告・集計 tick |
| `boss_shield_hit_sound` / `boss_shield_break_sound` | ボスシールド |
| `player_shield_hit_sound` / `player_shield_break_sound` | 自機シールド |
| `item_weapon_sound` / `item_shield_sound` / `item_speed_sound` | アイテム取得 |
| `ems_get_sound` / `ems_use_sound` | EMS |
| `launch_sound` | ゲーム開始 |
| `beam_sound` | ビーム系 |
| `laser_warning_sound` / `ripple_sound` / `boss_special_alert_sound` | ボス攻撃 |
| `boss5_gravity_sound` / `boss5_meteo3_sound` / `boss5_meteo1_sound` | ボス5 |
| `ending_screen_sound` | エンディング画面 |
| `support_arrive_sound` | 支援機 |
| `difficulty_select_sound` / `difficulty_confirm_sound` | 難易度 UI |
| `title_cheat_sound` | タイトルチート |

## 登録 callable（`REGISTRY_CALLABLE_KEYS`）

`spawn_enemy_bullet`, `spawn_enemy_laser`, `spawn_boss5_red_laser`, `spawn_boss5_ripple`, `spawn_boss5_meteor`, `enemy_bullet_hit_rect`, `update_enemy_bullets_frame`, `update_meteors_frame`, `draw_scroll`, `draw_text_with_shadow`, `key_label`, `pad_label`

## 入力・設定

| キー | 説明 |
|------|------|
| `config_mgr` | `ConfigManager` |
| `_c` | コントローラー軸/ボタン割当 dict |
| `KEY_BINDINGS` | キーボード割当 |
| `_config` | 設定画面 UI 状態 |
| `_joystick` | 接続中 `Joystick` または `None` |
| `joy_move_*`, `joy_shoot`, `joy_confirm`, `joy_ems` | 毎フレーム評価する入力ヘルパ |

## メニュー・コールバック

| キー | 説明 |
|------|------|
| `_bubble` | `BubbleMessage` |
| `splash_logo` | 起動ロゴ |
| `title_cheat` | タイトルチート |
| `_title_cheat_stick_prev` | スティックチート用前フレーム方向 |
| `_poll_title_cheat_stick` | タイトル用スティック処理 |
| `_title_cheat_dir_from_key` | キー→方向 |
| `_start_game_from_title` | タイトルから `reset_game` して PLAY へ |

## game_loop での参照グループ

[`game_loop/resources.py`](../game_loop/resources.py) が `RT.g()` からまとめて取り出す dataclass:

| 関数 | 内容 |
|------|------|
| `frame_core()` | `play`, `player`, `screen`, `diff`, `state`, `width`, `height` |
| `frame_core_with_app()` | 上記 + `app` |
| `ui_message()` | `_bubble` |
| `boss_combat_sfx()` / `boss_combat_images()` | ボス戦 SE・画像 |
| `battle_collision_sfx()` / `powerup_images()` | 弾衝突 SE・ドロップ画像 |
| `item_pickup_sfx()` | アイテム取得 SE |
| `player_input_bundle()` | 自機入力・射撃 SE・`joy_*` |
| `score_boss_bundle()` | 警告画像・警告/ tick SE |
| `spawn_images()` | 敵・タレット画像 |
| `hud_result_assets()` | GO/ED 画面用フォント・画像 |
| `title_flow_resources()` | タイトルチート・`launch_sound`・`joy_*` |

新しいフェーズを書くときは、まず上記のどれに当たるか決め、生の `g["explosion_sound"]` を増やさない。

## ディスプレイ・クロック

`screen`, `clock` — bootstrap で設定。

## 関連ドキュメント

- [エクストラステージ設計メモ](extra_stage_design.md)（未実装の `ENDING_EXTRA_PROMPT` / `EXTRA_PLAY`）
