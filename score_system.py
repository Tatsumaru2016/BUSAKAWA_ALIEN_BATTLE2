# score_system.py — チェーン倍率・ボス撃破スコア確定

import math

import pygame

from ui_bars import draw_glossy_bar_horizontal, draw_glossy_panel

CHAIN_MAX_FRAMES = 210  # 連鎖猶予（60fps: 約3.5秒）
# 到達時に短いフラッシュ＋SE（1ストリークで各段階1回まで）
CHAIN_MILESTONES = (5, 10, 20, 30, 50)
CHAIN_FLASH_FRAMES = 28
CHAIN_POP_FRAMES = 24
# 連鎖MAX到達時のみ表示（維持中は非表示）
CHAIN_MAX_CALLOUT_FRAMES = 48

# 連鎖カウント上限（HUD表示・register_kill はこのまま伸びる）
CHAIN_COUNT_MAX = 50

# chain_count → 得点倍率（インデックス = min(chain, len-1)）
# 高連鎖ほど「数」は伸びるが倍率は緩やか（12連鎖時点で旧12xより大幅に低い）
def _build_multiplier_table() -> tuple[int, ...]:
    table = [1] * (CHAIN_COUNT_MAX + 1)
    for c in range(1, CHAIN_COUNT_MAX + 1):
        if c <= 2:
            m = 1
        elif c <= 6:
            m = 2
        elif c <= 12:
            m = 3
        elif c <= 22:
            m = 4
        elif c <= 35:
            m = 5
        else:
            m = 6
        table[c] = m
    return tuple(table)


MULTIPLIER_TABLE = _build_multiplier_table()
CHAIN_MULTIPLIER_CAP = max(MULTIPLIER_TABLE)

# 8連鎖以降の撃破ボーナス tier（倍率は掛けず、tier 成長も遅め）
MAX_CHAIN_KILL_TIER = 3
CHAIN_KILL_BONUS_FROM = 8


def chain_multiplier_maxed(chain: int) -> bool:
    """倍率テーブル上限に達した連鎖数か。"""
    if chain <= 0:
        return False
    idx = min(chain, len(MULTIPLIER_TABLE) - 1)
    return MULTIPLIER_TABLE[idx] >= CHAIN_MULTIPLIER_CAP

BOSS_HIT_CAP = {
    1: 80_000,
    2: 100_000,
    3: 120_000,
    4: 160_000,
    5: 220_000,
    6: 240_000,
}

TALLY_FRAMES_PER_LINE = 38
TALLY_HOLD_FRAMES = 55
TALLY_HOLD_FRAMES_FINAL = 90
TALLY_HOLD_FRAMES_EXTRA = 300

# 黒パネル：透過率70%（=不透明度30%）… 視認性のため枠はやや濃いめ
TALLY_PANEL_ALPHA = int(255 * 0.30)
TALLY_PANEL_BORDER_ALPHA = int(255 * 0.55)


def difficulty_scale(diff):
    return float(getattr(diff, "score_scale", 1.0))


def scaled_score(base_pts, diff, multiplier):
    return int(base_pts * difficulty_scale(diff) * multiplier)


def boss_hit_cap(diff, boss_type):
    return int(BOSS_HIT_CAP.get(boss_type, 100_000) * difficulty_scale(diff))


class ScoreChain:
    """連続撃破チェーンとラン倍率。"""

    def __init__(self):
        self.chain = 0
        self.timer = 0
        self.boss_hit_bank = 0
        self._boss_hit_cap = 0
        self.chain_flash_timer = 0
        self.chain_pop_timer = 0
        self.chain_max_callout_timer = 0
        self.pending_milestone = None
        self._milestones_fired = set()

    def reset(self):
        self.chain = 0
        self.timer = 0
        self.boss_hit_bank = 0
        self._boss_hit_cap = 0
        self.chain_flash_timer = 0
        self.chain_pop_timer = 0
        self.chain_max_callout_timer = 0
        self.pending_milestone = None
        self._milestones_fired = set()

    def multiplier(self):
        idx = min(self.chain, len(MULTIPLIER_TABLE) - 1)
        return MULTIPLIER_TABLE[idx]

    def chain_fill_ratio(self):
        if self.chain <= 0 or CHAIN_MAX_FRAMES <= 0:
            return 0.0
        return max(0.0, min(1.0, self.timer / CHAIN_MAX_FRAMES))

    def tick(self, paused=False):
        if paused:
            return
        if self.chain_flash_timer > 0:
            self.chain_flash_timer -= 1
        if self.chain_pop_timer > 0:
            self.chain_pop_timer -= 1
        if self.chain_max_callout_timer > 0:
            self.chain_max_callout_timer -= 1
        if self.timer > 0:
            self.timer -= 1
            if self.timer == 0:
                self.chain = 0
                self.chain_max_callout_timer = 0

    def break_chain(self):
        self.chain = 0
        self.timer = 0
        self.chain_flash_timer = 0
        self.chain_pop_timer = 0
        self.chain_max_callout_timer = 0
        self.pending_milestone = None
        self._milestones_fired = set()

    def pop_chain_milestone(self):
        """HUD フェーズで SE 再生用。到達チェーン数、なければ None。"""
        m = self.pending_milestone
        self.pending_milestone = None
        return m

    @property
    def boss_hit_cap(self) -> int:
        return self._boss_hit_cap

    def boss_hit_bank_ratio(self) -> float:
        if self._boss_hit_cap <= 0:
            return 0.0
        return max(0.0, min(1.0, self.boss_hit_bank / self._boss_hit_cap))

    def _on_chain_milestone(self, chain_val: int) -> None:
        self.chain_flash_timer = CHAIN_FLASH_FRAMES
        self.pending_milestone = chain_val

    def register_kill(self):
        prev_chain = self.chain
        self.chain += 1
        self.timer = CHAIN_MAX_FRAMES
        self.chain_pop_timer = CHAIN_POP_FRAMES
        if chain_multiplier_maxed(self.chain):
            if not chain_multiplier_maxed(prev_chain):
                self.chain_max_callout_timer = CHAIN_MAX_CALLOUT_FRAMES
        else:
            self.chain_max_callout_timer = 0
        if (
            self.chain in CHAIN_MILESTONES
            and self.chain not in self._milestones_fired
        ):
            self._milestones_fired.add(self.chain)
            self._on_chain_milestone(self.chain)

    def begin_boss_fight(self, diff, boss_type):
        self._boss_hit_cap = boss_hit_cap(diff, boss_type)
        self.boss_hit_bank = 0

    def add_boss_hit(self, diff, damage, boss_hit_score):
        if self._boss_hit_cap <= 0:
            self.begin_boss_fight(diff, 1)
        raw = scaled_score(boss_hit_score * max(1, damage), diff, self.multiplier())
        room = max(0, self._boss_hit_cap - self.boss_hit_bank)
        add = min(raw, room)
        self.boss_hit_bank += add
        return add

    def chain_kill_bonus(self, diff):
        """高連鎖時の小さな固定ボーナス（メイン得点は倍率テーブル側）。"""
        if self.chain < CHAIN_KILL_BONUS_FROM:
            return 0
        base = int(getattr(diff, "combo_base", 1500))
        tier = min(
            MAX_CHAIN_KILL_TIER,
            1 + (self.chain - CHAIN_KILL_BONUS_FROM) // 8,
        )
        return scaled_score(base * tier, diff, 1)

    def score_enemy_kill(self, diff):
        self.register_kill()
        pts = scaled_score(int(diff.enemy_base_score), diff, self.multiplier())
        pts += self.chain_kill_bonus(diff)
        return pts

    def score_ace_kill(self, diff):
        """エース撃破: 基礎点＋連鎖ボーナス2倍。"""
        self.register_kill()
        pts = scaled_score(int(diff.enemy_base_score), diff, self.multiplier())
        pts += self.chain_kill_bonus(diff) * 2
        return pts

    def score_turret_kill(self, diff):
        self.register_kill()
        return scaled_score(int(diff.turret_score), diff, self.multiplier())

    def score_ems_kill(self, diff):
        self.register_kill()
        return scaled_score(int(diff.enemy_base_score * 0.5), diff, self.multiplier())


class BossScoreTally:
    """ボス撃破後のスコア確定演出。"""

    def __init__(self):
        self.active = False
        self.lines = []
        self.total = 0
        self.displayed_total = 0
        self.line_index = 0
        self.line_timer = 0
        self.phase = "lines"
        self.hold_timer = 0
        self.boss_type = 1
        self.is_final = False
        self.on_finish = None
        self.require_enter = False
        self.show_enter_prompt = False

    def reset(self):
        self.active = False
        self.lines = []
        self.total = 0
        self.displayed_total = 0
        self.line_index = 0
        self.line_timer = 0
        self.phase = "lines"
        self.hold_timer = 0
        self.on_finish = None
        self.require_enter = False
        self.show_enter_prompt = False

    def start(
        self,
        diff,
        boss_type,
        hit_bank,
        no_damage,
        fight_frames,
        lives_left,
        multiplier,
        is_final=False,
        on_finish=None,
        *,
        hold_frames: int | None = None,
        require_enter: bool | None = None,
        show_enter_prompt: bool | None = None,
    ):
        mult = max(1, int(multiplier))
        ds = difficulty_scale(diff)
        lines = []

        if hit_bank > 0:
            lines.append(("ボス戦闘点", int(hit_bank)))

        if is_final:
            lines.append(("ラストボス撃破", int(diff.boss_kill_base * 5 * ds * mult)))
            if no_damage:
                lines.append(
                    ("ノーダメージ", int(diff.boss_nodmg_base * 5 * ds * mult))
                )
            speed_ratio = max(0.0, 1.0 - (fight_frames / (60 * 180)))
            if speed_ratio > 0:
                lines.append(
                    (
                        "速攻ボーナス",
                        int(diff.boss_speed_base * 5 * speed_ratio * ds * mult),
                    )
                )
            if lives_left > 0:
                lines.append(
                    ("残機ボーナス", int(lives_left * diff.lives_bonus_unit * ds * mult))
                )
            lines.append(("クリアボーナス", int(diff.clear_bonus * ds * mult)))
        else:
            lines.append(
                (
                    "ボス撃破",
                    int(diff.boss_kill_base * boss_type * ds * mult),
                )
            )
            if no_damage:
                lines.append(
                    (
                        "ノーダメージ",
                        int(diff.boss_nodmg_base * boss_type * ds * mult),
                    )
                )
            par_frames = 60 * 25 * boss_type
            if fight_frames < par_frames:
                speed_ratio = 1.0 - (fight_frames / par_frames)
                lines.append(
                    (
                        "速攻ボーナス",
                        int(
                            diff.boss_speed_base
                            * boss_type
                            * speed_ratio
                            * ds
                            * mult
                        ),
                    )
                )
            if lives_left > 0:
                lines.append(
                    (
                        "残機ボーナス",
                        int(lives_left * diff.lives_bonus_unit * ds * mult),
                    )
                )

        self.lines = [{"label": a, "amount": b, "shown": False} for a, b in lines]
        self.total = sum(ln["amount"] for ln in self.lines)
        self.displayed_total = 0
        self.line_index = 0
        self.line_timer = 0
        self.phase = "lines"
        if hold_frames is not None:
            self.hold_timer = hold_frames
        else:
            self.hold_timer = (
                TALLY_HOLD_FRAMES_FINAL if is_final else TALLY_HOLD_FRAMES
            )
        self.boss_type = boss_type
        self.is_final = is_final
        self.on_finish = on_finish
        self.require_enter = (
            is_final if require_enter is None else require_enter
        )
        self.show_enter_prompt = (
            self.require_enter
            if show_enter_prompt is None
            else show_enter_prompt
        )
        self.active = True

    def skip(self):
        for ln in self.lines:
            ln["shown"] = True
        self.displayed_total = self.total
        self.phase = "hold"
        self.hold_timer = min(self.hold_timer, 20)

    def confirm_enter(self):
        """ENTER：加算表示を完了してゲームへ戻る（require_enter 時のみ）。"""
        if not self.active or not self.require_enter:
            return
        self._finish_immediate()

    def _finish_immediate(self):
        for ln in self.lines:
            ln["shown"] = True
        self.displayed_total = self.total
        self.phase = "done"
        self.active = False
        cb = self.on_finish
        self.on_finish = None
        if cb:
            cb(self.total)

    def update(self):
        if not self.active:
            return False

        if self.phase == "lines":
            self.line_timer += 1
            target = 0
            for i, ln in enumerate(self.lines):
                if i < self.line_index:
                    target += ln["amount"]
                elif i == self.line_index and not ln["shown"]:
                    t = min(1.0, self.line_timer / max(1, TALLY_FRAMES_PER_LINE))
                    target += int(ln["amount"] * t)
            self.displayed_total = target

            if self.line_timer >= TALLY_FRAMES_PER_LINE:
                if self.line_index < len(self.lines):
                    self.lines[self.line_index]["shown"] = True
                    self.line_index += 1
                    self.line_timer = 0
                else:
                    self.displayed_total = self.total
                    self.phase = "hold"
            return False

        if self.phase == "hold":
            self.displayed_total = self.total
            if not self.require_enter:
                self.hold_timer -= 1
                if self.hold_timer <= 0:
                    self._finish_immediate()
            return False
        return False

    def draw(self, surf, font, font_sm, font_lg, big_font):
        if not self.active:
            return

        sw, sh = surf.get_size()
        cx, cy = sw // 2, sh // 2

        pad_x = 32
        line_h = 36
        panel_w = min(520, sw - 100)
        header_h = 92
        footer_h = 78
        panel_h = min(sh - 140, header_h + len(self.lines) * line_h + footer_h)
        px = cx - panel_w // 2
        py = cy - panel_h // 2 - 24

        draw_glossy_panel(
            surf,
            px,
            py,
            panel_w,
            panel_h,
            (200, 205, 220),
            fill_alpha=TALLY_PANEL_ALPHA,
        )

        title = font_lg.render("SCORE LOCK", True, (255, 220, 90))
        surf.blit(title, title.get_rect(midtop=(cx, py + 16)))
        sub = font_sm.render("スコア確定", True, (190, 195, 205))
        surf.blit(sub, sub.get_rect(midtop=(cx, py + 52)))

        y0 = py + header_h
        for i, ln in enumerate(self.lines):
            shown = ln["shown"]
            row_cy = y0 + i * line_h + line_h // 2
            lbl = font_sm.render(
                ln["label"], True, (245, 245, 245) if shown else (110, 110, 115)
            )
            amt_col = (255, 230, 110) if shown else (85, 85, 90)
            amt = font.render(f"+{ln['amount']:,}", True, amt_col)
            surf.blit(lbl, lbl.get_rect(midleft=(px + pad_x, row_cy)))
            surf.blit(amt, amt.get_rect(midright=(px + panel_w - pad_x, row_cy)))

        sep_y = py + panel_h - footer_h
        pygame.draw.line(
            surf,
            (120, 120, 125),
            (px + pad_x - 4, sep_y),
            (px + panel_w - pad_x + 4, sep_y),
            1,
        )

        foot_cy = py + panel_h - footer_h // 2 + 2
        total_lbl = font_sm.render("加算合計", True, (180, 200, 255))
        total_s = font_lg.render(f"{self.displayed_total:,}", True, (255, 255, 255))
        surf.blit(total_lbl, total_lbl.get_rect(midleft=(px + pad_x, foot_cy)))
        surf.blit(total_s, total_s.get_rect(midright=(px + panel_w - pad_x, foot_cy)))

        prompt_y = py + panel_h + 36
        if (
            self.phase == "hold"
            and self.show_enter_prompt
            and (pygame.time.get_ticks() // 480) % 2 == 0
        ):
            _draw_blink_enter(
                surf,
                big_font,
                cx,
                prompt_y,
                hint_font=font_sm,
                hint_text="[続行]：ENTER / Button0",
            )


def compute_boss_tally_total(
    diff,
    boss_type,
    hit_bank,
    no_damage,
    fight_frames,
    lives_left,
    multiplier,
    is_final=False,
) -> int:
    """ボス撃破ボーナス合計（UIなし）。"""
    tally = BossScoreTally()
    tally.start(
        diff,
        boss_type,
        hit_bank,
        no_damage,
        fight_frames,
        lives_left,
        multiplier,
        is_final=is_final,
        on_finish=None,
    )
    return tally.total


def _draw_blink_enter(surf, big_font, cx, cy, *, hint_font=None, hint_text=None):
    """タイトル画面と同様の点滅 PRESS ENTER（任意で日本語ヒント）。"""
    text = "PRESS ENTER"
    shadow = big_font.render(text, True, (0, 0, 0))
    main = big_font.render(text, True, (255, 220, 0))
    rect = main.get_rect(center=(cx, cy))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        surf.blit(shadow, rect.move(dx, dy))
    surf.blit(main, rect)
    if hint_font is not None and hint_text:
        hint = hint_font.render(hint_text, True, (190, 220, 255))
        surf.blit(hint, hint.get_rect(center=(cx, cy + 38)))


def _hud_panel(surf, x, y, width, height, border_rgb, fill_alpha=88):
    draw_glossy_panel(surf, x, y, width, height, border_rgb, fill_alpha=fill_alpha)


HUD_METER_BAR_W = 92


def draw_chain_strip_hud(surf, chain, timer, multiplier, font_sm, x, y, width=260, height=44):
    """上部 HUD 用：CHAIN 1行＋短いタイマーバー。"""
    compact = height <= 34
    _hud_panel(surf, x, y, width, height, (55, 75, 110))

    lbl = font_sm.render("連鎖", True, (120, 180, 255))
    text_y = y + (4 if compact else 6)
    surf.blit(lbl, (x + 6, text_y))
    chain_s = font_sm.render(str(chain), True, (255, 255, 255) if chain else (90, 90, 95))
    surf.blit(chain_s, (x + 58, text_y - 1))
    mult_col = (255, 210, 60) if multiplier > 1 else (150, 150, 160)
    mult_s = font_sm.render(f"x{multiplier}", True, mult_col)
    surf.blit(mult_s, (x + 86, text_y - 1))

    bar_h = 5 if compact else 6
    bar_y = y + height - (10 if compact else 14)
    bar_w = min(HUD_METER_BAR_W, max(48, width - 16))
    bar_x = x + 6
    ratio = (
        max(0.0, min(1.0, timer / CHAIN_MAX_FRAMES))
        if chain > 0 and CHAIN_MAX_FRAMES > 0
        else 0.0
    )
    fill_col = (255, 200, 40) if ratio > 0.35 else (255, 90, 60)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (30, 35, 50), (70, 80, 100)
    )


def draw_boss_bank_strip_hud(surf, bank, cap, font_sm, x, y, width=260, height=40):
    """上部 HUD 用：ボス戦闘点バンク 1行＋短いバー。"""
    if cap <= 0:
        return
    compact = height <= 26
    _hud_panel(surf, x, y, width, height, (140, 90, 50))

    lbl = font_sm.render("ボス得点", True, (255, 190, 120))
    text_y = y + (3 if compact else 4)
    surf.blit(lbl, (x + 6, text_y))
    amt = font_sm.render(f"{bank:,}", True, (255, 245, 200))
    cap_s = font_sm.render(f"/ {cap:,}", True, (140, 130, 120))
    surf.blit(amt, (x + 48, text_y))
    surf.blit(cap_s, (x + 48 + amt.get_width() + 2, text_y))

    bar_h = 4 if compact else 5
    bar_y = y + height - (8 if compact else 12)
    bar_w = min(HUD_METER_BAR_W, max(48, width - 16))
    bar_x = x + 6
    ratio = max(0.0, min(1.0, bank / cap))
    fill_col = (255, 160, 50) if ratio < 0.95 else (255, 220, 100)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (40, 30, 25), (100, 70, 40)
    )


def draw_chain_hud(surf, chain, timer, multiplier, font_sm, x, y, width=200):
    """右上：チェーンメーター＋倍率。"""
    h = 52
    draw_glossy_panel(surf, x, y, width, h, (60, 90, 140), fill_alpha=110)

    lbl = font_sm.render("連鎖", True, (120, 180, 255))
    surf.blit(lbl, (x + 8, y + 4))

    mult_col = (255, 210, 60) if multiplier > 1 else (160, 160, 170)
    mult_s = font_sm.render(f"x{multiplier}", True, mult_col)
    surf.blit(mult_s, (x + width - 8 - mult_s.get_width(), y + 2))

    chain_s = font_sm.render(str(chain), True, (255, 255, 255) if chain > 0 else (80, 80, 90))
    surf.blit(chain_s, (x + 52, y + 2))

    bar_x = x + 8
    bar_y = y + 26
    bar_w = width - 16
    bar_h = 10
    ratio = (
        max(0.0, min(1.0, timer / CHAIN_MAX_FRAMES))
        if chain > 0 and CHAIN_MAX_FRAMES > 0
        else 0.0
    )
    fill_col = (255, 200, 40) if ratio > 0.35 else (255, 90, 60)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (30, 35, 50), (70, 80, 100)
    )


def _scale_text_surface(surf: pygame.Surface, scale: float) -> pygame.Surface:
    if abs(scale - 1.0) < 0.03:
        return surf
    w, h = surf.get_size()
    return pygame.transform.smoothscale(
        surf, (max(1, int(w * scale)), max(1, int(h * scale)))
    )


def _draw_golden_glow_label(
    surf: pygame.Surface,
    label: str,
    font: pygame.font.Font,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    pulse: float = 1.0,
) -> None:
    """金色の外光＋縁取り（コンボ表示用）。"""
    halo = _scale_text_surface(font.render(label, True, (255, 120, 25)), scale * 1.14)
    rim = _scale_text_surface(font.render(label, True, (255, 185, 50)), scale * 1.05)
    core = _scale_text_surface(font.render(label, True, (255, 248, 175)), scale)

    rect = core.get_rect(center=center)
    halo_r = halo.get_rect(center=center)
    rim_r = rim.get_rect(center=center)

    glow_a = int(95 * pulse)
    if glow_a > 0:
        layer = halo.copy()
        layer.set_alpha(glow_a)
        for ox, oy in ((-4, 0), (4, 0), (0, -3), (0, 3), (-3, -3), (3, 3)):
            surf.blit(layer, halo_r.move(ox, oy))

    surf.blit(rim, rim_r.move(-1, 1))
    surf.blit(core, rect)


def draw_chain_combo_callout(
    surf: pygame.Surface,
    chain: int,
    *,
    center: tuple[int, int],
    chain_pop_timer: int,
    chain_flash_timer: int,
    chain_max_callout_timer: int,
    big_font: pygame.font.Font,
) -> None:
    """通常戦闘: 「N連鎖！」／到達時のみ「連鎖MAX！」（MAX維持中は非表示）。"""
    if chain <= 0:
        return

    if chain_multiplier_maxed(chain):
        if chain_max_callout_timer <= 0:
            return
        label = "連鎖MAX！"
    else:
        label = f"{chain}連鎖！"

    pop = chain_pop_timer / max(1, CHAIN_POP_FRAMES)
    scale = 1.0 + 0.42 * pop

    ticks = pygame.time.get_ticks()
    pulse = 0.86 + 0.14 * math.sin(ticks * 0.014)
    if chain_flash_timer > 0:
        ft = chain_flash_timer / max(1, CHAIN_FLASH_FRAMES)
        pulse = min(1.4, pulse + 0.38 * ft)

    _draw_golden_glow_label(
        surf, label, big_font, center, scale=scale, pulse=pulse
    )


def draw_chain_milestone_flash(surf, flash_timer: int, panel_rect) -> None:
    """連鎖マイルストーン：上部HUDの連鎖枠と枠内のみ金色フラッシュ（全画面なし・光過敏配慮）。"""
    if flash_timer <= 0 or CHAIN_FLASH_FRAMES <= 0:
        return
    if panel_rect.width <= 0 or panel_rect.height <= 0:
        return
    t = flash_timer / CHAIN_FLASH_FRAMES
    t = t * t
    inner_a = int(42 * t)
    border_a = int(78 * t)
    if inner_a <= 0 and border_a <= 0:
        return
    w, h = int(panel_rect.width), int(panel_rect.height)
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    if inner_a > 0:
        overlay.fill((255, 205, 75, inner_a))
    if border_a > 0:
        pygame.draw.rect(overlay, (255, 228, 130, border_a), overlay.get_rect(), 2)
        pygame.draw.rect(
            overlay, (255, 190, 55, max(0, border_a - 20)), overlay.get_rect().inflate(-3, -3), 1
        )
    surf.blit(overlay, (int(panel_rect.x), int(panel_rect.y)))


def draw_boss_hit_bank_hud(
    surf,
    bank: int,
    cap: int,
    font_sm,
    x: int,
    y: int,
    width: int = 200,
) -> None:
    """ボス戦中：戦闘点バンク（確定前の蓄積）。"""
    if cap <= 0:
        return
    h = 40
    draw_glossy_panel(surf, x, y, width, h, (140, 90, 50), fill_alpha=120)

    lbl = font_sm.render("ボス得点", True, (255, 190, 120))
    surf.blit(lbl, (x + 8, y + 3))

    amt = font_sm.render(f"{bank:,}", True, (255, 245, 200))
    cap_s = font_sm.render(f"/ {cap:,}", True, (150, 140, 130))
    surf.blit(amt, (x + 8, y + 18))
    surf.blit(cap_s, (x + 8 + amt.get_width() + 4, y + 18))

    bar_x = x + 8
    bar_y = y + h - 12
    bar_w = width - 16
    bar_h = 6
    ratio = max(0.0, min(1.0, bank / cap))
    fill_col = (255, 160, 50) if ratio < 0.95 else (255, 220, 100)
    draw_glossy_bar_horizontal(
        surf, bar_x, bar_y, bar_w, bar_h, ratio, fill_col, (40, 30, 25), (100, 70, 40)
    )
