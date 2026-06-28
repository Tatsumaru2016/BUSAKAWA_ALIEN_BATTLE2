# platform_web.py — Web (pygbag / Emscripten) 判定

from __future__ import annotations

import sys


def is_web() -> bool:
    """pygbag がブラウザ上で動かすとき True。"""
    return sys.platform == "emscripten"
