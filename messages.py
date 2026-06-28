# messages.py
# ======================================
# プレイヤーセリフ管理モジュール
# ここを編集することで吹き出しのセリフを一元管理できます。
# ======================================

import pygame
import math
import random

# ======================================
# ★ セリフ定義 ★
# 各キー（トリガー名）に対してセリフのリストを設定。
# リストから毎回ランダムに1つ選ばれます。
# ======================================

MESSAGES = {
    # --- パワーアップアイテム取得 ---
    "weapon_up":    ["新兵器だっ！", "火力増加！", "いい感じだ！", "これで戦える！"],
    "shield_up":    ["シールド装備！", "守りを固めたぞ！", "これで安心だ！"],
    "speed_up":     ["スピードUP！", "速い…！", "身が軽い！"],
    "1up":          ["残機+1！", "予備機確保したぞ！", "まだ戦える！"],

    # --- レーザー／通常弾切替・ゲージ ---
    "weapon_mode_laser":  ["レーザー装填！", "ビームモードだ！", "開いたぞ！"],
    "laser_equipped":     ["レーザーを装着した！"],
    "weapon_mode_normal": ["通常弾に切替", "節約モード", "通常弾で行く"],
    "weapon_switch_hint": ["武器切替: B / Button2", "レーザー⇔通常: Bキー"],
    "laser_out":          ["レーザー切れた！", "ゲージが空だ！", "通常弾でいくか"],
    "laser_need_charge":  ["レーザー充填が必要だ！"],
    "laser_low":          ["レーザー残りわずか", "もうすぐ切れる", "節約しろ"],

    # --- シールドダメージ ---
    "shield_hit_3": ["シールド残り3！", "まだ余裕はある！"],
    "shield_hit_2": ["シールド残り2！", "気をつけなければ！"],
    "shield_hit_1": ["シールド残り1！", "これ以上はシールドがもたない！", "次の一発で終わる！"],
    "shield_broken":["シールド破壊！", "直撃は避けろ！", "シールドが・・・"],

    # --- エース / 特別機撃破 ---
    "ace_kill": [
        "エース撃墜！",
        "あの旗艦を落とした！",
        "上等だ、次も来い！",
        "エースごとき…！",
    ],
    "special_kill": [
        "特別機だ！？",
        "あいつを撃ち落とした！",
        "全装備フルチャージだ！",
        "うさぎ…いや、勝った！",
        "これで一気に行ける！",
    ],

    # --- ボス撃破 ---
    "boss_kill_1":  ["ボス1撃破！", "最初の壁を越えた！", "まだまだいくぞ！"],
    "boss_kill_2":  ["ボス2撃破！", "どんどん来い！", "次はどんな敵だ？"],
    "boss_kill_3":  ["ボス3撃破！", "強くなってきた…！", "ここまで来たか！"],
    "boss_kill_4":  ["ボス4撃破！", "化け物め…！", "次で終わりだ！"],
    "boss_kill_5":  ["ボス5撃破！", "やった…！勝利だ！！", "全て終わった！"],
    "boss_kill_6":  ["エクストラボス撃破！", "真の強敵を倒した！", "これで一段落だ！"],
    "extra_suck_1": ["だめだ！操縦不能！！"],
    "extra_suck_2": ["な・・・なんだアレは！"],
    "extra_suck_3": ["戦闘準備だっ！まだ機体は生きてる！"],

    # --- ボス警告 ---
    "boss_warning": ["やってやるぜぇぇぇ！", "デカブツめっ！覚悟しろ！", "でかすぎる..."],

    # --- 被弾（シールドなし）---
    "player_hit":   ["どこに当たった！？", "回避に集中だっ！", "被弾した！", "これ以上は・・・"],

    # --- 残機僅か ---
    "last_life":    ["予備機残り1機か・・・", "もう予備機は次で終わりか・・・", "ここが正念場だ！"],

    # --- 復活 ---
    "revive":       ["まだまだぁぁｌ！", "終わらないぞ！", "まだやれる！"],

    # --- EMS ---
    "ems_get":      ["EMS取得！", "緊急消去システム装備！", "これで一息つける！"],
    "ems_use":      ["EMS発動だっ！", "これでもくらえ！", "緊急消去システムEMS起動！", "全弾消去！"],
    "ems_empty":    ["EMSはもう使えない！", "EMSチャージが必要だ", "あのデカブツからいただくか！"],

    # --- ボス特殊攻撃 ---
    # ボス1: バースト連射
    "boss1_special":["広範囲攻撃か！", "発射口が複数開いたぞ！", "複数弾感知！"],
    # ボス2: 突進
    "boss2_charge": ["突っ込んでくる！", "体当たりか！", "ロックオンされた！"],
    # ボス3: 超高速弾幕
    "boss3_special":["あれは高速弾か！", "高速弾接近！", "多数の高速発射物くるぞ！"],
    # ボス4: 触手
    "boss4_tentacle":["触手が来るぞ！", "あの触手を避けろ！", "なんだ伸びてくる！"],
    # ボス2低HP突進（HP50%以下）
    "boss2_rush":   ["突進してくる！", "あれにぶつかったら", "本体ごとくる！"],

    # --- ボス5 支援機 ---
    "support_arrive_0": ["サンアイ！支援する！", "俺にまかせろ！", "やってやろうぜ！"],
    "support_arrive_1": ["待たせたな！", "なんて化物だ・・・", "まだまだ増援は来るぞ！"],
    "support_arrive_2": ["よぉ相棒！", "さぁここからが本番だ！", "撃ちまくれ！！"],
    "support_arrive_3": ["援護に入る！", "遅れたか？任せろ！", "ここから一緒に行くぞ！"],
    "support_arrive_4": ["増援到着！", "まだ終わらせない！", "押し切るぞ相棒！"],
    "support_leave_0":  ["一時帰還する！", "くっ被弾した一度退く！", "あとは任せたぜ！"],
    "support_leave_1":  ["まずい修理が必要だ・・・", "補給後に合流する！", "無念だ帰還する"],
    "support_leave_2":  ["すまん一度帰還する", "また来るぜ！", "では健闘を祈る！"],
    "support_leave_3":  ["一旦引く！", "弾切れだ・・・戻る！", "必ず戻ってくる次"],
    "support_leave_4":  ["くっ修理が必要だ退避する！", "無念だ・・・", "耐えてくれ！"],

    # --- エクストラステージ 支援機（戦闘中のたまに） ---
    "extra_support_quip_0": ["サンアイ、援護する！", "まだまだいける！", "押し切れ！"],
    "extra_support_quip_1": ["こっちも撃つぞ！", "任せろ！", "隙を突け！"],
    "extra_support_quip_2": ["相棒、行くぞ！", "一気にいく！", "弾幕ごと返す！"],
    "extra_support_quip_3": ["増援は十分だ！", "左右から撃つ！", "終わらせよう！"],
    "extra_support_quip_4": ["全弾発射！", "まだ終わらない！", "ここで決める！"],

    # --- エクストラボス撃破後（各支援機1回・最強の敵撃破＆ぶさかわ星帰還） ---
    "extra_clear_support_0_1": [
        "最強の敵を倒した！ぶさかわ星へ帰還だ！",
        "伝説の強敵を越えた…故郷に凱旋するぞ",
        "こいつが最強か…よくやった、帰ろう",
    ],
    "extra_clear_support_1_1": [
        "やったな！これでぶさかわ星に帰れる",
        "最強クラスの敵を撃破…任務完了だ",
        "震えが止まらない…でも勝った、帰還だ",
    ],
    "extra_clear_support_2_1": [
        "相棒、最強の壁を越えたぞ！",
        "ぶさかわの空が見える…帰ろうぜ",
        "最高の一戦だった…故郷へ帰還！",
    ],
    "extra_clear_support_3_1": [
        "遅れてすまん…でも最強を倒したな",
        "増援ごときじゃない…凱旋だ英雄",
        "ぶさかわ星で祝杯を上げようぜ",
    ],
    "extra_clear_support_4_1": [
        "全機、最強の敵を撃破！帰還開始",
        "ぶさかわ星の皆が待ってる…行こう",
        "これぞ英雄の帰り…故郷へ",
    ],
    "extra_clear_player_1": [
        "やった…！最強の敵を倒した！",
        "ぶさかわ星に帰れる…勝った！",
        "まだ信じられない…でも勝利だ",
    ],
    "extra_clear_player_2": [
        "長い戦いが終わった…",
        "ぶさかわ星へ…みんなで帰還だ",
        "最強を越えた…胸がいっぱいだ",
    ],
    "extra_clear_player_3": [
        "さあ、ぶさかわ星へ帰ろう",
        "故郷の空に帰るぞ…",
        "無事で帰還できる…よかった",
    ],

}

# ======================================
# ★ 優先度定義 ★
# 数値が大きいほど高優先。
# 表示中のメッセージより高優先なら即割り込み。
# 同優先度以下は、現在表示中が残り INTERRUPT_GRACE フレーム
# 以下になっていれば差し替え、そうでなければ捨てる。
# ======================================

PRIORITY = {
    # 最高優先（5）: 撃墜・残機ピンチ・ボス5撃破
    "player_hit":   5,
    "last_life":    5,
    "boss_kill_5":  5,
    "boss_kill_6":  5,
    "extra_suck_1": 5,
    "extra_suck_2": 5,
    "extra_suck_3": 5,

    # 高優先（4）: シールド破壊・ボス撃破・復活・ボス警告
    "shield_broken":4,
    "boss_kill_1":  4,
    "boss_kill_2":  4,
    "boss_kill_3":  4,
    "boss_kill_4":  4,
    "ace_kill":     4,
    "special_kill": 4,
    "boss_warning": 4,
    "revive":       4,

    # 中優先（3）: シールドダメージ・アイテム系・1UP
    "shield_hit_1": 3,
    "shield_hit_2": 3,
    "shield_hit_3": 3,
    "weapon_up":    3,
    "weapon_mode_laser": 3,
    "laser_equipped": 4,
    "weapon_mode_normal": 3,
    "weapon_switch_hint": 3,
    "laser_out":    4,
    "laser_need_charge": 4,
    "laser_low":    3,
    "shield_up":    3,
    "speed_up":     3,
    "1up":          3,

    # EMS（4）: 高優先
    "ems_get":      4,
    "ems_use":      5,
    "ems_empty":    3,

    # ボス特殊攻撃（4）: 高優先（boss_warningと同等にして確実に割り込み表示させる）
    "boss1_special":  4,
    "boss2_charge":   4,
    "boss3_special":  4,
    "boss4_tentacle": 4,
    "boss2_rush":     4,

    "support_arrive_0": 4,
    "support_arrive_1": 4,
    "support_arrive_2": 4,
    "support_arrive_3": 4,
    "support_arrive_4": 4,
    "support_leave_0":  3,
    "support_leave_1":  3,
    "support_leave_2":  3,
    "support_leave_3":  3,
    "support_leave_4":  3,
    "extra_support_quip_0": 2,
    "extra_support_quip_1": 2,
    "extra_support_quip_2": 2,
    "extra_support_quip_3": 2,
    "extra_support_quip_4": 2,
    "extra_clear_support_0_1": 5,
    "extra_clear_support_0_2": 5,
    "extra_clear_support_0_3": 5,
    "extra_clear_support_1_1": 5,
    "extra_clear_support_1_2": 5,
    "extra_clear_support_1_3": 5,
    "extra_clear_support_2_1": 5,
    "extra_clear_support_2_2": 5,
    "extra_clear_support_2_3": 5,
    "extra_clear_support_3_1": 5,
    "extra_clear_support_3_2": 5,
    "extra_clear_support_3_3": 5,
    "extra_clear_support_4_1": 5,
    "extra_clear_support_4_2": 5,
    "extra_clear_support_4_3": 5,
    "extra_clear_player_1": 5,
    "extra_clear_player_2": 5,
    "extra_clear_player_3": 5,
}

DEFAULT_PRIORITY = 1   # PRIORITY に未登録のトリガーはこの値

# ======================================
# BubbleMessage クラス
# ======================================

class BubbleMessage:
    """プレイヤーの吹き出しメッセージを管理するクラス。"""

    FONT_NAME   = None   # None = pygame デフォルトフォント
    FONT_SIZE   = 20
    DISPLAY_FRAMES  = 90    # 表示持続フレーム数（60fps=1.5秒）
    FADE_FRAMES     = 20    # フェードアウト開始フレーム前
    # 同優先度メッセージの割り込み猶予: 残りこのフレーム以下なら差し替え許可
    INTERRUPT_GRACE = 30

    # 吹き出しのデザイン
    BG_COLOR    = (20, 20, 40, 210)     # 背景 (RGBA)
    BORDER_COLOR= (180, 220, 255, 255)  # 枠 (RGBA)
    TEXT_COLOR  = (255, 255, 255)       # 文字色
    TAIL_COLOR  = (180, 220, 255, 200)  # しっぽ色

    PADDING_X = 14
    PADDING_Y = 8

    def __init__(self):
        self._font = pygame.font.SysFont(
            "Yu Gothic,Meiryo,msgothic,Arial", self.FONT_SIZE, bold=True
        )
        # _current: 現在表示中のメッセージ {"text": str, "priority": int}
        self._current: dict | None = None
        self._timer = 0
        # _next: 次に表示するメッセージ（1件のみ予約）
        self._next: dict | None = None

    def clear(self) -> None:
        """表示中・予約中の吹き出しをすべて消す。"""
        self._current = None
        self._next = None
        self._timer = 0

    # --------------------------------------------------
    # 外部API: メッセージを表示する
    # --------------------------------------------------
    def show(
        self,
        trigger: str,
        anchor_rect: pygame.Rect | None = None,
        anchor_style: str = "player",
    ):
        """トリガー名に対応するセリフをランダム選択して表示リクエスト。

        anchor_rect を渡すと自機ではなくその矩形を基準に吹き出しを描画する。
        anchor_style は "player"（自機）、"support"（支援機上）、"support_right"（支援機の右）。

        優先度制御:
          - 現在表示中より高優先 → 即割り込み（フェードインで切り替え）
          - 同優先度 かつ 残り INTERRUPT_GRACE フレーム以下 → 差し替え
          - それ以外 → _next に予約（1件のみ、古い予約は上書き）
        """
        msgs = MESSAGES.get(trigger)
        if not msgs:
            return
        text = random.choice(msgs)
        priority = PRIORITY.get(trigger, DEFAULT_PRIORITY)
        self._enqueue(text, priority, anchor_rect, anchor_style)

    def show_text(
        self,
        text: str,
        priority: int = DEFAULT_PRIORITY,
        anchor_rect: pygame.Rect | None = None,
        anchor_style: str = "player",
    ):
        """任意テキストを直接表示する。"""
        self._enqueue(text, priority, anchor_rect, anchor_style)

    def _enqueue(
        self,
        text: str,
        priority: int,
        anchor_rect: pygame.Rect | None = None,
        anchor_style: str = "player",
    ):
        """割り込み優先度ロジックの核。"""
        # 現在表示中がない → 即表示
        if self._current is None:
            self._activate(text, priority, anchor_rect, anchor_style)
            return

        cur_pri = self._current["priority"]

        if priority > cur_pri:
            # 高優先 → 即割り込み
            self._activate(text, priority, anchor_rect, anchor_style)
            self._next = None   # 予約も破棄
        elif priority == cur_pri and self._timer <= self.INTERRUPT_GRACE:
            # 同優先度 かつ 残り少ない → 差し替え
            self._activate(text, priority, anchor_rect, anchor_style)
            self._next = None
        else:
            # 低優先または表示時間がまだ長い → 予約に入れる
            # 既存の予約より優先度が高いときのみ上書き
            if self._next is None or priority >= self._next["priority"]:
                # 現在と同じテキストは予約しない
                if text != self._current.get("text"):
                    self._next = {
                        "text": text,
                        "priority": priority,
                        "anchor": anchor_rect,
                        "anchor_style": anchor_style,
                    }

    def _activate(
        self,
        text: str,
        priority: int,
        anchor_rect: pygame.Rect | None = None,
        anchor_style: str = "player",
    ):
        """指定テキストを現在表示にセット（フェードイン付き）。"""
        self._current = {
            "text": text,
            "priority": priority,
            "anchor": anchor_rect,
            "anchor_style": anchor_style,
        }
        self._timer = self.DISPLAY_FRAMES

    # --------------------------------------------------
    # 毎フレーム呼ぶ: 更新 & 描画
    # --------------------------------------------------
    def update_and_draw(
        self,
        screen: pygame.Surface,
        player_rect: pygame.Rect,
        follow_anchor: pygame.Rect | None = None,
    ):
        """毎フレームメインループから呼び出す。

        follow_anchor: anchor_style が support のとき、毎フレーム追従する矩形。
        """
        # 現在表示中がなく、予約があれば次を表示
        if self._current is None and self._next is not None:
            entry = self._next
            self._next = None
            self._activate(
                entry["text"],
                entry["priority"],
                entry.get("anchor"),
                entry.get("anchor_style", "player"),
            )

        if self._current is None:
            return

        self._timer -= 1
        if self._timer <= 0:
            self._current = None
            # 予約があればすぐ次を表示（フレームを空けない）
            if self._next is not None:
                entry = self._next
                self._next = None
                self._activate(
                    entry["text"],
                    entry["priority"],
                    entry.get("anchor"),
                    entry.get("anchor_style", "player"),
                )
            return

        # フェードアルファ計算
        alpha = 255
        if self._timer < self.FADE_FRAMES:
            alpha = int(255 * self._timer / self.FADE_FRAMES)

        text = self._current["text"]
        style = self._current.get("anchor_style", "player")
        if style in ("support", "support_right") and follow_anchor is not None:
            anchor_rect = follow_anchor
        else:
            anchor = self._current.get("anchor")
            anchor_rect = anchor if anchor is not None else player_rect
        self._draw_bubble(screen, anchor_rect, text, alpha, style)

    # --------------------------------------------------
    # 内部: 吹き出し描画
    # --------------------------------------------------
    def _draw_bubble(
        self,
        screen: pygame.Surface,
        anchor_rect: pygame.Rect,
        text: str,
        alpha: int,
        style: str = "player",
    ):
        txt_surf = self._font.render(text, True, self.TEXT_COLOR)
        tw, th = txt_surf.get_size()

        bw = tw + self.PADDING_X * 2
        bh = th + self.PADDING_Y * 2

        screen_w, screen_h = screen.get_size()

        if style == "support_right":
            tail_x = anchor_rect.right + 4
            tail_y = anchor_rect.centery
            bx = tail_x + 16
            by = tail_y - bh // 2
        elif style == "support":
            tail_x = anchor_rect.centerx
            tail_y = anchor_rect.top + 8
            bx = tail_x - bw // 2
            by = tail_y - bh - 16
        else:
            # 吹き出し位置: 自機コックピット付近（自機の左上あたり）
            tail_x = anchor_rect.centerx - 28
            tail_y = anchor_rect.top + 10
            bx = tail_x - bw - 8
            by = tail_y - bh - 14

        if bx < 8:
            bx = 8
        if bx + bw > screen_w - 8:
            bx = screen_w - bw - 8
        if by < 54:
            by = 54
        if by + bh > screen_h - 8:
            by = screen_h - bh - 8

        # 背景サーフェス（SRCALPHA）
        bg_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg_color_a = (*self.BG_COLOR[:3], min(255, int(self.BG_COLOR[3] * alpha / 255)))
        pygame.draw.rect(bg_surf, bg_color_a, (0, 0, bw, bh), border_radius=8)

        border_a = (*self.BORDER_COLOR[:3], min(255, int(self.BORDER_COLOR[3] * alpha / 255)))
        pygame.draw.rect(bg_surf, border_a, (0, 0, bw, bh), width=2, border_radius=8)

        screen.blit(bg_surf, (bx, by))

        # しっぽ（三角形）
        tail_surf = pygame.Surface((20, 16), pygame.SRCALPHA)
        tail_a = (*self.TAIL_COLOR[:3], min(255, int(self.TAIL_COLOR[3] * alpha / 255)))
        if style == "support_right":
            t_pts = [(2, 8), (2, 0), (14, 8)]
            tail_blit_x = bx - 12
        elif style == "support":
            t_pts = [(10, 14), (18, 14), (14, 0)]
            tail_blit_x = bx + bw // 2 - 10
        else:
            t_pts = [(20, 0), (2, 0), (20, 14)]
            tail_blit_x = bx + bw - 18
        pygame.draw.polygon(tail_surf, tail_a, t_pts)
        screen.blit(tail_surf, (tail_blit_x, by + bh - 2))

        # テキスト描画（アルファは Surface ごと適用）
        txt_a_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        txt_a_surf.fill((0, 0, 0, 0))
        txt_col_a = (*self.TEXT_COLOR[:3], alpha)
        txt_surf_a = self._font.render(text, True, txt_col_a)
        txt_a_surf.blit(txt_surf_a, (0, 0))
        screen.blit(txt_a_surf, (bx + self.PADDING_X, by + self.PADDING_Y))
