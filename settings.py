import math
import random
import sys

from game_layout import (
    HEIGHT,
    HUD_HEIGHT,
    PLAY_HEIGHT,
    PLAY_ORIGIN_X,
    PLAY_ORIGIN_Y,
    PLAY_TOP_MARGIN,
    PLAY_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WIDTH,
)

FPS = 60

# 起動スプラッシュ: "video"=MP4 / "logo"=従来アニメ（GGameSplash）
# Web (pygbag) では OpenCV 非対応のため logo 固定
SPLASH_MODE = "logo" if sys.platform == "emscripten" else "video"
SPLASH_VIDEO_FILE = "splash_intro.mp4"
SPLASH_VIDEO_POST_HOLD_SEC = 2.0  # 再生終了後、最終フレームを止めてから Notice へ

# ======================================
# ゲージ制（レーザー／スピード）
# ======================================
LASER_GAUGE_MAX = 100.0
LASER_GAUGE_DRAIN_PER_SHOT = 2.0  # 旧3.5: 連射で約6.7秒分（60fps・SHOT_INTERVAL=8）
LASER_GAUGE_REFILL_PER_WEAPON = 22.0
LASER_GAUGE_ON_UNLOCK = 35.0

SPEED_GAUGE_MAX = 100.0
SPEED_GAUGE_DRAIN_PER_FRAME_MOVING = 0.10  # 60fps想定: 移動し続けて約16秒（緩やか）
SPEED_GAUGE_REFILL_PER_ITEM = 40.0
SPEED_BOOST_SPEED = 2  # 速度上昇量（通常より緩め）

BOSS1_BASE_HP = 2600       # 2000の30%増
BOSS1_BASE_SHIELD = 650    # 500の30%増

# 自機周りブラケットHUD（明るめ）
BRACKET_LASER_FILL = (130, 245, 255)
BRACKET_LASER_TRACK = (72, 118, 150)
BRACKET_SPEED_FILL = (255, 215, 120)
BRACKET_SPEED_TRACK = (115, 88, 58)
BRACKET_SHIELD_TRACK = (88, 118, 155)

# 自機シールド（1.0 = 100%）。被弾で減少、0 で本体ダメージ
PLAYER_SHIELD_LOSS_GRUNT = 0.18
PLAYER_SHIELD_LOSS_BOSS = 0.34
PLAYER_SHIELD_LOSS_METEOR = 0.24
PLAYER_SHIELD_ITEM_FILL = 0.55

# 効果音の音量（mixer.set_volume、最大 1.0。numpy 不使用）
SFX_GAIN = 1.0
# BGM 音量（従来 0.25 より高め）
BGM_VOLUME = 0.45
# 射撃時: Normal⇔Shot の Shot 表示をキー離し後も少し維持
SHOT_VISUAL_HOLD_FRAMES = 6
SHOT_MUZZLE_FLASH_FRAMES = 5

# ボス5 BGM: HP割合での切替（攻撃フェーズの時間強制とは無関係）
# assets/ に配置する OGG ファイル名（高い→低いHP帯の順）
BOSS5_BGM_HP_LOW = 0.50       # この割合以下で hp50 曲へ
BOSS5_BGM_HP_CRITICAL = 0.25  # この割合以下で hp25 曲へ
BOSS5_BGM_HP_DYING = 0.10     # この割合以下で hp10 曲へ
BOSS5_BGM_TIER_ORDER = (1.0, BOSS5_BGM_HP_LOW, BOSS5_BGM_HP_CRITICAL, BOSS5_BGM_HP_DYING)
BOSS5_BGM_TRACKS = {
    1.0: "assets/bgm_boss5_hp100.ogg",                    # HP > 50%
    BOSS5_BGM_HP_LOW: "assets/bgm_boss5_hp50.ogg",        # HP ≤ 50%
    BOSS5_BGM_HP_CRITICAL: "assets/bgm_boss5_hp25.ogg",   # HP ≤ 25%
    BOSS5_BGM_HP_DYING: "assets/bgm_boss5_hp10.ogg",      # HP ≤ 10%
}
BOSS5_BGM_FALLBACK = "assets/bgm_boss5.ogg"  # 未配置時の旧BGM

# 自機表示（素材原寸 175×70。90% のうえさらに 15% 縮小 → 全体 76.5%）・マスク判定
_PLAYER_BASE_SCALE = 0.9
_PLAYER_EXTRA_SHRINK = 0.85
PLAYER_SPRITE_SCALE = _PLAYER_BASE_SCALE * _PLAYER_EXTRA_SHRINK
PLAYER_SPRITE_SIZE = (
    round(175 * PLAYER_SPRITE_SCALE),
    round(70 * PLAYER_SPRITE_SCALE),
)
# バリア: 自機シルエットからのオーラ描画（画像なし・PLAYER_SPRITE_SCALE 連動）
def _player_scaled_px(n: float) -> int:
    return max(1, round(n * PLAYER_SPRITE_SCALE))


PLAYER_SHIELD_OUTLINE_PX = _player_scaled_px(3)
PLAYER_SHIELD_AURA_GLOW = (
    (_player_scaled_px(12), 38),
    (_player_scaled_px(9), 58),
    (_player_scaled_px(6), 88),
    (_player_scaled_px(4), 130),
)
PLAYER_MASK_ALPHA_THRESHOLD = 200
# シールドなし時の当たり: 自機 rect 内のコックピット（右前方・円形）
PLAYER_COCKPIT_CENTER_U = 0.68
PLAYER_COCKPIT_CENTER_V = 0.50
PLAYER_COCKPIT_RADIUS_RATIO = 0.17
# パワーアイテム取得: コックピット（レチクル）＋余裕
ITEM_PICKUP_COCKPIT_RADIUS_SCALE = 1.35
ITEM_PICKUP_CENTER_GRAB_RADIUS = 26
# 敵・敵弾・隕石など（不透明ピクセルのみ当たり）
ENTITY_MASK_ALPHA_THRESHOLD = 160
# 自機スプライト: キー → assets 内ファイル名（全6種を読み込み）
PLAYER_SPRITE_FILES = {
    "normal": "player.png",
    "up": "player_up.png",
    "down": "player_down.png",
    "left": "player_left.png",
    "right": "player_right.png",
    "shot": "player_shot.png",
}
PLAYER_MAX_WEAPON_LEVEL = 5
BOSS_MID_BODY_HIT_INSET = 0.22
BOSS5_ENEMY_LASER_LENGTH = 60
BOSS5_LASER_SPEED_SCALE = 0.88
BOSS2_BASE_HP = 4250       # 5000の15%減
BOSS2_BASE_SHIELD = 850    # 1000の15%減
BOSS3_BASE_HP = 8500       # 10000の15%減
BOSS3_BASE_SHIELD = 1700   # 2000の15%減
BOSS4_BASE_HP = 9754       # 10838から10%減
BOSS4_BASE_SHIELD = 2550   # 3000の15%減
BOSS5_BASE_HP = 12000
# ボス5 HP: 武器Lv別（Lv5レーザーはLv4と同じ）
BOSS5_HP_WEAPON_MULT = {
    1: 1.00,
    2: 1.12,
    3: 1.30,
    4: 1.45,
    5: 1.45,
}
# ボス5のみ: レーザー弾ダメージ倍率（通常1→実効2）
BOSS5_LASER_DAMAGE_MUL = 2

# ボス戦サプライ（右端から出現）の間隔 [frames] — 出現率2倍 = 従来1050〜1350の半分
BOSS_SUPPLY_INTERVAL_MIN = 525
BOSS_SUPPLY_INTERVAL_MAX = 675

# ======================================
# 敵弾の最低速度・寿命設定
# スクロール速度より必ず大きい値にすること (スクロール5px/f)
# ======================================
ENEMY_BULLET_MIN_SPEED = 5.5   # 画面上で止まって見えないための最低合成速度（NIGHTMARE基準）
ENEMY_BULLET_MIN_SPEED_FLOOR = 2.8  # 難易度スケール後の雑魚弾下限の絶対最小
# ボス弾: boss_bullet_extra 適用後もこれ未満にしない（EASY で止まって見えるのを防ぐ）
BOSS_BULLET_SPEED_FLOOR = {
    "EASY": 2.2,
    "NORMAL": 2.6,
    "HARD": 3.0,
    "NIGHTMARE": 3.2,
}
ENEMY_BULLET_LIFE_FRAMES = 300  # 弾の最大寿命（フレーム数）。画面外に出ない弾もこれで消滅

# 雑魚・エース・特別機 — 表示サイズ (幅, 高さ) 固定（原寸一致時はスケールしない）
ENEMY_SPRITE_SIZE = (130, 87)
GRUNT_ENEMY_SPRITE_SIZE = ENEMY_SPRITE_SIZE
ENEMY_BULLET_SIZE = (24, 24)   # 雑魚弾（通常・ホーミング）
BOSS_BULLET_SIZE = (30, 30)    # ボス・タレット等の敵弾
ENEMY_GRUNT_COUNT = 8
ENEMY_GRUNT_TYPE_MAX = 7  # 雑魚 type インデックス上限（0始まり）
ENEMY_ACE_COUNT = 4
ENEMY_TYPE_ACE_FIRST = ENEMY_GRUNT_COUNT  # enemy_images[8]
ENEMY_TYPE_ACE_LAST = ENEMY_TYPE_ACE_FIRST + ENEMY_ACE_COUNT - 1  # [8..11]
ENEMY_TYPE_ACE = ENEMY_TYPE_ACE_FIRST  # 互換
ENEMY_SPECIAL_COUNT = 1
ENEMY_TYPE_SPECIAL = ENEMY_TYPE_ACE_LAST + 1  # enemy_images[12] ← enemy_special.png
ENEMY_TYPE_COUNT = ENEMY_GRUNT_COUNT  # 互換: 01〜08 をロード


def is_enemy_ace_type(enemy_type: int) -> bool:
    t = int(enemy_type)
    return ENEMY_TYPE_ACE_FIRST <= t <= ENEMY_TYPE_ACE_LAST


def is_enemy_special_type(enemy_type: int) -> bool:
    return int(enemy_type) == ENEMY_TYPE_SPECIAL


def pick_ace_enemy_type() -> int:
    return random.randint(ENEMY_TYPE_ACE_FIRST, ENEMY_TYPE_ACE_LAST)


# enemy_ace01〜04（type 8〜11）ごとの固定スタイル
ACE_STYLE_BY_TYPE = ("zigzag", "dash", "sine_spray", "bomber_run")
ACE_HP_BY_INDEX = (14, 15, 13, 16)  # 上記スタイルと同順


def ace_style_for_type(enemy_type: int) -> str:
    if not is_enemy_ace_type(enemy_type):
        return ACE_STYLE_BY_TYPE[0]
    idx = int(enemy_type) - ENEMY_TYPE_ACE_FIRST
    idx = max(0, min(len(ACE_STYLE_BY_TYPE) - 1, idx))
    return ACE_STYLE_BY_TYPE[idx]


ENEMY_SPAWN_OFFSCREEN_PAD = 200
ENEMY_MAX_ON_SCREEN = 11

# 雑魚ウェーブ密度（武器 Lv1=少なめ … Lv5=多め、Lv3=従来相当）
GRUNT_MAX_ON_SCREEN_BY_WEAPON = (8, 10, 12, 14, 16)
GRUNT_WAVE_COOLDOWN_MUL_BY_WEAPON = (1.12, 0.92, 0.75, 0.68, 0.60)
GRUNT_SPAWN_GAP_MUL_BY_WEAPON = (1.05, 0.88, 0.72, 0.65, 0.58)
GRUNT_FORMATION_COUNT_MUL_BY_WEAPON = (0.85, 1.00, 1.15, 1.22, 1.30)
GRUNT_ACE_WAVE_CHANCE_MUL_BY_WEAPON = (0.45, 0.72, 1.00, 1.00, 1.15)
GRUNT_SPECIAL_WAVE_CHANCE_MUL_BY_WEAPON = (0.35, 0.55, 0.85, 1.00, 1.10)
# 全体の出現ペース（小さいほどウェーブ間隔が短い）
GRUNT_SPAWN_RATE_MUL = 0.72


def grunt_spawn_tuning(weapon_level: int) -> dict:
    """武器レベル 1〜5 に対応した雑魚スポーン係数。"""
    idx = max(0, min(4, int(weapon_level) - 1))
    rate = float(GRUNT_SPAWN_RATE_MUL)
    return {
        "max_on_screen": int(GRUNT_MAX_ON_SCREEN_BY_WEAPON[idx] * 2.2),
        "cooldown_mul": GRUNT_WAVE_COOLDOWN_MUL_BY_WEAPON[idx] * rate,
        "gap_mul": GRUNT_SPAWN_GAP_MUL_BY_WEAPON[idx] * rate,
        "formation_mul": GRUNT_FORMATION_COUNT_MUL_BY_WEAPON[idx],
        "ace_chance_mul": GRUNT_ACE_WAVE_CHANCE_MUL_BY_WEAPON[idx],
        "special_chance_mul": GRUNT_SPECIAL_WAVE_CHANCE_MUL_BY_WEAPON[idx],
    }


# 無敵侵入後の「戦闘可能」目安（右端 inset）
ENEMY_SPAWN_EDGE_INSET = 56
# 無敵中の左進入速度（speed 倍率）
ENEMY_INVULN_ENTRY_SPEED_MUL = 3.0

# 右端出現の無敵（60fps: 90=1.5秒固定）— 侵入中は左へ移動のみ
ENEMY_INVULN_FRAMES_MIN = 90
ENEMY_INVULN_FRAMES_MAX = 90

# 雑魚: 無敵明けの装甲（先頭1ヒット無効＋残り時間は被弾可）
GRUNT_POST_INVULN_ARMOR_FRAMES = 20
GRUNT_POST_INVULN_RUSH_FRAMES = 95
GRUNT_POST_INVULN_RUSH_MUL = 1.85
# 雑魚: この X 比率より右では被弾しない（右端狩り防止）
GRUNT_DAMAGE_MAX_CENTER_X_RATIO = 0.86
# 自機武器 Lv3 以上で雑魚 HP +1
GRUNT_HP_BONUS_WEAPON_LEVEL = 3
# 雑魚の射撃間隔（1.0=従来、小さいほど撃ちやすい）
GRUNT_SHOOT_INTERVAL_MUL = 0.86
# 雑魚が撃つ弾は自機弾で消せない
GRUNT_BULLET_INDESTRUCTIBLE = True
# 雑魚弾の速度補正
GRUNT_BULLET_SPEED_MUL = 2.0
# 雑魚通常弾のスナイプ速度補正（体感で速い弾速）
GRUNT_SNIPE_SPEED_MUL = 1.85
# 雑魚弾の寿命（場外まで抜けやすく）
GRUNT_BULLET_LIFE_FRAMES = 520

# 砲台弾（30x30・緩いホーミング）
TURRET_BULLET_SIZE = (30, 30)
TURRET_BULLET_SPEED = 5.4

# 雑魚移動の滑らかさ（大きいほど素早く目標へ追従）
GRUNT_MOVE_Y_LERP = 0.13
# 雑魚エース: ジグザグ＋曲がり直前の高速スナイプ
GRUNT_ACE_SNIPE_SPEED_MUL = 1.48
GRUNT_ACE_ZIG_Y_SPEED_MUL = 2.05
GRUNT_ACE_ZIG_X_SPEED_MUL = 1.62
GRUNT_ACE_ZIG_SEG_MIN = 12
GRUNT_ACE_ZIG_SEG_MAX = 24
GRUNT_ACE_ZIG_PRE_SNIPE_FRAMES = 3
# エース04: 画面上部を高速通過しながらストライカー型爆弾（エクストラより多投下）
GRUNT_ACE_BOMBER_BOMB_COUNT = 8
GRUNT_ACE_BOMBER_SPEED_MUL = 2.45
GRUNT_ACE_BOMBER_BOMB_SPEED_Y = 8.6
GRUNT_ACE_EXIT_SPEED_MUL = 2.35
GRUNT_ACE_ZIG_DURATION = 480
GRUNT_ACE_PLAY_X_MIN_RATIO = 0.20
GRUNT_ACE_PLAY_X_MAX_INSET = 48

# 特別機: 弾回避＋ワープのみ（攻撃なし）。ワープ3回で右退場
GRUNT_SPECIAL_WARP_COUNT = 3
GRUNT_SPECIAL_WARP_FRAMES = 40
GRUNT_SPECIAL_DODGE_RADIUS = 150.0
GRUNT_SPECIAL_DODGE_STRENGTH = 0.62
GRUNT_SPECIAL_ACTIVE_WARP_CD_MIN = 48
GRUNT_SPECIAL_ACTIVE_WARP_CD_MAX = 72
# 特別機撃破: 自機5秒無敵＋ゲージ全快
PLAYER_SPECIAL_KILL_INVINCIBLE_FRAMES = 300

# 自機通常弾スプライトサイズ
PLAYER_BULLET_SIZE = (20, 8)

# 自機通常弾ダメージ（Lv3+ は扇形化とセットで 1、Lv1-2 は処理力確保で 2）
PLAYER_NORMAL_BULLET_DAMAGE = 1
PLAYER_NORMAL_BULLET_DAMAGE_EARLY = 2
PLAYER_NORMAL_BULLET_DAMAGE_EARLY_MAX_LEVEL = 2

# ======================================
# コントローラー設定
# ======================================
CONTROLLER = {
    "shoot":        0,   # ×/A ボタン → 発射
    "confirm":      0,   # 決定
    "cancel":       1,   # ×/B ボタン → キャンセル / ESC相当
    "ems":          3,   # △/Y ボタン → EMS発動
    "axis_x":       0,   # 左スティック X軸
    "axis_y":       1,   # 左スティック Y軸
    "dpad_x":       0,   # 十字キー X軸 (HAT)
    "dpad_y":       1,   # 十字キー Y軸 (HAT)
    "deadzone":     0.25,# スティックのデッドゾーン
}

WHITE = (255,255,255)
BLACK = (0,0,0)
RED = (255,0,0)
CYAN = (0,255,255)
YELLOW = (255,255,0)

# ======================================
# DIFFICULTY CONFIG
# ======================================
class DifficultyConfig:
    # EASY=体験用 / NORMAL=旧EASY / HARD=旧NORMAL / NIGHTMARE=旧HARD
    PRESETS = {
        "EASY": dict(
            boss_hp_scale      = 0.30,
            boss3_hp_mul       = 0.70,  # ボス3のみ追加30%減（EASY）
            boss4_hp_mul       = 0.80,  # ボス4のみ追加20%減（EASY）
            boss5_hp_mul       = 0.90,  # ボス5のみ追加10%減（EASY）
            boss_shield_scale  = 0.22,
            enemy_hp_scale     = 0.28,
            enemy_spd_scale    = 0.48,
            bullet_spd_scale   = 0.52,
            boss_bullet_spd_mul = 1.25,
            boss_fire_interval = 3.15,
            boss_easy_bullet_count_mul = 0.62,
            player_lives       = 7,
            shield_grace_f     = 300,
            turret_interval    = 620,
            enemy_interval     = 78,
            enemy_spawn_count  = 3,
            boss_kills         = [18, 38, 68, 105, 155],
            enemy_bullet_spd   = 2.4,
            enemy_fire_scale   = 3.35,
            enemy_pattern_plus = False,
            boss_bullet_extra  = 0.0,
            label_color        = (130, 255, 170),
            drop_1up_pct       = 14,
            drop_item_pct      = 58,
            score_scale        = 0.85,
            boss_hit_score     = 12,
            enemy_base_score   = 900,
            turret_score       = 4500,
            combo_base         = 2800,
            boss_kill_base     = 45000,
            boss_nodmg_base    = 55000,
            boss_speed_base    = 45000,
            lives_bonus_unit   = 9000,
            clear_bonus        = 180000,
        ),
        "NORMAL": dict(
            boss_hp_scale      = 0.45,
            boss3_hp_mul       = 0.80,  # ボス3のみ追加20%減（NORMAL）
            boss_shield_scale  = 0.35,
            enemy_hp_scale     = 0.4,
            enemy_spd_scale    = 0.60,
            bullet_spd_scale   = 0.65,
            boss_bullet_spd_mul = 1.35,
            boss_fire_interval = 2.20,
            player_lives       = 5,
            shield_grace_f     = 240,
            turret_interval    = 480,
            enemy_interval     = 56,
            enemy_spawn_count  = 4,
            boss_kills         = [75, 150, 270, 450, 660],
            enemy_bullet_spd   = 3,
            enemy_fire_scale   = 2.50,
            enemy_pattern_plus = False,
            enemy_pattern_normal = True,
            enemy_bullet_fast_mul = 1.30,
            enemy_bullet_mid_mul = 0.82,
            grunt_shoot_interval_mul = 0.80,
            boss_bullet_extra  = 0.0,
            label_color        = (100, 220, 100),
            drop_1up_pct       = 3,
            drop_item_pct      = 18,
            score_scale        = 1.0,
            boss_hit_score     = 15,
            enemy_base_score   = 1000,
            turret_score       = 5000,
            combo_base         = 3000,
            boss_kill_base     = 60000,
            boss_nodmg_base    = 80000,
            boss_speed_base    = 60000,
            lives_bonus_unit   = 10000,
            clear_bonus        = 300000,
        ),
        "HARD": dict(
            boss_hp_scale      = 0.80,
            boss_shield_scale  = 0.90,
            enemy_hp_scale     = 0.85,
            enemy_spd_scale    = 0.86,
            bullet_spd_scale   = 0.73,
            boss_fire_interval = 1.38,
            player_lives       = 4,
            shield_grace_f     = 228,
            turret_interval    = 280,
            enemy_interval     = 36,
            enemy_spawn_count  = 3,
            boss_kills         = [110, 250, 430, 650, 920],
            enemy_bullet_spd   = 5.6,
            grunt_bullet_spd_scale = 0.90,  # 雑魚弾のみ少し遅く
            enemy_fire_scale   = 1.38,
            enemy_pattern_plus = True,
            boss_bullet_extra  = 0.0,
            label_color        = (255, 255, 255),
            drop_1up_pct       = 5,
            drop_item_pct      = 26,
            score_scale        = 1.0,
            boss_hit_score     = 10,
            enemy_base_score   = 500,
            turret_score       = 3000,
            combo_base         = 1500,
            boss_kill_base     = 30000,
            boss_nodmg_base    = 40000,
            boss_speed_base    = 30000,
            lives_bonus_unit   = 5000,
            clear_bonus        = 150000,
        ),
        "NIGHTMARE": dict(
            boss_hp_scale      = 1.50,
            boss_shield_scale  = 1.50,
            enemy_hp_scale     = 1.5,
            enemy_spd_scale    = 1.10,
            bullet_spd_scale   = 1.00,
            boss_fire_interval = 0.80,
            player_lives       = 3,
            shield_grace_f     = 120,
            turret_interval    = 180,
            enemy_interval     = 24,
            enemy_spawn_count  = 2,
            boss_kills         = [160, 380, 640, 960, 1360],
            enemy_bullet_spd   = 6.5,
            grunt_bullet_spd_scale = 0.90,  # 雑魚弾のみ少し遅く
            enemy_fire_scale   = 1.20,
            enemy_pattern_plus = False,
            boss_bullet_extra  = 0.07,
            label_color        = (255, 180, 60),
            drop_1up_pct       = 6,
            drop_item_pct      = 34,
            score_scale        = 1.35,
            boss_hit_score     = 18,
            enemy_base_score   = 700,
            turret_score       = 4500,
            combo_base         = 1800,
            boss_kill_base     = 50000,
            boss_nodmg_base    = 70000,
            boss_speed_base    = 50000,
            lives_bonus_unit   = 8000,
            clear_bonus        = 250000,
        ),
    }
    ORDER = ["EASY", "NORMAL", "HARD", "NIGHTMARE"]

    def __init__(self, name="NORMAL"):
        self.name = name
        for k, v in self.PRESETS[name].items():
            setattr(self, k, v)

    def enemy_bullet_min_speed(self) -> float:
        """雑魚弾の合成速度下限（bullet_spd_scale 連動。EASY で一律5.5に張り付くのを防ぐ）。"""
        return max(
            ENEMY_BULLET_MIN_SPEED_FLOOR,
            ENEMY_BULLET_MIN_SPEED * self.bullet_spd_scale,
        )

    def boss_bullet_speed_floor(self) -> float:
        return float(BOSS_BULLET_SPEED_FLOOR.get(self.name, 2.6))

    def scale_boss_scalar_speed(self, speed: float) -> float:
        """b2_speed など vx/vy を持たないボス弾用の難易度スケール。"""
        spd = max(0.0, float(speed))
        if spd <= 0.0:
            return spd
        s = self.bullet_spd_scale
        if s != 1.0:
            spd *= s
        bmul = float(getattr(self, "boss_bullet_spd_mul", 1.0))
        if bmul != 1.0:
            spd *= bmul
        extra = getattr(self, "boss_bullet_extra", 0.0)
        if extra != 0.0:
            spd = max(self.boss_bullet_speed_floor(), spd + extra)
        return spd

    def scale_bullet(self, eb):
        s = self.bullet_spd_scale
        if s != 1.0:
            eb["vx"] = float(eb.get("vx", 0)) * s
            eb["vy"] = float(eb.get("vy", 0)) * s
        if eb.get("is_boss_bullet", False):
            bmul = float(getattr(self, "boss_bullet_spd_mul", 1.0))
            if bmul != 1.0:
                eb["vx"] = float(eb.get("vx", 0)) * bmul
                eb["vy"] = float(eb.get("vy", 0)) * bmul
        extra = getattr(self, "boss_bullet_extra", 0.0)
        if extra != 0.0 and eb.get("is_boss_bullet", False):
            vx = float(eb.get("vx", 0))
            vy = float(eb.get("vy", 0))
            spd = math.hypot(vx, vy)
            if spd > 0.1:
                floor = self.boss_bullet_speed_floor()
                new_spd = max(floor, spd + extra)
                scale = new_spd / spd
                eb["vx"] = vx * scale
                eb["vy"] = vy * scale
                if eb.get("force_leftward") and float(eb["vx"]) > -0.05:
                    eb["vx"] = -max(floor, abs(float(eb["vx"])))

    def fire_check(self, timer, base_interval):
        scaled = max(1, int(base_interval * self.boss_fire_interval))
        return (timer % scaled) == 0