from factories import make_archive, make_recording

from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence, ProcessStep


def _setup(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.own_recording,
        duration_s=20,
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:canting",
        term="canting",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        stage_id="nglowong",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(
            entry_id=e.id,
            recording_id=rec.id,
            source=Source.speech,
            t_start=5,
            t_end=6,
            stage_id="nglowong",
            keyframe_path="archives/1/recordings/1/occurrences/1/keyframe.jpg",
        )
    )
    session.add(
        ProcessStep(
            recording_id=rec.id,
            pack_stage_id="nglowong",
            name_raw="nglowong",
            t_start=0,
            t_end=10,
            order=0,
        )
    )
    session.commit()
    return a, rec, e


def test_studio_process_map(api, session):
    a, rec, e = _setup(session)
    r = api.get(f"/api/recordings/{rec.id}/process-map")
    assert r.status_code == 200
    body = r.json()
    assert body["steps"][0]["pack_stage_id"] == "nglowong"
    assert body["steps"][0]["entries"][0]["term"] == "canting"
    assert body["steps"][0]["entries"][0]["keyframe_url"].startswith("/media/")


def test_public_process_map(api, session):
    a, rec, e = _setup(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/public/recordings/{rec.id}/process-map")
    assert r.status_code == 200
    assert r.json()["steps"][0]["pack_stage_id"] == "nglowong"


def test_public_process_map_404_when_hidden(api, session):
    a = make_archive(session)
    rec = make_recording(session, a, source_kind=SourceKind.internal_eval)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/public/recordings/{rec.id}/process-map")
    assert r.status_code == 404