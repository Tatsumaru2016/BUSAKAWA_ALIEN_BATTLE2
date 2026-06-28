# extra_boss.py — エクストラステージ専用ボス（ビームライフル / ビームカッター / バルカン / ファンネル）

from __future__ import annotations

import math
import random

import pygame

from enemy_bullets import (
    spawn_extra_beam_cutter,
    spawn_extra_beam_orb_shot,
    spawn_extra_funnel_snipe_beam,
    spawn_extra_striker_fighter,
    spawn_extra_tank_machine_gun,
    spawn_extra_vulcan_snipe,
)
from boss_attacks.common import update_boss_supply_drop
from game_runtime import RT
from midboss import MidBoss

# --- 導入演出 ---
EXTRA_INTRO_BG_ROLL_FRAMES = 96
EXTRA_INTRO_BUBBLE_FRAMES = 90
EXTRA_INTRO_SCROLL_SPEED = (3, 5, 9)

# --- ボス配置（右端・やや下／front 寄り） ---
EXTRA_BOSS_TARGET_H = 580
EXTRA_BOSS_RIGHT_MARGIN = 28
# 見た目の重心を画面右端からこの距離に揃える（矩形右端だけだと中央寄りに見える）
EXTRA_BOSS_VISUAL_ANCHOR_FROM_RIGHT = 72
EXTRA_BOSS_Y_RATIO = 0.72
EXTRA_BOSS_Y_OFFSET = -115

_EXTRA_BOSS_VISUAL_CENTROID_CACHE: dict[int, float] = {}
# 射撃1(charge)＝通常ポーズ。銃口＝黄丸位置（充填・ビーム根本）
RIFLE_MUZZLE_CHARGE_X = 43   # 118 から左へ 75
RIFLE_MUZZLE_CHARGE_Y = 106  # 56 から下へ 50
EXTRA_SPRITE_REST = "charge"  # 射撃1
EXTRA_SPRITE_FIRE = "fire"  # 射撃2
# 登場のみ extra_boss_normal（ex_sprite "normal"）

# --- ビーム弾（充填エフェクトは同じ・5発ワンセット） ---
BEAM_CHARGE_FRAMES = 45
BEAM_COOLDOWN_FRAMES = 120
BEAM_ORB_SPEED = 24.0
BEAM_ORB_SHOTS_PER_SET = 5
BEAM_ORB_SHOT_INTERVAL = 16
BEAM_ORB_SHOT_FIRE_HOLD = 12  # 第二形態: 1発ごとの射撃2ポーズ
BEAM_SPRITE2_HOLD_FRAMES = 60
# 充填・発射根元オフセット（基準点からの相対）
TANK_BEAM_MUZZLE_OFFSET_X = -20
TANK_BEAM_MUZZLE_OFFSET_Y = 10
# 第一形態タンク1の充填エフェクト表示位置（主砲根元からの相対）
TANK_CHARGE_EFFECT_OFFSET_X = -25
TANK_CHARGE_EFFECT_OFFSET_Y = 15
TANK_MG_MUZZLE_OFFSET_X = 150
ROBOT_BEAM_MUZZLE_OFFSET_X = -25
ROBOT_BEAM_MUZZLE_OFFSET_Y = 0

# --- ビームカッター（HP25%以下・ボス中心→左端・wave_pose） ---
BEAM_CUTTER_HP_RATIO = 0.25
BEAM_CUTTER_SPEED = 27.0
BEAM_CUTTER_LANE_COUNT = 3
BEAM_CUTTER_LANE_DELAY = 22
BEAM_CUTTER_COOLDOWN = 95
EXTRA_SPRITE_BEAM_CUTTER = "wave_pose"

# --- ファンネル（HP問わず常時） ---
FUNNEL_HP_RATIO = 0.5  # フェーズ3判定用
FUNNEL_CYCLE_COOLDOWN = 360
FUNNEL_CYCLE_COOLDOWN_MID = 300
FUNNEL_CYCLE_COOLDOWN_LATE = 240
FUNNEL_WAVE_COUNT = 2  # 5機順射 × 2ラウンド（計10発）
FUNNEL_SNIPE_INTERVAL = 36
FUNNEL_SNIPE_SPEED = 13.5
FUNNEL_DEPLOY_FRAMES = 52
FUNNEL_RETURN_FRAMES = 52
FUNNEL_HOLD_Y = 58
FUNNEL_SLOT_X_RATIOS = (0.11, 0.28, 0.50, 0.72, 0.89)
FUNNEL_FLASH_FRAMES = 16

# --- 第一形態（タンク） ---
TANK_MUZZLE_X_RATIO = 0.095  # 主砲ビーム（tank1/2/3 画像左上基準）
TANK_MUZZLE_Y_RATIO = 0.520
TANK_MG_MUZZLE_X_RATIO = 0.115  # 機関砲（砲塔上・やや手前）
TANK_MG_MUZZLE_Y_RATIO = 0.435

TANK_TRANSFORM_TANK2_FRAMES = 30
TANK_TRANSFORM_TANK3_FRAMES = 30

TANK_MG_CD_FULL = 72
TANK_MG_CD_MIN = 52
TANK_MG_BURST_SHOTS = 10
TANK_MG_BURST_INTERVAL = 4

# --- 第一形態ストライカー（最上部・右→左・爆弾5投下） ---
TANK_STRIKER_COOLDOWN = 105
TANK_STRIKER_MAX_ACTIVE = 1
TANK_STRIKER_TOP_MARGIN = 50.0

# --- 第二形態ストライカー（最上部固定・右→左・爆弾5投下） ---
ROBOT_STRIKER_COOLDOWN = 72
ROBOT_STRIKER_MAX_ACTIVE = 1
ROBOT_STRIKER_SPEED = 11.0
ROBOT_STRIKER_TOP_MARGIN = 42.0
ROBOT_STRIKER_BOMB_COUNT = 5
ROBOT_STRIKER_BOMB_SPEED_Y = 7.8

# --- 頭部バルカン（HP問わず常時・ビーム／ファンネル中も可） ---
VULCAN_BURST_SHOTS = 10
VULCAN_SHOT_INTERVAL = 6
VULCAN_BURST_COOLDOWN = 88
VULCAN_BURST_COOLDOWN_LATE = 68
# extra_boss_normal 頭部の紫ポート（スプライト左上基準）
VULCAN_MUZZLE_X_FROM_LEFT = 430
VULCAN_MUZZLE_Y_FROM_TOP = 106
VULCAN_BULLET_SPEED = 12.0

# --- HPフェーズ（瀕死=phase4） ---
EXTRA_HP_PHASE_4 = 0.25
EXTRA_HP_PHASE_2 = 0.75
PHASE2_ATTACK_INTERVAL = 200
PHASE3_ATTACK_INTERVAL = 190
PHASE4_ATTACK_INTERVAL = 175

EXTRA_BOSS_BASE_HP = 14400  # 旧4800の3倍
EXTRA_BOSS_BARRIER_BASE_HP = 5200  # 水色バリア（難易度スケールあり）
EXTRA_BOSS_AURA_COLOR = (65, 215, 255)
EXTRA_BOSS_AURA_OUTLINE = 2
_EXTRA_BOSS_AURA_CACHE: dict[str, tuple[pygame.Surface, int]] = {}


def g():
    return RT.g()


def _extra_images():
    return g().get("extra_boss_images") or {}


def extra_boss_anchor_y(height: int) -> int:
    """前面パララックス（下部）寄りの縦位置。"""
    return int(height * EXTRA_BOSS_Y_RATIO) + EXTRA_BOSS_Y_OFFSET


def _play_extra_sfx(key: str) -> None:
    sfx = g().get(key)
    if sfx is None:
        return
    try:
        sfx.play()
    except Exception:
        pass


def _extra_boss_visual_centroid_x(surf: pygame.Surface) -> float:
    """スプライト内の不透明画素の水平重心（ポーズ差の吸収用）。"""
    sid = id(surf)
    cached = _EXTRA_BOSS_VISUAL_CENTROID_CACHE.get(sid)
    if cached is not None:
        return cached
    try:
        mask = pygame.mask.from_surface(surf)
        rects = mask.get_bounding_rects()
        if not rects:
            cx = surf.get_width() * 0.5
        else:
            bounds = rects[0]
            for extra in rects[1:]:
                bounds = bounds.union(extra)
            total = 0
            weighted = 0.0
            for x in range(bounds.left, bounds.right):
                col = sum(
                    1
                    for y in range(bounds.top, bounds.bottom)
                    if mask.get_at((x, y))
                )
                total += col
                weighted += x * col
            cx = weighted / total if total else surf.get_width() * 0.5
    except Exception:
        cx = surf.get_width() * 0.5
    _EXTRA_BOSS_VISUAL_CENTROID_CACHE[sid] = cx
    return cx


def _extra_boss_target_centroid_x(width: int) -> float:
    return width - EXTRA_BOSS_RIGHT_MARGIN - EXTRA_BOSS_VISUAL_ANCHOR_FROM_RIGHT


def _apply_extra_boss_rest_pose(boss) -> None:
    """定位置へ配置（見た目の重心を画面右寄りに固定）。"""
    boss.image = extra_boss_sprite(boss)
    surf = boss.image
    width = g()["WIDTH"]
    target_cx = _extra_boss_target_centroid_x(width)
    cx_sprite = _extra_boss_visual_centroid_x(surf)
    boss.rect = surf.get_rect()
    boss.rect.left = int(round(target_cx - cx_sprite))
    boss.rect.centery = extra_boss_anchor_y(g()["HEIGHT"])


def place_extra_boss_at_rest(boss) -> None:
    """定位置へ配置（導入スクロール中もこの座標）。"""
    _apply_extra_boss_rest_pose(boss)


def _funnel_busy(boss) -> bool:
    return getattr(boss, "ex_funnel_state", "idle") not in ("idle", "")


def _hp_ratio(boss) -> float:
    if boss.max_hp <= 0:
        return 0.0
    return max(0.0, boss.hp / float(boss.max_hp))


def _extra_hp_phase(boss) -> int:
    """1=高HP … 4=瀕死（到達したフェーズの追加攻撃は累積）。"""
    r = _hp_ratio(boss)
    if r <= EXTRA_HP_PHASE_4:
        return 4
    if r <= FUNNEL_HP_RATIO:
        return 3
    if r <= EXTRA_HP_PHASE_2:
        return 2
    return 1


def init_extra_boss_attrs(boss) -> None:
    # 第一形態（タンク）: シールドがある間はタンクを表示
    boss.ex_sprite = "tank1"
    boss.ex_tank_form = "tank1"  # tank1/tank2/tank3/robot2
    boss.ex_tank_transform_active = False
    boss.ex_tank_transform_timer = 0
    # タンク攻撃（シールドHPがある間のみ使用）
    boss.ex_tank_beam_state = "idle"  # idle / charge / fire / cooldown
    boss.ex_tank_beam_timer = 0
    boss.ex_tank_beam_fire_timer = 0
    boss.ex_tank_beam_burst_left = 0
    boss.ex_tank_beam_burst_wait = 0
    boss.ex_tank_charge_sfx_played = False
    boss.ex_tank_mg_cd = 50
    boss.ex_tank_mg_burst_left = 0
    boss.ex_tank_mg_burst_wait = 0
    boss.ex_tank_homing_cd = 90
    boss.ex_tank_homing_burst_left = 0
    boss.ex_tank_homing_burst_wait = 0
    boss.ex_tank_striker_cd = 70
    boss.ex_robot_striker_cd = 35
    boss.ex_robot_homing_cd = 100
    boss.ex_robot_homing_state = ""
    boss.ex_robot_homing_align_timer = 0
    boss.ex_robot_homing_charges = []
    boss.ex_robot_homing_queue = []
    boss.ex_robot_homing_wait = 0
    boss.ex_attack = "idle"
    boss.ex_attack_timer = 90
    boss.ex_funnel_state = "idle"
    boss.ex_funnel_timer = 0
    boss.ex_funnel_wave = 0
    boss.ex_funnel_cd = 180
    boss.ex_funnels = []
    boss.ex_funnel_snipe_idx = 0
    boss.ex_funnel_snipe_round = 0
    boss.ex_enter_sfx_played = False
    boss.ex_charge_sfx_played = False
    boss.ex_vulcan_state = "idle"
    boss.ex_vulcan_timer = 0
    boss.ex_vulcan_shot = 0
    boss.ex_vulcan_cd = 40
    boss.ex_hp_phase = 1
    boss.ex_phase2_cd = 70
    boss.ex_phase3_cd = 110
    boss.ex_phase4_cd = 150
    boss.ex_beam_muzzle_xy = None
    boss.ex_beam_fire_timer = 0
    boss.ex_beam_burst_left = 0
    boss.ex_beam_burst_wait = 0
    boss.ex_beam_sprite2_timer = 0
    boss.ex_beam_cutter_cd = 55
    boss.ex_beam_cutter_active = False
    boss.ex_beam_cutter_burst_left = 0
    boss.ex_beam_cutter_burst_wait = 0


def extra_boss_barrier_max(diff) -> int:
    scale = getattr(diff, "boss_shield_scale", 1.0)
    return max(1, int(EXTRA_BOSS_BARRIER_BASE_HP * scale))


def apply_extra_boss_barrier(play, diff) -> None:
    """オーラ式バリア（他ボス同様: 先にシールドHP→本体HP）。"""
    barrier = extra_boss_barrier_max(diff)
    play.set("boss_shield_hp", barrier)
    play.set("boss_shield_max", barrier)
    play.set("boss_shield_grace_timer", 0)


def extra_boss_barrier_ratio(play) -> float:
    mx = int(getattr(play, "boss_shield_max", 0) or 0)
    if mx <= 0:
        return 0.0
    hp = int(getattr(play, "boss_shield_hp", 0) or 0)
    return max(0.0, min(1.0, hp / float(mx)))


def tick_extra_boss_barrier(play) -> None:
    gt = int(getattr(play, "boss_shield_grace_timer", 0) or 0)
    if gt > 0:
        play.set("boss_shield_grace_timer", gt - 1)


def purge_extra_ground_purple_lasers_from_play(play) -> None:
    """地面這い紫レーザー（旧ショックウェーブ等）を除去。"""
    for el in play.enemy_lasers[:]:
        if el in play.enemy_lasers and (
            getattr(el, "laser_variant", "") == "purple_ground_crescent"
            or getattr(el, "extra_purple_shot", False)
        ):
            play.enemy_lasers.remove(el)


def purge_extra_beam_lasers_from_play(play) -> None:
    """ビームカッター（弾・旧レーザー）と旧紫地面ビームを除去。"""
    purge_extra_ground_purple_lasers_from_play(play)
    for eb in play.enemy_bullets[:]:
        if eb.get("image_type") == "extra_beam_cutter" and eb in play.enemy_bullets:
            play.enemy_bullets.remove(eb)
    for el in play.enemy_lasers[:]:
        if getattr(el, "extra_beam_cutter", False) and el in play.enemy_lasers:
            play.enemy_lasers.remove(el)


def purge_extra_beam_orbs_from_play(play) -> None:
    for eb in play.enemy_bullets[:]:
        if eb.get("image_type") == "extra_beam_orb" and eb in play.enemy_bullets:
            play.enemy_bullets.remove(eb)


def purge_extra_vulcan_from_play(play) -> None:
    for eb in play.enemy_bullets[:]:
        if eb.get("image_type") == "extra_vulcan" and eb in play.enemy_bullets:
            play.enemy_bullets.remove(eb)


def purge_extra_homing_bullets_from_play(play, boss=None) -> None:
    """エクストラボス追尾弾（廃止・残存弾の掃除）。"""
    for eb in play.enemy_bullets[:]:
        if eb.get("extra_tank_homing") or eb.get("extra_robot_homing_snipe"):
            play.enemy_bullets.remove(eb)
        elif eb.get("extra_robot_homing_charge"):
            play.enemy_bullets.remove(eb)
    if boss is not None:
        for eb in list(getattr(boss, "ex_robot_homing_charges", None) or []):
            if eb in play.enemy_bullets:
                play.enemy_bullets.remove(eb)
        boss.ex_robot_homing_state = ""
        boss.ex_robot_homing_align_timer = 0
        boss.ex_robot_homing_charges = []
        boss.ex_robot_homing_queue = []
        boss.ex_robot_homing_wait = 0
        boss.ex_tank_homing_burst_left = 0
        boss.ex_tank_homing_burst_wait = 0


def purge_extra_boss_hazards_from_play(play) -> None:
    """ビーム弾・ビームカッター・バルカン弾を除去（撃破時など）。"""
    purge_extra_beam_lasers_from_play(play)
    purge_extra_beam_orbs_from_play(play)
    purge_extra_vulcan_from_play(play)
    purge_extra_homing_bullets_from_play(play, play.boss)


def clear_extra_boss_combat_on_defeat(play, boss) -> None:
    """撃破直後: プレイヤー向け弾とビーム攻撃状態を止める。"""
    purge_extra_boss_hazards_from_play(play)
    if boss is None:
        return
    boss.ex_beam_muzzle_xy = None
    boss.ex_beam_fire_timer = 0
    boss.ex_beam_sprite2_timer = 0
    boss.ex_beam_cutter_active = False
    boss.ex_attack = "idle"
    boss.ex_attack_timer = 0
    boss.ex_charge_sfx_played = False
    boss.ex_tank_beam_state = "idle"
    boss.ex_tank_beam_timer = 0
    boss.ex_tank_beam_fire_timer = 0
    boss.ex_tank_beam_burst_left = 0
    boss.ex_tank_beam_burst_wait = 0
    boss.ex_tank_mg_burst_left = 0
    boss.ex_tank_mg_burst_wait = 0
    boss.ex_tank_homing_burst_left = 0
    boss.ex_tank_homing_burst_wait = 0
    boss.ex_robot_homing_state = ""
    boss.ex_robot_homing_charges = []
    boss.ex_robot_homing_queue = []
    boss.ex_robot_homing_wait = 0
    boss.ex_beam_burst_left = 0
    boss.ex_beam_burst_wait = 0


def ems_clear_extra_vulcan_bullets(play, diff) -> int:
    """EMS: ヘッドバルカン弾（extra_vulcan）のみ消去。ビーム・ファンネル等は対象外。"""
    from explosion import Explosion

    cleared = 0
    for eb in play.enemy_bullets[:]:
        if eb.get("image_type") != "extra_vulcan":
            continue
        play.explosions.append(
            Explosion(int(eb["x"]), int(eb["y"]), big=False)
        )
        play.enemy_bullets.remove(eb)
        cleared += 1
    if cleared > 0:
        play.add_score(play.score_chain.score_ems_kill(diff))
    return cleared


def _extra_boss_barrier_aura_cached(boss) -> tuple[pygame.Surface, int]:
    """2px 縁取りのみ。ポーズ（ex_sprite）ごとに1回生成してキャッシュ。"""
    key = str(getattr(boss, "ex_sprite", EXTRA_SPRITE_REST))
    hit = _EXTRA_BOSS_AURA_CACHE.get(key)
    if hit is not None:
        return hit
    from player_status_ui import _aura_surface_for_image

    surf, pad = _aura_surface_for_image(
        boss.image,
        EXTRA_BOSS_AURA_COLOR,
        outline_px=EXTRA_BOSS_AURA_OUTLINE,
        glow_layers=(),
    )
    _EXTRA_BOSS_AURA_CACHE[key] = (surf, pad)
    return surf, pad


def draw_extra_boss_barrier_aura(screen: pygame.Surface, boss, play) -> None:
    """水色 2px シルエット縁（グロー・毎フレーム再生成なし）。"""
    if int(getattr(play, "boss_shield_hp", 0) or 0) <= 0:
        return
    aura, pad = _extra_boss_barrier_aura_cached(boss)
    screen.blit(aura, (boss.rect.x - pad, boss.rect.y - pad))


def draw_extra_boss_barrier_grace_flash(screen: pygame.Surface, boss, play) -> None:
    """バリア破壊後の無敵猶予（他ボスと同じ黄フラッシュ）。"""
    gt = int(getattr(play, "boss_shield_grace_timer", 0) or 0)
    if gt <= 0 or gt % 10 >= 5:
        return
    flash = pygame.Surface(
        (max(1, boss.rect.width + 48), max(1, boss.rect.height)),
        pygame.SRCALPHA,
    )
    flash.fill((255, 255, 120, 58))
    screen.blit(flash, (boss.rect.left - 24, boss.rect.top))


def create_extra_boss(diff) -> MidBoss:
    imgs = _extra_images()
    surf = imgs.get("normal") or imgs.get("charge") or pygame.Surface((200, 200))
    boss = MidBoss(6, surf)
    hp_scale = getattr(diff, "boss_hp_scale", 1.0)
    boss.max_hp = int(EXTRA_BOSS_BASE_HP * hp_scale)
    boss.hp = boss.max_hp
    w = surf.get_width()
    width = g()["WIDTH"]
    h = g()["HEIGHT"]
    boss.rect = surf.get_rect()
    init_extra_boss_attrs(boss)
    place_extra_boss_at_rest(boss)
    return boss


def extra_boss_sprite(boss) -> pygame.Surface:
    imgs = _extra_images()
    if getattr(boss, "ex_beam_cutter_active", False):
        return (
            imgs.get("wave_pose")
            or imgs.get("normal")
            or boss.image
        )
    key = getattr(boss, "ex_sprite", EXTRA_SPRITE_REST)
    if _funnel_busy(boss) and key == EXTRA_SPRITE_REST:
        key = "funnel_pose"
    return (
        imgs.get(key)
        or imgs.get(EXTRA_SPRITE_REST)
        or imgs.get("normal")
        or boss.image
    )


def sync_extra_boss_sprite(boss) -> None:
    """ポーズ切替後も画面右の見え方を維持する。"""
    if boss.image is not None and boss.rect.width > 0:
        anchor_screen_cx = boss.rect.left + _extra_boss_visual_centroid_x(boss.image)
    else:
        anchor_screen_cx = _extra_boss_target_centroid_x(g()["WIDTH"])
    anchor_cy = boss.rect.centery
    boss.image = extra_boss_sprite(boss)
    cx_sprite = _extra_boss_visual_centroid_x(boss.image)
    boss.rect = boss.image.get_rect()
    boss.rect.left = int(round(anchor_screen_cx - cx_sprite))
    boss.rect.centery = anchor_cy


def _boss_center(boss) -> tuple[float, float]:
    """追加攻撃・ショックウェーブ等の発射原点（ボス中心）。"""
    return float(boss.rect.centerx), float(boss.rect.centery)


def _rifle_muzzle_charge(boss) -> tuple[float, float]:
    """射撃画像1の銃口（充填・ビーム根本）。"""
    return (
        float(boss.rect.left + RIFLE_MUZZLE_CHARGE_X),
        float(boss.rect.top + RIFLE_MUZZLE_CHARGE_Y),
    )


def _rifle_muzzle(boss) -> tuple[float, float]:
    """ビーム砲の根本（発射時に固定した射撃1銃口、なければ現在位置）。"""
    fixed = getattr(boss, "ex_beam_muzzle_xy", None)
    if fixed is not None:
        return float(fixed[0]), float(fixed[1])
    return _rifle_muzzle_charge(boss)


def _set_extra_rest_sprite(boss) -> None:
    """攻撃待機・終了後は射撃1(charge)へ。"""
    if boss.ex_sprite != EXTRA_SPRITE_REST:
        boss.ex_sprite = EXTRA_SPRITE_REST
        sync_extra_boss_sprite(boss)


def _charge_effect_ratio(frame: int) -> float:
    """充填エフェクト進行（45f目で1.0）。"""
    denom = max(1, BEAM_CHARGE_FRAMES - 1)
    return min(1.0, max(0, frame) / float(denom))


def _vulcan_head_muzzle(boss) -> tuple[float, float]:
    """頭部バルカン発射点（頭頂付近の紫ポート）。"""
    return (
        float(boss.rect.left + VULCAN_MUZZLE_X_FROM_LEFT),
        float(boss.rect.top + VULCAN_MUZZLE_Y_FROM_TOP),
    )


def _robot_beam_muzzle_xy(boss) -> tuple[float, float]:
    """第二形態: ビーム弾の充填・発射根元。"""
    return (
        float(boss.rect.left + RIFLE_MUZZLE_CHARGE_X + ROBOT_BEAM_MUZZLE_OFFSET_X),
        float(boss.rect.top + RIFLE_MUZZLE_CHARGE_Y + ROBOT_BEAM_MUZZLE_OFFSET_Y),
    )


def _charge_muzzle(boss) -> tuple[float, float]:
    """充填エフェクト（第二形態ビーム弾根元）。"""
    return _robot_beam_muzzle_xy(boss)


def _beam_cutter_allowed(boss) -> bool:
    return _hp_ratio(boss) <= BEAM_CUTTER_HP_RATIO


def _extra_beam_cutters_active(play) -> bool:
    for eb in play.enemy_bullets:
        if eb.get("image_type") == "extra_beam_cutter":
            return True
    for el in play.enemy_lasers:
        if getattr(el, "extra_beam_cutter", False):
            return True
    return False


def _clear_extra_beam_cutters(play) -> None:
    for eb in play.enemy_bullets[:]:
        if eb.get("image_type") == "extra_beam_cutter" and eb in play.enemy_bullets:
            play.enemy_bullets.remove(eb)
    for el in play.enemy_lasers[:]:
        if getattr(el, "extra_beam_cutter", False) and el in play.enemy_lasers:
            play.enemy_lasers.remove(el)


def _abort_beam_cutter(boss, play) -> None:
    _clear_extra_beam_cutters(play)
    boss.ex_beam_cutter_active = False
    boss.ex_beam_cutter_burst_left = 0
    boss.ex_beam_cutter_burst_wait = 0
    if not _funnel_busy(boss):
        _set_extra_rest_sprite(boss)


def _spawn_beam_cutter_lane(boss, lane_index: int) -> None:
    spawn_extra_beam_cutter(
        boss,
        lane_index=lane_index,
        speed=BEAM_CUTTER_SPEED,
    )
    _play_extra_sfx("extra_boss_beam_fire_sound")


def _tick_beam_cutter_burst(boss) -> None:
    """上→中→下の順で時間差発射。"""
    wait = int(getattr(boss, "ex_beam_cutter_burst_wait", 0) or 0)
    left = int(getattr(boss, "ex_beam_cutter_burst_left", 0) or 0)
    if left <= 0:
        return
    if wait > 0:
        boss.ex_beam_cutter_burst_wait = wait - 1
        return
    lane = BEAM_CUTTER_LANE_COUNT - left
    _spawn_beam_cutter_lane(boss, lane)
    boss.ex_beam_cutter_burst_left = left - 1
    if boss.ex_beam_cutter_burst_left > 0:
        boss.ex_beam_cutter_burst_wait = BEAM_CUTTER_LANE_DELAY


def _start_beam_cutter_burst(boss) -> None:
    play = g().get("play")
    if play is not None:
        purge_extra_ground_purple_lasers_from_play(play)
    boss.ex_beam_sprite2_timer = 0
    boss.ex_beam_cutter_active = True
    boss.ex_beam_cutter_burst_left = BEAM_CUTTER_LANE_COUNT
    boss.ex_beam_cutter_burst_wait = 0
    _tick_beam_cutter_burst(boss)
    if not _funnel_busy(boss):
        boss.ex_sprite = EXTRA_SPRITE_BEAM_CUTTER
        sync_extra_boss_sprite(boss)


def _restore_sprite_after_beam_cutter(boss) -> None:
    if _funnel_busy(boss):
        boss.ex_sprite = "funnel_pose"
    else:
        _set_extra_rest_sprite(boss)
    sync_extra_boss_sprite(boss)


def _update_phase4_beam_cutter_attack(boss, player, player_dead: bool, play) -> None:
    """HP25%以下: ビームカッター必須（ファンネル中も発動・ボス中心から左へ）。"""
    if player_dead or not _beam_cutter_allowed(boss):
        if getattr(boss, "ex_beam_cutter_active", False):
            boss.ex_beam_cutter_active = False
            if not _extra_beam_cutters_active(play):
                _restore_sprite_after_beam_cutter(boss)
        return

    if getattr(boss, "ex_beam_cutter_active", False):
        _tick_beam_cutter_burst(boss)
        if (
            not _funnel_busy(boss)
            and boss.ex_sprite != EXTRA_SPRITE_BEAM_CUTTER
        ):
            boss.ex_sprite = EXTRA_SPRITE_BEAM_CUTTER
            sync_extra_boss_sprite(boss)
        burst_done = int(getattr(boss, "ex_beam_cutter_burst_left", 0) or 0) <= 0
        if burst_done and not _extra_beam_cutters_active(play):
            boss.ex_beam_cutter_active = False
            boss.ex_beam_cutter_burst_left = 0
            boss.ex_beam_cutter_burst_wait = 0
            _restore_sprite_after_beam_cutter(boss)
        return

    boss.ex_beam_cutter_cd = max(0, int(getattr(boss, "ex_beam_cutter_cd", 0) or 0) - 1)
    if boss.ex_beam_cutter_cd > 0:
        return

    _start_beam_cutter_burst(boss)
    boss.ex_beam_cutter_cd = BEAM_CUTTER_COOLDOWN


def _funnel_emit(f) -> tuple[float, float]:
    fw = (g().get("extra_funnel_img") or pygame.Surface((1, 1))).get_width()
    return f["x"] + fw * 0.5, f["y"] + 26


def _funnel_home_positions(width: int) -> list[tuple[float, float]]:
    return [(width * ratio, float(FUNNEL_HOLD_Y)) for ratio in FUNNEL_SLOT_X_RATIOS]


def _funnel_back_offsets(boss) -> list[tuple[float, float]]:
    cx = boss.rect.centerx
    cy = boss.rect.centery
    return [
        (cx - 80, cy - 120),
        (cx - 40, cy - 150),
        (cx - 10, cy - 170),
        (cx - 40, cy + 150),
        (cx - 80, cy + 120),
    ]


def _spawn_funnels(boss, width: int) -> None:
    homes = _funnel_home_positions(width)
    backs = _funnel_back_offsets(boss)
    funnel_img = g().get("extra_funnel_img")
    fw = funnel_img.get_width() if funnel_img else 80
    boss.ex_funnels = []
    for i, (hx, hy) in enumerate(homes):
        bx, by = backs[i]
        boss.ex_funnels.append({
            "x": float(bx),
            "y": float(by),
            "home_x": float(hx - fw * 0.5),
            "home_y": float(hy),
            "back_x": float(bx),
            "back_y": float(by),
            "phase": "out",
            "timer": 0,
            "flash": 0,
        })


def _update_funnel_positions(boss) -> None:
    for f in boss.ex_funnels:
        f["timer"] += 1
        if f.get("flash", 0) > 0:
            f["flash"] -= 1
        t = min(1.0, f["timer"] / float(FUNNEL_DEPLOY_FRAMES))
        if f["phase"] == "out":
            e = t * t * (3.0 - 2.0 * t)
            f["x"] = f["back_x"] + (f["home_x"] - f["back_x"]) * e
            f["y"] = f["back_y"] + (f["home_y"] - f["back_y"]) * e
        elif f["phase"] == "back":
            e = t * t * (3.0 - 2.0 * t)
            f["x"] = f["home_x"] + (f["back_x"] - f["home_x"]) * e
            f["y"] = f["home_y"] + (f["back_y"] - f["home_y"]) * e


def _draw_purple_charge_effect(
    screen: pygame.Surface,
    x: float,
    y: float,
    frame: int,
    *,
    scale: float = 1.0,
    charge: float | None = None,
) -> None:
    """銃口／ファンネル口の紫エネルギー充填。"""
    pulse = 0.5 + 0.5 * math.sin(frame * 0.24)
    if charge is None:
        charge = _charge_effect_ratio(frame)
    for r, alpha in ((58, 22), (40, 42), (26, 78), (14, 120)):
        rr = int(r * scale * (0.8 + pulse * 0.35 + charge * 0.25))
        s = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (120, 30, 200, alpha), (rr, rr), rr)
        screen.blit(s, (int(x) - rr, int(y) - rr))
    for i in range(6):
        ang = frame * 0.15 + i * (math.tau / 6)
        dist = int(18 * scale * (0.6 + charge * 0.5))
        sx = int(x + math.cos(ang) * dist)
        sy = int(y + math.sin(ang) * dist)
        pygame.draw.circle(screen, (200, 100, 255), (sx, sy), max(2, int(3 * scale)))
    core = int(5 + 3 * charge)
    pygame.draw.circle(screen, (230, 140, 255), (int(x), int(y)), core + 2)
    pygame.draw.circle(screen, (255, 220, 255), (int(x), int(y)), core)


def _fire_tank_beam_orb_shot(boss, player) -> None:
    mx, my = _tank_beam_muzzle_xy(boss)
    spawn_extra_beam_orb_shot(mx, my, player, speed=BEAM_ORB_SPEED)
    _play_extra_sfx("extra_boss_beam_fire_sound")


def _fire_robot_beam_orb_shot(boss, player) -> None:
    """第二形態: 1発＋射撃2ポーズ。"""
    mx, my = _robot_beam_muzzle_xy(boss)
    spawn_extra_beam_orb_shot(mx, my, player, speed=BEAM_ORB_SPEED)
    _play_extra_sfx("extra_boss_beam_fire_sound")
    boss.ex_sprite = EXTRA_SPRITE_FIRE
    sync_extra_boss_sprite(boss)
    boss.ex_beam_sprite2_timer = BEAM_ORB_SHOT_FIRE_HOLD


def _finish_tank_beam_fire(boss) -> None:
    boss.ex_tank_beam_fire_timer = 0
    boss.ex_tank_beam_burst_left = 0
    boss.ex_tank_beam_burst_wait = 0
    boss.ex_tank_beam_state = "cooldown"
    boss.ex_tank_beam_timer = 0


def _abort_beam_for_funnel(boss) -> None:
    play = g().get("play")
    if play is not None:
        purge_extra_beam_orbs_from_play(play)
    boss.ex_beam_muzzle_xy = None
    boss.ex_attack = "idle"
    boss.ex_attack_timer = 0
    _set_extra_rest_sprite(boss)


def _start_beam_charge(boss) -> None:
    boss.ex_attack = "charge"
    boss.ex_attack_timer = 0
    boss.ex_charge_sfx_played = False
    _set_extra_rest_sprite(boss)


def _finish_beam_fire(boss) -> None:
    boss.ex_beam_muzzle_xy = None
    boss.ex_beam_fire_timer = 0
    boss.ex_beam_burst_left = 0
    boss.ex_beam_burst_wait = 0
    boss.ex_attack = "cooldown"
    boss.ex_attack_timer = 0
    # ex_sprite は ex_beam_sprite2_timer が0になるまで維持


def _extra_boss_hazards_disabled(play, boss) -> bool:
    if getattr(play, "extra_victory_active", False):
        return True
    return (
        boss is not None
        and boss.boss_type == 6
        and getattr(boss, "hp", 1) <= 0
    )


def _update_beam_attack(boss, player, player_dead: bool) -> None:
    if _funnel_busy(boss) or getattr(boss, "ex_beam_cutter_active", False):
        return
    atk = boss.ex_attack

    if atk == "idle":
        boss.ex_attack_timer += 1
        idle_wait = 30
        phase = _extra_hp_phase(boss)
        if phase >= 3:
            idle_wait = 18
        elif phase >= 2:
            idle_wait = 24
        if boss.ex_attack_timer >= idle_wait:
            _start_beam_charge(boss)
        return

    if atk == "charge":
        if not boss.ex_charge_sfx_played:
            boss.ex_charge_sfx_played = True
            _play_extra_sfx("extra_boss_beam_charge_sound")
        if boss.ex_attack_timer >= BEAM_CHARGE_FRAMES:
            boss.ex_attack = "fire"
            boss.ex_attack_timer = 0
            if player_dead:
                _finish_beam_fire(boss)
            else:
                boss.ex_beam_burst_left = BEAM_ORB_SHOTS_PER_SET
                boss.ex_beam_burst_wait = 0
            return
        boss.ex_attack_timer += 1
        return

    if atk == "fire":
        st = int(getattr(boss, "ex_beam_sprite2_timer", 0) or 0)
        if st > 0:
            boss.ex_beam_sprite2_timer = st - 1
            if boss.ex_beam_sprite2_timer <= 0:
                _set_extra_rest_sprite(boss)

        burst_wait = int(getattr(boss, "ex_beam_burst_wait", 0) or 0)
        if burst_wait > 0:
            boss.ex_beam_burst_wait = burst_wait - 1
            return

        burst_left = int(getattr(boss, "ex_beam_burst_left", 0) or 0)
        if burst_left > 0:
            _fire_robot_beam_orb_shot(boss, player)
            boss.ex_beam_burst_left = burst_left - 1
            boss.ex_beam_burst_wait = BEAM_ORB_SHOT_INTERVAL
            return

        _finish_beam_fire(boss)
        return

    if atk == "cooldown":
        boss.ex_attack_timer += 1
        st = int(getattr(boss, "ex_beam_sprite2_timer", 0) or 0)
        if st > 0:
            boss.ex_beam_sprite2_timer = st - 1
            if boss.ex_beam_sprite2_timer <= 0:
                _set_extra_rest_sprite(boss)
        if boss.ex_attack_timer >= BEAM_COOLDOWN_FRAMES:
            boss.ex_attack = "idle"
            boss.ex_attack_timer = 0


def _can_use_extra_attack(boss) -> bool:
    if _funnel_busy(boss):
        return False
    return boss.ex_attack in ("idle", "cooldown")


def _phase_bonus_attack_ready(boss) -> bool:
    if not _can_use_extra_attack(boss):
        return False
    if boss.ex_attack == "cooldown" and boss.ex_attack_timer < 36:
        return False
    return boss.ex_attack != "idle" or boss.ex_attack_timer >= 24


def _sync_extra_hp_phase(boss) -> None:
    phase = _extra_hp_phase(boss)
    prev = int(getattr(boss, "ex_hp_phase", 1) or 1)
    if phase <= prev:
        return
    boss.ex_hp_phase = phase
    if phase >= 4:
        boss.ex_beam_cutter_cd = 0
    if phase >= 3:
        boss.ex_funnel_cd = min(int(getattr(boss, "ex_funnel_cd", 999) or 999), 60)


def _abort_funnel_cycle(boss) -> None:
    if getattr(boss, "ex_funnel_state", "idle") in ("idle", ""):
        return
    boss.ex_funnel_state = "idle"
    boss.ex_funnel_timer = 0
    boss.ex_funnels = []
    _set_extra_rest_sprite(boss)


def _update_vulcan_attack(boss, player, player_dead: bool) -> None:
    """頭から10連バルカン（自機スナイプ・HP問わず・ビーム／ファンネル中も可）。"""
    if player_dead:
        boss.ex_vulcan_state = "idle"
        boss.ex_vulcan_timer = 0
        boss.ex_vulcan_shot = 0
        return

    st = boss.ex_vulcan_state
    if st == "idle":
        boss.ex_vulcan_cd = max(0, boss.ex_vulcan_cd - 1)
        if boss.ex_vulcan_cd <= 0:
            boss.ex_vulcan_state = "burst"
            boss.ex_vulcan_timer = 0
            boss.ex_vulcan_shot = 0
        return

    if st == "burst":
        boss.ex_vulcan_timer += 1
        if boss.ex_vulcan_timer % VULCAN_SHOT_INTERVAL == 0:
            if boss.ex_vulcan_shot < VULCAN_BURST_SHOTS:
                hx, hy = _vulcan_head_muzzle(boss)
                spawn_extra_vulcan_snipe(hx, hy, player, speed=VULCAN_BULLET_SPEED)
                sfx = g().get("shot_sound")
                if sfx is not None:
                    try:
                        sfx.play()
                    except Exception:
                        pass
                boss.ex_vulcan_shot += 1
            if boss.ex_vulcan_shot >= VULCAN_BURST_SHOTS:
                boss.ex_vulcan_state = "idle"
                boss.ex_vulcan_timer = 0
                vulcan_cd = VULCAN_BURST_COOLDOWN
                if _extra_hp_phase(boss) >= 3:
                    vulcan_cd = VULCAN_BURST_COOLDOWN_LATE
                boss.ex_vulcan_cd = vulcan_cd


def _update_hp_phase_bonus_attacks(boss, player, player_dead: bool) -> None:
    """フェーズ2+: ストライカー追加投入など（ビームカッターは25%専用）。"""
    if player_dead or _extra_hp_phase(boss) < 2:
        return
    if _funnel_busy(boss):
        return

    play = g().get("play")
    if play is None:
        return

    phase = _extra_hp_phase(boss)
    if phase >= 4:
        boss.ex_robot_striker_cd = min(
            int(getattr(boss, "ex_robot_striker_cd", 99) or 99), 20,
        )
        return

    if phase >= 3:
        boss.ex_robot_striker_cd = min(
            int(getattr(boss, "ex_robot_striker_cd", 99) or 99), 32,
        )
        return

    boss.ex_phase2_cd = max(0, int(getattr(boss, "ex_phase2_cd", 0) or 0) - 1)
    if boss.ex_phase2_cd > 0:
        return
    if _count_extra_strikers(play) >= ROBOT_STRIKER_MAX_ACTIVE + 1:
        return
    spawn_extra_striker_fighter(
        top_margin=ROBOT_STRIKER_TOP_MARGIN + 28.0,
        speed=ROBOT_STRIKER_SPEED + 1.5,
        bomb_count=ROBOT_STRIKER_BOMB_COUNT,
    )
    boss.ex_phase2_cd = 280


def _start_funnel_cycle(boss, width: int) -> None:
    _abort_beam_for_funnel(boss)
    play = RT.play()
    if play is not None and not _beam_cutter_allowed(boss):
        _abort_beam_cutter(boss, play)
    boss.ex_funnel_state = "deploy"
    boss.ex_funnel_timer = 0
    boss.ex_funnel_wave = 0
    boss.ex_funnel_snipe_idx = 0
    boss.ex_funnel_snipe_round = 0
    boss.ex_sprite = "funnel_pose"
    sync_extra_boss_sprite(boss)
    _spawn_funnels(boss, width)


def _funnel_cycle_cooldown(boss) -> int:
    phase = _extra_hp_phase(boss)
    if phase >= 4:
        return FUNNEL_CYCLE_COOLDOWN_LATE
    if phase >= 3:
        return FUNNEL_CYCLE_COOLDOWN_MID
    if phase >= 2:
        return FUNNEL_CYCLE_COOLDOWN
    return FUNNEL_CYCLE_COOLDOWN + 40


def _update_funnel_attack(boss, player, player_dead: bool, width: int) -> None:
    st = boss.ex_funnel_state
    if st in ("idle", ""):
        boss.ex_funnel_cd = max(0, boss.ex_funnel_cd - 1)
        if boss.ex_funnel_cd <= 0 and _can_use_extra_attack(boss):
            if boss.ex_attack == "cooldown" and boss.ex_attack_timer < BEAM_COOLDOWN_FRAMES // 3:
                return
            _start_funnel_cycle(boss, width)
        return

    boss.ex_funnel_timer += 1

    if st == "deploy":
        _update_funnel_positions(boss)
        if boss.ex_funnel_timer >= FUNNEL_DEPLOY_FRAMES:
            for f in boss.ex_funnels:
                f["phase"] = "hold"
                f["timer"] = 0
            boss.ex_funnel_state = "snipe"
            boss.ex_funnel_timer = 0
            boss.ex_funnel_snipe_idx = 0
            boss.ex_funnel_snipe_round = 0
        return

    if st == "snipe":
        if (
            not player_dead
            and boss.ex_funnels
            and boss.ex_funnel_timer % FUNNEL_SNIPE_INTERVAL == 0
        ):
            idx = boss.ex_funnel_snipe_idx
            if idx < len(boss.ex_funnels):
                f = boss.ex_funnels[idx]
                ex, ey = _funnel_emit(f)
                spawn_extra_funnel_snipe_beam(
                    ex,
                    ey,
                    player,
                    speed=FUNNEL_SNIPE_SPEED,
                )
                f["flash"] = FUNNEL_FLASH_FRAMES
                _play_extra_sfx("extra_funnel_shot_sound")
                boss.ex_funnel_snipe_idx = idx + 1
            if boss.ex_funnel_snipe_idx >= len(boss.ex_funnels):
                boss.ex_funnel_snipe_idx = 0
                boss.ex_funnel_snipe_round += 1
        if boss.ex_funnel_snipe_round >= FUNNEL_WAVE_COUNT:
            boss.ex_funnel_state = "return"
            boss.ex_funnel_timer = 0
            for f in boss.ex_funnels:
                f["phase"] = "back"
                f["timer"] = 0
        return

    if st == "return":
        _update_funnel_positions(boss)
        if boss.ex_funnel_timer >= FUNNEL_RETURN_FRAMES:
            boss.ex_funnel_state = "idle"
            boss.ex_funnel_timer = 0
            boss.ex_funnels = []
            boss.ex_funnel_cd = _funnel_cycle_cooldown(boss)
            _set_extra_rest_sprite(boss)


def _tank_muzzle_xy(boss) -> tuple[float, float]:
    """第一形態タンクの主砲基準点（画像左上基準の比率）。"""
    img = boss.image
    if img is None:
        return float(boss.rect.left + 80), float(boss.rect.top + 250)
    mx = boss.rect.left + img.get_width() * TANK_MUZZLE_X_RATIO
    my = boss.rect.top + img.get_height() * TANK_MUZZLE_Y_RATIO
    return float(mx), float(my)


def _tank_beam_muzzle_xy(boss) -> tuple[float, float]:
    """第一形態: ビーム弾の充填・発射根元。"""
    mx, my = _tank_muzzle_xy(boss)
    return (
        mx + float(TANK_BEAM_MUZZLE_OFFSET_X),
        my + float(TANK_BEAM_MUZZLE_OFFSET_Y),
    )


def _tank_charge_effect_xy(boss) -> tuple[float, float]:
    """第一形態タンク1: 充填エフェクトの表示位置。"""
    mx, my = _tank_muzzle_xy(boss)
    return (
        mx + float(TANK_CHARGE_EFFECT_OFFSET_X),
        my + float(TANK_CHARGE_EFFECT_OFFSET_Y),
    )


def _tank_mg_muzzle_xy(boss) -> tuple[float, float]:
    """第一形態タンクの機関砲射出口。"""
    img = boss.image
    if img is None:
        mx, my = _tank_muzzle_xy(boss)
        return mx + float(TANK_MG_MUZZLE_OFFSET_X), my - 40.0
    mx = boss.rect.left + img.get_width() * TANK_MG_MUZZLE_X_RATIO
    my = boss.rect.top + img.get_height() * TANK_MG_MUZZLE_Y_RATIO
    return float(mx) + float(TANK_MG_MUZZLE_OFFSET_X), float(my)


def _update_tank_beam_attack(boss, player, player_dead: bool) -> bool:
    """第二形態と同じ充填→ビーム弾1発。True の間は機関砲を止める。"""
    state = getattr(boss, "ex_tank_beam_state", "idle")

    if state == "idle":
        boss.ex_tank_beam_timer = int(getattr(boss, "ex_tank_beam_timer", 0) or 0) + 1
        if boss.ex_tank_beam_timer >= 30:
            boss.ex_tank_beam_state = "charge"
            boss.ex_tank_beam_timer = 0
            boss.ex_tank_charge_sfx_played = False
        return False

    if state == "charge":
        if not getattr(boss, "ex_tank_charge_sfx_played", False):
            boss.ex_tank_charge_sfx_played = True
            _play_extra_sfx("extra_boss_beam_charge_sound")
        boss.ex_tank_beam_timer = int(getattr(boss, "ex_tank_beam_timer", 0) or 0) + 1
        if boss.ex_tank_beam_timer >= BEAM_CHARGE_FRAMES:
            boss.ex_tank_beam_state = "fire"
            boss.ex_tank_beam_timer = 0
            if player_dead:
                _finish_tank_beam_fire(boss)
            else:
                boss.ex_tank_beam_burst_left = BEAM_ORB_SHOTS_PER_SET
                boss.ex_tank_beam_burst_wait = 0
        return True

    if state == "fire":
        burst_wait = int(getattr(boss, "ex_tank_beam_burst_wait", 0) or 0)
        if burst_wait > 0:
            boss.ex_tank_beam_burst_wait = burst_wait - 1
            return True

        burst_left = int(getattr(boss, "ex_tank_beam_burst_left", 0) or 0)
        if burst_left > 0:
            _fire_tank_beam_orb_shot(boss, player)
            boss.ex_tank_beam_burst_left = burst_left - 1
            if boss.ex_tank_beam_burst_left > 0:
                boss.ex_tank_beam_burst_wait = BEAM_ORB_SHOT_INTERVAL
            else:
                _finish_tank_beam_fire(boss)
            return True

        _finish_tank_beam_fire(boss)
        return True

    if state == "cooldown":
        boss.ex_tank_beam_timer = int(getattr(boss, "ex_tank_beam_timer", 0) or 0) + 1
        if boss.ex_tank_beam_timer >= BEAM_COOLDOWN_FRAMES:
            boss.ex_tank_beam_state = "idle"
            boss.ex_tank_beam_timer = 0
        return False

    boss.ex_tank_beam_state = "idle"
    return False


def _update_tank_machine_gun(boss, player, player_dead: bool, play) -> None:
    """ビーム充填・発射中以外で機関砲（10連射）。"""
    if player_dead:
        return
    t = 1.0 - extra_boss_barrier_ratio(play)
    mg_cd = int(max(TANK_MG_CD_MIN, TANK_MG_CD_FULL - 14 * t))

    burst_left = int(getattr(boss, "ex_tank_mg_burst_left", 0) or 0)
    if burst_left > 0:
        burst_wait = int(getattr(boss, "ex_tank_mg_burst_wait", 0) or 0)
        if burst_wait > 0:
            boss.ex_tank_mg_burst_wait = burst_wait - 1
            return
        mx, my = _tank_mg_muzzle_xy(boss)
        spawn_extra_tank_machine_gun(
            mx, my, player, bullets=1, speed=11.0, spread_rad=0.04,
        )
        boss.ex_tank_mg_burst_left = burst_left - 1
        if boss.ex_tank_mg_burst_left > 0:
            boss.ex_tank_mg_burst_wait = TANK_MG_BURST_INTERVAL
        else:
            boss.ex_tank_mg_cd = mg_cd
        return

    cd = int(getattr(boss, "ex_tank_mg_cd", 0) or 0)
    if cd > 0:
        boss.ex_tank_mg_cd = cd - 1
        return
    boss.ex_tank_mg_burst_left = TANK_MG_BURST_SHOTS
    boss.ex_tank_mg_burst_wait = 0


def _count_extra_strikers(play) -> int:
    return sum(
        1
        for eb in play.enemy_bullets
        if eb.get("attack_type") == "extra_striker"
    )


def _update_tank_striker_attack(boss, player, player_dead: bool, play) -> None:
    """第一形態: 最上部で右→左へ移動しながら爆弾を5投下。"""
    if player_dead:
        return

    cd = int(getattr(boss, "ex_tank_striker_cd", 0) or 0)
    if cd > 0:
        boss.ex_tank_striker_cd = cd - 1
        return

    if _count_extra_strikers(play) >= TANK_STRIKER_MAX_ACTIVE:
        boss.ex_tank_striker_cd = 8
        return

    spawn_extra_striker_fighter(
        top_margin=TANK_STRIKER_TOP_MARGIN,
        speed=ROBOT_STRIKER_SPEED,
        bomb_count=ROBOT_STRIKER_BOMB_COUNT,
    )
    boss.ex_tank_striker_cd = TANK_STRIKER_COOLDOWN


def _update_robot_striker_attack(boss, player, player_dead: bool, play) -> None:
    """第二形態: 最上部で右→左へ移動しながら爆弾を5投下。"""
    if player_dead:
        return
    if _funnel_busy(boss):
        return

    striker_cd = int(max(48, ROBOT_STRIKER_COOLDOWN - 8 * _extra_hp_phase(boss)))

    cd = int(getattr(boss, "ex_robot_striker_cd", 0) or 0)
    if cd > 0:
        boss.ex_robot_striker_cd = cd - 1
        return

    if _count_extra_strikers(play) >= ROBOT_STRIKER_MAX_ACTIVE:
        boss.ex_robot_striker_cd = 6
        return

    spawn_extra_striker_fighter(
        top_margin=ROBOT_STRIKER_TOP_MARGIN,
        speed=ROBOT_STRIKER_SPEED,
        bomb_count=ROBOT_STRIKER_BOMB_COUNT,
    )
    boss.ex_robot_striker_cd = striker_cd


def _update_tank_attack(boss, play, player, player_dead: bool) -> None:
    """第一形態：主砲ビーム砲＋機関砲（シールドがある間のみ）。"""
    if player_dead:
        return
    beam_busy = _update_tank_beam_attack(boss, player, player_dead)
    if not beam_busy:
        _update_tank_machine_gun(boss, player, player_dead, play)
        _update_tank_striker_attack(boss, player, player_dead, play)


def _start_tank_transform(boss, play) -> None:
    """シールド消滅：変形開始（自機/ボスの攻撃と画面の弾を全消去）。"""
    if getattr(boss, "ex_tank_transform_active", False):
        return

    boss.ex_tank_transform_active = True
    boss.ex_tank_transform_timer = 0
    boss.ex_tank_form = "tank2"
    boss.ex_sprite = "tank2"
    _play_extra_sfx("extra_boss_transform_sound")

    # 変形中は攻撃停止：画面の弾（自機・ボス）を全消去
    play.bullets.clear()
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.meteors.clear()

    # ボス側の攻撃状態もリセット（ここからは変形アニメだけ）
    boss.ex_attack = "idle"
    boss.ex_attack_timer = 0
    boss.ex_beam_muzzle_xy = None
    boss.ex_beam_fire_timer = 0
    boss.ex_beam_sprite2_timer = 0
    boss.ex_beam_cutter_active = False
    boss.ex_beam_cutter_burst_left = 0
    boss.ex_beam_cutter_burst_wait = 0
    boss.ex_tank_beam_state = "idle"
    boss.ex_tank_beam_timer = 0
    boss.ex_tank_beam_fire_timer = 0
    boss.ex_tank_beam_burst_left = 0
    boss.ex_tank_beam_burst_wait = 0
    boss.ex_tank_mg_burst_left = 0
    boss.ex_tank_mg_burst_wait = 0
    boss.ex_tank_homing_cd = 90
    boss.ex_tank_homing_burst_left = 0
    boss.ex_tank_homing_burst_wait = 0
    boss.ex_tank_striker_cd = 70
    boss.ex_robot_striker_cd = 35
    boss.ex_robot_homing_cd = 100
    boss.ex_robot_homing_state = ""
    boss.ex_robot_homing_charges = []
    boss.ex_robot_homing_queue = []
    boss.ex_robot_homing_wait = 0
    boss.ex_funnel_state = "idle"
    boss.ex_funnel_timer = 0
    boss.ex_funnels = []
    boss.ex_vulcan_state = "idle"
    boss.ex_vulcan_timer = 0

    # 自機の吹き出しメッセージ（変形を知らせる）
    bubble = g().get("_bubble")
    if bubble is not None:
        bubble.show_text("変形する！", priority=7)

    # BGM 切替
    from audio import start_extra_boss_transform_bgm

    start_extra_boss_transform_bgm()


def _update_tank_transform(boss, play) -> None:
    """変形アニメを進め、完了したら第二形態（射撃1=charge）へ。"""
    boss.ex_tank_transform_timer = int(getattr(boss, "ex_tank_transform_timer", 0) or 0) + 1
    t = boss.ex_tank_transform_timer

    if t <= TANK_TRANSFORM_TANK2_FRAMES:
        boss.ex_tank_form = "tank2"
        boss.ex_sprite = "tank2"
        return

    if t <= TANK_TRANSFORM_TANK2_FRAMES + TANK_TRANSFORM_TANK3_FRAMES:
        boss.ex_tank_form = "tank3"
        boss.ex_sprite = "tank3"
        return

    # 完了：第二形態へ移行
    boss.ex_tank_transform_active = False
    boss.ex_tank_form = "robot2"
    _set_extra_rest_sprite(boss)  # 射撃1=chargeへ
    boss.ex_attack = "idle"
    boss.ex_attack_timer = 45
    boss.ex_robot_striker_cd = 25
    boss.ex_robot_homing_cd = 50
    boss.ex_robot_homing_state = ""
    boss.ex_robot_homing_charges = []
    boss.ex_robot_homing_queue = []
    boss.ex_robot_homing_wait = 0
    boss.ex_beam_cutter_cd = 0

    # 第二形態BGMへ戻す
    from audio import start_extra_boss_bgm

    start_extra_boss_bgm()


def update_extra_intro(play) -> None:
    phase = getattr(play, "extra_intro_phase", "")
    if not phase or phase == "fight":
        return

    play.set("extra_intro_timer", play.extra_intro_timer + 1)
    t = play.extra_intro_timer

    if phase == "bg_roll":
        boss = play.boss
        if boss is not None:
            place_extra_boss_at_rest(boss)
        if t >= EXTRA_INTRO_BG_ROLL_FRAMES:
            play.set("extra_bg_frozen", True)
            play.set("boss_active", True)
            play.set("boss_fight_active", True)
            play.set("extra_intro_phase", "bubble")
            play.set("extra_intro_timer", 0)
            if boss is not None and not boss.ex_enter_sfx_played:
                boss.ex_enter_sfx_played = True
                _play_extra_sfx("extra_boss_enter_sound")
            RT.g()["_bubble"].show_text("な・・・なんだここは基地か？", priority=6)
        return

    if phase == "bubble":
        if t >= EXTRA_INTRO_BUBBLE_FRAMES:
            play.set("extra_intro_phase", "fight")
            play.set("extra_intro_timer", 0)
            from audio import start_extra_boss_tank_bgm

            start_extra_boss_tank_bgm()
            play.score_chain.begin_boss_fight(g()["diff"], 6)
            play.set("no_damage_since_boss", True)
            play.set("boss_fight_timer", 0)
            boss = play.boss
            if boss is not None:
                boss.ex_tank_form = "tank1"
                boss.ex_tank_transform_active = False
                boss.ex_tank_transform_timer = 0
                boss.ex_tank_beam_state = "idle"
                boss.ex_tank_beam_timer = 0
                boss.ex_tank_beam_fire_timer = 0
                boss.ex_tank_beam_burst_left = 0
                boss.ex_tank_beam_burst_wait = 0
                boss.ex_tank_charge_sfx_played = False
                boss.ex_tank_mg_cd = 50
                boss.ex_tank_mg_burst_left = 0
                boss.ex_tank_mg_burst_wait = 0
                boss.ex_tank_homing_cd = 90
                boss.ex_tank_homing_burst_left = 0
                boss.ex_tank_homing_burst_wait = 0
                boss.ex_tank_striker_cd = 70
                boss.ex_robot_striker_cd = 35
                boss.ex_sprite = "tank1"
                boss.ex_attack = "idle"
                boss.ex_attack_timer = 45


def update_extra_boss_combat(play, player, player_dead: bool) -> None:
    if getattr(play, "extra_intro_phase", "") != "fight":
        return
    if getattr(play, "extra_victory_active", False):
        return
    boss = play.boss
    if boss is None or not play.boss_active or boss.hp <= 0:
        return
    if play.boss_fight_active:
        play.set("boss_fight_timer", play.boss_fight_timer + 1)
    width = g()["WIDTH"]
    update_boss_supply_drop(boss)
    tick_extra_boss_barrier(play)
    # 第一形態（タンク）/ 変形 / 第二形態（ロボ）を振り分け
    tank_form = getattr(boss, "ex_tank_form", "robot2")
    shield_hp = int(getattr(play, "boss_shield_hp", 0) or 0)

    if tank_form != "robot2":
        # 変形中：弾消去＋表示だけ
        if getattr(boss, "ex_tank_transform_active", False):
            _update_tank_transform(boss, play)
            return

        # シールドがある間はタンク1で攻撃
        if shield_hp > 0:
            boss.ex_tank_form = "tank1"
            boss.ex_sprite = "tank1"
            sync_extra_boss_sprite(boss)
            _update_tank_attack(boss, play, player, player_dead)
            return

        # シールド消滅：変形開始
        _start_tank_transform(boss, play)
        return

    # 第二形態：従来のロボ戦ロジック
    purge_extra_ground_purple_lasers_from_play(play)
    _sync_extra_hp_phase(boss)
    _update_vulcan_attack(boss, player, player_dead)
    _update_funnel_attack(boss, player, player_dead, width)
    _update_phase4_beam_cutter_attack(boss, player, player_dead, play)
    _update_robot_striker_attack(boss, player, player_dead, play)
    if not _funnel_busy(boss) and not getattr(boss, "ex_beam_cutter_active", False):
        _update_beam_attack(boss, player, player_dead)
    _update_hp_phase_bonus_attacks(boss, player, player_dead)


def draw_extra_funnels(screen, boss) -> None:
    img = g().get("extra_funnel_img")
    if img is None:
        return
    for f in boss.ex_funnels:
        screen.blit(img, (int(f["x"]), int(f["y"])))
        flash = f.get("flash", 0)
        if flash > 0:
            ex, ey = _funnel_emit(f)
            _draw_purple_charge_effect(
                screen, ex, ey, FUNNEL_FLASH_FRAMES - flash, scale=0.65,
            )


def draw_extra_boss(screen, play) -> None:
    boss = play.boss
    if boss is None:
        return
    sync_extra_boss_sprite(boss)
    draw_extra_boss_barrier_aura(screen, boss, play)
    screen.blit(boss.image, boss.rect)
    draw_extra_boss_barrier_grace_flash(screen, boss, play)
    if (
        getattr(boss, "ex_tank_beam_state", "") == "charge"
        and getattr(boss, "ex_tank_form", "") in ("tank1", "tank2", "tank3")
    ):
        if getattr(boss, "ex_tank_form", "") == "tank1":
            mx, my = _tank_charge_effect_xy(boss)
        else:
            mx, my = _tank_beam_muzzle_xy(boss)
        elapsed = int(getattr(boss, "ex_tank_beam_timer", 0) or 0)
        _draw_purple_charge_effect(
            screen,
            mx,
            my,
            elapsed,
            scale=1.15,
            charge=_charge_effect_ratio(elapsed),
        )
    elif boss.ex_attack == "charge" and boss.ex_sprite == "charge":
        mx, my = _charge_muzzle(boss)
        _draw_purple_charge_effect(
            screen,
            mx,
            my,
            boss.ex_attack_timer,
            scale=1.0,
            charge=_charge_effect_ratio(boss.ex_attack_timer),
        )
    draw_extra_funnels(screen, boss)
