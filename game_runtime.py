# game_runtime.py — main ループとサブモジュール間の共有参照（Phase 2–4 ブリッジ）


class Runtime:
    """main の globals() を bind() で接続する。"""

    _g = None

    @classmethod
    def bind(cls, namespace: dict):
        cls._g = namespace

    @classmethod
    def g(cls):
        if cls._g is None:
            raise RuntimeError("game_runtime.RT.bind(globals()) を main で呼んでください")
        return cls._g

    @classmethod
    def play(cls):
        return cls.g()["play"]

    @classmethod
    def app(cls):
        return cls.g()["app"]

    @classmethod
    def screen_mode(cls) -> int:
        return cls.g()["state"]


RT = Runtime
