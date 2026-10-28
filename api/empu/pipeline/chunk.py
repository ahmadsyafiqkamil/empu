"""Fixed-window segmentation with overlap. Cuts are re-encoded so timestamps are exact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from empu.pipeline.ffmpeg import ffmpeg_to, has_audio
from empu.pipeline.normalize import ANALYSIS_AUDIO


@dataclass(frozen=True)
class ChunkSpec:
    idx: int
    start_s: float
    end_s: float

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


def plan_chunks(
    duration_s: float, window_s: float = 75.0, overlap_s: float = 10.0
) -> list[ChunkSpec]:
    if duration_s <= 0:
        raise ValueError("duration must be positive")
    if not 0 <= overlap_s < window_s:
        raise ValueError("overlap must be >= 0 and smaller than the window")
    step = window_s - overlap_s
    specs: list[ChunkSpec] = []
    start = 0.0
    while True:
        end = min(start + window_s, duration_s)
        specs.append(ChunkSpec(len(specs), start, end))
        if end >= duration_s:
            return specs
        start += step


def cut_chunk(src: Path, spec: ChunkSpec, dst: Path) -> Path:
    audio = ANALYSIS_AUDIO if has_audio(src) else ["-an"]
    return ffmpeg_to(dst, [
        "-ss", f"{spec.start_s:.3f}", "-i", str(src), "-t", f"{spec.duration_s:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", *audio,
    ])


def cut_chunks(src: Path, specs: list[ChunkSpec], out_dir: Path) -> list[Path]:
    paths = []
    for spec in specs:
        dst = Path(out_dir) / f"{spec.idx}.mp4"
        paths.append(dst if dst.exists() else cut_chunk(src, spec, dst))
    return paths
