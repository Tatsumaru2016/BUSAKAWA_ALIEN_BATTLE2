# game_state.py — アプリ／プレイセッション状態（Phase 4）

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from settings import DifficultyConfig
from boss5_support import clear_boss5_support
from extra_boss_victory import clear_extra_victory
from extra_stage_support import clear_extra_support
from audio import reset_boss5_hp_bgm
from score_system import ScoreChain, BossScoreTally
from hiscore import save_hiscore
from game_progress import (
    extra_stage_allowed,
    is_difficulty_selectable,
    load_progress,
    mark_hard_cleared,
)

PLAY_STATE_FIELDS = (
    "bullets",
    "enemy_bullets",
    "enemy_lasers",
    "meteors",
    "explosions",
    "enemies",
    "power_items",
    "turrets",
    "boss",
    "boss_active",
    "boss_warning",
    "boss_warning_timer",
    "boss_warning_pending",
    "boss_cycle",
    "enemy_timer",
    "turret_spawn_timer",
    "score",
    "boss_index",
    "boss_shield_hp",
    "boss_shield_grace_timer",
    "kill_count",
    "no_damage_since_boss",
    "boss_fight_timer",
    "boss_fight_active",
    "player_dead",
    "gameover_timer",
    "player_explode_timer",
    "ending_delay_timer",
    "_ending_screen_sfx_played",
    "_ending_sfx_timer",
    "lives",
    "revive_timer",
    "_prev_lives",
    "_shot_timer",
    "ems_count",
    "ems_flash_timer",
    "_boss_special_alert_timer",
    "boss_shield_max",
    "_tally_last_line",
    "far_x",
    "mid_x",
    "front_x",
    "boss5_far_x",
    "boss5_mid_x",
    "boss5_front_x",
    "boss5_bg_mode",
    "extra_bg_mode",
    "extra_far_x",
    "extra_mid_x",
    "extra_front_x",
    "extra_bg_frozen",
    "extra_bg_tilt",
    "extra_intro_phase",
    "extra_intro_timer",
    "score_chain",
    "boss_score_tally",
    "_boss_special_alert_ref",
)


@dataclass
class AppState:
    """画面モード・難易度などプレイ外のセッション状態。"""

    screen_mode: int
    hi_score: int = 0
    _g: Dict[str, Any] = field(default_factory=dict)
    _namespace: Optional[dict] = field(default=None, repr=False)

    @classmethod
    def create(cls, initial_screen_mode: int, diff_name: str = "NORMAL") -> AppState:
        diff = DifficultyConfig(diff_name)
        return cls(
            screen_mode=initial_screen_mode,
            _g={
                "diff": diff,
                "cursor": DifficultyConfig.ORDER.index(diff_name),
            },
        )

    @property
    def diff(self) -> DifficultyConfig:
        return self._g["diff"]

    @property
    def cursor(self) -> int:
        return self._g["cursor"]

    @property
    def progress(self) -> dict:
        return self._g.setdefault("progress", load_progress())

    def nudge_difficulty_cursor(self, delta: int) -> None:
        order = DifficultyConfig.ORDER
        self._g["cursor"] = (self._g["cursor"] + delta) % len(order)
        self._g["diff"] = DifficultyConfig(order[self._g["cursor"]])

    def selected_difficulty_name(self) -> str:
        return DifficultyConfig.ORDER[self._g["cursor"]]

    def is_selected_difficulty_unlocked(self) -> bool:
        return is_difficulty_selectable(self.selected_difficulty_name(), self.progress)

    def record_hard_clear_if_applicable(self) -> None:
        if self.diff.name == "HARD" and mark_hard_cleared():
            self._g["progress"] = load_progress()

    @staticmethod
    def can_enter_extra_stage(diff_name: str) -> bool:
        return extra_stage_allowed(diff_name)

    def bind_namespace(self, namespace: dict) -> None:
        self._namespace = namespace

    def set_screen_mode(self, mode: int) -> None:
        self.screen_mode = mode
        if self._namespace is not None:
            self._namespace["state"] = mode

    def install_to(self, namespace: dict) -> None:
        self.bind_namespace(namespace)
        namespace["app"] = self
        namespace["_g"] = self._g
        namespace["state"] = self.screen_mode
        namespace["hi_score"] = self.hi_score

    def maybe_update_hiscore(self, score: int) -> bool:
        """スコアがハイスコアを超えたら保存して True。"""
        if score <= self.hi_score:
            return False
        self.hi_score = score
        save_hiscore(self.hi_score)
        if self._namespace is not None:
            self._namespace["hi_score"] = self.hi_score
        return True


@dataclass
class PlayState:
    """1プレイセッション分の可変状態。"""

    bullets: List[Any] = field(default_factory=list)
    enemy_bullets: List[Any] = field(default_factory=list)
    enemy_lasers: List[Any] = field(default_factory=list)
    meteors: List[Any] = field(default_factory=list)
    explosions: List[Any] = field(default_factory=list)
    enemies: List[Any] = field(default_factory=list)
    power_items: List[Any] = field(default_factory=list)
    turrets: List[Any] = field(default_factory=list)

    boss: Any = None
    boss_active: bool = False
    boss_warning: bool = False
    boss_warning_timer: int = 0
    boss_warning_pending: bool = False
    boss_cycle: int = 0
    enemy_timer: int = 0
    turret_spawn_timer: int = 0
    score: int = 0
    boss_index: int = 0
    boss_shield_hp: int = 0
    boss_shield_grace_timer: int = 0
    kill_count: int = 0

    no_damage_since_boss: bool = True
    boss_fight_timer: int = 0
    boss_fight_active: bool = False

    player_dead: bool = False
    gameover_timer: int = 0
    player_explode_timer: int = 0
    ending_delay_timer: int = 0
    _ending_screen_sfx_played: bool = False
    _ending_sfx_timer: int = 0

    lives: int = 3
    revive_timer: int = 0
    _prev_lives: int = 3
    _shot_timer: int = 0

    ems_count: int = 3
    ems_flash_timer: int = 0
    _boss_special_alert_timer: int = 0
    boss_shield_max: int = 0
    _tally_last_line: int = -1

    far_x: int = 0
    mid_x: int = 0
    front_x: int = 0
    boss5_far_x: int = 0
    boss5_mid_x: int = 0
    boss5_front_x: int = 0
    boss5_bg_mode: bool = False
    extra_bg_mode: bool = False
    extra_far_x: int = 0
    extra_mid_x: int = 0
    extra_front_x: int = 0
    extra_bg_frozen: bool = False
    extra_bg_tilt: float = 0.0
    extra_intro_phase: str = ""
    extra_intro_timer: int = 0

    b5_victory_timer: int = -1
    b5_death_active: bool = False
    b5_death_timer: int = 0
    b5_death_silence_played: bool = False
    b5_death_from_surface: Any = None
    b5_death_dead_surface: Any = None
    b5_death_draw_rect: Any = None
    b5_death_pending_bonus: int = 0
    b5_clear_cinematic: bool = False
    b5_epilogue_phase: str = ""
    b5_epilogue_timer: int = 0
    b5_epilogue_fade: int = 0

    ending_menu_choice: int = 0
    extra_run: bool = False
    extra_dive_phase: str = ""
    extra_dive_snap_timer: int = 0
    extra_dive_suck_bubble_idx: int = -1
    extra_dive_target_x: int = 0
    extra_dive_target_y: int = 0
    extra_dive_player_x: int = 120
    extra_dive_player_y: int = 380
    extra_dive_suck_sfx_played: bool = False
    extra_dive_timer: int = 0
    extra_dive_done: bool = False
    extra_dive_boss_surf: Any = None
    extra_dive_boss_rect: Any = None

    score_chain: ScoreChain = field(default_factory=ScoreChain)
    boss_score_tally: BossScoreTally = field(default_factory=BossScoreTally)
    game_paused: bool = False
    _boss_special_alert_ref: List[int] = field(default_factory=lambda: [0])

    _namespace: Optional[dict] = field(default=None, repr=False)

    def bind_namespace(self, namespace: dict) -> None:
        self._namespace = namespace

    def set(self, name: str, value: Any) -> None:
        """play と main グローバルを同時更新。"""
        setattr(self, name, value)
        if self._namespace is not None:
            self._namespace[name] = value

    def update(self, **values: Any) -> None:
        for name, value in values.items():
            self.set(name, value)

    def reset(self, player, diff, height: int) -> None:
        clear_boss5_support()
        clear_extra_support(self)
        clear_extra_victory(self)
        reset_boss5_hp_bgm()

        self.bullets.clear()
        self.enemy_bullets.clear()
        self.enemy_lasers.clear()
        self.meteors.clear()
        self.enemies.clear()
        try:
            from enemy_waves import reset_grunt_waves

            reset_grunt_waves(self)
        except Exception:
            self._grunt_wave = None
            self.grunt_hit_ghosts = []
        self.explosions.clear()
        self.power_items.clear()
        self.turrets.clear()

        player.rect.x = 120
        player.rect.y = height // 2
        player.weapon_level = 1
        player.shield_meter = 0.0
        player.base_speed = 8
        player.speed = 8
        player.laser_gauge = 0.0
        player.speed_gauge = 0.0
        player.fire_mode = "normal"
        player._laser_low_warned = False
        player.invincible_timer = 0

        self.boss = None
        self.boss_active = False
        self.boss_warning = False
        self.boss_warning_timer = 0
        self.boss_warning_pending = False
        self.boss_cycle = 0
        self.boss_shield_hp = 0
        self.boss_shield_grace_timer = 0
        self.enemy_timer = 0
        self.turret_spawn_timer = 0
        self.boss_index = 0
        self.score = 0
        self.kill_count = 0

        self.score_chain.reset()
        self.boss_score_tally.reset()
        self.game_paused = False
        self._tally_last_line = -1

        self.no_damage_since_boss = True
        self.boss_fight_timer = 0
        self.boss_fight_active = False

        self.player_dead = False
        self.gameover_timer = 0
        self.player_explode_timer = 0
        self.ending_delay_timer = 0
        self._ending_screen_sfx_played = False
        self._ending_sfx_timer = 0
        self.b5_victory_timer = -1
        self.b5_death_active = False
        self.b5_death_timer = 0
        self.b5_death_silence_played = False
        self.b5_death_from_surface = None
        self.b5_death_dead_surface = None
        self.b5_death_draw_rect = None
        self.b5_death_pending_bonus = 0
        self.b5_clear_cinematic = False
        self.b5_epilogue_phase = ""
        self.b5_epilogue_timer = 0
        self.b5_epilogue_fade = 0
        self.ending_menu_choice = 0
        self.extra_run = False
        self.extra_dive_phase = ""
        self.extra_dive_snap_timer = 0
        self.extra_dive_suck_bubble_idx = -1
        self.extra_dive_timer = 0
        self.extra_dive_done = False
        self.extra_dive_boss_surf = None
        self.extra_dive_boss_rect = None
        self.extra_dive_target_x = 0
        self.extra_dive_target_y = 0
        self.extra_dive_player_x = 120
        self.extra_dive_player_y = height // 2
        self.extra_dive_suck_sfx_played = False

        self.lives = diff.player_lives
        self.revive_timer = 0
        self._prev_lives = diff.player_lives
        self._shot_timer = 0
        self.ems_count = 3
        self.ems_flash_timer = 0
        self._boss_special_alert_timer = 0
        self.boss_shield_max = 0

        self.far_x = 0
        self.mid_x = 0
        self.front_x = 0
        self.boss5_far_x = 0
        self.boss5_mid_x = 0
        self.boss5_front_x = 0
        self.boss5_bg_mode = False
        self.extra_bg_mode = False
        self.extra_far_x = 0
        self.extra_mid_x = 0
        self.extra_front_x = 0
        self.extra_bg_frozen = False
        self.extra_bg_tilt = 0.0
        self.extra_intro_phase = ""
        self.extra_intro_timer = 0

    def install_to(self, namespace: dict) -> None:
        self.bind_namespace(namespace)
        for name in PLAY_STATE_FIELDS:
            namespace[name] = getattr(self, name)
        namespace["play"] = self

    def capture_from(self, namespace: dict) -> None:
        """未移行のグローバル代入を play に取り込む。"""
        for name in PLAY_STATE_FIELDS:
            setattr(self, name, namespace[name])

    def add_score(self, amount: int) -> None:
        self.set("score", self.score + amount)

    def add_kill(self, count: int = 1) -> None:
        self.set("kill_count", self.kill_count + count)


def install_play_state(namespace: dict, play: PlayState) -> PlayState:
    play.install_to(namespace)
    return play
