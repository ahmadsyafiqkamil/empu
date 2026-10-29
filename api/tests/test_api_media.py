from factories import make_archive, make_recording

from empu.enums import ConsentStatus, SourceKind
from empu.media import can_access_media


def test_withdrawn_blocked_even_with_key(session, settings, tmp_path):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        consent_status=ConsentStatus.withdrawn,
        display_path="archives/1/recordings/1/display.mp4",
    )
    assert can_access_media(session, rec.display_path, has_key=True) is False


def test_public_recording_accessible_without_key(session):
    a = make_archive(session)
    rec = make_recording(session, a, display_path="archives/1/recordings/1/display.mp4")
    assert can_access_media(session, rec.display_path, has_key=True) is True
    assert can_access_media(session, rec.display_path, has_key=False) is True


def test_internal_eval_blocked_without_key(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        source_kind=SourceKind.internal_eval,
        display_path="archives/1/recordings/1/display.mp4",
    )
    assert can_access_media(session, rec.display_path, has_key=False) is False


def test_range_request(api, session, settings, tmp_path):
    a = make_archive(session)
    rel = f"archives/{a.id}/recordings/1/display.mp4"
    path = settings.data_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"0123456789")
    make_recording(session, a, display_path=rel)
    r = api.get(f"/media/{rel}", headers={"Range": "bytes=0-3"})
    assert r.status_code == 206
    assert r.content == b"0123"


def test_public_media_served_without_key(api, session, settings, tmp_path):
    a = make_archive(session)
    rel = f"archives/{a.id}/recordings/1/display.mp4"
    path = settings.data_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"0123456789")
    make_recording(session, a, display_path=rel)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/media/{rel}")
    assert r.status_code == 200
    assert r.content == b"0123456789"


def test_private_entry_occurrence_media_blocked_without_key(api, session, settings, tmp_path):
    from empu.enums import AccessLevel, Category, EntryStatus, Source
    from empu.models import Entry, Occurrence

    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public)
    rel = f"archives/{a.id}/recordings/{rec.id}/occurrences/1/clip.mp4"
    path = settings.data_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"secret")
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.private,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(
            entry_id=e.id,
            recording_id=rec.id,
            source=Source.speech,
            t_start=1,
            t_end=2,
            clip_path=rel,
        )
    )
    session.commit()
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/media/{rel}")
    assert r.status_code == 401
