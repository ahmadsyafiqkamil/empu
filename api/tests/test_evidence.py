import pytest
from conftest import requires_ffmpeg

from empu.pipeline.evidence import clip_window, make_evidence
from empu.pipeline.ffmpeg import has_audio, probe_duration


@pytest.mark.parametrize(
    "t0, t1, dur, expected",
    [
        (10, 11, 100, (9.0, 12.5)),
        (10, 10, 100, (8.75, 11.75)),
        (10, 20, 100, (9.0, 17.0)),
        (0.2, 0.5, 100, (0.0, 3.0)),
        (11.5, 11.8, 12, (9.0, 12.0)),
        (0.5, 1.0, 2, (0.0, 2.0)),
    ],
)
def test_clip_window(t0, t1, dur, expected):
    assert clip_window(t0, t1, dur) == expected


@requires_ffmpeg
def test_make_evidence(sample_video, tmp_path):
    ev = make_evidence(sample_video, 5.0, 6.0, 12.0, tmp_path / "occ")
    assert (ev.clip_start, ev.clip_end) == (4.0, 7.5)
    assert abs(probe_duration(ev.clip) - 3.5) < 0.3
    assert ev.audio is not None and has_audio(ev.audio)
    assert ev.keyframe.stat().st_size > 1000
    before = ev.clip.stat().st_mtime_ns
    make_evidence(sample_video, 5.0, 6.0, 12.0, tmp_path / "occ")
    assert ev.clip.stat().st_mtime_ns == before
