# game_paths.py — セーブデータの保存場所（開発 / EXE 共通）

import os
import sys


def get_save_dir():
    """ハイスコア・設定JSONなど、書き込み可能なデータの保存先。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def path_in_save_dir(filename):
    return os.path.join(get_save_dir(), filename)
