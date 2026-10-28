# api/tests/test_persist.py
from factories import make_archive, make_recording
from fakes import analysis, muse_term
from sqlmodel import select

from empu.enums import AccessLevel, EntryStatus, ReviewAction, Source
from empu.models import Entry, Occurrence, ProcessStep, ReviewEvent
from empu.persist import find_entry, persist_results
from empu.pipeline.merge import merge_analyses
from empu.pipeline.process_map import build_process_map


def drafts_and_steps(pack, terms, steps=()):
    a = analysis(0, 0, 75, terms=terms, steps=steps)
    s = build_process_map([a], pack)
    return merge_analyses([a], pack, steps=s), s


TERMS = [
    muse_term(term="canting", source="speech", t_start=2, t_end=3, confidence="high"),
    muse_term(term="tjanting", source="on_screen_text", t_start=9, t_end=10),
    muse_term(term="bethik", source="speech", t_start=5, t_end=6),
]


def test_persist_creates_entries_occurrences_steps(session, pack):
    a = make_archive(session)
    r = make_recording(session, a, consent_scope=AccessLevel.community)
    drafts, steps = drafts_and_steps(
        pack, TERMS, [{"step": "nglowong", "t_start": 0, "t_end": 75, "tools": []}]
    )
    entries = persist_results(session, r, drafts, steps, {0: 77})
    assert {e.canon_key for e in entries} == {"term:canting", "novel:bethik"}
    canting = find_entry(session, a.id, "term:canting")
    occs = session.exec(select(Occurrence).where(Occurrence.entry_id == canting.id)).all()
    assert len(occs) == 2 and {o.chunk_id for o in occs} == {77}
    best = session.get(Occurrence, canting.best_occurrence_id)
    assert best.source is Source.speech and best.stage_id == "nglowong"
    assert canting.access_level is AccessLevel.community and canting.status is EntryStatus.proposed
    assert session.exec(select(ProcessStep)).one().pack_stage_id == "nglowong"


def test_reprocess_replaces_and_cleans_orphans(session, pack):
    a = make_archive(session)
    r = make_recording(session, a)
    drafts, steps = drafts_and_steps(pack, TERMS)
    persist_results(session, r, drafts, steps, {})
    drafts2, steps2 = drafts_and_steps(pack, TERMS[:2])
    persist_results(session, r, drafts2, steps2, {})
    assert len(session.exec(select(Occurrence)).all()) == 2
    assert find_entry(session, a.id, "novel:bethik") is None


def test_reviewed_entry_survives_and_keeps_fields(session, pack):
    a = make_archive(session)
    r = make_recording(session, a)
    drafts, steps = drafts_and_steps(pack, TERMS)
    persist_results(session, r, drafts, steps, {})
    e = find_entry(session, a.id, "novel:bethik")
    e.status, e.gloss_en = EntryStatus.edited, "corrected by the expert"
    session.add(ReviewEvent(entry_id=e.id, action=ReviewAction.edit, actor="x"))
    session.commit()
    drafts2, steps2 = drafts_and_steps(pack, TERMS[:2])
    persist_results(session, r, drafts2, steps2, {})
    e = session.get(Entry, e.id)
    assert e.status is EntryStatus.edited and e.gloss_en == "corrected by the expert"
    assert e.best_occurrence_id is None


def test_second_recording_appends_to_same_entry(session, pack):
    a = make_archive(session)
    r1, r2 = make_recording(session, a), make_recording(session, a)
    for r in (r1, r2):
        drafts, steps = drafts_and_steps(pack, TERMS[:1])
        persist_results(session, r, drafts, steps, {})
    e = find_entry(session, a.id, "term:canting")
    occs = session.exec(select(Occurrence).where(Occurrence.entry_id == e.id))
    recs = {o.recording_id for o in occs}
    assert recs == {r1.id, r2.id}


def test_find_entry_follows_merge(session, pack):
    a = make_archive(session)
    target = Entry(archive_id=a.id, canon_key="term:canting", term="canting", category="tool")
    session.add(target)
    session.commit()
    src = Entry(
        archive_id=a.id,
        canon_key="novel:tjantingan",
        term="tjantingan",
        category="tool",
        status=EntryStatus.merged,
        merged_into_id=target.id,
    )
    session.add(src)
    session.commit()
    assert find_entry(session, a.id, "novel:tjantingan").id == target.id
