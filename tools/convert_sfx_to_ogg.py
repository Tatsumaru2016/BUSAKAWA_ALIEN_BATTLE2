#!/usr/bin/env python3
"""Convert assets/*.wav to assets/*.ogg for pygbag (Web). Requires ffmpeg or imageio-ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def _find_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def _convert_one(ffmpeg: str, wav: Path) -> bool:
    ogg = wav.with_suffix(".ogg")
    if ogg.is_file() and ogg.stat().st_mtime >= wav.stat().st_mtime:
        print(f"  skip (up to date): {ogg.name}")
        return True
    print(f"  {wav.name} -> {ogg.name}")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(wav),
                "-c:a",
                "libvorbis",
                "-q:a",
                "5",
                str(ogg),
            ],
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"  [ERROR] ffmpeg failed for {wav.name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    if not ASSETS.is_dir():
        print(f"[ERROR] Missing assets folder: {ASSETS}", file=sys.stderr)
        return 1

    wavs = sorted(ASSETS.glob("*.wav"))
    if not wavs:
        print("No WAV files in assets/ — nothing to convert.")
        return 0

    ffmpeg = _find_ffmpeg()
    if ffmpeg is None:
        print(
            "[ERROR] ffmpeg not found. Install ffmpeg or: pip install imageio-ffmpeg",
            file=sys.stderr,
        )
        return 1

    print(f"Using ffmpeg: {ffmpeg}")
    print(f"Converting {len(wavs)} WAV file(s) in {ASSETS} ...")
    failed = 0
    for wav in wavs:
        if not _convert_one(ffmpeg, wav):
            failed += 1

    if failed:
        print(f"[ERROR] {failed} conversion(s) failed.", file=sys.stderr)
        return 1
    print("SFX OGG conversion OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
