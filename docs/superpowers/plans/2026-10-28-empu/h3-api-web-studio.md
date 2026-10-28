# H3 (Sab 31 Okt): REST API, Media, Unggah, Progres, Studio

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pendokumentasi bisa mengunggah rekaman lewat UI, melihat progres pipeline, lalu menerima/mengubah/menolak/menggabungkan entri di Studio — end-to-end pada satu video CC BY.

**Architecture:** FastAPI di `api/empu/app.py` dengan route per domain. Semua endpoint tulis butuh `X-Studio-Key`. Frontend Next.js 16 (App Router) di `web/` memanggil API lewat rewrite same-origin (`/api/*`, `/media/*`). Studio adalah halaman desktop-first mode **Malam**: pemutar + timeline di kiri, kartu entri di kanan. Token, copy, dan layout: `desain.md`.

**Tech Stack:** FastAPI, SQLModel, Starlette `FileResponse` (Range), python-multipart. Next.js 16.4, TypeScript, Tailwind 4, next/font, lucide-react, vitest.

## Global Constraints

Semua butir di `00-ikhtisar.md` bagian "Global Constraints" berlaku. Yang paling relevan:
- Header `X-Studio-Key` wajib untuk semua endpoint di luar `/api/health`, `/api/packs*`. (Publik, eval, sandbox: H4–H6.)
- Label `source` tidak boleh hilang di JSON API maupun UI. `SourceBadge` = ikon + teks (`Spoken` / `On-screen text` / `Visual only`), bukan warna saja.
- UI bahasa Inggris. Istilah keahlian tetap asli. Glosa ID dan EN. Copy persis `desain.md` / brief bagian 8.
- Visual: baca `desain.md` (D11). Kalau kode kerangka di bawah bertentangan dengan `desain.md`, ikut `desain.md`.
- `window.prompt` dilarang. Edit/merge inline. Studio < 1280 px: pesan desktop-only.
- Polling progres setiap 2 detik.
- Unggahan: `consent_confirmed` wajib `true`. Batas 500 MB / 20 menit.
- Tes API memakai `TestClient` + SQLite temp + `FakeClient`. Tidak ada jaringan.
- `can_access_media` di H3: file dari rekaman `consent_status=withdrawn` ditolak; selain itu studio key boleh semua, tanpa key ditolak (aturan publik penuh di H4).

## Prasyarat
- Gate 1 lulus: satu video uji ada di DB dengan entri, klip, keyframe (dan crop kalau SAM jalan).
- Worker bisa dijalankan: `uv run python -m empu.worker`.
- Node 24, pnpm 10.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/db.py` | Modify | `get_session`, `get_engine` |
| `api/empu/auth.py` | Create | studio key |
| `api/empu/media.py` | Modify | `can_access_media` |
| `api/empu/api_schemas.py` | Create | request/response Pydantic |
| `api/empu/serialize.py` | Create | model DB → skema API |
| `api/empu/review.py` | Create | `apply_review` |
| `api/empu/routes/*.py` | Create | health, packs, archives, recordings, jobs, entries, media |
| `api/empu/app.py` | Create | `create_app()` |
| `api/tests/test_api_*.py` | Create | Tes HTTP |
| `web/` | Create | Next.js App Router |
| `CLAUDE.md` | Modify | perintah web, Status |

---

### Task H3-1: Auth, session, app, health

**Files:**
- Modify: `api/empu/db.py`
- Create: `api/empu/auth.py`, `api/empu/app.py`, `api/empu/routes/__init__.py`, `api/empu/routes/health.py`
- Test: `api/tests/test_api_health.py`

**Interfaces:**
- Consumes: `Settings`, `make_engine`, `init_db`, `studio_key: SecretStr`
- Produces:
  - `get_engine(settings: Settings) -> Engine` (lru_cache by `db_url`)
  - `get_session()` generator FastAPI (`yield Session`)
  - `AuthContext(has_key: bool, is_sandbox: bool = False)`
  - `require_studio(request, settings=Depends(get_settings)) -> AuthContext` (401 kalau kunci salah/kosong)
  - `optional_studio(...) -> AuthContext` (has_key True/False, tidak 401)
  - `create_app() -> FastAPI`; ASGI path: `empu.app:create_app`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_api_health.py
from fastapi.testclient import TestClient

from empu.app import create_app
from empu.config import Settings
from empu.db import init_db, make_engine


def client(tmp_path) -> TestClient:
    s = Settings(_env_file=None, data_dir=tmp_path / "data", studio_key="studio-test",
                 meta_model_api_key="k")
    init_db(make_engine(s.db_url))
    app = create_app()
    app.dependency_overrides = {}
    # inject settings
    from empu.config import get_settings
    app.dependency_overrides[get_settings] = lambda: s
    return TestClient(app)


def test_health_no_key(tmp_path):
    r = client(tmp_path).get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_studio_route_401_without_key(tmp_path):
    r = client(tmp_path).get("/api/archives")
    assert r.status_code == 401


def test_studio_route_ok_with_key(tmp_path):
    r = client(tmp_path).get("/api/archives", headers={"X-Studio-Key": "studio-test"})
    assert r.status_code == 200
    assert r.json() == []
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_api_health.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.app'`.

- [ ] **Step 3: Tambahkan ke `api/empu/db.py`**

```python
from collections.abc import Iterator
from functools import lru_cache

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

from empu import models  # noqa: F401
from empu.config import Settings, get_settings


def make_engine(db_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)


def init_db(engine: Engine, *, reset: bool = False) -> None:
    if reset:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@lru_cache
def get_engine_cached(db_url: str) -> Engine:
    return make_engine(db_url)


def get_engine(settings: Settings | None = None) -> Engine:
    s = settings or get_settings()
    eng = get_engine_cached(s.db_url)
    init_db(eng)
    return eng


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
```

Kalau `make_engine`/`init_db` sudah ada di H2 dengan tanda tangan sama, **jangan tulis ulang** — hanya tambah `get_engine`, `get_engine_cached`, `get_session`. Jangan duplikat `from empu import models`.

- [ ] **Step 4: Tulis `api/empu/auth.py`**

```python
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from empu.config import Settings, get_settings

STUDIO_HEADER = "X-Studio-Key"


@dataclass(frozen=True)
class AuthContext:
    has_key: bool
    is_sandbox: bool = False


def _match(settings: Settings, x_studio_key: str | None) -> bool:
    secret = settings.studio_key
    if secret is None or not secret.get_secret_value():
        return False
    return bool(x_studio_key) and x_studio_key == secret.get_secret_value()


def optional_studio(
    x_studio_key: str | None = Header(default=None, alias=STUDIO_HEADER),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    return AuthContext(has_key=_match(settings, x_studio_key))


def require_studio(auth: AuthContext = Depends(optional_studio)) -> AuthContext:
    if not auth.has_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "studio key required")
    return auth
```

- [ ] **Step 5: Tulis `api/empu/routes/health.py` dan `api/empu/app.py`**

```python
# api/empu/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    return {"ok": True}
```

```python
# api/empu/routes/__init__.py
# empty
```

```python
# api/empu/app.py
from fastapi import Depends, FastAPI

from empu.auth import require_studio
from empu.routes import archives, entries, health, jobs, media, packs, recordings


def create_app() -> FastAPI:
    app = FastAPI(title="Empu", version="0.1.0")
    app.include_router(health.router)
    app.include_router(packs.router)
    app.include_router(archives.router, dependencies=[Depends(require_studio)])
    app.include_router(recordings.router, dependencies=[Depends(require_studio)])
    app.include_router(jobs.router, dependencies=[Depends(require_studio)])
    app.include_router(entries.router, dependencies=[Depends(require_studio)])
    app.include_router(media.router)
    return app
```

Router `packs`/`archives`/`recordings`/`jobs`/`entries`/`media` belum ada. Untuk tes health yang memanggil `/api/archives`, **tulis stub dulu** di task ini supaya tes 401/200 jalan, lalu isi di H3-3.

```python
# api/empu/routes/packs.py, archives.py, recordings.py, jobs.py, entries.py, media.py
from fastapi import APIRouter
router = APIRouter()
```

```python
# api/empu/routes/archives.py  (stub cukup untuk H3-1)
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/archives")
def list_archives() -> list:
    return []
```

- [ ] **Step 6: Jalankan tes**

Run: `cd api && uv run pytest tests/test_api_health.py -q`
Expected: `3 passed`. Tes `test_studio_route_ok_with_key` mengembalikan `[]` dari stub; H3-3 mengganti implementasinya.

- [ ] **Step 7: Commit**

```bash
git add api/empu/app.py api/empu/auth.py api/empu/db.py api/empu/routes api/tests/test_api_health.py
git commit -m "feat(api): FastAPI app, studio-key auth, health"
```

---

### Task H3-2: Skema API dan serializer

**Files:**
- Create: `api/empu/api_schemas.py`, `api/empu/serialize.py`
- Test: `api/tests/test_serialize.py`

**Interfaces:**
- Consumes: model DB H2-1
- Produces: model Pydantic di bawah; `archive_out`, `recording_out`, `job_out`, `entry_out`, `entry_list_item`, `occurrence_out`, `media_url(rel: str | None) -> str | None`

Semua path media di JSON adalah URL `/media/<rel>`. `source` kemunculan **selalu** string enum (`speech`/`on_screen_text`/`visual_only`).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_serialize.py
from empu.enums import Category, Confidence, Source, VisualMatch
from empu.models import Entry, Occurrence
from empu.serialize import entry_out, media_url, occurrence_out
from factories import make_archive, make_recording


def test_media_url():
    assert media_url(None) is None
    assert media_url("archives/1/display.mp4") == "/media/archives/1/display.mp4"


def test_occurrence_keeps_source(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool)
    session.add(e); session.commit(); session.refresh(e)
    o = Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.on_screen_text,
                   t_start=1, t_end=2, spoken="X", term_raw="x",
                   visual_match=VisualMatch.yes, confidence=Confidence.high,
                   clip_path="archives/1/recordings/1/occurrences/1/clip.mp4")
    session.add(o); session.commit(); session.refresh(o)
    d = occurrence_out(o)
    assert d.source == "on_screen_text"
    assert d.clip_url == "/media/archives/1/recordings/1/occurrences/1/clip.mp4"
    assert "source" in d.model_dump()


def test_entry_out_includes_best_and_occurrences(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="canting", category=Category.tool,
              gloss_id="pena malam", gloss_en="wax pen")
    session.add(e); session.commit(); session.refresh(e)
    o = Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech,
                   t_start=3, t_end=4)
    session.add(o); session.commit(); session.refresh(o)
    e.best_occurrence_id = o.id
    session.add(e); session.commit(); session.refresh(e)
    d = entry_out(e, [o], recording_title=rec.title)
    assert d.term == "canting" and d.occurrences[0].source == "speech"
    assert d.best_occurrence.source == "speech"
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_serialize.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.serialize'`.

- [ ] **Step 3: Tulis `api/empu/api_schemas.py`**

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from empu.enums import (
    AccessLevel, Category, Confidence, ConsentStatus, ContributorRole, EntryStatus,
    JobStatus, OccurrenceStatus, PipelineMode, ReviewAction, SamStatus, Source,
    SourceKind, TimeSource, VisualMatch,
)


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ContributorOut(APIModel):
    id: int
    name: str
    role: ContributorRole
    region: str
    sanggar: str


class ArchiveOut(APIModel):
    id: int
    slug: str
    title: str
    craft_pack_id: str
    description: str
    is_demo: bool
    recording_count: int = 0
    validated_count: int = 0


class ArchiveIn(APIModel):
    slug: str
    title: str
    craft_pack_id: str = "batik_tulis"
    description: str = ""
    owner_name: str = ""


class OccurrenceOut(APIModel):
    id: int
    entry_id: int
    recording_id: int
    recording_title: str = ""
    spoken: str
    term_raw: str
    source: Source
    t_start: float
    t_end: float
    time_source: TimeSource
    stage_id: str | None
    visible: str
    visible_object_en: str | None
    visual_match: VisualMatch
    evidence_quote: str
    confidence: Confidence
    status: OccurrenceStatus
    clip_url: str | None
    audio_url: str | None
    keyframe_url: str | None


class EntryListItem(APIModel):
    id: int
    term: str
    category: Category
    stage_id: str | None
    gloss_id: str
    gloss_en: str
    is_novel: bool
    status: EntryStatus
    access_level: AccessLevel
    source: Source | None = None
    confidence: Confidence | None = None
    n_occurrences: int = 0
    crop_url: str | None = None
    keyframe_url: str | None = None
    clip_url: str | None = None


class EntryOut(EntryListItem):
    variants: list[str] = []
    pack_term_id: str | None = None
    maestro_note: str = ""
    sam_status: SamStatus = SamStatus.skipped
    overlay_url: str | None = None
    best_occurrence: OccurrenceOut | None = None
    occurrences: list[OccurrenceOut] = []
    attribution: str | None = None
    contributor_name: str | None = None


class JobStageOut(APIModel):
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    seconds: float | None = None


class JobOut(APIModel):
    id: int
    recording_id: int
    status: JobStatus
    progress: float
    detail: str
    error: str | None
    mode: PipelineMode
    stages: list[JobStageOut] = []


class RecordingOut(APIModel):
    id: int
    archive_id: int
    title: str
    duration_s: float | None
    status: JobStatus
    consent_status: ConsentStatus
    consent_scope: AccessLevel
    source_kind: SourceKind
    source_url: str | None
    source_creator: str | None
    license: str | None
    attribution: str | None
    contributor: ContributorOut | None = None
    job: JobOut | None = None
    display_url: str | None = None


class ReviewIn(APIModel):
    action: ReviewAction
    actor: str = "documenter"
    occurrence_id: int | None = None
    merge_into_id: int | None = None
    changes: dict[str, Any] = Field(default_factory=dict)


class ReprocessIn(APIModel):
    mode: PipelineMode | None = None


class UploadAck(APIModel):
    recording_id: int
    job_id: int
```

- [ ] **Step 4: Tulis `api/empu/serialize.py`**

```python
from empu.api_schemas import (
    ArchiveOut, ContributorOut, EntryListItem, EntryOut, JobOut, JobStageOut,
    OccurrenceOut, RecordingOut,
)
from empu.enums import JobStatus
from empu.models import Archive, Contributor, Entry, Job, Occurrence, Recording
from empu.pipeline.run import JOB_STAGES


def media_url(rel: str | None) -> str | None:
    return None if not rel else "/media/" + rel.lstrip("/")


def contributor_out(c: Contributor | None) -> ContributorOut | None:
    return None if c is None else ContributorOut.model_validate(c)


def occurrence_out(o: Occurrence, *, recording_title: str = "") -> OccurrenceOut:
    return OccurrenceOut(
        id=o.id, entry_id=o.entry_id, recording_id=o.recording_id,
        recording_title=recording_title, spoken=o.spoken, term_raw=o.term_raw,
        source=o.source, t_start=o.t_start, t_end=o.t_end, time_source=o.time_source,
        stage_id=o.stage_id, visible=o.visible, visible_object_en=o.visible_object_en,
        visual_match=o.visual_match, evidence_quote=o.evidence_quote,
        confidence=o.confidence, status=o.status,
        clip_url=media_url(o.clip_path), audio_url=media_url(o.audio_path),
        keyframe_url=media_url(o.keyframe_path),
    )


def _best(e: Entry, occs: list[Occurrence]) -> Occurrence | None:
    return next((o for o in occs if o.id == e.best_occurrence_id), occs[0] if occs else None)


def entry_list_item(e: Entry, occs: list[Occurrence], *, recording_title: str = "") -> EntryListItem:
    best = _best(e, occs)
    return EntryListItem(
        id=e.id, term=e.term, category=e.category, stage_id=e.stage_id,
        gloss_id=e.gloss_id, gloss_en=e.gloss_en, is_novel=e.is_novel,
        status=e.status, access_level=e.access_level,
        source=best.source if best else None,
        confidence=best.confidence if best else None,
        n_occurrences=len(occs),
        crop_url=media_url(e.crop_path),
        keyframe_url=media_url(best.keyframe_path) if best else None,
        clip_url=media_url(best.clip_path) if best else None,
    )


def entry_out(e: Entry, occs: list[Occurrence], *, recording_title: str = "",
              contributor_name: str | None = None, attribution: str | None = None) -> EntryOut:
    item = entry_list_item(e, occs, recording_title=recording_title)
    best = _best(e, occs)
    return EntryOut(
        **item.model_dump(),
        variants=list(e.variants_json or []),
        pack_term_id=e.pack_term_id, maestro_note=e.maestro_note,
        sam_status=e.sam_status, overlay_url=media_url(e.overlay_path),
        best_occurrence=occurrence_out(best, recording_title=recording_title) if best else None,
        occurrences=[occurrence_out(o, recording_title=recording_title) for o in occs],
        attribution=attribution, contributor_name=contributor_name,
    )


def job_out(job: Job) -> JobOut:
    timings = job.timings_json or {}
    failed_stage = (job.error or "").split(":", 1)[0].strip() if job.status is JobStatus.failed else ""
    stages = []
    for st in JOB_STAGES:
        info = timings.get(st.value) or {}
        if job.status is JobStatus.ready:
            status = "done"
        elif st.value == failed_stage:
            status = "error"
        elif info.get("finished_at"):
            status = "done"
        elif job.status is st:
            status = "running"
        else:
            status = "pending"
        stages.append(JobStageOut(
            name=st.value, status=status,
            started_at=_ts(info.get("started_at")),
            finished_at=_ts(info.get("finished_at")),
            seconds=info.get("seconds"),
        ))
    return JobOut(id=job.id, recording_id=job.recording_id, status=job.status,
                  progress=job.progress, detail=job.detail, error=job.error,
                  mode=job.mode, stages=stages)


def _ts(v):
    from datetime import datetime
    if isinstance(v, datetime) or v is None:
        return v
    try:
        return datetime.fromisoformat(v)
    except (TypeError, ValueError):
        return None


def recording_out(rec: Recording, *, job: Job | None = None,
                  contributor: Contributor | None = None) -> RecordingOut:
    return RecordingOut(
        id=rec.id, archive_id=rec.archive_id, title=rec.title, duration_s=rec.duration_s,
        status=rec.status, consent_status=rec.consent_status, consent_scope=rec.consent_scope,
        source_kind=rec.source_kind, source_url=rec.source_url, source_creator=rec.source_creator,
        license=rec.license, attribution=rec.attribution,
        contributor=contributor_out(contributor),
        job=job_out(job) if job else None,
        display_url=media_url(rec.display_path),
    )


def archive_out(a: Archive, *, recording_count: int = 0, validated_count: int = 0) -> ArchiveOut:
    return ArchiveOut(id=a.id, slug=a.slug, title=a.title, craft_pack_id=a.craft_pack_id,
                      description=a.description, is_demo=a.is_demo,
                      recording_count=recording_count, validated_count=validated_count)
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest tests/test_serialize.py -q`
Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add api/empu/api_schemas.py api/empu/serialize.py api/tests/test_serialize.py
git commit -m "feat(api): response schemas; media URLs; source label preserved"
```

---

### Task H3-3: Route packs, archives, recordings, jobs

**Files:**
- Modify: `api/empu/routes/packs.py`, `archives.py`, `recordings.py`, `jobs.py`
- Test: `api/tests/test_api_recordings.py`

**Interfaces:**
- Consumes: `load_pack`, `list_packs`, `create_recording`, `RecordingMeta`, `enqueue_job`, `get_or_create_archive`, `get_or_create_contributor`, serialize helpers
- Produces: endpoint spec bagian 10 (kecuali public, export, sandbox, eval, review)

Batas unggah: `settings.max_upload_mb`, `settings.max_duration_s` (durasi dicek **setelah** file tersimpan, di worker saat probe; di route cek ukuran saja). `consent_confirmed` yang bukan `"true"` → 400.

- [ ] **Step 1: Tulis helper tes di `api/tests/conftest.py`**

```python
from fastapi.testclient import TestClient

from empu.app import create_app
from empu.config import get_settings
from empu.db import get_session


@pytest.fixture
def api(session, settings):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        c.headers["X-Studio-Key"] = settings.studio_key.get_secret_value()
        yield c
```

`get_session` adalah generator. Override yang benar:

```python
    def _session():
        yield session

    app.dependency_overrides[get_session] = _session
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_api_recordings.py
from empu.enums import JobStatus, SourceKind
from factories import make_archive, make_contributor, make_recording


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
    r = api.post(f"/api/archives/{a.id}/recordings",
                 data={"title": "Tes", "consent_confirmed": "false"},
                 files={"file": ("a.mp4", video.read_bytes(), "video/mp4")})
    assert r.status_code == 400
    assert "consent" in r.json()["detail"].lower()


def test_upload_ok(api, tmp_path, session):
    a = make_archive(session)
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x" * 100)
    r = api.post(
        f"/api/archives/{a.id}/recordings",
        data={"title": "Nyanting", "consent_confirmed": "true", "contributor_name": "Bu Ahli",
              "consent_scope": "public"},
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
    video = tmp_path / "a.mp4"; video.write_bytes(b"x")
    r = api.post(
        f"/api/archives/{a.id}/recordings",
        data={"title": "CC", "consent_confirmed": "true", "source_kind": "cc_by_video"},
        files={"file": ("a.mp4", video.read_bytes(), "video/mp4")},
    )
    assert r.status_code == 400


def test_job_shape(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    from empu.models import Job
    from empu.enums import JobStatus, PipelineMode
    job = Job(recording_id=rec.id, status=JobStatus.analyzing, progress=0.4, detail="segment 2/5",
              mode=PipelineMode.B)
    session.add(job); session.commit(); session.refresh(job)
    r = api.get(f"/api/jobs/{job.id}").json()
    assert r["status"] == "analyzing" and r["progress"] == 0.4
    names = [s["name"] for s in r["stages"]]
    assert names == ["normalizing", "chunking", "analyzing", "merging", "grounding", "cutting"]
    assert r["stages"][2]["status"] == "running"
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_api_recordings.py -q`
Expected: FAIL (404 atau `[]` dari stub).

- [ ] **Step 4: Tulis route**

```python
# api/empu/routes/packs.py
from fastapi import APIRouter, Depends, HTTPException
from empu.config import Settings, get_settings
from empu.packs import PackError, list_packs, load_pack

router = APIRouter()


@router.get("/api/packs")
def packs(settings: Settings = Depends(get_settings)) -> list[dict]:
    return [{"id": p.id, "version": p.version, "name": p.name.model_dump()}
            for p in list_packs(settings.packs_dir)]


@router.get("/api/packs/{pack_id}")
def pack_detail(pack_id: str, settings: Settings = Depends(get_settings)) -> dict:
    try:
        p = load_pack(pack_id, settings.packs_dir)
    except PackError as e:
        raise HTTPException(404, str(e)) from e
    return p.model_dump()
```

```python
# api/empu/routes/archives.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from empu.api_schemas import ArchiveIn, ArchiveOut
from empu.db import get_session
from empu.enums import EntryStatus
from empu.intake import IntakeError, get_or_create_archive
from empu.models import Archive, Entry, Recording
from empu.serialize import archive_out

router = APIRouter()


def _stats(session: Session, archive_id: int) -> tuple[int, int]:
    n_rec = session.exec(select(func.count()).select_from(Recording).where(
        Recording.archive_id == archive_id)).one()
    n_val = session.exec(select(func.count()).select_from(Entry).where(
        Entry.archive_id == archive_id,
        Entry.status.in_((EntryStatus.accepted, EntryStatus.edited)),
    )).one()
    return int(n_rec), int(n_val)


@router.get("/api/archives", response_model=list[ArchiveOut])
def list_archives(session: Session = Depends(get_session)) -> list[ArchiveOut]:
    rows = session.exec(select(Archive).order_by(Archive.is_demo.desc(), Archive.id)).all()
    return [archive_out(a, recording_count=_stats(session, a.id)[0],
                        validated_count=_stats(session, a.id)[1]) for a in rows]


@router.post("/api/archives", response_model=ArchiveOut, status_code=201)
def create_archive(body: ArchiveIn, session: Session = Depends(get_session)) -> ArchiveOut:
    try:
        a = get_or_create_archive(session, body.slug, title=body.title,
                                  pack_id=body.craft_pack_id)
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    if body.description:
        a.description = body.description
        a.owner_name = body.owner_name
        session.add(a); session.commit(); session.refresh(a)
    return archive_out(a)


@router.get("/api/archives/{archive_id}", response_model=ArchiveOut)
def get_archive(archive_id: int, session: Session = Depends(get_session)) -> ArchiveOut:
    a = session.get(Archive, archive_id)
    if a is None:
        raise HTTPException(404, "archive not found")
    n_rec, n_val = _stats(session, a.id)
    return archive_out(a, recording_count=n_rec, validated_count=n_val)
```

```python
# api/empu/routes/recordings.py
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from empu.api_schemas import ReprocessIn, RecordingOut, UploadAck
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.enums import AccessLevel, ContributorRole, SourceKind
from empu.intake import IntakeError, RecordingMeta, create_recording, enqueue_job
from empu.models import Archive, Contributor, Job, Recording
from empu.serialize import recording_out

router = APIRouter()


def _truthy(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "on"}


@router.post("/api/archives/{archive_id}/recordings", response_model=UploadAck, status_code=201)
async def upload_recording(
    archive_id: int,
    file: UploadFile = File(...),
    title: str = Form(...),
    consent_confirmed: str = Form(...),
    consent_scope: AccessLevel = Form(AccessLevel.public),
    consent_note: str = Form(""),
    consent_evidence: str = Form(""),
    contributor_id: int | None = Form(None),
    contributor_name: str | None = Form(None),
    recorded_at: str | None = Form(None),
    location: str = Form(""),
    language_hint: str = Form("id,jv"),
    source_kind: SourceKind = Form(SourceKind.own_recording),
    source_url: str | None = Form(None),
    source_creator: str | None = Form(None),
    license: str | None = Form(None),
    attribution: str | None = Form(None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadAck:
    archive = session.get(Archive, archive_id)
    if archive is None:
        raise HTTPException(404, "archive not found")
    if not _truthy(consent_confirmed):
        raise HTTPException(400, "consent_confirmed must be true")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    tmp = SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"file exceeds {settings.max_upload_mb} MB")
        tmp.write(chunk)
    tmp.seek(0)
    from pathlib import Path as P
    import tempfile, os, shutil
    suffix = P(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as disk:
        shutil.copyfileobj(tmp, disk)
        src = Path(disk.name)
    try:
        meta = RecordingMeta(
            title=title, contributor_id=contributor_id, contributor_name=contributor_name,
            recorded_at=recorded_at, location=location, language_hint=language_hint,
            consent_confirmed=True, consent_scope=consent_scope, consent_note=consent_note,
            consent_evidence=consent_evidence, source_kind=source_kind,
            source_url=source_url, source_creator=source_creator, license=license,
            attribution=attribution,
        )
        rec, job = create_recording(session, settings, archive, src, meta,
                                    filename=file.filename or f"upload{suffix}")
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        src.unlink(missing_ok=True)
    return UploadAck(recording_id=rec.id, job_id=job.id)


def _load_recording(session: Session, recording_id: int) -> tuple[Recording, Job | None, Contributor | None]:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "recording not found")
    job = session.exec(select(Job).where(Job.recording_id == rec.id).order_by(Job.id.desc())).first()
    contrib = session.get(Contributor, rec.contributor_id) if rec.contributor_id else None
    return rec, job, contrib


@router.get("/api/recordings/{recording_id}", response_model=RecordingOut)
def get_recording(recording_id: int, session: Session = Depends(get_session)) -> RecordingOut:
    rec, job, contrib = _load_recording(session, recording_id)
    return recording_out(rec, job=job, contributor=contrib)


@router.post("/api/recordings/{recording_id}/reprocess", response_model=UploadAck)
def reprocess(recording_id: int, body: ReprocessIn | None = None,
              session: Session = Depends(get_session),
              settings: Settings = Depends(get_settings)) -> UploadAck:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "recording not found")
    job = enqueue_job(session, settings, rec, mode=body.mode if body else None)
    return UploadAck(recording_id=rec.id, job_id=job.id)
```

`ContributorRole` diimpor tapi tidak dipakai — hapus dari impor.

Pindahkan `import tempfile, os, shutil` ke **atas file**. `os` tidak dipakai, hapus.

```python
# api/empu/routes/jobs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from empu.api_schemas import JobOut
from empu.db import get_session
from empu.models import Job
from empu.serialize import job_out

router = APIRouter()


@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job_out(job)
```

- [ ] **Step 5: Perbaiki `create_app`** — `packs.router` **tanpa** `require_studio` (spec: `/api/packs*` publik). Sudah benar di H3-1.

- [ ] **Step 6: Jalankan tes**

Run: `cd api && uv run pytest tests/test_api_recordings.py tests/test_api_health.py -q`
Expected: semua lulus.

- [ ] **Step 7: Commit**

```bash
git add api/empu/routes api/tests
git commit -m "feat(api): packs, archives, upload, jobs"
```

---

### Task H3-4: `apply_review` dan route entries

**Files:**
- Create: `api/empu/review.py`
- Modify: `api/empu/routes/entries.py`
- Test: `api/tests/test_review.py`, `api/tests/test_api_entries.py`

**Interfaces:**
- Consumes: `Entry`, `Occurrence`, `ReviewEvent`, `ReviewIn`
- Produces: `ReviewError(ValueError)`, `apply_review(session, entry_id: int, req: ReviewIn) -> Entry` (commit). Selalu menulis `review_event`. Field `changes` yang diizinkan: `term`, `gloss_id`, `gloss_en`, `category`, `stage_id`, `access_level`, `maestro_note`, `variants` (list → `variants_json`).

Aturan:
- `accept`: `entry.status=accepted`; kemunculan `proposed` → `accepted` (atau satu kemunculan kalau `occurrence_id` diisi).
- `edit`: terapkan `changes`, lalu `status=edited`.
- `reject`: `status=rejected`; kemunculan ikut `rejected` (atau satu).
- `merge`: `status=merged`, `merged_into_id` wajib; pindahkan kemunculan ke entri tujuan; `choose_best` ulang pada tujuan.
- `restore`: kembalikan `status` dan field dari `before_json` event terakhir yang mengubah entri ini. Tidak menghapus event.
- `add_manual`: 400 di H3 (stretch H nanti).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_review.py
import pytest

from empu.api_schemas import ReviewIn
from empu.enums import Category, EntryStatus, OccurrenceStatus, ReviewAction, Source
from empu.models import Entry, Occurrence, ReviewEvent
from empu.review import ReviewError, apply_review
from factories import make_archive, make_recording


def _entry(session, a, rec, term="canting"):
    e = Entry(archive_id=a.id, canon_key=f"term:{term}", term=term, category=Category.tool)
    session.add(e); session.commit(); session.refresh(e)
    o = Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    session.add(o); session.commit(); session.refresh(o)
    e.best_occurrence_id = o.id
    session.add(e); session.commit(); session.refresh(e)
    return e, o


def test_accept_writes_event(session):
    a = make_archive(session); rec = make_recording(session, a)
    e, o = _entry(session, a, rec)
    out = apply_review(session, e.id, ReviewIn(action=ReviewAction.accept, actor="syafiq"))
    assert out.status is EntryStatus.accepted
    session.refresh(o)
    assert o.status is OccurrenceStatus.accepted
    ev = session.get(ReviewEvent, session.query) if False else None
    events = list(session.exec(__import__("sqlmodel").select(ReviewEvent)).all())
    assert events[0].actor == "syafiq" and events[0].action is ReviewAction.accept


def test_edit_changes_gloss(session):
    a = make_archive(session); rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    out = apply_review(session, e.id, ReviewIn(action=ReviewAction.edit, actor="syafiq",
                                              changes={"gloss_en": "wax pen", "maestro_note": "ok"}))
    assert out.status is EntryStatus.edited and out.gloss_en == "wax pen"


def test_merge_moves_occurrences(session):
    a = make_archive(session); rec = make_recording(session, a)
    e1, o1 = _entry(session, a, rec, "canting")
    e2, o2 = _entry(session, a, rec, "tjanting")
    apply_review(session, e1.id, ReviewIn(action=ReviewAction.accept, actor="s"))
    out = apply_review(session, e2.id, ReviewIn(action=ReviewAction.merge, actor="s",
                                               merge_into_id=e1.id))
    assert out.status is EntryStatus.merged and out.merged_into_id == e1.id
    session.refresh(o2)
    assert o2.entry_id == e1.id


def test_reject_unknown_field(session):
    a = make_archive(session); rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    with pytest.raises(ReviewError, match="unknown"):
        apply_review(session, e.id, ReviewIn(action=ReviewAction.edit, actor="s",
                                            changes={"nope": 1}))


def test_restore(session):
    a = make_archive(session); rec = make_recording(session, a)
    e, _ = _entry(session, a, rec)
    apply_review(session, e.id, ReviewIn(action=ReviewAction.accept, actor="s"))
    out = apply_review(session, e.id, ReviewIn(action=ReviewAction.restore, actor="s"))
    assert out.status is EntryStatus.proposed
```

Ganti baris `ev = session.get(ReviewEvent, session.query) if False else None` — itu sampah. Tes `test_accept_writes_event` yang benar:

```python
from sqlmodel import select
from empu.models import ReviewEvent
# ...
    events = session.exec(select(ReviewEvent).where(ReviewEvent.entry_id == e.id)).all()
    assert len(events) == 1 and events[0].actor == "syafiq"
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_review.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.review'`.

- [ ] **Step 3: Tulis `api/empu/review.py`**

```python
from typing import Any

from sqlmodel import Session, select

from empu.api_schemas import ReviewIn
from empu.enums import EntryStatus, OccurrenceStatus, ReviewAction
from empu.models import Entry, Occurrence, ReviewEvent, utcnow
from empu.persist import choose_best

ALLOWED_CHANGES = {
    "term", "gloss_id", "gloss_en", "category", "stage_id", "access_level",
    "maestro_note", "variants",
}


class ReviewError(ValueError):
    pass


def _snapshot(entry: Entry) -> dict[str, Any]:
    return {
        "term": entry.term, "gloss_id": entry.gloss_id, "gloss_en": entry.gloss_en,
        "category": entry.category.value if hasattr(entry.category, "value") else entry.category,
        "stage_id": entry.stage_id, "access_level": getattr(entry.access_level, "value", entry.access_level),
        "maestro_note": entry.maestro_note, "status": getattr(entry.status, "value", entry.status),
        "variants": list(entry.variants_json or []),
        "merged_into_id": entry.merged_into_id,
    }


def _occs(session: Session, entry_id: int) -> list[Occurrence]:
    return list(session.exec(select(Occurrence).where(Occurrence.entry_id == entry_id)).all())


def apply_review(session: Session, entry_id: int, req: ReviewIn) -> Entry:
    entry = session.get(Entry, entry_id)
    if entry is None:
        raise ReviewError("entry not found")
    if req.action is ReviewAction.add_manual:
        raise ReviewError("add_manual is not available")
    before = _snapshot(entry)
    occs = _occs(session, entry.id)

    if req.action is ReviewAction.accept:
        entry.status = EntryStatus.accepted
        _set_occ_status(occs, OccurrenceStatus.accepted, req.occurrence_id)
    elif req.action is ReviewAction.edit:
        _apply_changes(entry, req.changes)
        entry.status = EntryStatus.edited
    elif req.action is ReviewAction.reject:
        entry.status = EntryStatus.rejected
        _set_occ_status(occs, OccurrenceStatus.rejected, req.occurrence_id)
    elif req.action is ReviewAction.merge:
        if not req.merge_into_id:
            raise ReviewError("merge_into_id required")
        target = session.get(Entry, req.merge_into_id)
        if target is None or target.id == entry.id:
            raise ReviewError("invalid merge target")
        for o in occs:
            o.entry_id = target.id
            session.add(o)
        entry.status = EntryStatus.merged
        entry.merged_into_id = target.id
        session.flush()
        target.best_occurrence_id = (choose_best(_occs(session, target.id)) or type("X", (), {"id": None})()).id
        target.updated_at = utcnow()
        session.add(target)
    elif req.action is ReviewAction.restore:
        last = session.exec(
            select(ReviewEvent).where(ReviewEvent.entry_id == entry.id).order_by(ReviewEvent.id.desc())
        ).first()
        if last is None:
            raise ReviewError("nothing to restore")
        _restore(entry, last.before_json)
    else:
        raise ReviewError(f"unhandled action {req.action}")

    entry.updated_at = utcnow()
    session.add(entry)
    session.add(ReviewEvent(
        entry_id=entry.id, occurrence_id=req.occurrence_id, action=req.action,
        before_json=before, after_json=_snapshot(entry), actor=req.actor,
    ))
    session.commit()
    session.refresh(entry)
    return entry


def _set_occ_status(occs: list[Occurrence], status: OccurrenceStatus, occurrence_id: int | None) -> None:
    for o in occs:
        if occurrence_id is None or o.id == occurrence_id:
            o.status = status


def _apply_changes(entry: Entry, changes: dict[str, Any]) -> None:
    unknown = set(changes) - ALLOWED_CHANGES
    if unknown:
        raise ReviewError(f"unknown fields: {sorted(unknown)}")
    if "variants" in changes:
        entry.variants_json = list(changes["variants"])
    for key, val in changes.items():
        if key == "variants":
            continue
        setattr(entry, key, val)


def _restore(entry: Entry, before: dict[str, Any]) -> None:
    entry.term = before.get("term", entry.term)
    entry.gloss_id = before.get("gloss_id", entry.gloss_id)
    entry.gloss_en = before.get("gloss_en", entry.gloss_en)
    entry.stage_id = before.get("stage_id")
    entry.maestro_note = before.get("maestro_note", "")
    entry.merged_into_id = before.get("merged_into_id")
    entry.variants_json = list(before.get("variants") or [])
    entry.status = EntryStatus(before["status"])
    if before.get("access_level"):
        from empu.enums import AccessLevel
        entry.access_level = AccessLevel(before["access_level"])
    if before.get("category"):
        from empu.enums import Category
        entry.category = Category(before["category"])
```

Pindahkan impor `AccessLevel` dan `Category` ke atas file. Ganti `choose_best(...) or type("X"...` dengan:

```python
        best = choose_best(_occs(session, target.id))
        target.best_occurrence_id = best.id if best else None
```

`session.query` tidak ada di SQLModel 0.0.x seperti itu; tes memakai `select`.

- [ ] **Step 4: Tulis `api/empu/routes/entries.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, or_, select

from empu.api_schemas import EntryListItem, EntryOut, ReviewIn
from empu.db import get_session
from empu.enums import EntryStatus, Source
from empu.models import Contributor, Entry, Occurrence, Recording
from empu.review import ReviewError, apply_review
from empu.serialize import entry_list_item, entry_out

router = APIRouter()


@router.get("/api/archives/{archive_id}/entries", response_model=list[EntryListItem])
def list_entries(
    archive_id: int,
    status: EntryStatus | None = None,
    source: Source | None = None,
    is_novel: bool | None = None,
    stage: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
) -> list[EntryListItem]:
    stmt = select(Entry).where(Entry.archive_id == archive_id, Entry.status != EntryStatus.merged)
    if status:
        stmt = stmt.where(Entry.status == status)
    if is_novel is not None:
        stmt = stmt.where(Entry.is_novel == is_novel)
    if stage:
        stmt = stmt.where(Entry.stage_id == stage)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(col(Entry.term).ilike(like), col(Entry.gloss_id).ilike(like),
                              col(Entry.gloss_en).ilike(like)))
    entries = session.exec(stmt.order_by(Entry.term)).all()
    out = []
    for e in entries:
        occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
        if source and not any(o.source is source for o in occs):
            continue
        out.append(entry_list_item(e, occs))
    return out


@router.get("/api/entries/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, session: Session = Depends(get_session)) -> EntryOut:
    e = session.get(Entry, entry_id)
    if e is None:
        raise HTTPException(404, "entry not found")
    occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
    rec = session.get(Recording, occs[0].recording_id) if occs else None
    contrib = session.get(Contributor, rec.contributor_id) if rec and rec.contributor_id else None
    return entry_out(
        e, occs,
        recording_title=rec.title if rec else "",
        contributor_name=contrib.name if contrib else None,
        attribution=rec.attribution if rec else None,
    )


@router.post("/api/entries/{entry_id}/review", response_model=EntryOut)
def review_entry(entry_id: int, body: ReviewIn, session: Session = Depends(get_session)) -> EntryOut:
    try:
        e = apply_review(session, entry_id, body)
    except ReviewError as err:
        raise HTTPException(400, str(err)) from err
    occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
    return entry_out(e, occs)
```

```python
# api/tests/test_api_entries.py
from empu.enums import Category, Source
from empu.models import Entry, Occurrence
from factories import make_archive, make_recording


def test_list_and_review(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="canting", category=Category.tool, is_novel=True)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    listed = api.get(f"/api/archives/{a.id}/entries", params={"is_novel": True}).json()
    assert listed[0]["term"] == "canting" and listed[0]["source"] == "speech"
    r = api.post(f"/api/entries/{e.id}/review", json={"action": "accept", "actor": "syafiq"})
    assert r.status_code == 200 and r.json()["status"] == "accepted"
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest tests/test_review.py tests/test_api_entries.py -q`
Expected: semua lulus.

- [ ] **Step 6: Commit**

```bash
git add api/empu/review.py api/empu/routes/entries.py api/tests/test_review.py api/tests/test_api_entries.py
git commit -m "feat(api): studio review accept/edit/reject/merge/restore"
```

---

### Task H3-5: `/media` dengan Range dan `can_access_media`

**Files:**
- Modify: `api/empu/media.py`, `api/empu/routes/media.py`
- Test: `api/tests/test_api_media.py`

**Interfaces:**
- Consumes: `abs_from_rel`, `optional_studio`
- Produces: `can_access_media(session, rel_path: str, *, has_key: bool) -> bool`; `GET /media/{path:path}` → `FileResponse`; `GET /api/media-auth?path=` → 200/403 (dipakai Caddy di H6)

H3: `has_key=True` mengizinkan semua file di dalam `data_dir` kecuali rekaman `consent_status=withdrawn`. Tanpa kunci: 401 (publik di H4).

- [ ] **Step 1: Tulis tes**

```python
# api/tests/test_api_media.py
from empu.enums import ConsentStatus
from empu.media import can_access_media
from factories import make_archive, make_recording


def test_withdrawn_blocked_even_with_key(session, settings, tmp_path):
    a = make_archive(session)
    rec = make_recording(session, a, consent_status=ConsentStatus.withdrawn,
                         display_path="archives/1/recordings/1/display.mp4")
    assert can_access_media(session, rec.display_path, has_key=True) is False


def test_granted_ok_with_key(session):
    a = make_archive(session)
    rec = make_recording(session, a, display_path="archives/1/recordings/1/display.mp4")
    assert can_access_media(session, rec.display_path, has_key=True) is True
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
```

Starlette `FileResponse` mendukung Range dan mengembalikan 206. Kalau tes dapat 200 full body, cek versi Starlette — jangan tulis Range parser sendiri.

- [ ] **Step 2: Implementasi**

Tambah ke `api/empu/media.py`:

```python
from sqlmodel import Session, select

from empu.enums import ConsentStatus
from empu.models import Recording


def can_access_media(session: Session, rel_path: str, *, has_key: bool) -> bool:
    try:
        abs_from_rel(session.get.bind() if False else __import__("empu.config").config.REPO_ROOT, rel_path)
    except Exception:
        pass
    rel = rel_path.lstrip("/")
    recs = session.exec(select(Recording)).all()
    owner = next((r for r in recs if r.display_path == rel or r.analysis_path == rel
                  or r.original_path == rel
                  or (r.display_path and rel.startswith(str(Path(r.display_path).parent)))), None)
    # cheaper: parse archives/<aid>/recordings/<rid>/
    from pathlib import PurePosixPath
    parts = PurePosixPath(rel).parts
    rec = None
    if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "recordings":
        try:
            rec = session.get(Recording, int(parts[3]))
        except ValueError:
            rec = None
    if rec is None:
        return False
    if rec.consent_status is ConsentStatus.withdrawn:
        return False
    return has_key
```

Itu jelek (impor di tengah, `session.get.bind` palsu). Tulis **hanya** ini:

```python
from pathlib import PurePosixPath

from sqlmodel import Session

from empu.enums import ConsentStatus
from empu.models import Recording


def can_access_media(session: Session, rel_path: str, *, has_key: bool) -> bool:
    rel = rel_path.lstrip("/")
    parts = PurePosixPath(rel).parts
    if len(parts) < 4 or parts[0] != "archives" or parts[2] != "recordings":
        if not has_key:
            return False
        # entry crops: archives/<aid>/entries/<eid>/...
        if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "entries":
            return has_key
        return False
    try:
        rec = session.get(Recording, int(parts[3]))
    except ValueError:
        return False
    if rec is None or rec.consent_status is ConsentStatus.withdrawn:
        return False
    return has_key
```

```python
# api/empu/routes/media.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlmodel import Session

from empu.auth import optional_studio
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.media import abs_from_rel, can_access_media

router = APIRouter()


def _check(session: Session, rel: str, has_key: bool, settings: Settings):
    try:
        path = abs_from_rel(settings.data_dir, rel)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not can_access_media(session, rel, has_key=has_key):
        raise HTTPException(401 if not has_key else 403, "forbidden")
    if not path.is_file():
        raise HTTPException(404, "not found")
    return path


@router.get("/media/{path:path}")
def media(path: str, request: Request, session: Session = Depends(get_session),
          auth=Depends(optional_studio), settings: Settings = Depends(get_settings)):
    file_path = _check(session, path, auth.has_key, settings)
    return FileResponse(file_path, filename=file_path.name)


@router.get("/api/media-auth")
def media_auth(path: str = Query(...), session: Session = Depends(get_session),
               auth=Depends(optional_studio), settings: Settings = Depends(get_settings)):
    _check(session, path.lstrip("/"), auth.has_key, settings)
    return {"ok": True}
```

`FileResponse` butuh `request` untuk Range; Starlette membacanya dari scope. Jangan tulis parser Range.

- [ ] **Step 3: Tes + commit**

Run: `cd api && uv run pytest tests/test_api_media.py tests/test_media.py -q`
Expected: lulus.

```bash
git add api/empu/media.py api/empu/routes/media.py api/tests/test_api_media.py
git commit -m "feat(api): media Range serving with consent-aware access"
```

---

### Task H3-6: Scaffold `web/`

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/next.config.ts`, `web/postcss.config.mjs`, `web/vitest.config.ts`, `web/app/globals.css`, `web/app/layout.tsx`, `web/app/studio/layout.tsx`, `web/app/page.tsx`, `web/lib/types.ts`, `web/lib/api.ts`, `web/lib/cn.ts`
- Test: `web/lib/api.test.ts`

**Interfaces:**
- Produces: `apiGet<T>(path, opts?)`, `apiSend<T>(path, init)`, `studioHeaders()`, `mediaSrc(url)`
- Rewrite: `/api/:path*` dan `/media/:path*` → `http://127.0.0.1:8000`

- [ ] **Step 1: Tulis `web/package.json`**

```json
{
  "name": "empu-web",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "test": "vitest run"
  },
  "dependencies": {
    "lucide-react": "^0.545.0",
    "next": "16.4.3",
    "react": "19.2.0",
    "react-dom": "19.2.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.1.16",
    "@types/node": "^24.9.1",
    "@types/react": "^19.2.2",
    "@types/react-dom": "^19.2.2",
    "eslint": "^9.38.0",
    "eslint-config-next": "16.4.3",
    "tailwindcss": "^4.1.16",
    "typescript": "^5.9.3",
    "vitest": "^3.2.4"
  }
}
```

Pin React ke versi yang di-peer oleh Next 16.4.3 saat `pnpm install` (kalau peer conflict, ikuti apa yang diminta Next, jangan naikkan Next).

- [ ] **Step 2: Config**

```ts
// web/next.config.ts
import type { NextConfig } from "next";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API}/api/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
};
export default nextConfig;
```

```js
// web/postcss.config.mjs
const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
```

```json
// web/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

```ts
// web/vitest.config.ts
import { defineConfig } from "vitest/config";
import path from "node:path";
export default defineConfig({
  test: { environment: "node" },
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
});
```

Token CSS **persis** blok di `desain.md` (Mori `:root` + Malam `[data-theme="malam"]`). Jangan pakai palet gelap tunggal `#111110` / `#c4a574`.

```tsx
// web/app/layout.tsx
import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const display = Fraunces({ subsets: ["latin"], variable: "--font-display" });
const ui = Inter({ subsets: ["latin"], variable: "--font-ui" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Empu",
  description: "Capture what masters know, before it's gone.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${ui.variable} ${mono.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
```

```tsx
// web/app/studio/layout.tsx
export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return <div data-theme="malam" className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">{children}</div>;
}
```

```tsx
// web/app/page.tsx — stub sampai H4-6; jangan redirect ke Studio (juri mendarat di /)
import Link from "next/link";
export default function Home() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <p className="font-display text-3xl">empu</p>
      <p className="mt-2 text-[var(--muted)]">Capture what masters know, before it's gone.</p>
      <p className="mt-6"><Link href="/studio">Documenter studio →</Link></p>
    </main>
  );
}
```

- [ ] **Step 3: `web/lib/types.ts` dan `web/lib/api.ts`**

Salin field dari `api_schemas.py` ke TypeScript:

```ts
// web/lib/types.ts
export type Source = "speech" | "on_screen_text" | "visual_only";
export type EntryStatus = "proposed" | "accepted" | "edited" | "rejected" | "merged";
export type JobStatus =
  | "queued" | "normalizing" | "chunking" | "analyzing" | "merging"
  | "grounding" | "cutting" | "ready" | "failed";

export type Occurrence = {
  id: number; entry_id: number; recording_id: number; recording_title: string;
  spoken: string; term_raw: string; source: Source;
  t_start: number; t_end: number; time_source: "asr" | "muse";
  stage_id: string | null; visible: string; visible_object_en: string | null;
  visual_match: "yes" | "no" | "not_visible"; evidence_quote: string;
  confidence: "low" | "medium" | "high"; status: string;
  clip_url: string | null; audio_url: string | null; keyframe_url: string | null;
};

export type Entry = {
  id: number; term: string; category: string; stage_id: string | null;
  gloss_id: string; gloss_en: string; is_novel: boolean; status: EntryStatus;
  access_level: string; source: Source | null; confidence: string | null;
  n_occurrences: number; crop_url: string | null; keyframe_url: string | null;
  clip_url: string | null; variants: string[]; pack_term_id: string | null;
  maestro_note: string; sam_status: string; overlay_url: string | null;
  best_occurrence: Occurrence | null; occurrences: Occurrence[];
  attribution: string | null; contributor_name: string | null;
  validation_label?: string;
};

export type Job = {
  id: number; recording_id: number; status: JobStatus; progress: number;
  detail: string; error: string | null; mode: "A" | "B";
  stages: { name: string; status: string; started_at: string | null; finished_at: string | null; seconds: number | null }[];
};

export type Recording = {
  id: number; archive_id: number; title: string; duration_s: number | null;
  status: JobStatus; display_url: string | null; job: Job | null;
  attribution: string | null; source_kind: string;
};

export type Archive = {
  id: number; slug: string; title: string; craft_pack_id: string;
  description: string; is_demo: boolean; recording_count: number; validated_count: number;
};
```

```ts
// web/lib/api.ts
const KEY_STORAGE = "empu.studioKey";

export function getStudioKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(KEY_STORAGE) ?? process.env.NEXT_PUBLIC_STUDIO_KEY ?? "";
}

export function setStudioKey(key: string) {
  sessionStorage.setItem(KEY_STORAGE, key);
}

export function studioHeaders(extra?: HeadersInit): Headers {
  const h = new Headers(extra);
  const key = getStudioKey();
  if (key) h.set("X-Studio-Key", key);
  return h;
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: studioHeaders(), cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function apiSend<T>(path: string, init: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, headers: studioHeaders(init.headers) });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export function mediaSrc(url: string | null | undefined): string | undefined {
  return url ?? undefined;
}
```

```ts
// web/lib/api.test.ts
import { describe, expect, it } from "vitest";
import { mediaSrc } from "./api";

describe("mediaSrc", () => {
  it("passes through relative media urls", () => {
    expect(mediaSrc("/media/a.mp4")).toBe("/media/a.mp4");
    expect(mediaSrc(null)).toBeUndefined();
  });
});
```

- [ ] **Step 4: Instal dan tes**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/web
pnpm install
pnpm test
```
Expected: vitest 1 passed.

- [ ] **Step 5: Commit** (`web/pnpm-lock.yaml` ikut)

```bash
git add web
git commit -m "chore(web): Next.js 16 scaffold with API rewrite"
```

---

### Task H3-6b: Komponen bersama (kontrak desain)

**Files:**
- Create: `web/lib/copy.ts`, `web/lib/source.ts`, `web/lib/time.ts`, `web/lib/source.test.ts`
- Create: `web/components/{SourceBadge,TimeSourceTag,StatusChip,ConfidenceTag,NovelBadge,ValidationLabel,AttributionLine,EvidenceClip,CropView,PronounceButton}.tsx`
- Test: `web/lib/source.test.ts`

Baca `desain.md` bagian Komponen + Copy. Jangan tulis komponen yang tidak ada di tabel itu.

- [ ] **Step 1: Tes label sumber (exhaustive)**

```ts
// web/lib/source.ts
import type { Source } from "./types";

export function sourceLabel(source: Source): string {
  switch (source) {
    case "speech": return "Spoken";
    case "on_screen_text": return "On-screen text";
    case "visual_only": return "Visual only";
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function sourceTooltip(source: Source): string {
  switch (source) {
    case "speech": return "Heard in the recording's audio.";
    case "on_screen_text": return "Read from text shown in the video, not spoken.";
    case "visual_only": return "Seen in the video; not spoken or written.";
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}
```

```ts
// web/lib/source.test.ts
import { describe, expect, it } from "vitest";
import { sourceLabel } from "./source";

describe("sourceLabel", () => {
  it("uses brief microcopy, not lowercase shorthand", () => {
    expect(sourceLabel("speech")).toBe("Spoken");
    expect(sourceLabel("on_screen_text")).toBe("On-screen text");
    expect(sourceLabel("visual_only")).toBe("Visual only");
  });
});
```

`COPY` di `web/lib/copy.ts`: salin tabel brief bagian 8 (tagline, badge, time source, validasi, crop, izin, tahap progres, empty state). `formatTime` di `web/lib/time.ts` → `"0:37"` / `"2:05–2:09"`.

- [ ] **Step 2:** `SourceBadge` ikon Lucide `AudioLines` / teks `T` / `Eye` + `sourceLabel` + warna `var(--src-speech|onscreen|visual)`. `CropView`: bingkai tetap 4:5, `object-contain`, sakelar "Show in frame", fallback "No crop found · full frame shown". `EvidenceClip` 16:9 native video. Sisanya mengikuti tabel `desain.md`.

- [ ] **Step 3:** `pnpm test` lulus. Commit `feat(web): source badges, crop view, design copy`.

---

### Task H3-7: S2 Unggah

**Files:**
- Create: `web/app/studio/page.tsx`, `web/app/studio/upload/page.tsx`, `web/components/StudioKeyGate.tsx`, `web/components/UploadForm.tsx`
- Tidak ada tes browser; cek manual + `pnpm lint`

**Interfaces:**
- Form multipart ke `POST /api/archives/{id}/recordings`
- Checkbox izin **wajib** (disabled submit sampai dicentang), copy persis brief: "I confirm the contributor granted permission…"
- Radio cakupan dengan satu kalimat: Public / Community / Private (`desain.md` / brief bagian 8). Jangan dropdown tanpa penjelasan.
- `source_kind` segmented control "Own recording" / "CC BY video"; kalau CC BY, field URL/kreator/lisensi/atribusi wajib.
- Blok izin di atas tombol, menonjol (`border` + `--wax` atau `--surface`), bukan catatan kaki.

- [ ] **Step 1: Tulis komponen**

```tsx
// web/components/StudioKeyGate.tsx
"use client";
import { useEffect, useState } from "react";
import { getStudioKey, setStudioKey } from "@/lib/api";

export function StudioKeyGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [key, setKey] = useState("");
  useEffect(() => {
    const existing = getStudioKey();
    if (existing) setReady(true);
  }, []);
  if (ready) return children;
  return (
    <form className="mx-auto mt-24 max-w-sm space-y-3 p-6"
          onSubmit={(e) => { e.preventDefault(); setStudioKey(key); setReady(true); }}>
      <h1 className="text-xl font-medium">Studio key</h1>
      <p className="text-sm text-[var(--muted)]">Paste STUDIO_KEY from the server environment.</p>
      <input className="w-full border border-[var(--line)] bg-transparent px-3 py-2"
             type="password" value={key} onChange={(e) => setKey(e.target.value)} />
      <button className="bg-[var(--accent)] px-4 py-2 text-black" type="submit">Enter</button>
    </form>
  );
}
```

```tsx
// web/components/UploadForm.tsx
"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import type { Archive } from "@/lib/types";

export function UploadForm() {
  const router = useRouter();
  const [archives, setArchives] = useState<Archive[]>([]);
  const [consent, setConsent] = useState(false);
  const [kind, setKind] = useState("own_recording");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Archive[]>("/api/archives").then(setArchives).catch((e) => setError(String(e)));
  }, []);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!consent) return;
    const fd = new FormData(e.currentTarget);
    fd.set("consent_confirmed", "true");
    const archiveId = fd.get("archive_id");
    try {
      const res = await apiSend<{ recording_id: number; job_id: number }>(
        `/api/archives/${archiveId}/recordings`, { method: "POST", body: fd },
      );
      router.push(`/studio/jobs/${res.job_id}`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-2xl">Upload recording</h1>
      {error && <p className="text-[var(--danger)]">{error}</p>}
      <label className="block text-sm">Archive
        <select name="archive_id" className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" required>
          {archives.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
        </select>
      </label>
      <label className="block text-sm">Video
        <input name="file" type="file" accept="video/*" required className="mt-1 block" />
      </label>
      <label className="block text-sm">Title
        <input name="title" required className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" />
      </label>
      <label className="block text-sm">Contributor name
        <input name="contributor_name" className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" />
      </label>
      <label className="block text-sm">Location
        <input name="location" className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" />
      </label>
      <fieldset className="space-y-2 border border-[var(--line)] bg-[var(--surface)] p-3">
        <legend className="text-sm">Consent scope</legend>
        <label className="block text-sm"><input type="radio" name="consent_scope" value="public" defaultChecked /> Public: accepted entries can appear in the public dictionary.</label>
        <label className="block text-sm"><input type="radio" name="consent_scope" value="community" /> Community: kept out of the public dictionary; visible in the studio.</label>
        <label className="block text-sm"><input type="radio" name="consent_scope" value="private" /> Private: restricted knowledge; never public.</label>
      </fieldset>
      <label className="block text-sm">Consent note
        <input name="consent_note" className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" />
      </label>
      <label className="block text-sm">Source
        <select name="source_kind" value={kind} onChange={(e) => setKind(e.target.value)}
                className="mt-1 w-full border border-[var(--line)] bg-transparent p-2">
          <option value="own_recording">own recording</option>
          <option value="cc_by_video">CC BY video</option>
        </select>
      </label>
      {kind === "cc_by_video" && (
        <div className="space-y-2 border border-[var(--line)] p-3">
          <input name="source_url" required placeholder="Source URL" className="w-full border border-[var(--line)] bg-transparent p-2" />
          <input name="source_creator" required placeholder="Creator" className="w-full border border-[var(--line)] bg-transparent p-2" />
          <input name="license" required defaultValue="CC BY 3.0" className="w-full border border-[var(--line)] bg-transparent p-2" />
          <textarea name="attribution" required placeholder="Attribution text" className="w-full border border-[var(--line)] bg-transparent p-2" />
        </div>
      )}
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        I confirm the contributor granted permission to process this recording, and I recorded that consent.
      </label>
      <button disabled={!consent} className="bg-[var(--accent)] px-4 py-2 text-black disabled:opacity-40">
        Upload and process
      </button>
    </form>
  );
}
```

```tsx
// web/app/studio/page.tsx
import Link from "next/link";
import { StudioKeyGate } from "@/components/StudioKeyGate";

export default function StudioHome() {
  return (
    <StudioKeyGate>
      <main className="p-8">
        <p className="text-sm tracking-wide text-[var(--muted)]">EMPU · BATIK TULIS</p>
        <h1 className="mt-2 text-3xl">Studio</h1>
        <div className="mt-8 flex gap-4">
          <Link className="border border-[var(--line)] px-4 py-3" href="/studio/upload">Upload recording</Link>
        </div>
      </main>
    </StudioKeyGate>
  );
}
```

```tsx
// web/app/studio/upload/page.tsx
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { UploadForm } from "@/components/UploadForm";

export default function UploadPage() {
  return <StudioKeyGate><UploadForm /></StudioKeyGate>;
}
```

Kalau daftar arsip kosong, form unggah tidak bisa. Tambah tombol "Create archive" yang `POST /api/archives` dengan slug `demo`, title `Living Archive · Batik Tulis` kalau `archives.length === 0`.

- [ ] **Step 2: `pnpm lint` lalu commit**

```bash
cd web && pnpm lint
git add web
git commit -m "feat(web): upload form with mandatory consent"
```

---

### Task H3-8: S3 Progres

**Files:**
- Create: `web/app/studio/jobs/[id]/page.tsx`, `web/components/JobProgress.tsx`

Polling 2 detik ke `GET /api/jobs/{id}`. Saat `status === ready`, tautan ke `/studio/{recording_id}` (Studio rekaman). Saat `failed`, tombol Retry → `POST /api/recordings/{id}/reprocess`.

```tsx
// web/components/JobProgress.tsx
"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import type { Job } from "@/lib/types";

export function JobProgress({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    let stop = false;
    async function tick() {
      const j = await apiGet<Job>(`/api/jobs/${jobId}`);
      if (!stop) setJob(j);
      if (j.status !== "ready" && j.status !== "failed") setTimeout(tick, 2000);
    }
    tick();
    return () => { stop = true; };
  }, [jobId]);
  if (!job) return <p className="p-8">Loading…</p>;
  // STAGE_LABEL from COPY in web/lib/copy.ts (desain.md). Do not show raw enum names as the only label.
  return (
    <main className="mx-auto max-w-lg p-8">
      <h1 className="text-2xl">Processing</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        {job.mode === "B" ? "Mode B · retimed with speech recognition" : "Mode A"} · {job.detail || job.status}
      </p>
      <ol className="mt-6 space-y-2">
        {job.stages.map((s) => (
          <li key={s.name} className="flex justify-between border-b border-[var(--line)] py-2">
            <span>{STAGE_LABEL[s.name] ?? s.name}</span>
            <span className="text-[var(--muted)]">{s.status}{s.seconds != null ? ` · ${s.seconds.toFixed(1)}s` : ""}{s.status === "running" && job.detail ? ` · ${job.detail}` : ""}</span>
          </li>
        ))}
      </ol>
      <div className="mt-4 h-1 bg-[var(--line)]">
        <div className="h-1 bg-[var(--accent)]" style={{ width: `${Math.round(job.progress * 100)}%` }} />
      </div>
      {job.status === "ready" && (
        <Link className="mt-6 inline-block bg-[var(--accent)] px-4 py-2 text-[var(--bg)]"
              href={`/studio/recordings/${job.recording_id}`}>Open in Studio</Link>
      )}
      {job.status === "failed" && (
        <div className="mt-6 space-y-2">
          <p className="text-[var(--danger)]">{job.error}</p>
          <button className="border border-[var(--line)] px-4 py-2"
            onClick={async () => {
              const res = await apiSend<{ job_id: number }>(
                `/api/recordings/${job.recording_id}/reprocess`, { method: "POST", body: "{}" , headers: { "Content-Type": "application/json" } },
              );
              location.href = `/studio/jobs/${res.job_id}`;
            }}>Retry</button>
        </div>
      )}
    </main>
  );
}
```

Perbaiki Retry: `body: JSON.stringify({})` dan `headers: { "Content-Type": "application/json" }` lewat `apiSend` — `studioHeaders` sudah merge.

```tsx
// web/app/studio/jobs/[id]/page.tsx
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { JobProgress } from "@/components/JobProgress";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StudioKeyGate><JobProgress jobId={id} /></StudioKeyGate>;
}
```

Commit: `feat(web): job progress polling`.

---

### Task H3-9: S4 Studio validasi

**Files:**
- Create: `web/app/studio/recordings/[id]/page.tsx`, `web/components/Studio.tsx`, `web/components/EntryCard.tsx`, `web/components/SourceBadge.tsx`
- Modify: `api/empu/routes/recordings.py` — `GET /api/recordings/{id}/entries` (daftar entri yang punya kemunculan di rekaman ini, plus `display_url`)

Tanpa endpoint list-by-recording, Studio harus fetch semua entri arsip lalu filter. **Tambah endpoint** (superset spec, tidak menghapus yang ada):

```python
@router.get("/api/recordings/{recording_id}/entries", response_model=list[EntryOut])
def recording_entries(recording_id: int, session: Session = Depends(get_session)) -> list[EntryOut]:
    rec, _, contrib = _load_recording(session, recording_id)
    occs = session.exec(select(Occurrence).where(Occurrence.recording_id == recording_id)).all()
    by_entry: dict[int, list] = {}
    for o in occs:
        by_entry.setdefault(o.entry_id, []).append(o)
    out = []
    for eid, group in by_entry.items():
        e = session.get(Entry, eid)
        if e is None or e.status.value == "merged":
            continue
        out.append(entry_out(e, group, recording_title=rec.title,
                             contributor_name=contrib.name if contrib else None,
                             attribution=rec.attribution))
    out.sort(key=lambda x: x.term)
    return out
```

Tes: tambah di `test_api_entries.py` bahwa entri rekaman lain tidak ikut.

UI Studio (satu file client):
- Kiri: `<video src={recording.display_url}>` + marker timeline (div absolut, klik seek ke `t_start`)
- Kanan: filter status/source/novel; kartu: klip, crop/keyframe, term, spoken, quote, **SourceBadge**, confidence, gloss ID/EN, stage
- Tombol Accept / Edit / Reject / Merge. Keyboard: `A` `E` `R` `J` `K`
- Edit: dialog field gloss_id, gloss_en, term, maestro_note
- Merge: input id entri tujuan

`SourceBadge` sudah ada dari H3-6b. **Wajib** di kartu, timeline, dan mode edit. Jangan pernah drop field `source`. Jangan tulis ulang label lowercase.

Studio.tsx inti (implementasi penuh di file; jangan pecah jadi "dll."):

```tsx
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import type { Entry, Recording, Source } from "@/lib/types";
import { SourceBadge } from "./SourceBadge";

export function Studio({ recordingId }: { recordingId: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [rec, setRec] = useState<Recording | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [idx, setIdx] = useState(0);
  const [status, setStatus] = useState<string>("proposed");
  const [source, setSource] = useState<Source | "all">("all");
  const [novel, setNovel] = useState(false);

  async function reload() {
    const r = await apiGet<Recording>(`/api/recordings/${recordingId}`);
    const e = await apiGet<Entry[]>(`/api/recordings/${recordingId}/entries`);
    setRec(r); setEntries(e);
  }
  useEffect(() => { reload(); }, [recordingId]);

  const visible = useMemo(() => entries.filter((e) => {
    if (status && e.status !== status) return false;
    if (source !== "all" && e.source !== source) return false;
    if (novel && !e.is_novel) return false;
    return true;
  }), [entries, status, source, novel]);
  const current = visible[idx];

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (ev.target instanceof HTMLInputElement || ev.target instanceof HTMLTextAreaElement) return;
      if (ev.key === "j" || ev.key === "J") setIdx((i) => Math.min(visible.length - 1, i + 1));
      if (ev.key === "k" || ev.key === "K") setIdx((i) => Math.max(0, i - 1));
      if (ev.key === "a" || ev.key === "A") void act("accept");
      if (ev.key === "r" || ev.key === "R") void act("reject");
      if (ev.key === "e" || ev.key === "E") void edit();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  async function act(action: string, extra?: Record<string, unknown>) {
    if (!current) return;
    const updated = await apiSend<Entry>(`/api/entries/${current.id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, actor: "documenter", ...extra }),
    });
    setEntries((all) => all.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)));
  }
  const [editing, setEditing] = useState(false);
  async function edit() {
    setEditing(true);
  }
  // Inline form in the card (term, gloss_en, gloss_id, maestro_note) + Save edit / Cancel.
  // window.prompt is forbidden (desain.md). Merge: popover search by headword, not prompt("Merge into entry id").

  if (!rec) return <p className="p-8">Loading…</p>;
  return (
    <div className="grid min-h-screen grid-cols-[minmax(0,1.2fr)_minmax(24rem,1fr)]">
      <section className="border-r border-[var(--line)] p-4">
        {rec.display_url && (
          <video ref={videoRef} src={rec.display_url} controls className="w-full bg-black" />
        )}
        <div className="relative mt-2 h-8 bg-[var(--line)]">
          {visible.map((e, i) => {
            const t = e.best_occurrence?.t_start ?? 0;
            const dur = rec.duration_s || 1;
            return (
              <button key={e.id} title={e.term}
                className={`absolute top-0 h-8 w-1 ${i === idx ? "bg-[var(--accent)]" : "bg-white/50"}`}
                style={{ left: `${(t / dur) * 100}%` }}
                onClick={() => { setIdx(i); videoRef.current && (videoRef.current.currentTime = t); }} />
            );
          })}
        </div>
      </section>
      <section className="flex flex-col">
        <header className="flex flex-wrap gap-2 border-b border-[var(--line)] p-3 text-sm">
          <select value={status} onChange={(e) => { setStatus(e.target.value); setIdx(0); }}
                  className="bg-transparent border border-[var(--line)] p-1">
            {["proposed","accepted","edited","rejected"].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={source} onChange={(e) => setSource(e.target.value as Source | "all")}
                  className="bg-transparent border border-[var(--line)] p-1">
            <option value="all">all sources</option>
            <option value="speech">spoken</option>
            <option value="on_screen_text">on-screen text</option>
            <option value="visual_only">visual only</option>
          </select>
          <label className="flex items-center gap-1"><input type="checkbox" checked={novel} onChange={(e) => setNovel(e.target.checked)} /> novel</label>
          <span className="ml-auto text-[var(--muted)]">{visible.length} entries</span>
        </header>
        {current ? (
          <article className="space-y-3 overflow-y-auto p-4">
            {current.clip_url && <video src={current.clip_url} controls className="w-full" />}
            <div className="flex gap-3">
              {(current.crop_url || current.keyframe_url) && (
                // eslint-disable-next-line @next/next/no-img-element
                <img alt="" src={current.crop_url ?? current.keyframe_url ?? ""} className="h-32 object-contain" />
              )}
              <div>
                <h2 className="text-2xl">{current.term}</h2>
                <p className="text-[var(--muted)]">{current.best_occurrence?.spoken}</p>
                <div className="mt-2 flex gap-2">
                  <SourceBadge source={current.source} />
                  {current.is_novel && <span className="text-xs">new term</span>}
                  <span className="text-xs">{current.confidence}</span>
                </div>
              </div>
            </div>
            <blockquote className="border-l-2 border-[var(--accent)] pl-3 text-sm">
              {current.best_occurrence?.evidence_quote}
            </blockquote>
            <p>{current.gloss_id}</p>
            <p className="text-[var(--muted)]">{current.gloss_en}</p>
            {current.attribution && <p className="text-xs text-[var(--muted)]">{current.attribution}</p>}
            <div className="flex gap-2 pt-4">
              <button className="bg-[var(--ok)] px-3 py-2 text-black" onClick={() => act("accept")}>Accept (A)</button>
              <button className="border border-[var(--line)] px-3 py-2" onClick={() => edit()}>Edit (E)</button>
              <button className="bg-[var(--danger)] px-3 py-2" onClick={() => act("reject")}>Reject (R)</button>
              <button className="border border-[var(--line)] px-3 py-2" onClick={() => {/* merge popover */}}>Merge…</button>
            </div>
          </article>
        ) : <p className="p-4 text-[var(--muted)]">No entries in this filter.</p>}
      </section>
    </div>
  );
}
```

Edit **inline** di kartu (bukan `window.prompt`, bukan `confirm`). Merge: popover cari kata kepala. Di bawah 1280 px tampilkan "Studio works best on a desktop screen" — jangan layout HP. Penanda timeline: lingkaran Spoken, persegi On-screen text, segitiga Visual only; aktif `--wax`. Tombol aksi memakai copy `Accept (A)` · `Edit (E)` · `Reject (R)` · `Merge…`. Filter kosong: "Nothing left in this filter."

Bungkus halaman dengan `StudioKeyGate`. Commit: `feat(web): studio validation with source badges and keyboard`.

---

### Task H3-10: Video CC BY demo lewat UI, Status

**Files:**
- Modify: `CLAUDE.md`, `docs/00-konteks-hackathon.md` (cek ulang persyaratan submission kalau H0-2 Step 4 masih "belum dicek")

- [ ] **Step 1: Pastikan arsip demo ada**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
uv run empu db init
uv run empu ingest "../data-uji/cc-by/Macam Canting dalam Batik Tulis [FodqwNTWOrQ].mp4" \
  --archive hidup-batik --title "Macam Canting dalam Batik Tulis" \
  --source-kind cc_by_video --license-file ../docs/eval/lisensi/FodqwNTWOrQ.json \
  --run
```

Kalau CLI ingest H2-10 memakai flag berbeda, **ikuti tanda tangan H2-10**, jangan mengarang flag. Intinya: rekaman CC BY masuk DB, job `ready`.

- [ ] **Step 2: Jalankan api + worker + web**

```bash
# terminal A
cd api && uv run uvicorn empu.app:create_app --factory --reload --port 8000
# terminal B
cd api && uv run python -m empu.worker
# terminal C
cd web && pnpm dev
```

Buka `http://localhost:3000/studio`, masukkan studio key, buka rekaman, terima 5 entri, ubah 1 glosa, tolak 1. Pastikan badge sumber terlihat. Cek Range: seek video display tidak merestart dari 0.

- [ ] **Step 3: CLAUDE.md Status**

```markdown
- H3 (Sab 31 Okt): API + Studio jalan; video CC BY divalidasi lewat UI. Berikutnya: H4 kamus + ekspor.
```

Perintah web:

```bash
cd web && pnpm install && pnpm dev    # http://localhost:3000
pnpm test && pnpm lint
```

- [ ] **Step 4: Commit docs saja**

```bash
git add CLAUDE.md docs/00-konteks-hackathon.md
git commit -m "docs: H3 studio validated on CC BY recording"
```

---

## Selesai kalau
- [ ] Bisa unggah (atau buka rekaman yang sudah di-ingest) dan memvalidasi 1 rekaman lewat UI.
- [ ] `SourceBadge` ikon+teks di kartu Studio (termasuk saat edit). `window.prompt` tidak dipakai.
- [ ] Tema Studio = Malam (`data-theme="malam"`). Token `desain.md`, bukan palet `#c4a574`.
- [ ] `cd api && uv run pytest -q` dan `cd web && pnpm test && pnpm lint` lulus.
- [ ] Seek video tidak rusak (Range 206).

## Kalau pukul 17:00 belum ada Studio yang bisa dipakai
Potong Merge dari UI (tetap ada di API). Jangan mulai kamus (H4) sebelum Accept/Reject/Edit jalan — itu satu-satunya bukti "manusia memutuskan" untuk juri.
