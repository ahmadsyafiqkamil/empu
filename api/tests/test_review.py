import pytest
from factories import make_archive, make_recording
from sqlmodel import select

from empu.api_schemas import ReviewIn
from empu.enums import Category, EntryStatus, OccurrenceStatus, ReviewAction, Source
from empu.models import Entry, Occurrence, ReviewEvent
from empu.review import ReviewError, apply_review


def _entry(session, a, rec, term="canting"):
    e = Entry(archive_id=a.id, canon_key=f"term:{term}", term=term, category=Category.tool)
    session.add(e)
    session.commit()
    session.refresh(e)
    o = Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    session.add(o)
    session.commit()
    session.refresh(o)
    e.best_occurrence_id = o.id
    session.add(e)
    session.commit()
    session.refresh(e)
    return e, o


def test_accept_writes_event(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e, o = _entry(session, a, rec)
    out = apply_review(session, e.id, ReviewIn(action=ReviewAction.accept, actor="syafiq"))
    assert out.status is EntryStatus.accepted
    session.refresh(o)
    assert o.status is OccurrenceStatus.accepted
    events = session.exec(select(ReviewEvent).where(ReviewEvent.entry_id == e.id)).all()
    assert len(events) == 1 and events[0].actor == "syafiq"
    assert events[0].action is ReviewAction.accept


def test_edit_changes_gloss(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    out = apply_review(
        session,
        e.id,
        ReviewIn(
            action=ReviewAction.edit,
            actor="syafiq",
            changes={"gloss_en": "wax pen", "maestro_note": "ok"},
        ),
    )
    assert out.status is EntryStatus.edited and out.gloss_en == "wax pen"


def test_merge_moves_occurrences(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e1, _o1 = _entry(session, a, rec, "canting")
    e2, o2 = _entry(session, a, rec, "tjanting")
    apply_review(session, e1.id, ReviewIn(action=ReviewAction.accept, actor="s"))
    out = apply_review(
        session,
        e2.id,
        ReviewIn(action=ReviewAction.merge, actor="s", merge_into_id=e1.id),
    )
    assert out.status is EntryStatus.merged and out.merged_into_id == e1.id
    session.refresh(o2)
    assert o2.entry_id == e1.id


def test_reject_unknown_field(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    with pytest.raises(ReviewError, match="unknown"):
        apply_review(
            session,
            e.id,
            ReviewIn(action=ReviewAction.edit, actor="s", changes={"nope": 1}),
        )


def test_restore(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    apply_review(session, e.id, ReviewIn(action=ReviewAction.accept, actor="s"))
    out = apply_review(session, e.id, ReviewIn(action=ReviewAction.restore, actor="s"))
    assert out.status is EntryStatus.proposed
