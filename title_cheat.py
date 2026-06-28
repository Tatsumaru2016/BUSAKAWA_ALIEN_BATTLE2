# title_cheat.py — タイトル画面のみ：上上下下左右左右

from settings import PLAYER_MAX_WEAPON_LEVEL

TITLE_CHEAT_SEQUENCE = (
    "up", "up", "down", "down", "left", "right", "left", "right",
)

PLAYER_MAX_SHIELD_METER = 1.0
PLAYER_MAX_SPEED = 11


class TitleCheat:
    """タイトル専用。armed は入力成功時のみ。ゲーム開始で消費、GO/エンディングで消去。"""

    def __init__(self):
        self.armed = False
        self._step = 0
        self._last_dir = None

    def clear_armed(self):
        self.armed = False

    def reset_sequence(self):
        self._step = 0
        self._last_dir = None

    def reset_all(self):
        self.clear_armed()
        self.reset_sequence()

    def feed(self, direction):
        """方向1入力。シーケンス完了で True（armed を立てる）。"""
        if self.armed or direction not in TITLE_CHEAT_SEQUENCE:
            return False
        if direction == self._last_dir:
            return False
        self._last_dir = direction

        if direction == TITLE_CHEAT_SEQUENCE[self._step]:
            self._step += 1
            if self._step >= len(TITLE_CHEAT_SEQUENCE):
                self._step = 0
                self.armed = True
                return True
            return False

        self._step = 1 if direction == TITLE_CHEAT_SEQUENCE[0] else 0
        return False

    def release_direction(self):
        self._last_dir = None

    @staticmethod
    def apply_to_player(player):
        player.weapon_level = PLAYER_MAX_WEAPON_LEVEL
        player.shield_meter = PLAYER_MAX_SHIELD_METER
        player.speed = PLAYER_MAX_SPEED


def cardinal_from_bools(up, down, left, right):
    """単一方向のみ。斜め・同時押しは None。"""
    pressed = []
    if up:
        pressed.append("up")
    if down:
        pressed.append("down")
    if left:
        pressed.append("left")
    if right:
        pressed.append("right")
    if len(pressed) == 1:
        return pressed[0]
    return None
