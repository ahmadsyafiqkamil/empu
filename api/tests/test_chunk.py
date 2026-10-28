import pytest
from conftest import requires_ffmpeg

from empu.pipeline.chunk import ChunkSpec, cut_chunks, plan_chunks
from empu.pipeline.ffmpeg import probe_duration


def starts(specs):
    return [s.start_s for s in specs]


def test_five_minutes_gives_five_segments():
    specs = plan_chunks(300)
    assert starts(specs) == [0, 65, 130, 195, 260]
    assert specs[-1].end_s == 300
    assert [s.idx for s in specs] == [0, 1, 2, 3, 4]


def test_241s_gives_four_segments():
    specs = plan_chunks(241)
    assert [(s.start_s, s.end_s) for s in specs] == [(0, 75), (65, 140), (130, 205), (195, 241)]


def test_short_and_boundary_durations():
    assert plan_chunks(60) == [ChunkSpec(0, 0, 60)]
    assert plan_chunks(75) == [ChunkSpec(0, 0, 75)]
    assert [(s.start_s, s.end_s) for s in plan_chunks(76)] == [(0, 75), (65, 76)]


def test_invalid_arguments():
    with pytest.raises(ValueError):
        plan_chunks(0)
    with pytest.raises(ValueError):
        plan_chunks(100, window_s=10, overlap_s=10)


def test_duration_property():
    assert ChunkSpec(1, 65, 140).duration_s == 75


@requires_ffmpeg
def test_cut_chunks_real_video(sample_video, tmp_path):
    specs = plan_chunks(12, window_s=5, overlap_s=1)
    assert starts(specs) == [0, 4, 8]
    paths = cut_chunks(sample_video, specs, tmp_path / "chunks")
    assert [p.stem for p in paths] == ["0", "1", "2"]
    assert abs(probe_duration(paths[0]) - 5) < 0.3
    assert abs(probe_duration(paths[2]) - 4) < 0.3
