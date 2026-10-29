import io
import json
import zipfile

from factories import make_archive, make_recording

from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.export.zip_export import build_zip
from empu.models import Entry, Occurrence


def test_all_scope_requires_key(api, session):
    a = make_archive(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/archives/{a.id}/export", params={"format": "json", "scope": "all"})
    assert r.status_code == 401


def test_public_json_ok(api, session):
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
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/archives/{a.id}/export", params={"format": "json", "scope": "public"})
    assert r.status_code == 200
    assert r.json()["entries"][0]["occurrences"][0]["source"] == "speech"


def test_zip_contains_dataset_csv_readme_and_clip(session, settings, pack):
    a = make_archive(session)
    rel = f"archives/{a.id}/recordings/1/occurrences/1/clip.mp4"
    path = settings.data_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"clip-bytes")
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.own_recording,
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="canting",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
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
    data = build_zip(session, a, pack, "public", settings)
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    assert "empu-dataset.json" in names
    assert "entries.csv" in names
    assert "README.txt" in names
    assert f"media/{rel}" in names
    assert json.loads(z.read("empu-dataset.json"))["entries"][0]["term"] == "canting"
