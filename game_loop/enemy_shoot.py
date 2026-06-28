# game_loop/enemy_shoot.py
"""敵タイプ別の射撃パターン。"""

import math
import random

from enemy_bullets import spawn_enemy_bullet
from game_loop.resources import frame_core
from game_runtime import RT


def enemy_on_screen(enemy, width: int) -> bool:
    return enemy.rect.right > 80 and enemy.rect.left < width - 40


def enemy_combat_active(enemy, width: int) -> bool:
    """画面内に十分入り、弾幕を出してよい状態か。"""
    if not enemy_on_screen(enemy, width):
        return False
    if getattr(enemy, "combat_ready", True):
        return enemy.rect.left < width - 100
    return enemy.rect.left < width - 220


def try_enemy_shoot(enemy) -> None:
    core = frame_core()
    diff = core.diff
    player = core.player
    width = core.width

    if getattr(enemy, "grunt_behavior", None):
        from grunt_behavior import try_grunt_shoot

        try_grunt_shoot(enemy, diff, width, core.height)
        return

    if not enemy_combat_active(enemy, width):
        if not getattr(enemy, "combat_ready", True) and enemy.rect.left < width - 200:
            enemy.combat_ready = True
        return

    cx = enemy.rect.centerx
    cy = enemy.rect.centery
    et = enemy.type
    vt = getattr(enemy, "variant", 0)

    # 発射タイミング分散（敵ごとに固有オフセット）
    ofs = getattr(enemy, "shot_offset", 0)
    t = enemy.timer + ofs

    # 難易度パラメータを取得
    bspd  = diff.enemy_bullet_spd          # 基底弾速
    fscl  = diff.enemy_fire_scale          # 発射間隔係数(>1=遅い)
    plus  = diff.enemy_pattern_plus        # 強化パターン有効フラグ

    # 発射間隔スケールを適用したタイミング判定ヘルパ
    def fire_t(base_interval, offset=0):
        interval = max(1, int(base_interval * fscl))
        return (t - offset) % interval == 0

    # プレイヤー方向の単位ベクトル取得
    def aim_dir():
        dx = player.rect.centerx - cx
        dy = player.rect.centery - cy
        dist = max(1, math.hypot(dx, dy))
        return dx / dist, dy / dist

    # ======================================
    # TYPE 0: 直線型（スラスト変化）
    #   variant 0: 等速飛行
    #     EASY/NORMAL: 正面直線1発
    #     HARD:        正面＋上下斜め3way
    #     NIGHTMARE:   3way＋後方バウンス弾追加
    #   variant 1: 急加速突入
    #     EASY/NORMAL: 加速前に狙い撃ち、加速後に直線
    #     HARD:        加速前に扇3発
    #     NIGHTMARE:   扇3発＋加速後にホーミング追加
    #   variant 2: 減速停止→ダッシュ
    #     EASY/NORMAL: 停止中に上下交互
    #     HARD:        停止中にプレイヤー狙い追加
    #     NIGHTMARE:   停止中に全方位8発バースト
    # ======================================
    if et == 0:

        if vt == 0:
            if fire_t(60):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd, vy=0, image_type="normal")
            if plus:
                # HARD/NIGHTMARE: 上下斜め各1発追加
                if fire_t(60, offset=10):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.85, vy=-bspd * 0.4, image_type="normal")
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.85, vy= bspd * 0.4, image_type="normal")
            if diff.name == "NIGHTMARE":
                # NIGHTMARE: 後方バウンス弾
                if fire_t(90, offset=45):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=bspd * 0.5, vy=0,
                                       image_type="normal", bounce=True)

        elif vt == 1:
            tt = getattr(enemy, "thrust_timer", 0)
            if 32 <= tt <= 34 and fire_t(33):
                adx, ady = aim_dir()
                if plus:
                    # 扇3発（左・左上・左下）
                    for spread_vy in (-bspd * 0.35, 0, bspd * 0.35):
                        spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd, vy=ady * bspd + spread_vy, image_type="normal")
                else:
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd, vy=ady * bspd, image_type="normal")
            if tt > 40 and fire_t(70):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 1.1, vy=0, image_type="normal")
            if diff.name == "NIGHTMARE" and tt > 40 and fire_t(90, offset=45):
                # NIGHTMARE: 加速後にホーミング1発追加
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd * 0.7, vy=ady * bspd * 0.7,
                                   homing=True, image_type="homing")

        elif vt == 2:
            tt = getattr(enemy, "thrust_timer", 0)
            # 停止期間（tt:30-70）は最大2発に制限してEASYで連発しないようにする
            if 30 <= tt <= 70:
                _stop_shots = getattr(enemy, "stop_shot_count", 0)
                if _stop_shots < 2 and fire_t(22):
                    vy_dir = bspd * 0.45 if (t // max(1, int(22 * fscl))) % 2 == 0 else -bspd * 0.45
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.75, vy=vy_dir, image_type="normal")
                    enemy.stop_shot_count = _stop_shots + 1
                if plus and fire_t(30, offset=15):
                    # HARD/NIGHTMARE: 停止中にプレイヤー狙い追加
                    adx, ady = aim_dir()
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd, vy=ady * bspd, image_type="normal")
            elif tt > 70:
                # 停止終了後にカウントリセット
                enemy.stop_shot_count = 0
            if diff.name == "NIGHTMARE" and tt == 50:
                # NIGHTMARE: 停止中盤に全方位8発バースト
                for ang in range(0, 360, 45):
                    rad = math.radians(ang)
                    spawn_enemy_bullet(x=float(cx), y=float(cy),
                                       vx=math.cos(rad) * bspd * 0.7,
                                       vy=math.sin(rad) * bspd * 0.7,
                                       image_type="normal")

    # ======================================
    # TYPE 1: サイン波型（振幅・周波数 variant別）
    #   variant 0: 波に乗る斜め弾
    #     EASY/NORMAL: 波向きに1発＋狙い1発
    #     HARD:        波向きに1発＋狙い1発＋前方ブレ弾
    #     NIGHTMARE:   全方向に扇5発
    #   variant 1: 大振幅・折り返しで発射
    #     EASY/NORMAL: 折り返しで狙い1発
    #     HARD:        折り返しで2発（上下オフセット）
    #     NIGHTMARE:   折り返しで3発＋中間にバウンス弾
    #   variant 2: 高速サイン
    #     EASY/NORMAL: 正面＋時差上下
    #     HARD:        正面高速＋時差ホーミング
    #     NIGHTMARE:   正面＋時差ホーミング＋追尾強化弾
    # ======================================
    elif et == 1:

        if vt == 0:
            if fire_t(65):
                d = enemy.sine_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.75, vy=d * bspd * 0.4, image_type="normal")
            if fire_t(75, offset=30):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd * 0.9, vy=ady * bspd * 0.9, image_type="normal")
            if plus:
                # HARD/NIGHTMARE: 前方ランダムブレ弾
                if fire_t(50, offset=20):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=-bspd * 0.9,
                                       vy=random.uniform(-bspd * 0.3, bspd * 0.3),
                                       image_type="normal")
            if diff.name == "NIGHTMARE":
                # 扇5発（前方中心に±30°ずつ）
                if fire_t(80, offset=40):
                    for ang in (-60, -30, 0, 30, 60):
                        rad = math.radians(180 + ang)
                        spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                           vx=math.cos(rad) * bspd,
                                           vy=math.sin(rad) * bspd,
                                           image_type="normal")

        elif vt == 1:
            sin_amp = getattr(enemy, "sin_amp", 130)
            near_top = enemy.rect.centery <= enemy.base_y - sin_amp * 0.75
            near_bot = enemy.rect.centery >= enemy.base_y + sin_amp * 0.75
            if (near_top or near_bot) and fire_t(30):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd, vy=ady * bspd, image_type="normal")
                if plus:
                    # HARD/NIGHTMARE: 上下オフセット追加弾
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy - 14, vx=adx * bspd, vy=ady * bspd - bspd * 0.25, image_type="normal")
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy + 14, vx=adx * bspd, vy=ady * bspd + bspd * 0.25, image_type="normal")
            if diff.name == "NIGHTMARE" and fire_t(60, offset=30):
                # 中間にバウンス弾
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.6, vy=bspd * 0.5,
                                   image_type="normal", bounce=True)

        elif vt == 2:
            if fire_t(45):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd, vy=0, image_type="normal")
            if fire_t(100):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy - 12, vx=-bspd * 0.9, vy=-bspd * 0.3, image_type="normal")
            if fire_t(100, offset=15):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy + 12, vx=-bspd * 0.9, vy= bspd * 0.3, image_type="normal")
            if plus:
                # HARD/NIGHTMARE: 時差ホーミング追加
                if fire_t(90, offset=45):
                    adx, ady = aim_dir()
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=adx * bspd * 0.65, vy=ady * bspd * 0.65,
                                       homing=True, image_type="homing")
            if diff.name == "NIGHTMARE":
                # 強化ホーミング弾（追尾速度高め）
                if fire_t(110, offset=55):
                    adx, ady = aim_dir()
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=adx * bspd * 0.8, vy=ady * bspd * 0.8,
                                       homing=True, image_type="homing")

    # ======================================
    # TYPE 2: ホーミング型（接近停止）
    #   variant 0: hover中ホーミング連射
    #     EASY/NORMAL: hover中1発＋撃ち逃げ
    #     HARD:        hover中2発（上下時差）
    #     NIGHTMARE:   hover中3発同時＋撃ち逃げ強化
    #   variant 1: 停止中の狙い撃ち
    #     EASY/NORMAL: hover中ゆっくり狙い
    #     HARD:        hover中に加えて接近中も低速ホーミング
    #     NIGHTMARE:   hover中2発＋接近中に拡散弾
    #   variant 2: 溜め→ホーミングバースト
    #     EASY/NORMAL: 時差2発
    #     HARD:        時差3発
    #     NIGHTMARE:   時差3発＋トリガー後に扇状直線弾
    # ======================================
    elif et == 2:
        state_2 = getattr(enemy, "approach_state", "move")

        if vt == 0:
            # hover中ホーミング（hover開始ごとに1回制限）
            base_iv = 85
            if state_2 == "hover" and not getattr(enemy, "hover_shot_done", False) and fire_t(base_iv):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                   vx=adx * bspd * 0.55, vy=ady * bspd * 0.55,
                                   homing=True, image_type="homing")
                enemy.hover_shot_done = True  # hover1回につき1発のみ
            if plus and state_2 == "hover" and not getattr(enemy, "hover_shot_done2", False) and fire_t(base_iv, offset=int(base_iv * fscl) // 2):
                # HARD/NIGHTMARE: 時差2発目
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy - 12,
                                   vx=adx * bspd * 0.5, vy=ady * bspd * 0.5,
                                   homing=True, image_type="homing")
                enemy.hover_shot_done2 = True
            if diff.name == "NIGHTMARE" and state_2 == "hover" and not getattr(enemy, "hover_shot_done3", False) and fire_t(base_iv, offset=int(base_iv * fscl) // 3):
                # 3発目
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy + 12,
                                   vx=adx * bspd * 0.45, vy=ady * bspd * 0.45,
                                   homing=True, image_type="homing")
                enemy.hover_shot_done3 = True
            # hover→retreatに移行したらフラグリセット
            if state_2 == "retreat":
                enemy.hover_shot_done = False
                enemy.hover_shot_done2 = False
                enemy.hover_shot_done3 = False
            # 退場中撃ち逃げ
            if state_2 == "retreat" and fire_t(30):
                n_shots = 3 if diff.name == "NIGHTMARE" else 1
                for i in range(n_shots):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=-bspd, vy=random.choice([-bspd * 0.25, 0, bspd * 0.25]),
                                       image_type="normal")

        elif vt == 1:
            if state_2 == "hover" and fire_t(60):
                adx, ady = aim_dir()
                spd = bspd * 0.5
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * spd, vy=ady * spd, image_type="normal")
            if plus and state_2 in ("move", "hover") and fire_t(80, offset=40):
                # HARD/NIGHTMARE: 接近中にも低速ホーミング
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                   vx=adx * bspd * 0.4, vy=ady * bspd * 0.4,
                                   homing=True, image_type="homing")
            if diff.name == "NIGHTMARE" and state_2 == "move" and fire_t(50, offset=25):
                # 拡散弾（前方3方向）
                for spread_vy in (-bspd * 0.4, 0, bspd * 0.4):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=-bspd * 0.85, vy=spread_vy,
                                       image_type="normal")

        elif vt == 2:
            if not enemy.burst_ready and fire_t(100):
                enemy.freeze_timer = 40
                enemy.burst_ready = True
            if enemy.burst_ready and enemy.freeze_timer == 1:
                adx, ady = aim_dir()
                # 1発目
                spawn_enemy_bullet(x=float(cx), y=float(cy - 10),
                                   vx=adx * bspd * 0.65, vy=ady * bspd * 0.65,
                                   homing=True, image_type="homing")
                if diff.name == "NIGHTMARE":
                    # 即座に扇状直線弾3発
                    for ang in (-40, 0, 40):
                        rad = math.radians(180 + ang)
                        spawn_enemy_bullet(x=float(cx), y=float(cy),
                                           vx=math.cos(rad) * bspd * 0.9,
                                           vy=math.sin(rad) * bspd * 0.9,
                                           image_type="normal")
                enemy.burst_ready = False
            # 30f後に2発目
            if not enemy.burst_ready and enemy.freeze_timer == 0 and fire_t(100, offset=70):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=float(cx), y=float(cy + 10),
                                   vx=adx * bspd * 0.7, vy=ady * bspd * 0.7,
                                   homing=True, image_type="homing")
            # HARD/NIGHTMARE: 60f後に3発目
            if plus and not enemy.burst_ready and enemy.freeze_timer == 0 and fire_t(100, offset=40):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=float(cx), y=float(cy),
                                   vx=adx * bspd * 0.75, vy=ady * bspd * 0.75,
                                   homing=True, image_type="homing")

    # ======================================
    # TYPE 3: 重装甲型（体当たり・2段階攻撃）
    #   variant 0: HP半減で体当たり突進
    #     EASY/NORMAL: 突進前に正面高速弾
    #     HARD:        突進前に3way
    #     NIGHTMARE:   突進前に3way＋バースト直前に全方位
    #   variant 1: 上下交互砲撃
    #     EASY/NORMAL: 上下時差＋狙い打ち
    #     HARD:        上下時差＋狙い打ち＋加速弾
    #     NIGHTMARE:   全方位ばらまき＋ホーミング追加
    #   variant 2: 精密狙い撃ち
    #     EASY/NORMAL: 精密1発＋加速弾
    #     HARD:        精密1発＋加速弾＋横ばらまき
    #     NIGHTMARE:   精密2発同時＋加速弾＋ホーミング
    # ======================================
    elif et == 3:

        if vt == 0:
            if not enemy.charge and enemy.hp <= 3:
                enemy.charge = True
                adx, ady = aim_dir()
                enemy.charge_vx = adx * enemy.speed * 2.2
                enemy.charge_vy = ady * enemy.speed * 2.2
                if diff.name == "NIGHTMARE":
                    # 突進直前に全方位8発
                    for ang in range(0, 360, 45):
                        rad = math.radians(ang)
                        spawn_enemy_bullet(x=float(cx), y=float(cy),
                                           vx=math.cos(rad) * bspd * 0.75,
                                           vy=math.sin(rad) * bspd * 0.75,
                                           image_type="normal")
            if not enemy.charge and fire_t(35):
                if plus:
                    # HARD/NIGHTMARE: 3way
                    for spread_vy in (-bspd * 0.35, 0, bspd * 0.35):
                        spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 1.1, vy=spread_vy, image_type="normal")
                else:
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 1.1, vy=0, image_type="normal")

        elif vt == 1:
            if fire_t(50):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy - 22, vx=-bspd, vy=-bspd * 0.15, image_type="normal")
            if fire_t(75, offset=38):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy + 22, vx=-bspd, vy= bspd * 0.15, image_type="normal")
            if fire_t(120, offset=60):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd * 1.05, vy=ady * bspd * 1.05, image_type="normal")
            if plus:
                # HARD/NIGHTMARE: 加速弾追加
                if fire_t(110, offset=55):
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.35, vy=0,
                                       image_type="normal", speed_type="accel",
                                       action_timer=25, cruise_vx=-bspd * 0.35, cruise_vy=0.0)
            if diff.name == "NIGHTMARE":
                # 全方位ばらまき（6発）
                if fire_t(90, offset=45):
                    for ang in range(0, 360, 60):
                        rad = math.radians(ang)
                        spawn_enemy_bullet(x=float(cx), y=float(cy),
                                           vx=math.cos(rad) * bspd * 0.8,
                                           vy=math.sin(rad) * bspd * 0.8,
                                           image_type="normal")
                # ホーミング追加
                if fire_t(130, offset=65):
                    adx, ady = aim_dir()
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=adx * bspd * 0.6, vy=ady * bspd * 0.6,
                                       homing=True, image_type="homing")

        elif vt == 2:
            if fire_t(70):
                adx, ady = aim_dir()
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=adx * bspd, vy=ady * bspd, image_type="normal")
                if diff.name == "NIGHTMARE":
                    # 精密2発同時（微ズレ）
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy - 8, vx=adx * bspd, vy=ady * bspd - bspd * 0.15, image_type="normal")
            if fire_t(150, offset=75):
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.3, vy=0,
                                   image_type="normal", speed_type="accel",
                                   action_timer=30, cruise_vx=-bspd * 0.3, cruise_vy=0.0)
            if plus:
                # HARD/NIGHTMARE: 横ばらまき
                if fire_t(80, offset=40):
                    for vy_off in (-bspd * 0.55, bspd * 0.55):
                        spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.85, vy=vy_off, image_type="normal")
            if diff.name == "NIGHTMARE":
                # ホーミング追加
                if fire_t(100, offset=50):
                    adx, ady = aim_dir()
                    spawn_enemy_bullet(x=enemy.rect.x, y=cy,
                                       vx=adx * bspd * 0.7, vy=ady * bspd * 0.7,
                                       homing=True, image_type="homing")

    # ======================================
    # TYPE 4: スイープ型（蛇行しながら扇・狙い撃ち）
    # ======================================
    elif et == 4:
        if fire_t(55):
            spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd, vy=0, image_type="normal")
        if plus and fire_t(55, offset=18):
            for spread_vy in (-bspd * 0.32, bspd * 0.32):
                spawn_enemy_bullet(
                    x=enemy.rect.x, y=cy, vx=-bspd * 0.9, vy=spread_vy, image_type="normal"
                )
        if fire_t(95, offset=40):
            adx, ady = aim_dir()
            spawn_enemy_bullet(
                x=enemy.rect.x, y=cy, vx=adx * bspd * 0.95, vy=ady * bspd * 0.95, image_type="normal"
            )
        if diff.name == "NIGHTMARE" and fire_t(110, offset=55):
            spawn_enemy_bullet(
                x=enemy.rect.x,
                y=cy,
                vx=-bspd * 0.35,
                vy=0,
                image_type="normal",
                speed_type="accel",
                action_timer=25,
                cruise_vx=-bspd * 0.35,
                cruise_vy=0.0,
            )

    # ======================================
    # TYPE 5: エース機体（舷側3way・紫加速砲・編隊リーダー）
    # ======================================
    elif et == 5:
        phase = getattr(enemy, "ace_phase", "cruise")
        if phase == "enter":
            if fire_t(90) and enemy.timer > 40:
                spawn_enemy_bullet(x=enemy.rect.x, y=cy, vx=-bspd * 0.55, vy=0, image_type="normal")
            return

        if phase in ("cruise", "exit"):
            if fire_t(48):
                for spread_vy in (-bspd * 0.38, 0, bspd * 0.38):
                    spawn_enemy_bullet(
                        x=enemy.rect.x, y=cy, vx=-bspd * 0.95, vy=spread_vy, image_type="normal"
                    )
            if fire_t(72, offset=20):
                adx, ady = aim_dir()
                spawn_enemy_bullet(
                    x=enemy.rect.x, y=cy, vx=adx * bspd * 0.88, vy=ady * bspd * 0.88, image_type="normal"
                )

        if phase == "broadside":
            if fire_t(32):
                spawn_enemy_bullet(
                    x=enemy.rect.x,
                    y=cy - 18,
                    vx=-bspd * 0.42,
                    vy=-bspd * 0.55,
                    image_type="normal",
                    speed_type="accel",
                    action_timer=28,
                    cruise_vx=-bspd * 0.55,
                    cruise_vy=-bspd * 0.35,
                )
                spawn_enemy_bullet(
                    x=enemy.rect.x,
                    y=cy + 18,
                    vx=-bspd * 0.42,
                    vy=bspd * 0.55,
                    image_type="normal",
                    speed_type="accel",
                    action_timer=28,
                    cruise_vx=-bspd * 0.55,
                    cruise_vy=bspd * 0.35,
                )
            if plus and fire_t(55, offset=12):
                for spread_vy in (-bspd * 0.5, bspd * 0.5):
                    spawn_enemy_bullet(
                        x=enemy.rect.x, y=cy, vx=-bspd, vy=spread_vy, image_type="normal"
                    )
            if diff.name == "NIGHTMARE" and fire_t(80, offset=40):
                for ang in (-20, 0, 20):
                    rad = math.radians(180 + ang)
                    spawn_enemy_bullet(
                        x=float(cx),
                        y=float(cy),
                        vx=math.cos(rad) * bspd * 0.85,
                        vy=math.sin(rad) * bspd * 0.85,
                        image_type="normal",
                    )
