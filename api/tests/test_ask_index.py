from factories import make_archive, make_recording
from sqlmodel import select

from empu.ask.index import build_index, prefilter
from empu.enums import AccessLevel, Category, EntryStatus, Source
from empu.models import Entry, Occurrence


def _entry(session, archive, term: str, **kw) -> Entry:
    e = Entry(
        archive_id=archive.id,
        canon_key=f"term:{term}",
        term=term,
        category=kw.pop("category", Category.tool),
        status=kw.pop("status", EntryStatus.accepted),
        access_level=kw.pop("access_level", AccessLevel.public),
        gloss_id=kw.pop("gloss_id", ""),
        gloss_en=kw.pop("gloss_en", ""),
        variants_json=kw.pop("variants_json", []),
        **kw,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    return e


def _occ(session, entry, recording, **kw) -> Occurrence:
    o = Occurrence(
        entry_id=entry.id,
        recording_id=recording.id,
        source=kw.pop("source", Source.speech),
        t_start=kw.pop("t_start", 1.0),
        t_end=kw.pop("t_end", 2.0),
        **kw,
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def test_build_index_prefers_best_occurrence_and_caps_evidence(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = _entry(session, a, "canting", gloss_en="wax pen")
    first = _occ(session, e, rec, t_start=1.0, evidence_quote="first")
    best = _occ(session, e, rec, t_start=9.0, evidence_quote="best")
    third = _occ(session, e, rec, t_start=20.0, evidence_quote="third")
    e.best_occurrence_id = best.id
    session.add(e)
    session.commit()

    rows = build_index([(e, [first, best, third])])

    assert len(rows) == 1
    assert len(rows[0].evidence) == 2
    assert rows[0].evidence[0].quote == "best"
    assert rows[0].evidence[0].t_start == 9.0


def test_build_index_falls_back_to_visible_when_quote_is_empty(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = _entry(session, a, "nglorod")
    _occ(session, e, rec, source=Source.visual_only, visible="kain diaduk", evidence_quote="")

    occ = session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).one()
    rows = build_index([(e, [occ])])

    assert rows[0].evidence[0].quote == "kain diaduk"
    assert rows[0].evidence[0].source == "visual_only"


def test_build_index_keeps_entry_with_no_occurrences(session):
    a = make_archive(session)
    e = _entry(session, a, "canting")
    rows = build_index([(e, [])])
    assert rows[0].evidence == ()
    assert rows[0].term == "canting"


def test_prefilter_returns_everything_when_under_limit(session):
    a = make_archive(session)
    rows = [build_index([(_entry(session, a, f"t{i}"), [])])[0] for i in range(3)]
    assert prefilter("anything", rows, limit=10) == rows


def test_prefilter_keeps_exact_term_when_limit_is_tight(session):
    a = make_archive(session)
    rows = [
        build_index([(_entry(session, a, "canting", gloss_id="alat pena tembaga"), [])])[0],
        build_index([(_entry(session, a, "mori", gloss_id="kain katun putih"), [])])[0],
        build_index([(_entry(session, a, "cecek", gloss_id="titik-titik kecil"), [])])[0],
        build_index([(_entry(session, a, "nembok", gloss_id="menutup bidang dasar"), [])])[0],
        build_index([(_entry(session, a, "paruh", gloss_id="ujung pencucur"), [])])[0],
    ]

    picked = prefilter("apa itu canting?", rows, limit=2)

    assert picked[0].term == "canting"
    assert len(picked) == 2


def test_prefilter_matches_a_variant(session):
    a = make_archive(session)
    rows = [
        build_index([(_entry(session, a, "nglorod", variants_json=["ngelorot"]), [])])[0],
        build_index([(_entry(session, a, "mori"), [])])[0],
        build_index([(_entry(session, a, "cecek"), [])])[0],
    ]

    picked = prefilter("apa itu ngelorot", rows, limit=1)

    assert [r.term for r in picked] == ["nglorod"]


def test_prefilter_respects_limit_and_returns_id_order(session):
    a = make_archive(session)
    rows = [build_index([(_entry(session, a, f"istilah{i}"), [])])[0] for i in range(8)]

    picked = prefilter("istilah3", rows, limit=3)

    assert len(picked) == 3
    assert [r.id for r in picked] == sorted(r.id for r in picked)
