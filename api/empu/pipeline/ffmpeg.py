"""Thin subprocess wrappers around ffmpeg/ffprobe."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.strip()[-2000:] or f"ffmpeg exited {proc.returncode}")


def ffmpeg_to(dst: Path, args: list[str]) -> Path:
    """Run ffmpeg writing to a temp file next to dst, then rename (no half-written outputs)."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f"{dst.stem}.tmp{dst.suffix}")
    try:
        run_ffmpeg([*args, str(tmp)])
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)
    return dst


def _probe(path: Path, *args: str) -> str:
    proc = subprocess.run(["ffprobe", "-v", "error", *args, "-of", "default=nw=1:nk=1", str(path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.strip()[-2000:] or f"ffprobe failed on {path}")
    return proc.stdout.strip()


def probe_duration(path: Path) -> float:
    return float(_probe(path, "-show_entries", "format=duration"))


def probe_height(path: Path) -> int:
    return int(_probe(path, "-select_streams", "v:0", "-show_entries", "stream=height"))


def has_audio(path: Path) -> bool:
    return bool(_probe(path, "-select_streams", "a", "-show_entries", "stream=index"))
