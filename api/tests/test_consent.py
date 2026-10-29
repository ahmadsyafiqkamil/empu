"""Tests for consent withdrawal."""

from factories import make_archive, make_recording

from empu.consent import withdraw_consent
from empu.enums import AccessLevel, Category, ConsentStatus, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence
from empu.visibility import public_entries, public_occurrences


def test_withdraw_hides_public_entries(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.own_recording,
    )
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
    rec2 = withdraw_consent(session, rec.id)
    assert rec2.consent_status is ConsentStatus.withdrawn
    assert public_occurrences(session, e.id) == []
    assert public_entries(session, a.id) == []


def test_withdraw_http(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    r = api.post(f"/api/recordings/{rec.id}/withdraw-consent")
    assert r.status_code == 200
    assert r.json()["consent_status"] == "withdrawn"
