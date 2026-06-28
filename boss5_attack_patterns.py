# boss5_attack_patterns.py - 隕石のみ特化版 + 重力攻撃追加
# ★ 変更: 四方から中央へ向かう隕石攻撃 → Boss3風艦隊編隊攻撃（難易度別追尾性能付き）

import math
import random
import pygame

from boss5_update import b5_begin_rush_scale, B5_SIN_ANCHOR_X, B5_SIN_ANCHOR_Y

# HP10%以下: ボス中心からの放射小隕石（1回あたりの本数 = 従来6の5分の3）
B5_DYING_RADIAL_PER_BURST = max(1, (6 * 3) // 5)


# ============================================================
# ユーティリティ
# ============================================================

def _init_b5_attrs(boss):
    """Boss5固有属性の安全な初期化（未定義なら追加）"""
    defaults = dict(
        b5_spiral       = 0.0,
        b5_spiral2      = math.pi,
        b5_phase_timer  = 0,
        b5_charge_phase = 0,
        b5_special_timer= 0,
        b5_rush_state   = "idle",
        b5_rush_timer   = 0,
        b5_rush_vx      = 0.0,
        b5_rush_vy      = 0.0,
        b5_meteor_timer = 0,
        b5_ring_meteors = [],
        b5_obstacle_cd = 0,
        b5_sin_anchor_x = B5_SIN_ANCHOR_X,
        b5_sin_anchor_y = B5_SIN_ANCHOR_Y,
        b5_rush_scaled  = False,
        b5_rush_spin_angle     = 0.0,
        b5_rush_flash_timer    = 0,
        b5_selfdestruct_state  = "idle",
        b5_selfdestruct_timer  = 0,
        b5_selfdestruct_shakes = 0,
        b5_final_laser_count   = 0,
        # ★ 重力攻撃用属性
        b5_gravity_state       = "idle",   # "idle" / "warning" / "active" / "cooldown"
        b5_gravity_timer       = 0,
        b5_gravity_shake       = 0,        # ボスの震えオフセット（描画側で使用）
        b5_gravity_cycle_cd    = 0,        # 次の重力攻撃までのCD
        # ★ 艦隊攻撃用属性（新規）
        b5_fleet_timer         = 0,        # 艦隊攻撃発動カウンター
        b5_fleet_cycle_cd      = 0,        # 艦隊攻撃クールダウン
    )
    for k, v in defaults.items():
        if not hasattr(boss, k):
            setattr(boss, k, v)

# ============================================================
# ★ 重力攻撃設定定数
# ============================================================

GRAVITY_WARN_F   = 70
GRAVITY_ACTIVE_F = 240
GRAVITY_COOL_F   = 140
# フェーズ別の重力攻撃発動間隔（フレーム）
GRAVITY_CYCLE = {
    1: 980,
    2: 820,
    3: 660,
    4: 540,
}
# フェーズ別: 重力発動中の移動制限係数 (0.0=完全停止, 1.0=制限なし)
# EASY は従来 NORMAL 相当の緩さ、NORMAL はやや強めの減速
GRAVITY_RESTRICT_BY_DIFF = {
    "EASY": {1: 0.38, 2: 0.32, 3: 0.28, 4: 0.24},
    "NORMAL": {1: 0.30, 2: 0.24, 3: 0.20, 4: 0.16},
    "HARD": {1: 0.28, 2: 0.22, 3: 0.18, 4: 0.14},
    "NIGHTMARE": {1: 0.24, 2: 0.18, 3: 0.14, 4: 0.10},
}


# ============================================================
# ★ 艦隊編隊攻撃設定定数（新規）
# ============================================================

# フェーズ別: 艦隊攻撃発動間隔（フレーム）
FLEET_CYCLE = {
    1: 500,   # Phase1: 約8.3秒おき
    2: 420,   # Phase2: 約7秒おき
    3: 340,   # Phase3: 約5.7秒おき
    4: 270,   # Phase4: 約4.5秒おき
}

# 編隊パターン定義
# 各隊形: (隊形名, spawn_func_key)
FLEET_FORMATIONS = ["arrow_v", "line_h", "diamond", "cross"]

# 難易度別ホーミング強度
# EASY: 追尾なし  NORMAL: 弱追尾  HARD: 中追尾  NIGHTMARE: 強追尾
FLEET_HOMING_STRENGTH = {
    "EASY":      0.0,
    "NORMAL":    0.0,
    "HARD":      0.022,
    "NIGHTMARE": 0.062,
}

# 難易度別艦隊サイズ（隕石の数）
FLEET_SIZE = {
    "EASY":      4,
    "NORMAL":    5,
    "HARD":      7,
    "NIGHTMARE": 9,
}

# 難易度別艦隊飛行速度
FLEET_BASE_SPEED = {
    "EASY":      3.8,
    "NORMAL":    4.5,
    "HARD":      5.5,
    "NIGHTMARE": 6.8,
}


# ============================================================
# ★ 艦隊隕石データ構造ヘルパー
# 艦隊所属隕石は通常のmeteors dictに "fleet" キーを追加して区別する
# ============================================================

def _make_fleet_meteor(x, y, vx, vy, homing_strength, formation_id):
    """艦隊編隊所属の隕石dictを生成（破壊不可・左へ進み続ける）。"""
    return {
        "x":               float(x),
        "y":               float(y),
        "vx":              float(vx),
        "vy":              float(vy),
        "angle":           math.atan2(vy, vx),
        "indestructible":  True,
        "fleet":           True,
        "formation_id":    formation_id,
        "homing_strength": homing_strength,
        "homing_active":   False,
        "life":            900,
    }


# ============================================================
# ★ 艦隊編隊スポーン関数（旧「四方から中央」攻撃の置き換え）
# ============================================================

def spawn_fleet_formation(
    boss, meteors, player, diff,
    b5_phase, formation_name, formation_id,
    WIDTH, HEIGHT,
):
    """
    Boss3風艦隊編隊を生成する。
    formation_name: "arrow_v" / "line_h" / "diamond" / "cross"
    難易度に応じてホーミング強度・隊形サイズ・速度が変化。
    """
    diff_name       = getattr(diff, "name", "NORMAL")
    homing_str      = FLEET_HOMING_STRENGTH.get(diff_name, 0.028)
    size            = FLEET_SIZE.get(diff_name, 7)
    base_spd        = FLEET_BASE_SPEED.get(diff_name, 5.5)

    # 進行方向: 右端ボスから左（プレイヤー方向）
    # 初期速度ベクトル: 基本は左方向 (vx < 0)
    base_vx = -base_spd
    base_vy = 0.0

    # スポーン基点: 画面右端+マージン（ボス付近から出現）
    spawn_x = float(WIDTH + 80)

    new_meteors = []

    if formation_name == "arrow_v":
        # ▽型（V字）編隊 ─ 先頭1機が前、後続が扇形に広がる
        # 画面中央のY座標付近を基点に配置
        base_y = float(HEIGHT // 2) + random.randint(-80, 80)
        half   = size // 2
        for i in range(size):
            offset_x = i * 38         # X方向間隔（後ろほど右に）
            if i == 0:
                oy = 0                # 先頭
            elif i % 2 == 1:
                oy = -((i + 1) // 2) * 52   # 上側
            else:
                oy = (i // 2) * 52          # 下側
            m = _make_fleet_meteor(
                spawn_x + offset_x,
                base_y + oy,
                base_vx, base_vy,
                homing_str, formation_id,
            )
            new_meteors.append(m)

    elif formation_name == "line_h":
        # 横一列編隊（Y方向に均等に並ぶ）
        spacing = max(40, (HEIGHT - 160) // max(1, size - 1))
        start_y = 80
        stagger_x = 0
        for i in range(size):
            # 列ごとにX位置を少しずらしてジグザグっぽく
            stagger_x = (i % 2) * 40
            m = _make_fleet_meteor(
                spawn_x + stagger_x,
                float(start_y + i * spacing),
                base_vx, base_vy,
                homing_str, formation_id,
            )
            new_meteors.append(m)

    elif formation_name == "diamond":
        # ◆型（菱形）編隊
        # 上下左右の4頂点＋中間点で菱形を作る
        cx_spawn = spawn_x + 60
        cy_spawn = float(HEIGHT // 2) + random.randint(-60, 60)
        diamond_pts = []
        # 菱形の各点（ローカル座標）
        # サイズに応じてスケール
        scale = max(1, size // 3)
        half_w = scale * 55
        half_h = scale * 75
        # 菱形の外周点を生成
        for step in range(size):
            t_ratio = step / float(max(1, size - 1))
            # 菱形の周に沿ってパラメトリック配置
            angle = t_ratio * math.pi * 2
            ex = math.cos(angle) * half_w
            ey = math.sin(angle) * half_h
            diamond_pts.append((cx_spawn + ex, cy_spawn + ey))
        # スポーン順: 後ろのほど遅くなるようにX方向にオフセット
        for idx, (px, py) in enumerate(diamond_pts):
            # 菱形の後方点は遅れて出現（X+オフセット）
            delay_x = (size - 1 - idx) * 22
            m = _make_fleet_meteor(
                px + delay_x, py,
                base_vx, base_vy,
                homing_str, formation_id,
            )
            new_meteors.append(m)

    elif formation_name == "cross":
        # ╋型（十字）編隊 — 機数上限を守る
        cx_spawn = spawn_x + 60
        cy_spawn = float(HEIGHT // 2) + random.randint(-40, 40)
        arm      = min(max(1, size // 3), 3)
        spacing  = 52
        pts = []
        for i in range(-arm, arm + 1):
            pts.append((cx_spawn + abs(i) * spacing, cy_spawn + i * spacing))
        for i in range(-arm, arm + 1):
            if i == 0:
                continue
            pts.append((cx_spawn + abs(i) * spacing, cy_spawn))
        for px, py in pts[:size]:
            m = _make_fleet_meteor(px, py, base_vx, base_vy, homing_str, formation_id)
            new_meteors.append(m)

    meteors.extend(new_meteors)


# ============================================================
# ★ 艦隊隕石の毎フレーム更新（main.pyのmeteor updateループで呼ぶ）
# ============================================================

def update_fleet_meteor(m, player, WIDTH):
    """
    艦隊所属隕石の追尾ロジック更新。
    main.pyのupdate処理内で通常の移動後に呼ぶ。

    使い方（main.py内の隕石updateループ）:
        for m in meteors:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            if m.get("fleet"):
                from boss5_attack_patterns import update_fleet_meteor
                update_fleet_meteor(m, player, WIDTH)

    Returns:
        bool: Falseなら寿命切れ（meteorsから除去すべき）
    """
    if not m.get("fleet"):
        return True

    # 寿命カウント
    m["life"] = m.get("life", 600) - 1
    if m["life"] <= 0:
        return False

    # プレイエリア右端に入ったら追尾を有効化（右外スポーン用）
    if not m.get("homing_active") and m["x"] <= WIDTH - 40:
        m["homing_active"] = True

    if not m.get("homing_active"):
        return True

    hs = m.get("homing_strength", 0.0)
    if hs <= 0.0 or player is None:
        return True

    # プレイヤーへのベクトル
    dx = player.rect.centerx - m["x"]
    dy = player.rect.centery - m["y"]
    dist = math.hypot(dx, dy)
    if dist < 5:
        return True

    cur_spd = math.hypot(m["vx"], m["vy"])
    if cur_spd < 1.0:
        cur_spd = 4.5

    target_vx = (dx / dist) * cur_spd
    target_vy = (dy / dist) * cur_spd

    # 追尾補間（steering）
    m["vx"] = m["vx"] * (1.0 - hs) + target_vx * hs
    m["vy"] = m["vy"] * (1.0 - hs) + target_vy * hs

    # 最低速度保証
    new_spd = math.hypot(m["vx"], m["vy"])
    if new_spd < 3.5:
        scale = 3.5 / max(new_spd, 0.01)
        m["vx"] *= scale
        m["vy"] *= scale

    # 描画用angleを速度から更新
    m["angle"] = math.atan2(m["vy"], m["vx"])

    return True


# ============================================================
# ★ 艦隊攻撃管理（run_boss5_attacks から呼ぶ）
# ============================================================

def _manage_fleet_attack(
    boss, meteors, player, diff,
    b5_phase, WIDTH, HEIGHT,
    _bubble,
):
    """
    艦隊攻撃のサイクル管理。
    旧「四方から中央」攻撃の代替。
    毎フレーム run_boss5_attacks から呼ぶ。
    """
    boss.b5_fleet_cycle_cd += 1
    cycle = FLEET_CYCLE.get(b5_phase, 500)

    if boss.b5_fleet_cycle_cd < cycle:
        return

    # 発動
    boss.b5_fleet_cycle_cd = 0
    boss.b5_fleet_timer   += 1

    # 編隊パターンをラウンドロビンで選択
    formation_name = FLEET_FORMATIONS[boss.b5_fleet_timer % len(FLEET_FORMATIONS)]
    formation_id   = boss.b5_fleet_timer  # 識別用

    spawn_fleet_formation(
        boss, meteors, player, diff,
        b5_phase, formation_name, formation_id,
        WIDTH, HEIGHT,
    )

    # 吹き出し警告
    if _bubble is not None:
        diff_name = getattr(diff, "name", "NORMAL")
        if diff_name == "NIGHTMARE":
            _bubble.show_text("誘導隕石艦隊！全機突撃！", priority=4)
        elif diff_name == "HARD":
            _bubble.show_text("隕石艦隊接近！追尾あり！", priority=3)
        else:
            _bubble.show_text("隕石艦隊接近！", priority=2)


# ============================================================
# ★ プレイヤー移動制限API（main.py から毎フレーム参照）
# ============================================================

def get_gravity_screen_shake(boss):
    """重力攻撃中の画面振動オフセット (dx, dy)。"""
    gs = getattr(boss, "b5_gravity_state", "idle")
    if gs not in ("warning", "active"):
        return (0, 0)
    t = getattr(boss, "b5_gravity_timer", 0)
    if gs == "warning":
        intensity = min(1.0, t / float(GRAVITY_WARN_F))
        amp = 2 + int(3 * intensity)
    else:
        remain = max(0.0, 1.0 - t / float(GRAVITY_ACTIVE_F))
        amp = 3 + int(4 * remain)
    shake_x = int(math.sin(t * 1.15) * amp + math.sin(t * 2.3) * (amp // 2))
    shake_y = int(math.cos(t * 0.93) * amp + math.cos(t * 1.7) * (amp // 2))
    return (shake_x, shake_y)


def get_gravity_boss_purple_flash_alpha(boss):
    """重力中: ボスを濃い紫で点滅させるアルファ (0=なし)。"""
    gs = getattr(boss, "b5_gravity_state", "idle")
    if gs not in ("warning", "active"):
        return 0
    t = getattr(boss, "b5_gravity_timer", 0)
    pulse = 0.5 + 0.5 * math.sin(t * 0.22)
    if gs == "warning":
        return int(45 + 55 * pulse)
    return int(65 + 75 * pulse)


def get_gravity_player_speed_scale(boss):
    """重力攻撃中ならプレイヤー速度スケールを返す。通常時は1.0。"""
    if not hasattr(boss, "b5_gravity_state"):
        return 1.0
    if boss.b5_gravity_state == "active":
        from game_runtime import RT

        diff_name = RT.g()["diff"].name
        table = GRAVITY_RESTRICT_BY_DIFF.get(
            diff_name, GRAVITY_RESTRICT_BY_DIFF["NORMAL"]
        )
        phase = int(getattr(boss, "_b5_gravity_phase_key", 1))
        return float(table.get(phase, 0.13))
    return 1.0


def get_gravity_boss_shake(boss):
    """ボスの震えオフセット（X方向ピクセル）を返す。描画時に rect.x に加算。"""
    return getattr(boss, "b5_gravity_shake", 0)


def get_gravity_player_shake(boss):
    """プレイヤーの震えオフセット（X, Y ピクセルのタプル）を返す。"""
    if not hasattr(boss, "b5_gravity_state"):
        return (0, 0)
    if boss.b5_gravity_state == "active":
        t = getattr(boss, "b5_gravity_timer", 0)
        shake_x = int(math.sin(t * 0.55) * 3)
        shake_y = int(math.cos(t * 0.78) * 2)
        return (shake_x, shake_y)
    return (0, 0)


def is_gravity_active(boss):
    """重力攻撃が発動中（active フェーズ）かどうか。"""
    return getattr(boss, "b5_gravity_state", "idle") == "active"


def get_gravity_hud_indicator(boss):
    """ボスHP下インジケーター用。(fill_ratio 0〜1, mode) または None。

    warn: 警戒中（左から充填）
    active: 発動中（残り時間で減衰）
    """
    gs = getattr(boss, "b5_gravity_state", "idle")
    if gs not in ("warning", "active"):
        return None
    t = getattr(boss, "b5_gravity_timer", 0)
    if gs == "warning":
        return (min(1.0, t / float(GRAVITY_WARN_F)), "warn")
    return (max(0.0, 1.0 - t / float(GRAVITY_ACTIVE_F)), "active")


# ============================================================
# メイン関数
# ============================================================

def run_boss5_attacks(
    boss, screen, player, player_dead,
    diff, meteors, enemy_bullets, enemy_lasers,
    explosions, b5_fire_x, b5_fire_y,
    is_low_hp, is_critical_hp, is_dying_hp,
    _bubble, alert_timer_container,
    laser_warning_sound, ripple_sound, boss_special_alert_sound,
    spawn_enemy_bullet, spawn_boss5_red_laser, spawn_boss5_ripple,
    spawn_boss5_meteor, spawn_boss5_meteor_custom,
    apply_player_hit,
    WIDTH, HEIGHT,
):
    """Boss5 全フェーズ攻撃処理（隕石のみ版 + 重力攻撃 + 艦隊攻撃）"""

    _init_b5_attrs(boss)

    # ---- フェーズ判定 ----
    if is_dying_hp:
        b5_phase = 4
    elif is_critical_hp:
        b5_phase = 3
    elif is_low_hp:
        b5_phase = 2
    else:
        b5_phase = 1

    # ---- ★ 重力攻撃管理 ----
    _manage_gravity_attack(
        boss, screen, b5_phase, b5_fire_x, b5_fire_y,
        meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
        laser_warning_sound, boss_special_alert_sound,
        _bubble, alert_timer_container,
        WIDTH, HEIGHT,
    )

    # ---- ★ 艦隊編隊攻撃管理（旧四方隕石の代替）----
    _grav_ok = boss.b5_gravity_state in ("idle", "cooldown")
    _sd_state = getattr(boss, "b5_selfdestruct_state", "idle")
    _fleet_ok = (
        _grav_ok
        and _sd_state not in ("warning", "burst")
        and boss.b5_charge_phase == 0
    )
    if _fleet_ok:
        _manage_fleet_attack(
            boss, meteors, player, diff,
            b5_phase, WIDTH, HEIGHT, _bubble,
        )

    # ---- Phase4: 自爆ギミック管理 ----
    if b5_phase == 4:
        _manage_selfdestruct(
            boss, screen, player, player_dead,
            diff, meteors, enemy_bullets,
            b5_fire_x, b5_fire_y,
            _bubble, alert_timer_container,
            laser_warning_sound, boss_special_alert_sound,
            spawn_boss5_meteor, spawn_boss5_meteor_custom,
            WIDTH, HEIGHT,
        )

    # ---- 大技サイクルパラメータ ----
    PHASE_PARAMS = {
        1: (380, 65),
        2: (360, 60),
        3: (300, 55),
        4: (280, 50),
    }
    SPECIAL_CYCLE, CHARGE_F = PHASE_PARAMS.get(b5_phase, (380, 65))

    _b5_rush_busy = getattr(boss, "b5_rush_state", "idle") in ("charge", "wait", "return")
    _rush_ok = _sd_state not in ("warning", "burst") and _grav_ok and not _b5_rush_busy

    if _rush_ok:
        boss.b5_special_timer += 1

    # ---- チャージ開始判定 ----
    if (boss.b5_charge_phase == 0
            and _rush_ok
            and boss.b5_special_timer >= SPECIAL_CYCLE - CHARGE_F):
        if b5_phase == 3:
            # 突進大技: 紫リングのチャージは使わず、そのまま発動へ
            boss.b5_charge_phase = 2
        else:
            boss.b5_charge_phase = 1
        boss.b5_phase_timer = 0
        if laser_warning_sound:
            laser_warning_sound.play()

    # ---- チャージ演出（突進中はスキップ・Phase3は上でスキップ）----
    elif boss.b5_charge_phase == 1 and not is_b5_rush_active(boss):
        boss.b5_phase_timer += 1
        progress = boss.b5_phase_timer / float(CHARGE_F)
        _ticks = pygame.time.get_ticks()
        pulse = int(20 + progress * 44 + math.sin(_ticks * 0.18) * 8)
        for ring_r, ring_col in [
            (pulse + 14, (60,  20, 200)),
            (pulse + 5,  (180, 60, 255)),
            (pulse,      (255, 255, 255)),
        ]:
            pygame.draw.circle(screen, ring_col, (int(b5_fire_x), int(b5_fire_y)), ring_r, 3)
        if boss.b5_phase_timer >= CHARGE_F:
            boss.b5_charge_phase = 2
            boss.b5_phase_timer = 0

    # ---- 大技発動 ----
    elif boss.b5_charge_phase == 2:
        boss.b5_phase_timer += 1
        if b5_phase == 3:
            _fire_special_phase3_rush(
                boss, player, enemy_bullets,
                laser_warning_sound, boss_special_alert_sound,
                _bubble, alert_timer_container,
            )
        else:
            _fire_special_meteor(
                boss, b5_phase,
                b5_fire_x, b5_fire_y,
                meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
                WIDTH, HEIGHT,
            )

    # ---- 通常攻撃（隕石のみ）----
    _normal_ok = (
        boss.b5_charge_phase == 0
        and _sd_state not in ("burst",)
    )
    if _normal_ok:
        _fire_normal_meteor(
            boss, b5_phase,
            b5_fire_x, b5_fire_y,
            diff, meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
            WIDTH, HEIGHT,
        )


# ============================================================
# ★ 重力攻撃管理
# idle → warning（震え＋警告） → active（移動制限＋隕石継続） → cooldown
# ============================================================

def _manage_gravity_attack(
    boss, screen, b5_phase, b5_fire_x, b5_fire_y,
    meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
    laser_warning_sound, boss_special_alert_sound,
    _bubble, alert_timer_container,
    WIDTH, HEIGHT,
):
    """重力攻撃のステートマシン。毎フレーム呼ぶ。"""

    gs = boss.b5_gravity_state
    boss.b5_gravity_timer += 1
    t = boss.b5_gravity_timer

    # -- idle: CDカウント、発動判定 --
    if gs == "idle":
        boss.b5_gravity_shake = 0
        boss.b5_gravity_cycle_cd += 1
        cycle = GRAVITY_CYCLE.get(b5_phase, 700)
        if boss.b5_gravity_cycle_cd >= cycle:
            boss.b5_gravity_cycle_cd   = 0
            boss.b5_gravity_state      = "warning"
            boss.b5_gravity_timer      = 0
            boss._b5_gravity_phase_key = b5_phase
            if laser_warning_sound:
                laser_warning_sound.play()
            if boss_special_alert_sound:
                boss_special_alert_sound.play()
            if alert_timer_container is not None:
                alert_timer_container[0] = 80
            if _bubble is not None:
                _bubble.show_text("重力場展開…動けるか！", priority=5)

    # -- warning: 紫リング拡大（画面振動は get_gravity_screen_shake）--
    elif gs == "warning":
        intensity = min(1.0, t / float(GRAVITY_WARN_F))
        boss.b5_gravity_shake = 0
        _fa = int(18 + math.sin(t * 0.25) * 12)
        _overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _overlay.fill((80, 0, 160, _fa))
        screen.blit(_overlay, (0, 0))
        ring_r = int(40 + t * 2.5)
        pygame.draw.circle(screen, (160, 0, 255),
                           (int(b5_fire_x), int(b5_fire_y)), ring_r, 4)
        pygame.draw.circle(screen, (220, 100, 255),
                           (int(b5_fire_x), int(b5_fire_y)), max(0, ring_r - 20), 2)
        if t >= GRAVITY_WARN_F:
            boss.b5_gravity_state = "active"
            boss.b5_gravity_timer = 0

    # -- active: 重力場発動中 --
    elif gs == "active":
        boss.b5_gravity_shake = 0
        remain_ratio = max(0.0, 1.0 - t / float(GRAVITY_ACTIVE_F))
        _fa_overlay = int(28 * remain_ratio)
        _overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _overlay.fill((60, 0, 130, _fa_overlay))
        screen.blit(_overlay, (0, 0))
        for ring_i in range(4):
            phase_offset = ring_i * (GRAVITY_ACTIVE_F // 4)
            ring_t = (t + phase_offset) % GRAVITY_ACTIVE_F
            max_r  = 340
            ring_r = int(max_r * (1.0 - ring_t / float(GRAVITY_ACTIVE_F)))
            if ring_r <= 0:
                continue
            col = (
                max(0, min(255, 120 + ring_i * 30)),
                0,
                max(0, min(255, 200 + ring_i * 15)),
            )
            pygame.draw.circle(screen, col,
                               (int(b5_fire_x), int(b5_fire_y)), ring_r, 2)
        if t % 45 == 0:
            spawn_boss5_meteor()
        if t % 70 == 0:
            for i in range(4):
                _ang = math.radians(i * 90 + t * 2)
                spawn_boss5_meteor_custom(
                    meteors, boss.rect.centerx, boss.rect.centery,
                    _ang, random.uniform(4.0, 6.5),
                )
        if t >= GRAVITY_ACTIVE_F:
            boss.b5_gravity_state = "cooldown"
            boss.b5_gravity_timer = 0
            boss.b5_gravity_shake = 0
            if _bubble is not None:
                _bubble.show_text("重力場解除！", priority=4)

    # -- cooldown: 次の重力攻撃まで待機 --
    elif gs == "cooldown":
        boss.b5_gravity_shake = 0
        if t >= GRAVITY_COOL_F:
            boss.b5_gravity_state = "idle"
            boss.b5_gravity_timer = 0


# ============================================================
# Phase4 自爆ギミック（隕石のみ版）
# ============================================================

def _manage_selfdestruct(
    boss, screen, player, player_dead,
    diff, meteors, enemy_bullets,
    b5_fire_x, b5_fire_y,
    _bubble, alert_timer_container,
    laser_warning_sound, boss_special_alert_sound,
    spawn_boss5_meteor, spawn_boss5_meteor_custom,
    WIDTH, HEIGHT,
):
    sd = boss.b5_selfdestruct_state
    boss.b5_selfdestruct_timer += 1
    t = boss.b5_selfdestruct_timer

    if sd == "idle":
        if t >= 420:
            boss.b5_selfdestruct_state = "warning"
            boss.b5_selfdestruct_timer = 0
            boss.b5_selfdestruct_shakes = 0
            if laser_warning_sound:
                laser_warning_sound.play()
            if boss_special_alert_sound:
                boss_special_alert_sound.play()
            if alert_timer_container is not None:
                alert_timer_container[0] = 80
            if _bubble is not None:
                _bubble.show("boss_warning")

    elif sd == "warning":
        boss.b5_selfdestruct_shakes = int(math.sin(t * 0.6) * 8)
        _fa = int(80 + math.sin(t * 0.25) * 60)
        _bs = pygame.Surface((boss.rect.width, boss.rect.height), pygame.SRCALPHA)
        _bs.fill((255, 40, 40, _fa))
        screen.blit(_bs, (boss.rect.x + boss.b5_selfdestruct_shakes, boss.rect.y))
        if t >= 60:
            boss.b5_selfdestruct_state = "burst"
            boss.b5_selfdestruct_timer = 0

    elif sd == "burst":
        if t % 3 == 0:
            for _ in range(random.randint(2, 3)):
                _ang = random.uniform(0, math.pi * 2)
                _spd = random.uniform(3.0, 12.0)
                spawn_boss5_meteor_custom(
                    meteors,
                    boss.rect.centerx + random.randint(-60, 60),
                    boss.rect.centery + random.randint(-60, 60),
                    _ang,
                    _spd,
                    small=True,
                    passes_b5_shield=True,
                )
        if t % 15 == 0:
            for i in range(8):
                _ang = math.radians(i * 45 + t * 3)
                _spd = random.uniform(4.0, 11.0)
                spawn_boss5_meteor_custom(
                    meteors,
                    boss.rect.centerx,
                    boss.rect.centery,
                    _ang,
                    _spd,
                    small=True,
                    passes_b5_shield=True,
                )
        if t % 45 == 0:
            for _ in range(5):
                _ang = random.uniform(math.pi * 0.6, math.pi * 1.4)
                _spd = random.uniform(3.5, 13.0)
                spawn_boss5_meteor_custom(
                    meteors,
                    boss.rect.centerx + random.randint(-80, 80),
                    boss.rect.centery + random.randint(-80, 80),
                    _ang,
                    _spd,
                    small=True,
                    passes_b5_shield=True,
                )
        if t >= 160:
            boss.b5_selfdestruct_state  = "cooldown"
            boss.b5_selfdestruct_timer  = 0
            boss.b5_selfdestruct_shakes = 0

    elif sd == "cooldown":
        if t >= 180:
            boss.b5_selfdestruct_state = "idle"
            boss.b5_selfdestruct_timer = 0


# ============================================================
# Phase3 大技: ボス2と同型の突進体当たり
# ============================================================

B5_RUSH_SPEED = 11.5
B5_RUSH_SPIN_PER_FRAME = 11.0
B5_RUSH_RETURN_SPEED = 12.0
B5_RUSH_WAIT_FRAMES = 45


def _fire_special_phase3_rush(
    boss, player, enemy_bullets,
    laser_warning_sound, boss_special_alert_sound,
    _bubble, alert_timer_container,
):
    """Phase3大技: 突進開始（移動・当たりは main.py で更新）。"""
    t = boss.b5_phase_timer
    rs = getattr(boss, "b5_rush_state", "idle")

    if t == 1 and rs == "idle":
        from game_loop.boss5_rush import init_b5_snipe_rush_velocity

        rush_img = boss.image
        b5_begin_rush_scale(boss, rush_img)
        if player is not None:
            init_b5_snipe_rush_velocity(boss, player)
        else:
            boss.b5_rush_vx = -B5_RUSH_SPEED
            boss.b5_rush_vy = 0.0
        boss.b5_rush_spin_angle = 0.0
        from boss5_update import B5_RUSH_CHARGE_FLASH_FRAMES

        boss.b5_rush_flash_timer = B5_RUSH_CHARGE_FLASH_FRAMES
        boss.b5_rush_state = "charge"
        boss.b5_rush_timer = 0
        boss.b5_rush_prev_center = (boss.rect.centerx, boss.rect.centery)
        enemy_bullets.clear()
        if laser_warning_sound:
            laser_warning_sound.play()
        if boss_special_alert_sound:
            boss_special_alert_sound.play()
        if alert_timer_container is not None:
            alert_timer_container[0] = 50
        if _bubble is not None:
            _bubble.show("boss2_rush")

    if rs == "idle" and t > 1:
        boss.b5_charge_phase = 0
        boss.b5_special_timer = 0
        boss.b5_phase_timer = 0


def is_b5_rush_active(boss):
    return getattr(boss, "b5_rush_state", "idle") in ("charge", "wait", "return")


# ============================================================
# 大技（フェーズ別・隕石のみ）
# ============================================================

def _fire_special_meteor(
    boss, b5_phase,
    b5_fire_x, b5_fire_y,
    meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
    WIDTH, HEIGHT,
):
    t = boss.b5_phase_timer
    END_T = {1: 60, 2: 90, 3: 110, 4: 30}

    if b5_phase == 1:
        if t == 1:
            for i in range(12):
                _ang = math.radians(i * 30)
                _spd = 3.2 + (i % 4) * 0.7
                spawn_boss5_meteor_custom(meteors, b5_fire_x, b5_fire_y, _ang, _spd)
        if t == 20:
            for i in range(8):
                _ang = math.radians(i * 45 + 22.5)
                spawn_boss5_meteor_custom(meteors, b5_fire_x, b5_fire_y, _ang, 4.8)
        if t == 35:
            for i in range(6):
                _ang = math.radians(i * 60)
                spawn_boss5_meteor_custom(meteors, b5_fire_x, b5_fire_y, _ang, 5.5)
        if t == 50:
            for i in range(6):
                _ang = math.radians(i * 60 + 30)
                spawn_boss5_meteor_custom(meteors, b5_fire_x, b5_fire_y, _ang, 5.5)
        if t >= END_T[1]:
            boss.b5_charge_phase  = 0
            boss.b5_special_timer = 0
            boss.b5_phase_timer   = 0

    elif b5_phase == 2:
        if t in (5, 13, 21, 29, 37, 45, 53, 61):
            for i in range(6):
                _ang = math.radians(i * 60 + t * 5)
                _spd = random.uniform(4.0, 7.5)
                spawn_boss5_meteor_custom(meteors, boss.rect.centerx, boss.rect.centery, _ang, _spd)
        if t in (20, 40, 60):
            for lane in [HEIGHT // 4, HEIGHT // 2, HEIGHT * 3 // 4]:
                _ang = math.pi + random.uniform(-0.2, 0.2)
                spawn_boss5_meteor_custom(meteors, float(WIDTH + 60), float(lane), _ang, random.uniform(6.0, 9.0))
        if t >= END_T[2]:
            boss.b5_charge_phase  = 0
            boss.b5_special_timer = 0
            boss.b5_phase_timer   = 0

    else:
        boss.b5_charge_phase  = 0
        boss.b5_special_timer = 0
        boss.b5_phase_timer   = 0


# ============================================================
# 通常攻撃（フェーズ別・隕石のみ）
# ============================================================

def _fire_normal_meteor(
    boss, b5_phase,
    b5_fire_x, b5_fire_y,
    diff, meteors, spawn_boss5_meteor, spawn_boss5_meteor_custom,
    WIDTH, HEIGHT,
):
    t = boss.shot_timer
    boss.b5_meteor_timer += 1

    if b5_phase == 1:
        if boss.b5_meteor_timer >= 120:
            boss.b5_meteor_timer = 0
            spawn_boss5_meteor()
            for _lane_y in [HEIGHT // 4, HEIGHT // 2, HEIGHT * 3 // 4]:
                _lane_y += random.randint(-40, 40)
                spawn_boss5_meteor_custom(
                    meteors,
                    float(WIDTH + 60), float(_lane_y),
                    math.pi + random.uniform(-0.25, 0.25),
                    random.uniform(5.0, 8.0),
                )
        if t % 60 == 0:
            for i in range(2):
                _ang = math.radians(i * 180 + t * 2)
                spawn_boss5_meteor_custom(meteors, boss.rect.centerx, boss.rect.centery, _ang, 3.5)

    elif b5_phase == 2:
        if boss.b5_meteor_timer >= 90:
            boss.b5_meteor_timer = 0
            spawn_boss5_meteor()
            for i in range(4):
                _ang = math.radians(i * 90 + 45)
                spawn_boss5_meteor_custom(meteors, boss.rect.centerx, boss.rect.centery, _ang, 5.0)
        if t % 45 == 0:
            _lane_y = random.randint(80, HEIGHT - 80)
            spawn_boss5_meteor_custom(
                meteors, float(WIDTH + 60), float(_lane_y),
                math.pi + random.uniform(-0.3, 0.3),
                random.uniform(6.0, 10.0),
            )

    elif b5_phase == 3:
        if boss.b5_meteor_timer >= 55:
            boss.b5_meteor_timer = 0
            spawn_boss5_meteor()
            if diff.name in ("HARD", "NIGHTMARE"):
                spawn_boss5_meteor()
        if t % 30 == 0:
            for i in range(3):
                _ang = math.radians(i * 120 + t * 3)
                _spd = random.uniform(4.5, 7.0)
                spawn_boss5_meteor_custom(meteors, boss.rect.centerx, boss.rect.centery, _ang, _spd)
        if t % 70 == 0:
            for _ in range(3):
                _lane_y = random.randint(60, HEIGHT - 60)
                spawn_boss5_meteor_custom(
                    meteors, float(WIDTH + 60), float(_lane_y),
                    math.pi + random.uniform(-0.4, 0.4),
                    random.uniform(7.0, 12.0),
                )

    else:
        if boss.b5_meteor_timer >= 40:
            boss.b5_meteor_timer = 0
            spawn_boss5_meteor()
        if t % 20 == 0:
            step = 360 / B5_DYING_RADIAL_PER_BURST
            for i in range(B5_DYING_RADIAL_PER_BURST):
                _ang = math.radians(i * step) + boss.b5_spiral * 0.5
                _spd = random.uniform(3.0, 10.5)
                spawn_boss5_meteor_custom(
                    meteors,
                    boss.rect.centerx,
                    boss.rect.centery,
                    _ang,
                    _spd,
                    small=True,
                    passes_b5_shield=True,
                )
        boss.b5_spiral += 0.12

