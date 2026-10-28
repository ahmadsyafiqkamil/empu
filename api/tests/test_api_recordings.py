from factories import make_archive, make_recording

from empu.enums import JobStatus, PipelineMode
from empu.models import Job


def test_list_packs(api, pack):
    r = api.get("/api/packs")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert "batik_tulis" in ids


def test_create_archive_and_list(api):
    r = api.post("/api/archives", json={"slug": "hidup-batik", "title": "Arsip Hidup Batik"})
    assert r.status_code == 201
    assert r.json()["slug"] == "hidup-batik"
    listed = api.get("/api/archives").json()
    assert listed[0]["title"] == "Arsip Hidup Batik"


def test_upload_requires_consent(api, tmp_path, session):
    a = make_archive(session)
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x" * 100)
    r = api.post(
        f"/api/archives/{a.id}/recordings",
        data={"title": "Tes", "consent_confirmed": "false"},
        files={"file": ("a.mp4", video.read_bytes(), "video/mp4")},
    )
    assert r.status_code == 400
    assert "consent" in r.json()["detail"].lower()


def test_upload_ok(api, tmp_path, session):
    a = make_archive(session)
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x" * 100)
    r = api.post(
        f"/api/archives/{a.id}/recordings",
        data={
            "title": "Nyanting",
            "consent_confirmed": "true",
            "contributor_name": "Bu Ahli",
            "consent_scope": "public",
        },
        files={"file": ("a.mp4", video.read_bytes(), "video/mp4")},
    )
    assert r.status_code == 201
    body = r.json()
    assert "recording_id" in body and "job_id" in body
    rec = api.get(f"/api/recordings/{body['recording_id']}").json()
    assert rec["title"] == "Nyanting"
    assert rec["job"]["status"] == "queued"


def test_cc_by_requires_attribution(api, tmp_path, session):
    a = make_archive(session)
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    r = api.post(
        f"/api/archives/{a.id}/recordings",
        data={"title": "CC", "consent_confirmed": "true", "source_kind": "cc_by_video"},
        files={"file": ("a.mp4", video.read_bytes(), "video/mp4")},
    )
    assert r.status_code == 400


def test_job_shape(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    job = Job(
        recording_id=rec.id,
        status=JobStatus.analyzing,
        progress=0.4,
        detail="segment 2/5",
        mode=PipelineMode.B,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    r = api.get(f"/api/jobs/{job.id}").json()
    assert r["status"] == "analyzing" and r["progress"] == 0.4
    names = [s["name"] for s in r["stages"]]
    assert names == ["normalizing", "chunking", "analyzing", "merging", "grounding", "cutting"]
    assert r["stages"][2]["status"] == "running"
