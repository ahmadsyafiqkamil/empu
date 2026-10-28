import pytest

from conftest import requires_ffmpeg
from empu.pipeline.ffmpeg import FFmpegError, has_audio, probe_height, run_ffmpeg
from empu.pipeline.normalize import normalize_recording


@requires_ffmpeg
def test_normalize_makes_two_derivatives(sample_video, tmp_path):
    m = normalize_recording(sample_video, tmp_path / "rec")
    assert m.analysis_path == tmp_path / "rec" / "analysis.mp4"
    assert m.display_path == tmp_path / "rec" / "display.mp4"
    assert probe_height(m.analysis_path) == 480
    assert probe_height(m.display_path) == 720
    assert has_audio(m.analysis_path) and has_audio(m.display_path)
    assert abs(m.duration_s - 12) < 0.3


@requires_ffmpeg
def test_strip_audio_only_affects_analysis(sample_video, tmp_path):
    m = normalize_recording(sample_video, tmp_path / "rec", strip_audio=True)
    assert not has_audio(m.analysis_path)
    assert has_audio(m.display_path)


@requires_ffmpeg
def test_normalize_is_idempotent_and_leaves_no_tmp(sample_video, tmp_path):
    m = normalize_recording(sample_video, tmp_path / "rec")
    before = m.analysis_path.stat().st_mtime_ns
    normalize_recording(sample_video, tmp_path / "rec")
    assert m.analysis_path.stat().st_mtime_ns == before
    assert list((tmp_path / "rec").glob("*.tmp*")) == []


@requires_ffmpeg
def test_ffmpeg_error_carries_stderr(tmp_path):
    with pytest.raises(FFmpegError, match="No such file"):
        run_ffmpeg(["-i", str(tmp_path / "missing.mp4"), str(tmp_path / "out.mp4")])
