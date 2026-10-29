from factories import make_archive, make_recording

from empu.enums import (
    AccessLevel,
    Category,
    ConsentStatus,
    EntryStatus,
    Source,
    SourceKind,
)
from empu.models import Entry, Occurrence
from empu.visibility import (
    entry_is_public,
    public_entries,
    public_occurrences,
    recording_is_public,
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