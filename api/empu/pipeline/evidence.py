"""Evidence media per occurrence, cut from display.mp4 (spec 8.7). Original frames only."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from empu.pipeline.ffmpeg import ffmpeg_to, has_audio

PRE_S, POST_S, MIN_S, MAX_S = 1.0, 1.5, 3.0, 8.0


def clip_window(t_start: float, t_end: float, duration_s: float) -> tuple[float, float]:
    a, b = t_start - PRE_S, max(t_end, t_start) + POST_S
    if b - a > MAX_S:
        b = a + MAX_S
    if b - a < MIN_S:
        pad = (MIN_S - (b - a)) / 2
        a, b = a - pad, b + pad
    if a < 0:
        a, b = 0.0, b - a
    if b > duration_s:
        a, b = max(0.0, a - (b - duration_s)), duration_s
    return round(a, 3), round(b, 3)


@dataclass(frozen=True)
class EvidencePaths:
    clip: Path
    audio: Path | None
    keyframe: Path
    clip_start: float
    clip_end: float


def extract_keyframe(display: Path, t: float, dst: Path) -> Path:
    if Path(dst).exists():
        return Path(dst)
    return ffmpeg_to(Path(dst), ["-ss", f"{max(0.0, t):.3f}", "-i", str(display),
                                 "-frames:v", "1", "-q:v", "2"])


def make_evidence(display: Path, t_start: float, t_end: float, duration_s: float,
                  out_dir: Path) -> EvidencePaths:
    out_dir = Path(out_dir)
    a, b = clip_window(t_start, t_end, duration_s)
    seek = ["-ss", f"{a:.3f}", "-i", str(display), "-t", f"{b - a:.3f}"]
    clip, audio, keyframe = out_dir / "clip.mp4", out_dir / "audio.m4a", out_dir / "keyframe.jpg"
    with_audio = has_audio(display)
    if not clip.exists():
        ffmpeg_to(clip, [*seek, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                         *(["-c:a", "aac", "-b:a", "128k"] if with_audio else ["-an"]),
                         "-movflags", "+faststart"])
    if with_audio and not audio.exists():
        ffmpeg_to(audio, [*seek, "-vn", "-c:a", "aac", "-b:a", "96k"])
    extract_keyframe(display, (t_start + t_end) / 2, keyframe)
    return EvidencePaths(clip, audio if with_audio else None, keyframe, a, b)
