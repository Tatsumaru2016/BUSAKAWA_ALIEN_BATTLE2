# hiscore.py — ハイスコアの読み書き

from game_paths import path_in_save_dir

HISCORE_FILE = path_in_save_dir("hiscore.dat")


def load_hiscore():
    try:
        with open(HISCORE_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_hiscore(score_val):
    try:
        with open(HISCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(int(score_val)))
    except Exception:
        pass
