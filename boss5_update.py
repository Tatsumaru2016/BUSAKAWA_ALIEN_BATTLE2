# boss5_update.py
# ボス5新攻撃パターン実装用モジュール

import math
import random
import pygame

from settings import (
    BOSS5_BGM_HP_DYING,
    BOSS5_BGM_HP_CRITICAL,
    BOSS5_BGM_HP_LOW,
    BOSS5_BGM_TRACKS,
    BOSS5_BGM_FALLBACK,
    BOSS5_BGM_TIER_ORDER,
    BOSS5_BASE_HP,
    BOSS5_HP_WEAPON_MULT,
    PLAYER_MAX_WEAPON_LEVEL,
)

# 突進時: 見た目・当たり判定を通常の60%（40%小さく）
B5_RUSH_SCALE = 0.6
B5_RUSH_CHARGE_FLASH_FRAMES = 26
# 回転キャッシュ刻み（度）— 毎フレーム smoothscale+rotate しない
B5_RUSH_SPIN_QUANT_DEG = 15

# サイン移動の基準点（突進後もこの周りを移動）
B5_SIN_ANCHOR_X = 1050
B5_SIN_ANCHOR_Y = 320
B5_SIN_AMP_X = 80
B5_SIN_AMP_Y = 120
B5_SIN_FREQ_X = 0.012
B5_SIN_FREQ_Y = 0.018


def get_b5_sin_position(boss):
    """現在の move_timer に応じたサイン移動位置。"""
    ax = getattr(boss, "b5_sin_anchor_x", B5_SIN_ANCHOR_X)
    ay = getattr(boss, "b5_sin_anchor_y", B5_SIN_ANCHOR_Y)
    mt = getattr(boss, "move_timer", 0)
    cx = ax + int(math.sin(mt * B5_SIN_FREQ_X) * B5_SIN_AMP_X)
    cy = ay + int(math.sin(mt * B5_SIN_FREQ_Y) * B5_SIN_AMP_Y)
    return cx, cy


def apply_b5_sin_position(boss):
    boss.rect.center = get_b5_sin_position(boss)


def b5_quant_spin(spin: float) -> int:
    q = int(round(spin / B5_RUSH_SPIN_QUANT_DEG) * B5_RUSH_SPIN_QUANT_DEG) % 360
    return q


def b5_begin_rush_scale(boss, image: pygame.Surface | None = None):
    """突進開始: ボス rect を40%縮小（中心維持）。"""
    if getattr(boss, "b5_rush_scaled", False):
        if image is not None:
            b5_prepare_rush_render_cache(boss, image)
        return
    boss.b5_rush_full_w = boss.rect.width
    boss.b5_rush_full_h = boss.rect.height
    cx, cy = boss.rect.centerx, boss.rect.centery
    boss.rect.width = max(8, int(boss.b5_rush_full_w * B5_RUSH_SCALE))
    boss.rect.height = max(8, int(boss.b5_rush_full_h * B5_RUSH_SCALE))
    boss.rect.center = (cx, cy)
    boss.b5_rush_scaled = True
    b5_clear_rush_surface_cache(boss)
    if image is not None:
        b5_prepare_rush_render_cache(boss, image)


def b5_end_rush_scale(boss):
    """突進終了: 通常サイズに戻す。"""
    if not getattr(boss, "b5_rush_scaled", False):
        return
    cx, cy = boss.rect.centerx, boss.rect.centery
    boss.rect.width = boss.b5_rush_full_w
    boss.rect.height = boss.b5_rush_full_h
    boss.rect.center = (cx, cy)
    boss.b5_rush_scaled = False
    b5_clear_rush_surface_cache(boss)


def _b5_rush_scaled_base_surface(boss, image: pygame.Surface) -> pygame.Surface:
    """縮小済みベース（突進中は1回だけ scale）。"""
    sw = max(1, int(image.get_width() * B5_RUSH_SCALE))
    sh = max(1, int(image.get_height() * B5_RUSH_SCALE))
    key = (id(image), sw, sh)
    cached = getattr(boss, "_b5_rush_scaled_base", None)
    if cached and cached[0] == key:
        return cached[1]
    scaled = pygame.transform.scale(image, (sw, sh))
    boss._b5_rush_scaled_base = (key, scaled)
    return scaled


def b5_prepare_rush_render_cache(boss, image: pygame.Surface) -> None:
    """突進開始時: 縮小ベース＋赤オーラを先に作る（戦闘中のマスク生成を避ける）。"""
    scaled = _b5_rush_scaled_base_surface(boss, image)
    outline, glow = _b5_rush_aura_spec(image)
    from player_status_ui import _aura_surface_for_image

    aura, _pad = _aura_surface_for_image(
        scaled, B5_RUSH_AURA_COLOR, outline_px=outline, glow_layers=glow
    )
    boss._b5_rush_aura_base = aura
    boss._b5_rush_aura_rot_cache = None


def b5_rush_draw_surface(boss, image, *, center=None):
    """突進スプライトと描画先 rect（当たり判定・描画で共通）。"""
    if not getattr(boss, "b5_rush_scaled", False):
        dest = boss.rect.copy()
        return image, dest
    scaled = _b5_rush_scaled_base_surface(boss, image)
    spin = float(getattr(boss, "b5_rush_spin_angle", 0.0))
    qspin = b5_quant_spin(spin)
    cache_key = (id(image), qspin)
    cached = getattr(boss, "_b5_rush_surf_cache", None)
    if cached and cached[0] == cache_key:
        surf = cached[1]
    else:
        surf = pygame.transform.rotate(scaled, qspin) if qspin else scaled
        boss._b5_rush_surf_cache = (cache_key, surf)
    cx, cy = center if center is not None else boss.rect.center
    dest = surf.get_rect(center=(int(cx), int(cy)))
    return surf, dest


def b5_clear_rush_surface_cache(boss) -> None:
    boss._b5_rush_surf_cache = None
    boss._b5_rush_scaled_base = None
    boss._b5_rush_aura_base = None
    boss._b5_rush_aura_rot_cache = None


def is_b5_rush_active(boss) -> bool:
    return getattr(boss, "b5_rush_state", "idle") in ("charge", "wait", "return")


def boss5_special_visual_active(boss) -> bool:
    """突進以外の特殊攻撃中（midboss5b 表示）。"""
    if is_b5_rush_active(boss):
        return False
    if int(getattr(boss, "b5_rush_flash_timer", 0)) > 0:
        return False
    if getattr(boss, "b5_phase", 1) == 3:
        # Phase3大技は突進のみ。紫チャージ用の special スプライトは使わない
        pass
    elif getattr(boss, "b5_charge_phase", 0) >= 1:
        return True
    if getattr(boss, "b5_gravity_state", "idle") in ("warning", "active"):
        return True
    if getattr(boss, "b5_selfdestruct_state", "idle") in ("warning", "burst"):
        return True
    return False


def boss5_body_image(boss, images: dict):
    if boss5_special_visual_active(boss):
        return images.get("special", images.get("normal"))
    return images.get("normal", boss.image)


def sync_boss5_body_sprite(boss, images: dict) -> None:
    if boss.boss_type != 5:
        return
    if getattr(boss, "b5_rush_scaled", False):
        target = images.get("normal", boss.image)
    else:
        target = boss5_body_image(boss, images)
    if boss.image is target:
        return
    center = boss.rect.center
    boss.image = target
    boss.rect = boss.image.get_rect(center=center)


def get_b5_rush_charge_shake(boss) -> tuple[int, int]:
    """突進開始の予兆中: ボス全体を震わせるオフセット。"""
    ft = int(getattr(boss, "b5_rush_flash_timer", 0))
    if ft <= 0:
        return (0, 0)
    max_f = max(1, B5_RUSH_CHARGE_FLASH_FRAMES)
    t = max_f - ft
    amp = 2 + int(7 * (t + 1) / max_f)
    ox = ((t * 73 + ft * 19) % (amp * 2 + 1)) - amp
    oy = ((t * 59 + ft * 23) % (amp * 2 + 1)) - amp
    return ox, oy


B5_RUSH_AURA_COLOR = (235, 58, 48)
# オーラの帯の厚み・外側の広がり（1.0=初期の outline / glow 半径相当）
B5_RUSH_AURA_THICKNESS_SCALE = 0.72


def _b5_rush_aura_spec(image: pygame.Surface) -> tuple[int, tuple[tuple[int, int], ...]]:
    m = max(1, max(image.get_width(), image.get_height()))
    o = max(5, min(18, m // 14))
    s = B5_RUSH_AURA_THICKNESS_SCALE
    outline = max(3, round(o * s))
    glow = (
        (max(outline + 1, round(o * 3 * s)), 58),
        (max(outline + 1, round((o + 2) * s)), 115),
    )
    return outline, glow


def _b5_rush_aura_for_draw(boss) -> pygame.Surface | None:
    aura = getattr(boss, "_b5_rush_aura_base", None)
    if aura is None:
        return None
    if not getattr(boss, "b5_rush_scaled", False):
        return aura
    qspin = b5_quant_spin(float(getattr(boss, "b5_rush_spin_angle", 0.0)))
    if not qspin:
        return aura
    rot_cache = getattr(boss, "_b5_rush_aura_rot_cache", None)
    if rot_cache and rot_cache[0] == qspin:
        return rot_cache[1]
    rotated = pygame.transform.rotate(aura, qspin)
    boss._b5_rush_aura_rot_cache = (qspin, rotated)
    return rotated


def draw_b5_rush_red_aura(
    screen: pygame.Surface,
    image: pygame.Surface,
    draw_rect: pygame.Rect,
    *,
    intensity: float = 1.0,
    boss=None,
) -> None:
    """突進: 自機シールド同型の赤オーラ＋縁取り（可能なら事前生成を回転 blit）。"""
    if boss is not None:
        aura = _b5_rush_aura_for_draw(boss)
        if aura is not None:
            dest = aura.get_rect(center=draw_rect.center)
            alpha = int(255 * max(0.0, min(1.0, intensity)))
            if alpha > 0:
                layer = aura.copy()
                layer.set_alpha(alpha)
                screen.blit(layer, dest)
            return
    from player_status_ui import draw_sprite_aura

    outline, glow = _b5_rush_aura_spec(image)
    draw_sprite_aura(
        screen,
        image,
        draw_rect,
        B5_RUSH_AURA_COLOR,
        intensity=intensity,
        outline_px=outline,
        glow_layers=glow,
    )


def b5_rush_aura_intensity(boss) -> float:
    """突進予兆・突進中の赤オーラ強度 (0=なし)。"""
    flash_t = int(getattr(boss, "b5_rush_flash_timer", 0))
    if flash_t > 0:
        max_f = max(1, B5_RUSH_CHARGE_FLASH_FRAMES)
        pulse = 0.5 + 0.5 * math.sin((max_f - flash_t) * 0.85)
        return 0.72 + 0.28 * pulse
    if not is_b5_rush_active(boss):
        return 0.0
    rs = getattr(boss, "b5_rush_state", "idle")
    if rs == "charge":
        return 0.82
    if rs == "wait":
        return 0.55
    if rs == "return":
        return 0.4
    return 0.0


def blit_boss5(screen, boss, image, *, shake_xy: tuple[int, int] | None = None):
    """突進中は縮小＋回転描画、通常時は rect にそのまま blit。"""
    sx, sy = shake_xy or (0, 0)
    if getattr(boss, "b5_rush_scaled", False):
        surf, dest = b5_rush_draw_surface(boss, image)
        if sx or sy:
            dest = dest.move(sx, sy)
        screen.blit(surf, dest)
        return dest, surf
    dest = boss.rect.move(sx, sy)
    screen.blit(image, dest)
    return dest, image


def spawn_boss5_meteor_custom(
    meteors,
    center_x,
    center_y,
    angle,
    speed,
    *,
    small=False,
    passes_b5_shield=False,
):
    """Boss5用: カスタム角度・速度で隕石を生成。"""
    entry = {
        "x": float(center_x),
        "y": float(center_y),
        "vx": math.cos(angle) * speed,
        "vy": math.sin(angle) * speed,
        "angle": angle,
    }
    if small:
        entry["small"] = True
        entry["hp"] = 1
    else:
        entry["indestructible"] = True
    if passes_b5_shield:
        entry["passes_b5_shield"] = True
    meteors.append(entry)

def boss5_weapon_hp_mult(weapon_level: int) -> float:
    """武器Lv別HP倍率（Lv5レーザーはLv4と同じ）。"""
    wl = max(1, min(PLAYER_MAX_WEAPON_LEVEL, int(weapon_level)))
    return float(BOSS5_HP_WEAPON_MULT.get(wl, BOSS5_HP_WEAPON_MULT[4]))


def calc_boss5_max_hp(diff, weapon_level):
    """自機の武器レベルに応じてボス5の最大HPを調整。"""
    hp_scale = diff.boss_hp_scale * (0.7 if diff.name == "EASY" else 1.0)
    hp_scale *= getattr(diff, "boss5_hp_mul", 1.0)
    weapon_mult = boss5_weapon_hp_mult(weapon_level)
    return int(BOSS5_BASE_HP * hp_scale * weapon_mult)


def get_boss5_phase(boss, is_dying_hp, is_critical_hp, is_low_hp):
    """ボス5のフェーズを判定"""
    if is_dying_hp:
        return 4
    elif is_critical_hp:
        return 3
    elif is_low_hp:
        return 2
    else:
        return 1


def compute_boss5_phase(boss, boss_fight_timer, diff):
    """HP・経過時間（難易度別フェーズ強制）から現在フェーズを算出。"""
    if diff.name == "EASY":
        force_low_f, force_crit_f = 600, 1200
    elif diff.name == "NORMAL":
        force_low_f, force_crit_f = 900, 1800
    elif diff.name == "HARD":
        force_low_f, force_crit_f = 1200, 2400
    else:  # NIGHTMARE
        force_low_f, force_crit_f = 1200, 2400
    phase_force_low = boss_fight_timer >= force_low_f
    phase_force_critical = boss_fight_timer >= force_crit_f
    is_low_hp = (boss.hp <= boss.max_hp * 0.5) or phase_force_low
    is_critical_hp = (boss.hp <= boss.max_hp * 0.25) or phase_force_critical
    is_dying_hp = boss.hp <= boss.max_hp * 0.10
    return get_boss5_phase(boss, is_dying_hp, is_critical_hp, is_low_hp)


def get_boss5_bgm_hp_tier(boss) -> float:
    """現在HP割合に対応するBGM帯キー（1.0 / 0.5 / 0.25 / 0.10）。"""
    ratio = boss.hp / max(1, boss.max_hp)
    if ratio <= BOSS5_BGM_HP_DYING:
        return BOSS5_BGM_HP_DYING
    if ratio <= BOSS5_BGM_HP_CRITICAL:
        return BOSS5_BGM_HP_CRITICAL
    if ratio <= BOSS5_BGM_HP_LOW:
        return BOSS5_BGM_HP_LOW
    return 1.0


def resolve_boss5_bgm_track(tier: float, path_exists) -> str:
    """BGMパスを解決。未配置ならより高HP帯→旧 boss5 へフォールバック。"""
    try:
        start = BOSS5_BGM_TIER_ORDER.index(tier)
    except ValueError:
        start = 0
    for i in range(start, -1, -1):
        key = BOSS5_BGM_TIER_ORDER[i]
        track = BOSS5_BGM_TRACKS.get(key)
        if track and path_exists(track):
            return track
    if path_exists(BOSS5_BGM_FALLBACK):
        return BOSS5_BGM_FALLBACK
    return BOSS5_BGM_TRACKS.get(1.0, BOSS5_BGM_FALLBACK)


def get_boss5_attack_params(b5_phase):
    """フェーズごとの攻撃パラメータを取得"""
    params = {
        1: {"SPECIAL_CYCLE": 380, "CHARGE_F": 65},
        2: {"SPECIAL_CYCLE": 320, "CHARGE_F": 55},
        3: {"SPECIAL_CYCLE": 300, "CHARGE_F": 50},
        4: {"SPECIAL_CYCLE": 260, "CHARGE_F": 40},
    }
    return params.get(b5_phase, {"SPECIAL_CYCLE": 380, "CHARGE_F": 65})