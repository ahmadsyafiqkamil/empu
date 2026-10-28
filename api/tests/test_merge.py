import pytest
from fakes import analysis, muse_term

from empu.enums import Category, Source, TimeSource
from empu.pipeline.merge import Canonicalizer, collect_occurrences, dedup_overlap, merge_analyses
from empu.pipeline.process_map import StepDraft


@pytest.fixture(scope="module")
def canon(pack):
    return Canonicalizer(pack)


def test_exact_variant_to_pack_term(canon):
    m = canon.match("Tjanting")
    assert (m.canon_key, m.term, m.pack_term_id, m.method, m.is_novel) == (
        "term:canting",
        "canting",
        "canting",
        "exact",
        False,
    )


def test_spoken_used_when_term_unknown(canon):
    m = canon.match("pena lilin", spoken="canting klowong")
    assert m.canon_key == "term:canting_klowongan"


def test_stage_variant(canon):
    m = canon.match("ngelorot")
    assert (m.canon_key, m.pack_stage_id, m.term) == ("stage:nglorod", "nglorod", "nglorod")
    assert canon.match("persiapan kain").term == "persiapan kain"


def test_fuzzy_match(canon):
    m = canon.match("cantingg")
    assert m.canon_key == "term:canting" and m.method == "fuzzy" and m.score >= 90


def test_novel(canon):
    m = canon.match("Bethik!", spoken="bethik")
    assert (m.canon_key, m.term, m.is_novel, m.method) == ("novel:bethik", "Bethik!", True, "novel")


def test_absolute_times_and_clamp(canon):
    a = analysis(
        1,
        65,
        140,
        terms=[
            muse_term(term="canting", t_start=3, t_end=4),
            muse_term(term="wajan", t_start=80, t_end=90),
        ],
    )
    occs = collect_occurrences([a], canon)
    assert [(o.t_start, o.t_end) for o in occs] == [(68, 69), (140, 140)]
    assert occs[0].edge_s == 3


def test_dedup_across_overlap_keeps_higher_confidence(canon):
    a0 = analysis(
        0, 0, 75, terms=[muse_term(term="canting", t_start=70, t_end=71, confidence="high")]
    )
    a1 = analysis(
        1, 65, 140, terms=[muse_term(term="canting", t_start=5.5, t_end=6, confidence="medium")]
    )
    kept = dedup_overlap(collect_occurrences([a0, a1], canon))
    assert len(kept) == 1 and kept[0].chunk_idx == 0


def test_dedup_tie_prefers_farther_from_edge(canon):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=73, t_end=74)])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=8, t_end=9)])
    kept = dedup_overlap(collect_occurrences([a0, a1], canon))
    assert len(kept) == 1 and kept[0].chunk_idx == 1


def test_same_chunk_repeats_and_far_apart_are_kept(canon):
    a0 = analysis(
        0,
        0,
        75,
        terms=[
            muse_term(term="canting", t_start=10, t_end=11),
            muse_term(term="canting", t_start=12, t_end=13),
        ],
    )
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=30, t_end=31)])
    assert len(dedup_overlap(collect_occurrences([a0, a1], canon))) == 3


def test_group_entries_best_category_variants_gloss(pack):
    a = analysis(
        0,
        0,
        75,
        terms=[
            muse_term(
                term="canting",
                spoken="tjanting",
                source="visual_only",
                confidence="high",
                t_start=5,
                t_end=6,
                gloss_id="",
            ),
            muse_term(
                term="canting",
                spoken="nyanting",
                source="speech",
                confidence="low",
                t_start=20,
                t_end=21,
                gloss_id="alat tulis lilin",
                gloss_en="wax pen",
                stage="nglowong",
            ),
            muse_term(term="bethik", category="material", source="speech", t_start=30, t_end=31),
        ],
    )
    drafts = {d.canon.canon_key: d for d in merge_analyses([a], pack)}
    c = drafts["term:canting"]
    assert c.best.muse.source is Source.speech and c.best.t_start == 20
    assert c.category is Category.tool and c.gloss_id == "alat tulis lilin"
    assert c.variants == ["nyanting", "tjanting"]
    assert c.stage_id == "nglowong"
    n = drafts["novel:bethik"]
    assert n.canon.is_novel and n.category is Category.material


def test_stage_from_process_steps_when_muse_stage_missing(pack):
    a = analysis(0, 0, 75, terms=[muse_term(term="wajan", t_start=40, t_end=41)])
    steps = [StepDraft("nembok", "nembok", 30, 50)]
    (d,) = merge_analyses([a], pack, steps=steps)
    assert d.occurrences[0].stage_id == "nembok" and d.stage_id == "nembok"


def test_stage_entry_uses_its_own_stage(pack):
    (d,) = merge_analyses(
        [analysis(0, 0, 75, terms=[muse_term(term="nglorod", category="stage")])], pack
    )
    assert d.category is Category.stage and d.stage_id == "nglorod"


def test_retime_runs_before_dedup(pack):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=10, t_end=11)])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=5, t_end=6)])

    def retime(occs):
        for o in occs:
            o.t_start, o.time_source = 70.0, TimeSource.asr
        return occs

    (d,) = merge_analyses([a0, a1], pack, retime=retime)
    assert len(d.occurrences) == 1 and d.best.time_source is TimeSource.asr
