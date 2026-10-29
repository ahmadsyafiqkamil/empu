"""Tests for the judge sandbox: no-key upload, unlisted archive, and no-key read gating."""

from factories import make_archive, make_recording

from empu.enums import AccessLevel, Category, EntryStatus, JobStatus, ReviewAction, Source
from empu.models import Archive, Entry, Job, Occurrence, Recording
from empu.visibility import public_entries, public_occurrences


def _upload(api):
    return api.post(
        "/api/sandbox/recordings",
        data={"title": "Judge clip", "consent_confirmed": "true"},
        files={"file": ("a.mp4", b"xxxxx", "video/mp4")},
    )


def test_sandbox_upload_without_key(api, session):
    api.headers.pop("X-Studio-Key", None)
    r = _upload(api)
    assert r.status_code == 201
    rec = session.get(Recording, r.json()["recording_id"])
    arch = session.get(Archive, rec.archive_id)
    assert arch.is_sandbox is True


def test_sandbox_hidden_from_public_list(api, session):
    api.headers.pop("X-Studio-Key", None)
    _upload(api)
    slugs = [a["slug"] for a in api.get("/api/public/archives").json()]
    assert "sandbox" not in slugs


def test_non_sandbox_job_still_401(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    job = Job(recording_id=rec.id, status=JobStatus.queued)
    session.add(job)
    session.commit()
    session.refresh(job)
    api.headers.pop("X-Studio-Key", None)
    assert api.get(f"/api/jobs/{job.id}").status_code == 401


def test_non_sandbox_recording_and_entries_still_401(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    api.headers.pop("X-Studio-Key", None)
    assert api.get(f"/api/recordings/{rec.id}").status_code == 401
    assert api.get(f"/api/recordings/{rec.id}/entries").status_code == 401


def test_sandbox_recording_and_entries_without_key(api, session):
    api.headers.pop("X-Studio-Key", None)
    r = _upload(api)
    rec_id = r.json()["recording_id"]
    assert api.get(f"/api/recordings/{rec_id}").status_code == 200
    assert api.get(f"/api/recordings/{rec_id}/entries").status_code == 200
    job_id = r.json()["job_id"]
    assert api.get(f"/api/jobs/{job_id}").status_code == 200


def _sandbox_entry(session, rec) -> Entry:
    e = Entry(
        archive_id=rec.archive_id,
        canon_key="term:canting",
        term="canting",
        category=Category.tool,
        status=EntryStatus.proposed,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    return e


def test_sandbox_review_without_key(api, session):
    api.headers.pop("X-Studio-Key", None)
    r = _upload(api)
    rec = session.get(Recording, r.json()["recording_id"])
    e = _sandbox_entry(session, rec)
    rr = api.post(
        f"/api/entries/{e.id}/review",
        json={"action": ReviewAction.accept.value, "actor": "judge"},
    )
    assert rr.status_code == 200
    assert rr.json()["status"] == "accepted"


def test_sandbox_not_publicly_visible(session):
    a = make_archive(session, is_sandbox=True)
    rec = make_recording(session, a, consent_scope=AccessLevel.public)
    e = _sandbox_entry(session, rec)
    session.refresh(e)
    e.status = EntryStatus.accepted
    session.add(e)
    session.commit()
    assert public_occurrences(session, e.id) == []
    assert public_entries(session, a.id) == []
