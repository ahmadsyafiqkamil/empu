import pytest
from fakes import analysis

from empu.pipeline.process_map import StageMatcher, build_process_map, stage_at


@pytest.fixture(scope="module")
def matcher(pack):
    return StageMatcher(pack)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("nglowong", "nglowong"),
        ("Ngelorot", "nglorod"),
        ("persiapan kain", "persiapan_kain"),
        ("nglowongg", "nglowong"),
        ("proses nglowong dengan canting", "nglowong"),
        ("istirahat sebentar", None),
        ("", None),
        (None, None),
    ],
)
def test_resolve(matcher, name, expected):
    assert matcher.resolve(name) == expected


def test_term_variants_are_not_stages(matcher):
    assert matcher.resolve("canting") is None


def test_build_merges_same_stage_across_overlap(pack):
    a0 = analysis(
        0,
        0,
        75,
        steps=[
            {"step": "memola", "t_start": 0, "t_end": 50, "tools": ["pensil"]},
            {"step": "nglowong", "t_start": 60, "t_end": 75, "tools": ["canting"]},
        ],
    )
    a1 = analysis(
        1,
        65,
        140,
        steps=[
            {"step": "ngelowong", "t_start": 0, "t_end": 20, "tools": ["wajan"]},
            {"step": "minum teh", "t_start": 30, "t_end": 40, "tools": []},
        ],
    )
    steps = build_process_map([a0, a1], pack)
    assert [(s.pack_stage_id, s.t_start, s.t_end) for s in steps] == [
        ("memola", 0, 50),
        ("nglowong", 60, 85),
        (None, 95, 105),
    ]
    assert steps[1].tools == ["canting", "wajan"]
    assert [s.order for s in steps] == [0, 1, 2]
    assert steps[2].name_raw == "minum teh"


def test_gap_larger_than_five_seconds_not_merged(pack):
    a = analysis(
        0,
        0,
        75,
        steps=[
            {"step": "nglowong", "t_start": 0, "t_end": 10, "tools": []},
            {"step": "nglowong", "t_start": 20, "t_end": 30, "tools": []},
        ],
    )
    assert len(build_process_map([a], pack)) == 2


def test_failed_chunks_skipped(pack):
    a = analysis(0, 0, 75)
    a.output = None
    assert build_process_map([a], pack) == []


def test_stage_at(pack):
    steps = build_process_map(
        [
            analysis(
                0,
                0,
                75,
                steps=[
                    {"step": "memola", "t_start": 0, "t_end": 30, "tools": []},
                    {"step": "nglowong", "t_start": 25, "t_end": 60, "tools": []},
                ],
            )
        ],
        pack,
    )
    assert stage_at(steps, 10) == "memola"
    assert stage_at(steps, 27) == "nglowong"
    assert stage_at(steps, 70) is None
