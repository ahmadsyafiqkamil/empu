from factories import make_archive, make_recording

from empu.enums import (
    AccessLevel,
    Category,
    ConsentStatus,
    EntryStatus,
    ReviewAction,
    Source,
    SourceKind,
)
from empu.models import Entry, Occurrence, ReviewEvent
from empu.visibility import (
    entry_is_public,
    public_entries,
    public_occurrences,
    recording_is_public,
    validated_by_expert,
    validation_label_for,
)


def _pub_rec(session, a, **kw):
    return make_recording(
        session,
        a,
        consent_status=ConsentStatus.granted,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.cc_by_video,
        source_url="https://youtu.be/x",
        source_creator="Batik Education",
        license="CC BY 3.0",
        attribution="clip by Batik Education",
        **kw,
    )


def test_internal_eval_never_public(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        source_kind=SourceKind.internal_eval,
        consent_scope=AccessLevel.private,
    )
    assert recording_is_public(rec) is False


def test_cc_by_missing_attribution_not_public(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        source_kind=SourceKind.cc_by_video,
        source_url="https://x",
        consent_scope=AccessLevel.public,
    )
    assert recording_is_public(rec) is False


def test_entry_hidden_when_no_public_occurrence(session):
    a = make_archive(session)
    rec = _pub_rec(session, a)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    assert public_occurrences(session, e.id)
    rec.consent_status = ConsentStatus.withdrawn
    session.add(rec)
    session.commit()
    assert public_occurrences(session, e.id) == []
    assert entry_is_public(e, []) is False


def test_proposed_not_public():
    e = Entry(
        archive_id=1,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.proposed,
        access_level=AccessLevel.public,
    )
    assert entry_is_public(e, []) is False


def test_public_entries_skips_rejected(session):
    a = make_archive(session)
    rec = _pub_rec(session, a)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.rejected,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    assert public_entries(session, a.id) == []


def _expert_event(session, e, action, actor):
    ev = ReviewEvent(entry_id=e.id, action=action, actor=actor)
    session.add(ev)
    session.commit()
    return ev


def test_expert_accept_counts_as_validation(session):
    a = make_archive(session)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    _expert_event(session, e, ReviewAction.accept, "Batik Education")
    assert validated_by_expert(session, e.id) is True
    assert validation_label_for(session, e.id) == "Validated by the expert · Batik Education"


def test_expert_reject_is_not_validation(session):
    a = make_archive(session)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    _expert_event(session, e, ReviewAction.reject, "Batik Education")
    assert validated_by_expert(session, e.id) is False
    assert validation_label_for(session, e.id) == "Validated by the documenter"


def test_empty_or_documenter_actor_is_not_expert(session):
    a = make_archive(session)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    _expert_event(session, e, ReviewAction.accept, "")
    _expert_event(session, e, ReviewAction.accept, "documenter")
    assert validated_by_expert(session, e.id) is False
