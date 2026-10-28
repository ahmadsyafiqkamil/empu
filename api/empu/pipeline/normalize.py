"""Two derivatives per recording: analysis.mp4 (for Muse) and display.mp4 (clips, keyframes)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from empu.pipeline.ffmpeg import ffmpeg_to, has_audio, probe_duration

# Height is capped, never upscaled. The comma inside min() must be escaped for the filter graph.
ANALYSIS_VIDEO = ["-vf", "scale=-2:min(480\\,ih)", "-c:v", "libx264", "-preset", "veryfast",
                  "-crf", "28", "-pix_fmt", "yuv420p"]
ANALYSIS_AUDIO = ["-c:a", "aac", "-ac", "1", "-b:a", "64k"]
DISPLAY_VIDEO = ["-vf", "scale=-2:min(720\\,ih)", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
DISPLAY_AUDIO = ["-c:a", "aac", "-b:a", "128k"]


@dataclass(frozen=True)
class NormalizedMedia:
    analysis_path: Path
    display_path: Path
    duration_s: float


def normalize_recording(src: Path, out_dir: Path, *, strip_audio: bool = False) -> NormalizedMedia:
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_in = has_audio(src)
    analysis = out_dir / "analysis.mp4"
    display = out_dir / "display.mp4"
    if not analysis.exists():
        audio = ANALYSIS_AUDIO if audio_in and not strip_audio else ["-an"]
        ffmpeg_to(analysis, ["-i", str(src), *ANALYSIS_VIDEO, *audio])
    if not display.exists():
        ffmpeg_to(
            display,
            ["-i", str(src), *DISPLAY_VIDEO, *(DISPLAY_AUDIO if audio_in else ["-an"])],
        )
    return NormalizedMedia(analysis, display, probe_duration(display))
