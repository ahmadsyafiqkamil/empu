import pytest
from factories import make_archive, make_recording
from sqlalchemy.exc import IntegrityError

from empu.enums import AccessLevel, EntryStatus, JobStatus, PipelineMode, SourceKind
from empu.models import Entry, Job


def test_tables_roundtrip_with_json_columns(session):
    a = make_archive(session)
    r = make_recording(
        session,
        a,
        source_kind=SourceKind.cc_by_video,
        source_url="https://y/1",
        source_creator="Kreator",
        license="CC BY 3.0",
        attribution="by Kreator",
    )
    job = Job(
        recording_id=r.id,
        mode=PipelineMode.B,
        model="m",
        prompt_version="v",
        timings_json={"normalizing": {"seconds": 1.5}},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    assert job.status is JobStatus.queued and job.timings_json["normalizing"]["seconds"] == 1.5
    assert r.consent_scope is AccessLevel.public and r.source_kind is SourceKind.cc_by_video


def test_entry_defaults_and_unique_canon_key_per_archive(session):
    a = make_archive(session)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category="tool", variants_json=["X"])
    session.add(e)
    session.commit()
    assert e.status is EntryStatus.proposed
    assert e.variants_json == ["X"] and e.sam_status == "skipped"
    session.add(Entry(archive_id=a.id, canon_key="term:x", term="x", category="tool"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_canon_key_allowed_in_other_archive(session):
    a, b = make_archive(session), make_archive(session)
    session.add_all(
        [
            Entry(archive_id=a.id, canon_key="term:x", term="x", category="tool"),
            Entry(archive_id=b.id, canon_key="term:x", term="x", category="tool"),
        ]
    )
    session.commit()


def test_wal_and_foreign_keys_enabled(engine):
    with engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
