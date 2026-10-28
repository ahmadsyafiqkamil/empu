import pytest

from empu.media import abs_from_rel, occurrence_dir, recording_dir, rel_to_data


def test_layout(tmp_path):
    assert recording_dir(tmp_path, 1, 3) == tmp_path / "archives/1/recordings/3"
    assert occurrence_dir(tmp_path, 1, 3, 9) == tmp_path / "archives/1/recordings/3/occurrences/9"


def test_rel_roundtrip(tmp_path):
    p = recording_dir(tmp_path, 1, 3) / "display.mp4"
    rel = rel_to_data(tmp_path, p)
    assert rel == "archives/1/recordings/3/display.mp4"
    assert abs_from_rel(tmp_path, rel) == tmp_path / rel


@pytest.mark.parametrize("bad", ["", "/etc/passwd", "../x", "archives/../../x"])
def test_abs_from_rel_rejects_escape(tmp_path, bad):
    with pytest.raises(ValueError):
        abs_from_rel(tmp_path, bad)


def test_rel_to_data_rejects_outside(tmp_path):
    with pytest.raises(ValueError):
        rel_to_data(tmp_path / "data", tmp_path / "elsewhere.mp4")
