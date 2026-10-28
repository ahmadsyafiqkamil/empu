# H2 (Jum 30 Okt): Penggabungan, Bukti, SAM, DB, Worker

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Satu video uji berjalan end-to-end lewat CLI **dan** worker: hasil Muse per segmen digabung menjadi entri arsip (kanonisasi ke pack, dedup overlap, koreksi waktu Mode B), peta tahapan, klip/audio/keyframe per kemunculan, potongan SAM per entri, semuanya tersimpan di SQLite. Ini **Gate 1**.

**Architecture:** Modul murni tanpa I/O untuk logika (`process_map`, `merge`, `transcribe.realign`, `evidence.clip_window`) supaya mudah dites. Modul I/O tipis (`evidence`, `ground`, `persist`). Orkestrator `pipeline/run.py` menjalankan tahap berurutan dan menulis progres ke baris `job`. Worker `python -m empu.worker` mengambil job `queued` dari tabel. Logika intake (`intake.py`) dipakai bersama oleh CLI sekarang dan API upload di H3.

**Tech Stack:** SQLModel + SQLite (WAL), rapidfuzz, faster-whisper (lokal, CPU int8), Pillow, ffmpeg, Typer, pytest.

## Global Constraints

Semua butir di `00-ikhtisar.md` bagian "Global Constraints" berlaku. Yang paling relevan untuk fase ini:
- Tidak ada istilah batik di `api/empu/**` (tes `test_no_craft_terms_in_package` dari H1 tetap harus lulus). Semua istilah, varian, dan `sam_prompt` dari pack.
- Label sumber (`speech`/`on_screen_text`/`visual_only`) disalin apa adanya dari Muse ke `occurrence.source`. Tidak ada kode yang mengubah sumber.
- Gambar hanya dari frame asli: keyframe dari `display.mp4`, crop dan overlay dibuat dari keyframe itu. Tidak ada pembuatan gambar.
- Dedup overlap |Δt| ≤ 4 s. Fuzzy kanonisasi rapidfuzz `ratio` ≥ 90. Klip `t_start − 1,0` s.d. `t_end + 1,5`, min 3 s, maks 8 s. Padding crop 15%.
- Mode B (D10): `evidence_quote` istilah `speech` dicocokkan ke transkrip faster-whisper per kata, `partial_ratio` ≥ 80, jendela ±30 s. Ejaan istilah tetap dari Muse. `occurrence.time_source` = `asr` atau `muse`.
- Semua path media di DB relatif terhadap `data_dir`.
- Semua panggilan Meta lewat `meta_client.py`. Respons SAM juga di-cache (`data/cache/sam/`), supaya proses ulang tidak memanggil API untuk keyframe dan prompt yang sama.
- Tes tidak memanggil API sungguhan dan tidak mengunduh model whisper.

## Prasyarat
- H1 selesai: `cd api && uv run pytest -q` lulus, `empu analyze` sudah jalan sungguhan sekali.
- `data/cache/muse/` berisi hasil run H1 (*Macam Canting*), supaya Gate 1 untuk video itu tidak berbayar lagi.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/enums.py` | Modify | Tambah `SourceKind`, `TimeSource` |
| `api/empu/models.py` | Create | Tabel SQLModel (spec 9 + D5, D9, D10) |
| `api/empu/db.py` | Create | `make_engine` (PRAGMA WAL, FK, busy_timeout), `init_db` |
| `api/empu/media.py` | Create | Tata letak `data/`, `rel_to_data`, `abs_from_rel` |
| `api/empu/pipeline/process_map.py` | Create | `StageMatcher`, `StepDraft`, `build_process_map`, `stage_at` |
| `api/empu/pipeline/merge.py` | Create | `Canonicalizer`, `AbsOccurrence`, dedup, `EntryDraft`, `merge_analyses`, `occurrence_rank` |
| `api/empu/pipeline/transcribe.py` | Create | `Word`, `whisper_transcriber`, `transcribe_cached`, `realign` |
| `api/empu/pipeline/evidence.py` | Create | `clip_window`, `make_evidence`, `extract_keyframe` |
| `api/empu/meta_client.py` | Modify | `parse_sam_boxes`, `segment_image_raw`, `segment_image` |
| `api/empu/pipeline/ground.py` | Create | `sam_prompts_for`, `crop_box`, `ground_keyframe` |
| `api/empu/persist.py` | Create | `persist_results`, `find_entry`, `choose_best` |
| `api/empu/pipeline/run.py` | Create | `JOB_STAGES`, `StageTracker`, `process_recording` |
| `api/empu/worker.py` | Create | `claim_next_job`, `reset_stale_jobs`, `run_once`, `main` |
| `api/empu/intake.py` | Create | `RecordingMeta`, `create_recording`, `enqueue_job`, `meta_from_license_file` |
| `api/empu/cli.py` | Modify | `db init`, `ingest`, `reprocess`, `process`, `status` |
| `api/pyproject.toml` | Modify | `faster-whisper` jadi dependensi utama |
| `api/tests/conftest.py`, `api/tests/fakes.py`, `api/tests/factories.py` | Modify/Create | Fixture DB, helper `analysis()`/`muse_term()`, SAM palsu |
| `packs/batik_tulis.yaml` | Modify | `sam_prompt` alat lain setelah diuji di keyframe nyata (H2-10) |
| `docs/reference/hasil-gate1.md` | Create | Angka Gate 1 |
| `CLAUDE.md` | Modify | Perintah baru, Status |

---

### Task H2-1: Model DB, engine, dan tata letak media

**Files:**
- Modify: `api/empu/enums.py`
- Create: `api/empu/models.py`, `api/empu/db.py`, `api/empu/media.py`
- Create: `api/tests/factories.py`
- Modify: `api/tests/conftest.py` (fixture `engine`, `session`)
- Test: `api/tests/test_models.py`, `api/tests/test_media.py`

**Interfaces:**
- Consumes: enum H1, `Settings.db_url`, `Settings.data_dir`
- Produces:
  - `SourceKind(own_recording, cc_by_video, internal_eval)`, `TimeSource(asr, muse)` di `enums.py`
  - `utcnow() -> datetime` (UTC **naive**, karena SQLite tidak menyimpan zona waktu); tabel `Archive`, `Contributor`, `Recording`, `Job`, `Chunk`, `Entry`, `Occurrence`, `ProcessStep`, `ReviewEvent`; konstanta `DEFAULT_DATASET_LICENSE`
  - `make_engine(db_url: str) -> Engine`, `init_db(engine, *, reset: bool = False) -> None`
  - `recording_dir(data_dir, archive_id, recording_id) -> Path`, `occurrence_dir(data_dir, archive_id, recording_id, occurrence_id) -> Path`, `entry_dir(data_dir, archive_id, entry_id) -> Path`, `rel_to_data(data_dir, path) -> str`, `abs_from_rel(data_dir, rel: str) -> Path` (melempar `ValueError` untuk path kosong, absolut, atau berisi `..`)
  - `tests/factories.py`: `make_archive(session, **kw) -> Archive`, `make_contributor(session, **kw) -> Contributor`, `make_recording(session, archive, **kw) -> Recording`
  - Fixture pytest `engine`, `session`

Catatan desain:
- Kolom JSON (`*_json`) memakai `sa_column=Column(JSON)`. SQLAlchemy **tidak** mendeteksi mutasi di tempat; selalu tetapkan dict/list baru (`job.timings_json = {**job.timings_json, ...}`).
- `entry.best_occurrence_id`, `entry.merged_into_id`, dan `occurrence.chunk_id` sengaja **tanpa** foreign key (menghindari siklus entry↔occurrence dan error FK saat proses ulang). Integritasnya dijaga `persist.py`.
- Model `table=True` di SQLModel **tidak** memvalidasi saat dibuat. Enum yang diisi string (`category="tool"`) tetap tersimpan benar, dan kembali sebagai enum setelah dibaca dari DB.
- Tidak ada migrasi. Kalau model berubah, `empu db init --reset` lalu proses ulang. Cache Muse membuat proses ulang gratis.

- [ ] **Step 1: Tambahkan enum ke `api/empu/enums.py`** (di akhir file)

```python
class SourceKind(StrEnum):
    own_recording = "own_recording"
    cc_by_video = "cc_by_video"
    internal_eval = "internal_eval"


class TimeSource(StrEnum):
    asr = "asr"
    muse = "muse"
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_models.py
import pytest
from sqlalchemy.exc import IntegrityError

from empu.enums import AccessLevel, EntryStatus, JobStatus, PipelineMode, SourceKind
from empu.models import Entry, Job
from factories import make_archive, make_recording


def test_tables_roundtrip_with_json_columns(session):
    a = make_archive(session)
    r = make_recording(session, a, source_kind=SourceKind.cc_by_video, source_url="https://y/1",
                       source_creator="Kreator", license="CC BY 3.0", attribution="by Kreator")
    job = Job(recording_id=r.id, mode=PipelineMode.B, model="m", prompt_version="v",
              timings_json={"normalizing": {"seconds": 1.5}})
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
    assert e.status is EntryStatus.proposed and e.variants_json == ["X"] and e.sam_status == "skipped"
    session.add(Entry(archive_id=a.id, canon_key="term:x", term="x", category="tool"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_canon_key_allowed_in_other_archive(session):
    a, b = make_archive(session), make_archive(session)
    session.add_all([Entry(archive_id=a.id, canon_key="term:x", term="x", category="tool"),
                     Entry(archive_id=b.id, canon_key="term:x", term="x", category="tool")])
    session.commit()


def test_wal_and_foreign_keys_enabled(engine):
    with engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
```

```python
# api/tests/test_media.py
import pytest

from empu.media import abs_from_rel, occurrence_dir, recording_dir, rel_to_data


def test_layout(tmp_path):
    assert recording_dir(tmp_path, 1, 3) == tmp_path / "archives/1/recordings/3"
    assert occurrence_dir(tmp_path, 1, 3, 9) == tmp_path / "archives/1/recordings/3/occurrences/9"


def test_rel_roundtrip(tmp_path):
    p = recording_dir(tmp_path, 1, 3) / "display.mp4"
    rel = rel_to_data(tmp_path, p)
    assert rel == "archives/1/recordings/3/display.mp4"
    assert abs_from_rel(tmp_path, rel) == tmp_path / rel


@pytest.mark.parametrize("bad", ["", "/etc/passwd", "../x", "archives/../../x"])
def test_abs_from_rel_rejects_escape(tmp_path, bad):
    with pytest.raises(ValueError):
        abs_from_rel(tmp_path, bad)


def test_rel_to_data_rejects_outside(tmp_path):
    with pytest.raises(ValueError):
        rel_to_data(tmp_path / "data", tmp_path / "elsewhere.mp4")
```

- [ ] **Step 3: Tulis `api/tests/factories.py` dan fixture DB di `api/tests/conftest.py`**

```python
# api/tests/factories.py
from itertools import count

from empu.enums import AccessLevel, ContributorRole
from empu.models import Archive, Contributor, Recording

_n = count(1)


def _save(session, obj):
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_archive(session, **kw) -> Archive:
    n = next(_n)
    return _save(session, Archive(**({"slug": f"arsip-{n}", "title": f"Arsip {n}",
                                      "craft_pack_id": "batik_tulis"} | kw)))


def make_contributor(session, **kw) -> Contributor:
    return _save(session, Contributor(**({"name": f"Ahli {next(_n)}", "role": ContributorRole.maestro} | kw)))


def make_recording(session, archive, **kw) -> Recording:
    return _save(session, Recording(**({
        "archive_id": archive.id, "title": "Rekaman uji", "original_path": "",
        "consent_scope": AccessLevel.public,
    } | kw)))
```

Tambahkan ke `api/tests/conftest.py` (impor di atas, fixture di bawah):

```python
from sqlmodel import Session

from empu.db import init_db, make_engine


@pytest.fixture
def engine(settings):
    eng = make_engine(settings.db_url)
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
```

- [ ] **Step 4: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_models.py tests/test_media.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.models'`.

- [ ] **Step 5: Tulis `api/empu/models.py`**

```python
"""Database tables: spec section 9 plus D5 (stage_id, canon_key), D9 (source_*), D10 (time_source).

No `from __future__ import annotations` here: SQLModel resolves field types at class creation.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from empu.enums import (
    AccessLevel,
    Category,
    ChunkStatus,
    Confidence,
    ConsentStatus,
    ContributorRole,
    EntryStatus,
    JobStatus,
    OccurrenceStatus,
    PipelineMode,
    ReviewAction,
    SamStatus,
    Source,
    SourceKind,
    TimeSource,
    VisualMatch,
)

DEFAULT_DATASET_LICENSE = "Determined by the community; contact the archive owner"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Archive(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    craft_pack_id: str
    description: str = ""
    owner_name: str = ""
    license: str = DEFAULT_DATASET_LICENSE
    default_access: AccessLevel = AccessLevel.public
    is_demo: bool = False
    is_sandbox: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class Contributor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    role: ContributorRole = ContributorRole.maestro
    region: str = ""
    sanggar: str = ""
    bio: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Recording(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    archive_id: int = Field(foreign_key="archive.id", index=True)
    contributor_id: int | None = Field(default=None, foreign_key="contributor.id")
    title: str
    recorded_at: str | None = None
    location: str = ""
    language_hint: str = "id,jv"
    duration_s: float | None = None
    original_path: str
    display_path: str | None = None
    analysis_path: str | None = None
    consent_status: ConsentStatus = ConsentStatus.granted
    consent_scope: AccessLevel = AccessLevel.public
    consent_note: str = ""
    consent_evidence: str = ""
    consent_withdrawn_at: datetime | None = None
    source_kind: SourceKind = SourceKind.own_recording
    source_url: str | None = None
    source_creator: str | None = None
    license: str | None = None
    attribution: str | None = None
    status: JobStatus = JobStatus.queued
    created_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    status: JobStatus = Field(default=JobStatus.queued, index=True)
    progress: float = 0.0
    detail: str = ""
    error: str | None = None
    mode: PipelineMode = PipelineMode.A
    model: str = ""
    prompt_version: str = ""
    usage_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    timings_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Chunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    idx: int
    start_s: float
    end_s: float
    path: str
    sha256: str = ""
    file_id: str | None = None
    status: ChunkStatus = ChunkStatus.pending
    raw_path: str | None = None
    parsed_path: str | None = None
    error: str | None = None
    usage_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    latency_s: float | None = None
    cached: bool = False


class Entry(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("archive_id", "canon_key"),)

    id: int | None = Field(default=None, primary_key=True)
    archive_id: int = Field(foreign_key="archive.id", index=True)
    canon_key: str = Field(index=True)
    term: str
    category: Category = Category.other
    stage_id: str | None = None
    gloss_id: str = ""
    gloss_en: str = ""
    variants_json: list = Field(default_factory=list, sa_column=Column(JSON))
    pack_term_id: str | None = None
    is_novel: bool = False
    status: EntryStatus = Field(default=EntryStatus.proposed, index=True)
    merged_into_id: int | None = None
    access_level: AccessLevel = AccessLevel.public
    best_occurrence_id: int | None = None
    crop_path: str | None = None
    overlay_path: str | None = None
    sam_status: SamStatus = SamStatus.skipped
    sam_prompt: str | None = None
    maestro_note: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Occurrence(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(foreign_key="entry.id", index=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    chunk_id: int | None = None
    spoken: str = ""
    term_raw: str = ""
    source: Source
    t_start: float
    t_end: float
    time_source: TimeSource = TimeSource.muse
    asr_score: float | None = None
    stage_raw: str | None = None
    stage_id: str | None = None
    visible: str = ""
    visible_object_en: str | None = None
    visual_match: VisualMatch = VisualMatch.not_visible
    gloss_raw: str = ""
    gloss_en_raw: str = ""
    evidence_quote: str = ""
    confidence: Confidence = Confidence.low
    clip_path: str | None = None
    audio_path: str | None = None
    keyframe_path: str | None = None
    status: OccurrenceStatus = OccurrenceStatus.proposed


class ProcessStep(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    pack_stage_id: str | None = None
    name_raw: str
    t_start: float
    t_end: float
    tools_json: list = Field(default_factory=list, sa_column=Column(JSON))
    order: int = 0


class ReviewEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(foreign_key="entry.id", index=True)
    occurrence_id: int | None = None
    action: ReviewAction
    before_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    after_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    actor: str
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 6: Tulis `api/empu/db.py`**

```python
"""SQLite engine with WAL (API and worker are separate processes) and enforced foreign keys."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from empu import models  # noqa: F401  (registers the tables on SQLModel.metadata)


def make_engine(db_url: str) -> Engine:
    is_sqlite = db_url.startswith("sqlite")
    if db_url.startswith("sqlite:///") and ":memory:" not in db_url:
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _record) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()
    return engine


def init_db(engine: Engine, *, reset: bool = False) -> None:
    if reset:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
```

- [ ] **Step 7: Tulis `api/empu/media.py`**

```python
"""Media layout under data_dir (spec section 9). The DB stores paths relative to data_dir."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


def recording_dir(data_dir: Path, archive_id: int, recording_id: int) -> Path:
    return Path(data_dir) / "archives" / str(archive_id) / "recordings" / str(recording_id)


def occurrence_dir(data_dir: Path, archive_id: int, recording_id: int, occurrence_id: int) -> Path:
    return recording_dir(data_dir, archive_id, recording_id) / "occurrences" / str(occurrence_id)


def entry_dir(data_dir: Path, archive_id: int, entry_id: int) -> Path:
    return Path(data_dir) / "archives" / str(archive_id) / "entries" / str(entry_id)


def rel_to_data(data_dir: Path, path: Path) -> str:
    return Path(path).resolve().relative_to(Path(data_dir).resolve()).as_posix()


def abs_from_rel(data_dir: Path, rel: str) -> Path:
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"invalid media path: {rel!r}")
    return Path(data_dir).joinpath(*p.parts)
```

- [ ] **Step 8: Jalankan tes**

Run: `cd api && uv run pytest tests/test_models.py tests/test_media.py -q`
Expected: `11 passed`.

- [ ] **Step 9: Commit**

```bash
git add api/empu/enums.py api/empu/models.py api/empu/db.py api/empu/media.py api/tests
git commit -m "feat(db): SQLModel tables, SQLite engine, media layout"
```

---

### Task H2-2: Peta tahapan (`process_map.py`)

**Files:**
- Create: `api/empu/pipeline/process_map.py`
- Modify: `api/tests/fakes.py` (helper `muse_term`, `analysis`)
- Test: `api/tests/test_process_map.py`

**Interfaces:**
- Consumes: `CraftPack.variant_index()`, `normalize`, `ChunkAnalysis` (hanya `.spec` dan `.output`)
- Produces:
  - `StageMatcher(pack, threshold=90.0)` dengan `resolve(name: str | None) -> str | None` (id tahap pack). Urutan: cocok persis → fuzzy `ratio` ≥ 90 → n-gram 3/2/1 kata yang persis cocok. Hanya varian **tahap**, bukan istilah
  - `StepDraft(pack_stage_id: str | None, name_raw: str, t_start: float, t_end: float, tools: list[str], order: int = 0)`
  - `build_process_map(analyses, pack) -> list[StepDraft]`: waktu absolut, urut, langkah berurutan dengan tahap yang sama digabung kalau jaraknya ≤ 5 s (`MERGE_GAP_S`); langkah yang tidak cocok tetap ada dengan `pack_stage_id=None` (tampil sebagai "other")
  - `stage_at(steps, t: float) -> str | None`
  - `tests/fakes.py`: `muse_term(**kw) -> dict`, `analysis(idx, start_s, end_s, terms=(), steps=()) -> ChunkAnalysis`

- [ ] **Step 1: Tambahkan helper ke `api/tests/fakes.py`** (impor di atas file)

```python
from empu.muse_schema import MuseSegmentOutput
from empu.pipeline.analyze import ChunkAnalysis
from empu.pipeline.chunk import ChunkSpec


def muse_term(**kw) -> dict:
    base = {
        "spoken": kw.get("term", "x"), "term": "x", "category": "tool", "source": "speech",
        "t_start": 1.0, "t_end": 2.0, "stage": None, "evidence_quote": "", "visible": "",
        "visible_object_en": None, "visual_match": "not_visible", "gloss_id": "", "gloss_en": "",
        "confidence": "medium",
    }
    return base | kw


def analysis(idx: int, start_s: float, end_s: float, terms=(), steps=()) -> ChunkAnalysis:
    out = MuseSegmentOutput.model_validate(
        {"speech_heard": True, "terms": list(terms), "process_steps": list(steps)})
    return ChunkAnalysis(ChunkSpec(idx, start_s, end_s), Path(f"{idx}.mp4"), f"sha{idx}", f"key{idx}",
                         "analyze-v3", out, None, None, {}, 0.0, None, False, 1, 0, None)
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_process_map.py
import pytest

from empu.pipeline.process_map import StageMatcher, build_process_map, stage_at
from fakes import analysis


@pytest.fixture(scope="module")
def matcher(pack):
    return StageMatcher(pack)


@pytest.mark.parametrize("name, expected", [
    ("nglowong", "nglowong"),
    ("Ngelorot", "nglorod"),
    ("persiapan kain", "persiapan_kain"),
    ("nglowongg", "nglowong"),
    ("proses nglowong dengan canting", "nglowong"),
    ("istirahat sebentar", None),
    ("", None),
    (None, None),
])
def test_resolve(matcher, name, expected):
    assert matcher.resolve(name) == expected


def test_term_variants_are_not_stages(matcher):
    assert matcher.resolve("canting") is None


def test_build_merges_same_stage_across_overlap(pack):
    a0 = analysis(0, 0, 75, steps=[{"step": "memola", "t_start": 0, "t_end": 50, "tools": ["pensil"]},
                                   {"step": "nglowong", "t_start": 60, "t_end": 75, "tools": ["canting"]}])
    a1 = analysis(1, 65, 140, steps=[{"step": "ngelowong", "t_start": 0, "t_end": 20, "tools": ["wajan"]},
                                     {"step": "minum teh", "t_start": 30, "t_end": 40, "tools": []}])
    steps = build_process_map([a0, a1], pack)
    assert [(s.pack_stage_id, s.t_start, s.t_end) for s in steps] == [
        ("memola", 0, 50), ("nglowong", 60, 85), (None, 95, 105)]
    assert steps[1].tools == ["canting", "wajan"]
    assert [s.order for s in steps] == [0, 1, 2]
    assert steps[2].name_raw == "minum teh"


def test_gap_larger_than_five_seconds_not_merged(pack):
    a = analysis(0, 0, 75, steps=[{"step": "nglowong", "t_start": 0, "t_end": 10, "tools": []},
                                  {"step": "nglowong", "t_start": 20, "t_end": 30, "tools": []}])
    assert len(build_process_map([a], pack)) == 2


def test_failed_chunks_skipped(pack):
    a = analysis(0, 0, 75)
    a.output = None
    assert build_process_map([a], pack) == []


def test_stage_at(pack):
    steps = build_process_map([analysis(0, 0, 75, steps=[
        {"step": "memola", "t_start": 0, "t_end": 30, "tools": []},
        {"step": "nglowong", "t_start": 25, "t_end": 60, "tools": []}])], pack)
    assert stage_at(steps, 10) == "memola"
    assert stage_at(steps, 27) == "nglowong"
    assert stage_at(steps, 70) is None
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_process_map.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.pipeline.process_map'`.

- [ ] **Step 4: Tulis `api/empu/pipeline/process_map.py`**

```python
"""Process map: Muse process_steps from all chunks, resolved to pack stages, on one timeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz, process

from empu.packs import CraftPack
from empu.text import normalize

MERGE_GAP_S = 5.0


class StageMatcher:
    def __init__(self, pack: CraftPack, threshold: float = 90.0) -> None:
        self.index = {k: ref.id for k, ref in pack.variant_index().items() if ref.kind == "stage"}
        self._keys = list(self.index)
        self.threshold = threshold

    def resolve(self, name: str | None) -> str | None:
        key = normalize(name)
        if not key:
            return None
        if key in self.index:
            return self.index[key]
        hit = process.extractOne(key, self._keys, scorer=fuzz.ratio, score_cutoff=self.threshold)
        if hit is not None:
            return self.index[hit[0]]
        words = key.split()
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i:i + n])
                if gram in self.index:
                    return self.index[gram]
        return None


@dataclass
class StepDraft:
    pack_stage_id: str | None
    name_raw: str
    t_start: float
    t_end: float
    tools: list[str] = field(default_factory=list)
    order: int = 0


def _same_stage(a: StepDraft, b: StepDraft) -> bool:
    if b.pack_stage_id is not None:
        return a.pack_stage_id == b.pack_stage_id
    return a.pack_stage_id is None and normalize(a.name_raw) == normalize(b.name_raw)


def build_process_map(analyses: Sequence[Any], pack: CraftPack) -> list[StepDraft]:
    matcher = StageMatcher(pack)
    raw: list[StepDraft] = []
    for a in analyses:
        if a.output is None:
            continue
        spec = a.spec
        for st in a.output.process_steps:
            ts = min(spec.start_s + st.t_start, spec.end_s)
            te = min(max(spec.start_s + st.t_end, ts), spec.end_s)
            raw.append(StepDraft(matcher.resolve(st.step), st.step.strip(), ts, te, list(st.tools)))
    raw.sort(key=lambda d: (d.t_start, d.t_end))
    merged: list[StepDraft] = []
    for d in raw:
        prev = merged[-1] if merged else None
        if prev is not None and _same_stage(prev, d) and d.t_start <= prev.t_end + MERGE_GAP_S:
            prev.t_end = max(prev.t_end, d.t_end)
            prev.tools += [t for t in d.tools if t not in prev.tools]
        else:
            merged.append(d)
    for i, d in enumerate(merged):
        d.order = i
    return merged


def stage_at(steps: Sequence[StepDraft], t: float) -> str | None:
    hits = [s for s in steps if s.pack_stage_id and s.t_start <= t <= s.t_end]
    return max(hits, key=lambda s: s.t_start).pack_stage_id if hits else None
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest tests/test_process_map.py tests/test_no_hardcoded_terms.py -q`
Expected: `14 passed`.

- [ ] **Step 6: Commit**

```bash
git add api/empu/pipeline/process_map.py api/tests
git commit -m "feat(pipeline): process map with stage resolution against the pack"
```

---

### Task H2-3: Penggabungan dan kanonisasi (`merge.py`)

**Files:**
- Create: `api/empu/pipeline/merge.py`
- Test: `api/tests/test_merge.py`

**Interfaces:**
- Consumes: `CraftPack`, `StageMatcher`, `StepDraft`, `stage_at`, `MuseTerm`, `normalize`, `CONFIDENCE_RANK`
- Produces:
  - `CanonMatch(canon_key: str, term: str, pack_term_id: str | None, pack_stage_id: str | None, is_novel: bool, method: Literal["exact","fuzzy","novel"], score: float)`. Format `canon_key`: `term:<pack_term_id>`, `stage:<pack_stage_id>`, atau `novel:<normalize(term)>`
  - `Canonicalizer(pack, threshold=90.0).match(term: str, spoken: str = "") -> CanonMatch`
  - `AbsOccurrence(chunk_idx: int, muse: MuseTerm, canon: CanonMatch, t_start: float, t_end: float, edge_s: float, stage_id: str | None = None, time_source: TimeSource = muse, asr_score: float | None = None)` (waktu absolut, dapat diubah oleh `realign`)
  - `occurrence_rank(source, visual_match, confidence, duration) -> tuple` (prioritas best occurrence spec 8.5.5; dipakai juga oleh `persist.choose_best`)
  - `collect_occurrences(analyses, canon) -> list[AbsOccurrence]`, `dedup_overlap(occs, tol_s=4.0) -> list[AbsOccurrence]`, `group_entries(occs, pack, steps=None) -> list[EntryDraft]`
  - `EntryDraft(canon, category: Category, stage_id, gloss_id, gloss_en, variants: list[str], occurrences: list[AbsOccurrence], best_index: int)` dengan properti `best`
  - `merge_analyses(analyses, pack, *, steps=None, tol_s=4.0, retime: Callable[[list[AbsOccurrence]], list[AbsOccurrence]] | None = None) -> list[EntryDraft]`. `retime` dijalankan **sebelum** dedup (Mode B)

Aturan (spec 8.5):
- Kanonisasi mencoba `term` lalu `spoken`: cocok persis ke `variant_index()`, lalu fuzzy `ratio` ≥ 90 ke semua kunci indeks. Kalau tidak ada, entri baru `is_novel=True`.
- Dedup hanya antar-segmen berbeda (kemunculan berulang di satu segmen tetap dipertahankan). Yang dipertahankan: keyakinan lebih tinggi, lalu yang lebih jauh dari tepi segmen.
- Kategori: tahap pack → `stage`; istilah pack → kategori pack; istilah baru → kategori Muse terbanyak.
- `stage_id` kemunculan: tahap pack itu sendiri (untuk entri tahap) → `stage` dari Muse yang ter-resolve → `stage_at(steps, t_start)`. `stage_id` entri: tahap terbanyak dari kemunculannya, fallback `stage` di pack.
- Glosa dari Muse (best occurrence dulu, lalu kemunculan lain). Glosa pack hanya fallback kalau Muse kosong.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_merge.py
import pytest

from empu.enums import Category, Source, TimeSource
from empu.pipeline.merge import Canonicalizer, collect_occurrences, dedup_overlap, merge_analyses
from empu.pipeline.process_map import StepDraft
from fakes import analysis, muse_term


@pytest.fixture(scope="module")
def canon(pack):
    return Canonicalizer(pack)


def test_exact_variant_to_pack_term(canon):
    m = canon.match("Tjanting")
    assert (m.canon_key, m.term, m.pack_term_id, m.method, m.is_novel) == (
        "term:canting", "canting", "canting", "exact", False)


def test_spoken_used_when_term_unknown(canon):
    m = canon.match("pena lilin", spoken="canting klowong")
    assert m.canon_key == "term:canting_klowongan"


def test_stage_variant(canon):
    m = canon.match("ngelorot")
    assert (m.canon_key, m.pack_stage_id, m.term) == ("stage:nglorod", "nglorod", "nglorod")
    assert canon.match("persiapan kain").term == "persiapan kain"


def test_fuzzy_match(canon):
    m = canon.match("cantingg")
    assert m.canon_key == "term:canting" and m.method == "fuzzy" and m.score >= 90


def test_novel(canon):
    m = canon.match("Bethik!", spoken="bethik")
    assert (m.canon_key, m.term, m.is_novel, m.method) == ("novel:bethik", "Bethik!", True, "novel")


def test_absolute_times_and_clamp(canon):
    a = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=3, t_end=4),
                                     muse_term(term="wajan", t_start=80, t_end=90)])
    occs = collect_occurrences([a], canon)
    assert [(o.t_start, o.t_end) for o in occs] == [(68, 69), (140, 140)]
    assert occs[0].edge_s == 3


def test_dedup_across_overlap_keeps_higher_confidence(canon):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=70, t_end=71, confidence="high")])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=5.5, t_end=6, confidence="medium")])
    kept = dedup_overlap(collect_occurrences([a0, a1], canon))
    assert len(kept) == 1 and kept[0].chunk_idx == 0


def test_dedup_tie_prefers_farther_from_edge(canon):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=73, t_end=74)])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=8, t_end=9)])
    kept = dedup_overlap(collect_occurrences([a0, a1], canon))
    assert len(kept) == 1 and kept[0].chunk_idx == 1


def test_same_chunk_repeats_and_far_apart_are_kept(canon):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=10, t_end=11),
                                    muse_term(term="canting", t_start=12, t_end=13)])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=30, t_end=31)])
    assert len(dedup_overlap(collect_occurrences([a0, a1], canon))) == 3


def test_group_entries_best_category_variants_gloss(pack):
    a = analysis(0, 0, 75, terms=[
        muse_term(term="canting", spoken="tjanting", source="visual_only", confidence="high",
                  t_start=5, t_end=6, gloss_id=""),
        muse_term(term="canting", spoken="nyanting", source="speech", confidence="low", t_start=20,
                  t_end=21, gloss_id="alat tulis lilin", gloss_en="wax pen", stage="nglowong"),
        muse_term(term="bethik", category="material", source="speech", t_start=30, t_end=31),
    ])
    drafts = {d.canon.canon_key: d for d in merge_analyses([a], pack)}
    c = drafts["term:canting"]
    assert c.best.muse.source is Source.speech and c.best.t_start == 20
    assert c.category is Category.tool and c.gloss_id == "alat tulis lilin"
    assert c.variants == ["nyanting", "tjanting"]
    assert c.stage_id == "nglowong"
    n = drafts["novel:bethik"]
    assert n.canon.is_novel and n.category is Category.material


def test_stage_from_process_steps_when_muse_stage_missing(pack):
    a = analysis(0, 0, 75, terms=[muse_term(term="wajan", t_start=40, t_end=41)])
    steps = [StepDraft("nembok", "nembok", 30, 50)]
    (d,) = merge_analyses([a], pack, steps=steps)
    assert d.occurrences[0].stage_id == "nembok" and d.stage_id == "nembok"


def test_stage_entry_uses_its_own_stage(pack):
    (d,) = merge_analyses([analysis(0, 0, 75, terms=[muse_term(term="nglorod", category="stage")])], pack)
    assert d.category is Category.stage and d.stage_id == "nglorod"


def test_retime_runs_before_dedup(pack):
    a0 = analysis(0, 0, 75, terms=[muse_term(term="canting", t_start=10, t_end=11)])
    a1 = analysis(1, 65, 140, terms=[muse_term(term="canting", t_start=5, t_end=6)])

    def retime(occs):
        for o in occs:
            o.t_start, o.time_source = 70.0, TimeSource.asr
        return occs

    (d,) = merge_analyses([a0, a1], pack, retime=retime)
    assert len(d.occurrences) == 1 and d.best.time_source is TimeSource.asr
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_merge.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.pipeline.merge'`.

- [ ] **Step 3: Tulis `api/empu/pipeline/merge.py`**

```python
"""Merge per-chunk Muse output into archive entries (spec 8.5).

Absolute times -> optional retime (Mode B) -> overlap dedup -> canonical grouping -> best occurrence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from rapidfuzz import fuzz, process

from empu.enums import CONFIDENCE_RANK, Category, Confidence, Source, TimeSource, VisualMatch
from empu.muse_schema import MuseTerm
from empu.packs import CraftPack, PackRef
from empu.pipeline.process_map import StageMatcher, StepDraft, stage_at
from empu.text import normalize


@dataclass(frozen=True)
class CanonMatch:
    canon_key: str
    term: str
    pack_term_id: str | None
    pack_stage_id: str | None
    is_novel: bool
    method: Literal["exact", "fuzzy", "novel"]
    score: float


class Canonicalizer:
    def __init__(self, pack: CraftPack, threshold: float = 90.0) -> None:
        self.pack = pack
        self.threshold = threshold
        self.index = pack.variant_index()
        self._keys = list(self.index)

    def match(self, term: str, spoken: str = "") -> CanonMatch:
        forms = [k for k in (normalize(term), normalize(spoken)) if k]
        for key in forms:
            if key in self.index:
                return self._resolve(self.index[key], "exact", 100.0)
        best: tuple[str, float] | None = None
        for key in forms:
            hit = process.extractOne(key, self._keys, scorer=fuzz.ratio, score_cutoff=self.threshold)
            if hit is not None and (best is None or hit[1] > best[1]):
                best = (hit[0], float(hit[1]))
        if best is not None:
            return self._resolve(self.index[best[0]], "fuzzy", best[1])
        label = term.strip() or spoken.strip()
        return CanonMatch(f"novel:{forms[0] if forms else ''}", label, None, None, True, "novel", 0.0)

    def _resolve(self, ref: PackRef, method: Literal["exact", "fuzzy"], score: float) -> CanonMatch:
        if ref.kind == "term":
            t = self.pack.term(ref.id)
            assert t is not None
            return CanonMatch(f"term:{t.id}", t.label, t.id, None, False, method, score)
        s = self.pack.stage(ref.id)
        assert s is not None
        return CanonMatch(f"stage:{s.id}", s.display_label, None, s.id, False, method, score)


@dataclass
class AbsOccurrence:
    chunk_idx: int
    muse: MuseTerm
    canon: CanonMatch
    t_start: float
    t_end: float
    edge_s: float
    stage_id: str | None = None
    time_source: TimeSource = TimeSource.muse
    asr_score: float | None = None


def occurrence_rank(source: Source | str, visual_match: VisualMatch | str,
                    confidence: Confidence | str, duration: float) -> tuple:
    return (Source(source) is Source.speech, VisualMatch(visual_match) is VisualMatch.yes,
            CONFIDENCE_RANK[Confidence(confidence)], duration)


def _rank(o: AbsOccurrence) -> tuple:
    return occurrence_rank(o.muse.source, o.muse.visual_match, o.muse.confidence, o.t_end - o.t_start)


def collect_occurrences(analyses: Sequence[Any], canon: Canonicalizer) -> list[AbsOccurrence]:
    out: list[AbsOccurrence] = []
    for a in analyses:
        if a.output is None:
            continue
        spec = a.spec
        for t in a.output.terms:
            ts = min(spec.start_s + t.t_start, spec.end_s)
            te = min(max(spec.start_s + t.t_end, ts), spec.end_s)
            out.append(AbsOccurrence(spec.idx, t, canon.match(t.term, t.spoken), ts, te,
                                     edge_s=min(ts - spec.start_s, spec.end_s - te)))
    return sorted(out, key=lambda o: (o.t_start, o.chunk_idx))


def dedup_overlap(occs: Sequence[AbsOccurrence], tol_s: float = 4.0) -> list[AbsOccurrence]:
    kept: list[AbsOccurrence] = []
    last: dict[str, int] = {}
    for o in sorted(occs, key=lambda o: (o.t_start, o.chunk_idx)):
        i = last.get(o.canon.canon_key)
        if i is not None:
            prev = kept[i]
            if prev.chunk_idx != o.chunk_idx and abs(o.t_start - prev.t_start) <= tol_s:
                if (CONFIDENCE_RANK[o.muse.confidence], o.edge_s) > (
                        CONFIDENCE_RANK[prev.muse.confidence], prev.edge_s):
                    kept[i] = o
                continue
        last[o.canon.canon_key] = len(kept)
        kept.append(o)
    return kept


@dataclass
class EntryDraft:
    canon: CanonMatch
    category: Category
    stage_id: str | None
    gloss_id: str
    gloss_en: str
    variants: list[str]
    occurrences: list[AbsOccurrence]
    best_index: int

    @property
    def best(self) -> AbsOccurrence:
        return self.occurrences[self.best_index]


def _first(values: Sequence[str]) -> str:
    return next((v for v in values if v), "")


def group_entries(occs: Sequence[AbsOccurrence], pack: CraftPack,
                  steps: Sequence[StepDraft] | None = None) -> list[EntryDraft]:
    matcher = StageMatcher(pack)
    groups: dict[str, list[AbsOccurrence]] = {}
    for o in occs:
        o.stage_id = (o.canon.pack_stage_id or matcher.resolve(o.muse.stage)
                      or (stage_at(steps, o.t_start) if steps else None))
        groups.setdefault(o.canon.canon_key, []).append(o)
    drafts: list[EntryDraft] = []
    for items in groups.values():
        items.sort(key=lambda o: o.t_start)
        best_i = max(range(len(items)), key=lambda i: _rank(items[i]))
        best, c = items[best_i], items[best_i].canon
        pack_term = pack.term(c.pack_term_id) if c.pack_term_id else None
        if c.pack_stage_id:
            category = Category.stage
        elif pack_term is not None:
            category = pack_term.category
        else:
            category = Counter(o.muse.category for o in items).most_common(1)[0][0]
        stages = Counter(o.stage_id for o in items if o.stage_id)
        stage_id = c.pack_stage_id or (stages.most_common(1)[0][0] if stages
                                       else (pack_term.stage if pack_term else None))
        ordered = [best, *[o for o in items if o is not best]]
        gloss_id = _first([o.muse.gloss_id for o in ordered]) or (pack_term.gloss_id if pack_term else "")
        gloss_en = _first([o.muse.gloss_en for o in ordered]) or (pack_term.gloss_en if pack_term else "")
        canon_norm = normalize(c.term)
        variants = sorted({f.strip() for o in items for f in (o.muse.spoken, o.muse.term)
                           if f.strip() and normalize(f) != canon_norm}, key=str.casefold)
        drafts.append(EntryDraft(c, category, stage_id, gloss_id, gloss_en, variants, items, best_i))
    return sorted(drafts, key=lambda d: d.best.t_start)


def merge_analyses(analyses: Sequence[Any], pack: CraftPack, *, steps: Sequence[StepDraft] | None = None,
                   tol_s: float = 4.0,
                   retime: Callable[[list[AbsOccurrence]], list[AbsOccurrence]] | None = None,
                   ) -> list[EntryDraft]:
    occs = collect_occurrences(analyses, Canonicalizer(pack))
    if retime is not None:
        occs = retime(occs)
    return group_entries(dedup_overlap(occs, tol_s), pack, steps)
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_merge.py tests/test_no_hardcoded_terms.py -q`
Expected: semua lulus. Kalau `test_spoken_used_when_term_unknown` gagal karena "pena lilin" ternyata lolos fuzzy ke sesuatu, ganti dengan frasa lain yang jelas di luar pack; jangan menurunkan ambang.

- [ ] **Step 5: Commit**

```bash
git add api/empu/pipeline/merge.py api/tests/test_merge.py
git commit -m "feat(pipeline): canonicalize to pack, overlap dedup, entry grouping"
```

---

### Task H2-4: Mode B, transkripsi lokal dan koreksi waktu (`transcribe.py`)

Mode B adalah default sejak Gate 0 (D10), jadi task ini wajib dan dikerjakan sebelum orkestrator.

**Files:**
- Modify: `api/pyproject.toml` (`faster-whisper>=1.1` ke `dependencies`, hapus grup opsional `asr`)
- Create: `api/empu/pipeline/transcribe.py`
- Test: `api/tests/test_transcribe.py`

**Interfaces:**
- Consumes: `AbsOccurrence`, `TimeSource`, `Source`, `normalize`, `sha256_file`
- Produces:
  - `Word(t_start: float, t_end: float, text: str)` (frozen dataclass)
  - `Transcriber = Callable[[Path], list[Word]]`
  - `whisper_transcriber(model_name: str = "small", language: str = "id") -> Transcriber` (model dimuat saat dipanggil pertama)
  - `transcribe_cached(media: Path, transcriber: Transcriber, *, cache_root: Path, model_name: str) -> list[Word]` (cache `data/cache/asr/<sha256>__<model>.json`)
  - `realign(occs: list[AbsOccurrence], words: list[Word], *, window_s: float = 30.0, threshold: float = 80.0) -> list[AbsOccurrence]`

Algoritma `realign` untuk setiap kemunculan `source=speech`:
1. Kutipan = `normalize(evidence_quote)`, atau `normalize(spoken)` kalau kutipan kosong. Panjang `n` kata.
2. Kandidat: setiap jendela `n` kata berurutan yang kata pertamanya berada dalam ±30 s dari `t_start` Muse. Skor = `fuzz.partial_ratio(kutipan, teks jendela)`. Ambil skor tertinggi (seri: yang paling dekat waktu Muse).
3. Kalau skor < 80: tidak berubah (`time_source=muse`).
4. Kalau ≥ 80: di dalam jendela itu, cari sub-rentang `k` atau `k+1` kata (`k` = jumlah kata `spoken`) dengan `fuzz.ratio` tertinggi terhadap `spoken`. Kalau rasio ≥ 60, pakai waktu sub-rentang itu; kalau tidak, pakai waktu seluruh jendela. Tandai `time_source=asr`, `asr_score=skor`.

Contoh nyata dari Gate 0: Muse menaruh *waterglass* di 142 s, ucapannya di 162–165 s ("watera gelas" di subtitle). Skor terkalibrasi dengan rapidfuzz: jendela "pakai watera gelas biar warnanya" = 93,5; "watera gelas" vs "waterglass" = 81,8; "watera" saja = 75.

- [ ] **Step 1: Ubah dependensi dan sinkronkan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
uv add "faster-whisper>=1.1"
uv sync
uv run python -c "import faster_whisper; print(faster_whisper.__version__)"
```
Expected: versi tercetak. Hapus blok `[project.optional-dependencies]` `asr = [...]` dari `pyproject.toml` kalau masih ada, lalu `uv sync` lagi.

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_transcribe.py
import pytest

from empu.enums import TimeSource
from empu.pipeline.merge import Canonicalizer, collect_occurrences
from empu.pipeline.transcribe import Word, realign, transcribe_cached
from fakes import analysis, muse_term

WORDS = [Word(130.0, 130.4, "lalu"), Word(130.5, 131.0, "kita"), Word(131.1, 131.6, "rebus"),
         Word(162.0, 162.3, "pakai"), Word(162.4, 162.8, "watera"), Word(162.9, 163.3, "gelas"),
         Word(163.4, 163.6, "biar"), Word(163.7, 164.2, "warnanya"), Word(164.3, 164.6, "kuat")]


@pytest.fixture(scope="module")
def canon(pack):
    return Canonicalizer(pack)


def occs_for(canon, **kw):
    return collect_occurrences([analysis(2, 130, 205, terms=[muse_term(**kw)])], canon)


def test_realign_moves_shifted_speech_to_asr_time(canon):
    occs = occs_for(canon, term="waterglass", spoken="waterglass", t_start=12, t_end=13,
                    evidence_quote="pakai waterglass biar warnanya kuat")
    (o,) = realign(occs, WORDS)
    assert (o.t_start, o.t_end) == (162.4, 163.3)
    assert o.time_source is TimeSource.asr and o.asr_score >= 80


def test_no_match_keeps_muse_time(canon):
    occs = occs_for(canon, term="soda abu", t_start=12, t_end=13, evidence_quote="tambahkan soda abu sedikit")
    (o,) = realign(occs, WORDS)
    assert (o.t_start, o.time_source) == (142, TimeSource.muse)


def test_outside_window_keeps_muse_time(canon):
    occs = occs_for(canon, term="waterglass", t_start=12, t_end=13,
                    evidence_quote="pakai waterglass biar warnanya kuat")
    (o,) = realign(occs, WORDS, window_s=10)
    assert o.time_source is TimeSource.muse


def test_non_speech_untouched(canon):
    occs = occs_for(canon, term="waterglass", source="on_screen_text", t_start=12, t_end=13,
                    evidence_quote="pakai waterglass biar warnanya kuat")
    (o,) = realign(occs, WORDS)
    assert o.time_source is TimeSource.muse and o.t_start == 142


def test_empty_quote_falls_back_to_spoken(canon):
    words = [Word(150.0, 150.5, "ini"), Word(150.6, 151.2, "spang"), Word(151.3, 151.7, "king")]
    occs = occs_for(canon, term="spangkring", spoken="spangkring", t_start=10, t_end=11, evidence_quote="")
    (o,) = realign(occs, words)
    assert (o.t_start, o.t_end, o.time_source) == (150.6, 151.7, TimeSource.asr)


def test_empty_transcript_is_noop(canon):
    occs = occs_for(canon, term="waterglass", t_start=12, t_end=13, evidence_quote="pakai waterglass")
    assert realign(occs, [])[0].time_source is TimeSource.muse


def test_transcribe_cached_calls_once(tmp_path):
    media = tmp_path / "a.mp4"
    media.write_bytes(b"audio")
    calls = []

    def fake(path):
        calls.append(path)
        return [Word(0.0, 0.5, "halo")]

    a = transcribe_cached(media, fake, cache_root=tmp_path / "asr", model_name="small")
    b = transcribe_cached(media, fake, cache_root=tmp_path / "asr", model_name="small")
    assert a == b == [Word(0.0, 0.5, "halo")] and len(calls) == 1
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_transcribe.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.pipeline.transcribe'`.

- [ ] **Step 4: Tulis `api/empu/pipeline/transcribe.py`**

```python
"""Mode B (D10): local faster-whisper word timestamps as a time anchor for Muse speech terms.

Muse keeps the spelling; only t_start/t_end move. Transcripts are cached by media hash + model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from faster_whisper import WhisperModel
from rapidfuzz import fuzz

from empu.cache import sha256_file
from empu.enums import Source, TimeSource
from empu.pipeline.merge import AbsOccurrence
from empu.text import normalize

SPOKEN_MIN_RATIO = 60.0


@dataclass(frozen=True)
class Word:
    t_start: float
    t_end: float
    text: str


Transcriber = Callable[[Path], list[Word]]


def whisper_transcriber(model_name: str = "small", language: str = "id") -> Transcriber:
    model: WhisperModel | None = None

    def run(path: Path) -> list[Word]:
        nonlocal model
        if model is None:
            model = WhisperModel(model_name, device="auto", compute_type="int8")
        segments, _info = model.transcribe(str(path), language=language, word_timestamps=True,
                                           vad_filter=True, beam_size=5)
        return [Word(round(w.start, 2), round(w.end, 2), w.word.strip())
                for seg in segments for w in (seg.words or []) if w.word.strip()]

    return run


def transcribe_cached(media: Path, transcriber: Transcriber, *, cache_root: Path,
                      model_name: str) -> list[Word]:
    path = Path(cache_root) / f"{sha256_file(media)}__{model_name}.json"
    if path.exists():
        return [Word(**w) for w in json.loads(path.read_text())]
    words = transcriber(Path(media))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(w) for w in words], ensure_ascii=False))
    return words


def _text(words: list[Word]) -> str:
    return normalize(" ".join(w.text for w in words))


def _best_window(quote: str, words: list[Word], center: float, window_s: float) -> tuple[float, int, int]:
    n = max(1, len(quote.split()))
    best, best_dist = (0.0, -1, -1), float("inf")
    for i, w in enumerate(words):
        dist = abs(w.t_start - center)
        if dist > window_s:
            continue
        j = min(len(words), i + n)
        score = fuzz.partial_ratio(quote, _text(words[i:j]))
        if score > best[0] or (score == best[0] and dist < best_dist):
            best, best_dist = (score, i, j), dist
    return best


def _spoken_span(spoken: str, span: list[Word]) -> tuple[int, int] | None:
    k = max(1, len(spoken.split()))
    best: tuple[float, int, int] = (0.0, 0, 0)
    for size in (k, k + 1):
        for i in range(0, max(0, len(span) - size) + 1):
            score = fuzz.ratio(spoken, _text(span[i:i + size]))
            if score > best[0]:
                best = (score, i, min(len(span), i + size))
    return (best[1], best[2]) if best[0] >= SPOKEN_MIN_RATIO else None


def realign(occs: list[AbsOccurrence], words: list[Word], *, window_s: float = 30.0,
            threshold: float = 80.0) -> list[AbsOccurrence]:
    if not words:
        return occs
    for o in occs:
        if o.muse.source is not Source.speech:
            continue
        quote = normalize(o.muse.evidence_quote) or normalize(o.muse.spoken)
        if not quote:
            continue
        score, i, j = _best_window(quote, words, o.t_start, window_s)
        if score < threshold or i < 0:
            continue
        span = words[i:j]
        sub = _spoken_span(normalize(o.muse.spoken), span)
        first, last = (span[sub[0]], span[sub[1] - 1]) if sub else (span[0], span[-1])
        o.t_start, o.t_end = first.t_start, last.t_end
        o.time_source, o.asr_score = TimeSource.asr, round(score, 1)
    return occs
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest tests/test_transcribe.py -q`
Expected: `7 passed`. Kalau `test_realign_moves_shifted_speech_to_asr_time` meleset di batas sub-rentang (mis. dapat `162.0`), periksa `_spoken_span`: "watera gelas" (2 kata) harus mengalahkan "watera" (81,8 vs 75).

- [ ] **Step 6: Cek manual whisper pada satu video** (tidak di tes; mengunduh model ~480 MB sekali)

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
time uv run python -c "
from pathlib import Path
from empu.pipeline.transcribe import whisper_transcriber
words = whisper_transcriber('small')(Path('../data/runs/macam-canting/media/display.mp4'))
print(len(words)); print(' '.join(w.text for w in words[:60]))"
```
Expected: ratusan kata, teks bahasa Indonesia yang bisa dibaca. Catat waktu proses (target ≤ 1 menit untuk 246 s). Kalau kualitasnya buruk (kata acak), coba `medium` dan catat waktunya. Nilai yang dipilih ditulis ke `.env` sebagai `EMPU_TRANSCRIBE_MODEL` dan ke `hasil-gate1.md`.

- [ ] **Step 7: Commit**

```bash
git add api/pyproject.toml api/uv.lock api/empu/pipeline/transcribe.py api/tests/test_transcribe.py
git commit -m "feat(pipeline): Mode B realign with faster-whisper word timestamps"
```

---

### Task H2-5: Media bukti (`evidence.py`)

**Files:**
- Create: `api/empu/pipeline/evidence.py`
- Test: `api/tests/test_evidence.py`

**Interfaces:**
- Consumes: `ffmpeg_to`, `has_audio`
- Produces:
  - `clip_window(t_start: float, t_end: float, duration_s: float) -> tuple[float, float]`
  - `EvidencePaths(clip: Path, audio: Path | None, keyframe: Path, clip_start: float, clip_end: float)`
  - `extract_keyframe(display: Path, t: float, dst: Path) -> Path`
  - `make_evidence(display: Path, t_start: float, t_end: float, duration_s: float, out_dir: Path) -> EvidencePaths` (file: `clip.mp4`, `audio.m4a`, `keyframe.jpg`; file yang sudah ada tidak dibuat ulang)

Aturan `clip_window`: `[t_start − 1,0 ; t_end + 1,5]`. Kalau lebih dari 8 s, potong ujungnya (awal ucapan dipertahankan). Kalau kurang dari 3 s, lebarkan rata di kedua sisi. Lalu geser ke dalam `[0, durasi]`. Kalau durasi video < 3 s, hasilnya seluruh video.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_evidence.py
import pytest

from conftest import requires_ffmpeg
from empu.pipeline.evidence import clip_window, make_evidence
from empu.pipeline.ffmpeg import has_audio, probe_duration


@pytest.mark.parametrize("t0, t1, dur, expected", [
    (10, 11, 100, (9.0, 12.5)),
    (10, 10, 100, (8.75, 11.75)),
    (10, 20, 100, (9.0, 17.0)),
    (0.2, 0.5, 100, (0.0, 3.0)),
    (11.5, 11.8, 12, (9.0, 12.0)),
    (0.5, 1.0, 2, (0.0, 2.0)),
])
def test_clip_window(t0, t1, dur, expected):
    assert clip_window(t0, t1, dur) == expected


@requires_ffmpeg
def test_make_evidence(sample_video, tmp_path):
    ev = make_evidence(sample_video, 5.0, 6.0, 12.0, tmp_path / "occ")
    assert (ev.clip_start, ev.clip_end) == (4.0, 7.5)
    assert abs(probe_duration(ev.clip) - 3.5) < 0.3
    assert ev.audio is not None and has_audio(ev.audio)
    assert ev.keyframe.stat().st_size > 1000
    before = ev.clip.stat().st_mtime_ns
    make_evidence(sample_video, 5.0, 6.0, 12.0, tmp_path / "occ")
    assert ev.clip.stat().st_mtime_ns == before
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_evidence.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.pipeline.evidence'`.

- [ ] **Step 3: Tulis `api/empu/pipeline/evidence.py`**

```python
"""Evidence media per occurrence, cut from display.mp4 (spec 8.7). Original frames only."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from empu.pipeline.ffmpeg import ffmpeg_to, has_audio

PRE_S, POST_S, MIN_S, MAX_S = 1.0, 1.5, 3.0, 8.0


def clip_window(t_start: float, t_end: float, duration_s: float) -> tuple[float, float]:
    a, b = t_start - PRE_S, max(t_end, t_start) + POST_S
    if b - a > MAX_S:
        b = a + MAX_S
    if b - a < MIN_S:
        pad = (MIN_S - (b - a)) / 2
        a, b = a - pad, b + pad
    if a < 0:
        a, b = 0.0, b - a
    if b > duration_s:
        a, b = max(0.0, a - (b - duration_s)), duration_s
    return round(a, 3), round(b, 3)


@dataclass(frozen=True)
class EvidencePaths:
    clip: Path
    audio: Path | None
    keyframe: Path
    clip_start: float
    clip_end: float


def extract_keyframe(display: Path, t: float, dst: Path) -> Path:
    if Path(dst).exists():
        return Path(dst)
    return ffmpeg_to(Path(dst), ["-ss", f"{max(0.0, t):.3f}", "-i", str(display),
                                 "-frames:v", "1", "-q:v", "2"])


def make_evidence(display: Path, t_start: float, t_end: float, duration_s: float,
                  out_dir: Path) -> EvidencePaths:
    out_dir = Path(out_dir)
    a, b = clip_window(t_start, t_end, duration_s)
    seek = ["-ss", f"{a:.3f}", "-i", str(display), "-t", f"{b - a:.3f}"]
    clip, audio, keyframe = out_dir / "clip.mp4", out_dir / "audio.m4a", out_dir / "keyframe.jpg"
    with_audio = has_audio(display)
    if not clip.exists():
        ffmpeg_to(clip, [*seek, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                         *(["-c:a", "aac", "-b:a", "128k"] if with_audio else ["-an"]),
                         "-movflags", "+faststart"])
    if with_audio and not audio.exists():
        ffmpeg_to(audio, [*seek, "-vn", "-c:a", "aac", "-b:a", "96k"])
    extract_keyframe(display, (t_start + t_end) / 2, keyframe)
    return EvidencePaths(clip, audio if with_audio else None, keyframe, a, b)
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_evidence.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/empu/pipeline/evidence.py api/tests/test_evidence.py
git commit -m "feat(pipeline): evidence clip, audio and keyframe per occurrence"
```

---

### Task H2-6: SAM 3.1 (`meta_client` + `ground.py`)

**Files:**
- Modify: `api/empu/meta_client.py`
- Modify: `api/tests/fakes.py` (`make_sam_raw`, SAM di `FakeClient`)
- Create: `api/empu/pipeline/ground.py`
- Test: `api/tests/test_sam.py`, `api/tests/test_ground.py`

**Interfaces:**
- Consumes: `create_response`, `output_text`, `ResponseCache`, `sha256_file`, `CraftPack.term()`
- Produces:
  - `parse_sam_boxes(text: str, label: str = "") -> list[Detection]`. `Detection.bbox_xyxy` **dinormalisasi 0–1** terhadap `w`×`h` yang dilaporkan SAM; `score=1.0` (SAM tidak mengirim skor); `mask_png_bytes=None` (mask belum dipecahkan, keputusan Gate 0)
  - `MetaClient.segment_image_raw(image_path: Path, prompt: str, *, model: str) -> dict`; `MetaClient.segment_image(image_path, prompts, *, model) -> list[Detection]` (satu panggilan per prompt)
  - `FakeClient(responses=None, detections=None, sam=None)` dengan `sam: dict[str, dict]` (prompt → respons mentah); `segment_image_raw` mencatat `sam_calls` dan mengembalikan respons tanpa kotak kalau prompt tidak dikenal; `make_sam_raw(boxes: list[tuple[int,int,int,int]], w=854, h=480) -> dict`
  - `sam_prompts_for(pack, *, pack_term_id: str | None, is_novel: bool, visible_object_en: str | None) -> list[str]`
  - `crop_box(size: tuple[int, int], bbox: tuple[float, float, float, float], pad: float = 0.15) -> tuple[int, int, int, int]`
  - `GroundResult(status: SamStatus, prompt_used: str | None, detections: list[Detection], crop_path: Path | None, overlay_path: Path | None, error: str | None = None)`
  - `ground_keyframe(client, cache, keyframe: Path, prompts: list[str], out_dir: Path, *, model: str) -> GroundResult` (file `crop.png`, `overlay.jpg`)

Aturan:
- Prompt dicoba berurutan; berhenti pada prompt pertama yang menghasilkan kotak (Gate 0: deskripsi Inggris berhasil, istilah lokal gagal).
- Dari beberapa kotak, pilih yang **terluas**. Overlay menggambar semua kotak (tipis) dan yang terpilih (tebal).
- Respons SAM di-cache dengan kunci `ResponseCache.key(sha256(keyframe), model, "sam-" + sha1(prompt)[:10], "img")`.
- `skipped` kalau tidak ada prompt (istilah non-visual, tahap, atau istilah baru tanpa `visible_object_en`). `empty` kalau tidak ada kotak. `error` untuk error API atau gambar.

- [ ] **Step 1: Tambahkan SAM palsu ke `api/tests/fakes.py`**

```python
def make_sam_raw(boxes, w: int = 854, h: int = 480) -> dict:
    text = "<0f>0" + "".join(f"<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={w};h={h}|><|mask;x=0;y=0;data=x|>"
                             for x1, y1, x2, y2 in boxes)
    return make_raw(text, usage={"input_tokens": 0, "output_tokens": 0, "images_processed": 1})
```

Ubah `FakeClient.__init__` menerima `sam: dict[str, dict] | None = None` (simpan `self.sam = sam or {}`) dan tambahkan metode:

```python
    def segment_image_raw(self, image_path: Path, prompt: str, *, model: str) -> dict:
        self.sam_calls.append((Path(image_path), [prompt]))
        return self.sam.get(prompt, make_sam_raw([]))
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_sam.py
import json

import httpx
import respx

from conftest import load_fixture
from empu.meta_client import MetaClient, output_text, parse_sam_boxes

BASE = "https://api.test/v1"


def test_parse_row_fixture_four_boxes():
    raw = load_fixture("sam/sam-canting-row.raw.json")["response"]
    dets = parse_sam_boxes(output_text(raw), label="wooden stick with copper tip")
    assert len(dets) == 4
    assert dets[0].label == "wooden stick with copper tip" and dets[0].score == 1.0
    x1, y1, x2, y2 = dets[3].bbox_xyxy
    assert (round(x1 * 854), round(y1 * 480), round(x2 * 854), round(y2 * 480)) == (553, 265, 736, 425)


def test_parse_ignores_degenerate_and_garbage():
    text = "<|box;x1=5;y1=5;x2=5;y2=9;w=10;h=10|> junk <|box;x1=1;y1=1;x2=4;y2=4;w=10;h=10|>"
    assert [d.bbox_xyxy for d in parse_sam_boxes(text)] == [(0.1, 0.1, 0.4, 0.4)]
    assert parse_sam_boxes("no boxes") == []


@respx.mock
def test_segment_image_raw_body(tmp_path):
    img = tmp_path / "k.jpg"
    img.write_bytes(b"\xff\xd8fakejpeg")
    raw = load_fixture("sam/sam-canting-closeup.raw.json")["response"]
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    client = MetaClient("k", BASE, backoff_s=0)
    dets = client.segment_image(img, ["pen with wooden handle"], model="sam-3.1")
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "sam-3.1" and body["stream"] is False
    content = body["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "pen with wooden handle"}
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")
    assert len(dets) == 1
```

```python
# api/tests/test_ground.py
import pytest
from PIL import Image

from empu.cache import ResponseCache
from empu.enums import SamStatus
from empu.meta_client import MetaAPIError
from empu.pipeline.ground import crop_box, ground_keyframe, sam_prompts_for
from fakes import FakeClient, make_sam_raw


@pytest.fixture
def keyframe(tmp_path):
    p = tmp_path / "keyframe.jpg"
    Image.new("RGB", (854, 480), (120, 90, 60)).save(p)
    return p


def test_sam_prompts_for(pack):
    assert sam_prompts_for(pack, pack_term_id="canting", is_novel=False, visible_object_en="x") == [
        "wooden stick with copper tip", "pen with wooden handle"]
    assert sam_prompts_for(pack, pack_term_id="waterglass", is_novel=False, visible_object_en="jar") == []
    assert sam_prompts_for(pack, pack_term_id=None, is_novel=True, visible_object_en="small bowl") == ["small bowl"]
    assert sam_prompts_for(pack, pack_term_id=None, is_novel=True, visible_object_en=None) == []
    assert sam_prompts_for(pack, pack_term_id=None, is_novel=False, visible_object_en="pot") == []


def test_crop_box_pads_15_percent_and_clamps():
    bbox = (209 / 854, 135 / 480, 743 / 854, 340 / 480)
    assert crop_box((854, 480), bbox) == (128, 104, 823, 371)
    assert crop_box((100, 100), (0.0, 0.0, 1.0, 1.0)) == (0, 0, 100, 100)


def test_ground_tries_prompts_in_order_and_caches(tmp_path, keyframe):
    cache = ResponseCache(tmp_path / "sam-cache")
    client = FakeClient(sam={"second": make_sam_raw([(209, 135, 743, 340), (10, 10, 50, 50)])})
    res = ground_keyframe(client, cache, keyframe, ["first", "second", "third"], tmp_path / "e", model="sam-3.1")
    assert res.status is SamStatus.ok and res.prompt_used == "second" and len(res.detections) == 2
    assert [c[1] for c in client.sam_calls] == [["first"], ["second"]]
    with Image.open(res.crop_path) as im:
        assert im.size == (823 - 128, 371 - 104)
    assert res.overlay_path.exists()
    again = FakeClient()
    res2 = ground_keyframe(again, cache, keyframe, ["first", "second"], tmp_path / "e2", model="sam-3.1")
    assert res2.status is SamStatus.ok and again.sam_calls == []


def test_ground_empty_skipped_error(tmp_path, keyframe):
    cache = ResponseCache(tmp_path / "c")
    assert ground_keyframe(FakeClient(), cache, keyframe, ["x"], tmp_path / "e", model="m").status is SamStatus.empty
    assert ground_keyframe(FakeClient(), cache, keyframe, [], tmp_path / "e", model="m").status is SamStatus.skipped

    class Boom(FakeClient):
        def segment_image_raw(self, image_path, prompt, *, model):
            raise MetaAPIError(500, "sam down")

    res = ground_keyframe(Boom(), cache, keyframe, ["y"], tmp_path / "e", model="m")
    assert res.status is SamStatus.error and "500" in res.error and res.crop_path is None
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_sam.py tests/test_ground.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'parse_sam_boxes'`.

- [ ] **Step 4: Tambahkan ke `api/empu/meta_client.py`**

Tambahkan `import base64` di blok impor, lalu konstanta dan fungsi modul ini di bawah `extract_json`:

```python
_SAM_BOX = re.compile(
    r"<\|box;x1=([\d.]+);y1=([\d.]+);x2=([\d.]+);y2=([\d.]+);w=(\d+);h=(\d+)\|>")
_IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def parse_sam_boxes(text: str, label: str = "") -> list[Detection]:
    """SAM 3.1 returns one <|box;...|><|mask;...|> pair per instance, in pixels of w x h."""
    dets: list[Detection] = []
    for m in _SAM_BOX.finditer(text):
        x1, y1, x2, y2, w, h = map(float, m.groups())
        if w <= 0 or h <= 0 or x2 <= x1 or y2 <= y1:
            continue
        dets.append(Detection(label, 1.0, (x1 / w, y1 / h, x2 / w, y2 / h)))
    return dets
```

Dan dua metode di kelas `MetaClient` (di bawah `analyze_video`):

```python
    def segment_image_raw(self, image_path: Path, prompt: str, *, model: str) -> dict:
        path = Path(image_path)
        mime = _IMAGE_MIME.get(path.suffix.lower(), "image/jpeg")
        data_url = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
        body = {"model": model, "stream": False, "input": [{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": data_url},
        ]}]}
        return self.create_response(body, timeout=120)

    def segment_image(self, image_path: Path, prompts: list[str], *, model: str) -> list[Detection]:
        dets: list[Detection] = []
        for prompt in prompts:
            raw = self.segment_image_raw(image_path, prompt, model=model)
            dets += parse_sam_boxes(output_text(raw), prompt)
        return dets
```

- [ ] **Step 5: Tulis `api/empu/pipeline/ground.py`**

```python
"""SAM 3.1 grounding on one keyframe. Bounding box only (Gate 0); crop = bbox + 15% padding."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw

from empu.cache import ResponseCache, sha256_file
from empu.enums import SamStatus
from empu.meta_client import Detection, MetaAPIError, output_text, parse_sam_boxes
from empu.packs import CraftPack

PAD = 0.15


@dataclass
class GroundResult:
    status: SamStatus
    prompt_used: str | None
    detections: list[Detection] = field(default_factory=list)
    crop_path: Path | None = None
    overlay_path: Path | None = None
    error: str | None = None


def sam_prompts_for(pack: CraftPack, *, pack_term_id: str | None, is_novel: bool,
                    visible_object_en: str | None) -> list[str]:
    if pack_term_id:
        t = pack.term(pack_term_id)
        if t is None or not t.visual or not t.sam_prompt:
            return []
        return [p.strip() for p in t.sam_prompt.split(",") if p.strip()]
    if is_novel and visible_object_en and visible_object_en.strip():
        return [visible_object_en.strip()]
    return []


def crop_box(size: tuple[int, int], bbox: tuple[float, float, float, float],
             pad: float = PAD) -> tuple[int, int, int, int]:
    w, h = size
    x1, y1, x2, y2 = bbox[0] * w, bbox[1] * h, bbox[2] * w, bbox[3] * h
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    return (max(0, int(x1 - px)), max(0, int(y1 - py)), min(w, round(x2 + px)), min(h, round(y2 + py)))


def _area(d: Detection) -> float:
    x1, y1, x2, y2 = d.bbox_xyxy
    return (x2 - x1) * (y2 - y1)


def _raw_for(client: Any, cache: ResponseCache, keyframe: Path, sha: str, prompt: str, model: str) -> dict:
    key = ResponseCache.key(sha, model, "sam-" + hashlib.sha1(prompt.encode()).hexdigest()[:10], "img")
    if (hit := cache.get(key)) is not None:
        return hit["raw"]
    raw = client.segment_image_raw(keyframe, prompt, model=model)
    cache.put(key, {"raw": raw, "prompt": prompt, "model": model})
    return raw


def ground_keyframe(client: Any, cache: ResponseCache, keyframe: Path, prompts: list[str], out_dir: Path,
                    *, model: str) -> GroundResult:
    if not prompts:
        return GroundResult(SamStatus.skipped, None)
    try:
        sha = sha256_file(keyframe)
        used, dets = None, []
        for prompt in prompts:
            dets = parse_sam_boxes(output_text(_raw_for(client, cache, keyframe, sha, prompt, model)), prompt)
            if dets:
                used = prompt
                break
        if not dets:
            return GroundResult(SamStatus.empty, None)
        chosen = max(dets, key=_area)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        crop_path, overlay_path = out_dir / "crop.png", out_dir / "overlay.jpg"
        with Image.open(keyframe) as src:
            im = src.convert("RGB")
        im.crop(crop_box(im.size, chosen.bbox_xyxy)).save(crop_path)
        draw = ImageDraw.Draw(im)
        w, h = im.size
        for d in dets:
            x1, y1, x2, y2 = d.bbox_xyxy
            draw.rectangle([x1 * w, y1 * h, x2 * w, y2 * h], outline=(255, 196, 0),
                           width=6 if d is chosen else 2)
        im.save(overlay_path, quality=88)
        return GroundResult(SamStatus.ok, used, dets, crop_path, overlay_path)
    except (MetaAPIError, httpx.HTTPError, OSError) as e:
        return GroundResult(SamStatus.error, None, error=str(e)[:500])
```

- [ ] **Step 6: Jalankan tes**

Run: `cd api && uv run pytest tests/test_sam.py tests/test_ground.py tests/test_meta_client.py -q`
Expected: semua lulus.

- [ ] **Step 7: Commit**

```bash
git add api/empu/meta_client.py api/empu/pipeline/ground.py api/tests
git commit -m "feat(pipeline): SAM 3.1 bbox grounding with cache, crop and overlay"
```

---

### Task H2-7: Persistensi hasil ke DB (`persist.py`)

**Files:**
- Create: `api/empu/persist.py`
- Test: `api/tests/test_persist.py`

**Interfaces:**
- Consumes: `EntryDraft`, `AbsOccurrence`, `StepDraft`, `occurrence_rank`, model DB
- Produces:
  - `find_entry(session, archive_id: int, canon_key: str) -> Entry | None` (mengikuti `merged_into_id` sampai entri tujuan)
  - `choose_best(occs: list[Occurrence]) -> Occurrence | None` (abaikan yang `rejected` kalau masih ada yang lain)
  - `clear_recording(session, recording_id: int) -> set[int]` (hapus kemunculan dan tahapan rekaman ini; kembalikan id entri yang tersentuh)
  - `persist_results(session, recording: Recording, drafts: list[EntryDraft], steps: list[StepDraft], chunk_ids: dict[int, int]) -> list[Entry]` (commit; mengembalikan entri yang menerima kemunculan dari rekaman ini)

Aturan:
- **Idempoten per rekaman.** Proses ulang menghapus kemunculan dan tahapan lama rekaman itu dulu, lalu menulis yang baru.
- Satu entri per `canon_key` per arsip. Kemunculan dari rekaman baru masuk ke entri yang sudah ada (kamus tumbuh). Entri `merged` diikuti ke tujuannya.
- Entri baru: `status=proposed`, `access_level = recording.consent_scope`.
- Entri yang sudah ditinjau (`accepted`/`edited`/`rejected`) **tidak diubah isinya**. Hanya kemunculannya bertambah, dan `best_occurrence_id` dihitung ulang.
- Entri `proposed` lama yang tidak punya kemunculan lagi dan belum punya `review_event` dihapus. Entri yang sudah ditinjau tetap ada (tersembunyi dari publik karena tidak punya kemunculan).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_persist.py
from sqlmodel import select

from empu.enums import AccessLevel, EntryStatus, ReviewAction, Source
from empu.models import Entry, Occurrence, ProcessStep, ReviewEvent
from empu.persist import find_entry, persist_results
from empu.pipeline.merge import merge_analyses
from empu.pipeline.process_map import build_process_map
from factories import make_archive, make_recording
from fakes import analysis, muse_term


def drafts_and_steps(pack, terms, steps=()):
    a = analysis(0, 0, 75, terms=terms, steps=steps)
    s = build_process_map([a], pack)
    return merge_analyses([a], pack, steps=s), s


TERMS = [muse_term(term="canting", source="speech", t_start=2, t_end=3, confidence="high"),
         muse_term(term="tjanting", source="on_screen_text", t_start=9, t_end=10),
         muse_term(term="bethik", source="speech", t_start=5, t_end=6)]


def test_persist_creates_entries_occurrences_steps(session, pack):
    a = make_archive(session)
    r = make_recording(session, a, consent_scope=AccessLevel.community)
    drafts, steps = drafts_and_steps(pack, TERMS, [{"step": "nglowong", "t_start": 0, "t_end": 75, "tools": []}])
    entries = persist_results(session, r, drafts, steps, {0: 77})
    assert {e.canon_key for e in entries} == {"term:canting", "novel:bethik"}
    canting = find_entry(session, a.id, "term:canting")
    occs = session.exec(select(Occurrence).where(Occurrence.entry_id == canting.id)).all()
    assert len(occs) == 2 and {o.chunk_id for o in occs} == {77}
    best = session.get(Occurrence, canting.best_occurrence_id)
    assert best.source is Source.speech and best.stage_id == "nglowong"
    assert canting.access_level is AccessLevel.community and canting.status is EntryStatus.proposed
    assert session.exec(select(ProcessStep)).one().pack_stage_id == "nglowong"


def test_reprocess_replaces_and_cleans_orphans(session, pack):
    a = make_archive(session)
    r = make_recording(session, a)
    drafts, steps = drafts_and_steps(pack, TERMS)
    persist_results(session, r, drafts, steps, {})
    drafts2, steps2 = drafts_and_steps(pack, TERMS[:2])
    persist_results(session, r, drafts2, steps2, {})
    assert len(session.exec(select(Occurrence)).all()) == 2
    assert find_entry(session, a.id, "novel:bethik") is None


def test_reviewed_entry_survives_and_keeps_fields(session, pack):
    a = make_archive(session)
    r = make_recording(session, a)
    drafts, steps = drafts_and_steps(pack, TERMS)
    persist_results(session, r, drafts, steps, {})
    e = find_entry(session, a.id, "novel:bethik")
    e.status, e.gloss_en = EntryStatus.edited, "corrected by the expert"
    session.add(ReviewEvent(entry_id=e.id, action=ReviewAction.edit, actor="x"))
    session.commit()
    drafts2, steps2 = drafts_and_steps(pack, TERMS[:2])
    persist_results(session, r, drafts2, steps2, {})
    e = session.get(Entry, e.id)
    assert e.status is EntryStatus.edited and e.gloss_en == "corrected by the expert"
    assert e.best_occurrence_id is None


def test_second_recording_appends_to_same_entry(session, pack):
    a = make_archive(session)
    r1, r2 = make_recording(session, a), make_recording(session, a)
    for r in (r1, r2):
        drafts, steps = drafts_and_steps(pack, TERMS[:1])
        persist_results(session, r, drafts, steps, {})
    e = find_entry(session, a.id, "term:canting")
    recs = {o.recording_id for o in session.exec(select(Occurrence).where(Occurrence.entry_id == e.id))}
    assert recs == {r1.id, r2.id}


def test_find_entry_follows_merge(session, pack):
    a = make_archive(session)
    target = Entry(archive_id=a.id, canon_key="term:canting", term="canting", category="tool")
    session.add(target)
    session.commit()
    src = Entry(archive_id=a.id, canon_key="novel:tjantingan", term="tjantingan", category="tool",
                status=EntryStatus.merged, merged_into_id=target.id)
    session.add(src)
    session.commit()
    assert find_entry(session, a.id, "novel:tjantingan").id == target.id
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_persist.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.persist'`.

- [ ] **Step 3: Tulis `api/empu/persist.py`**

```python
"""Write merged pipeline output for one recording into the DB. Idempotent per recording."""

from __future__ import annotations

from sqlmodel import Session, col, select

from empu.enums import EntryStatus, OccurrenceStatus
from empu.models import Entry, Occurrence, ProcessStep, Recording, ReviewEvent, utcnow
from empu.pipeline.merge import AbsOccurrence, EntryDraft, occurrence_rank
from empu.pipeline.process_map import StepDraft


def find_entry(session: Session, archive_id: int, canon_key: str) -> Entry | None:
    entry = session.exec(select(Entry).where(Entry.archive_id == archive_id,
                                             Entry.canon_key == canon_key)).first()
    seen: set[int] = set()
    while (entry is not None and entry.status is EntryStatus.merged and entry.merged_into_id
           and entry.id not in seen):
        seen.add(entry.id)
        entry = session.get(Entry, entry.merged_into_id)
    return entry


def choose_best(occs: list[Occurrence]) -> Occurrence | None:
    live = [o for o in occs if o.status is not OccurrenceStatus.rejected] or occs
    return max(live, key=lambda o: occurrence_rank(o.source, o.visual_match, o.confidence,
                                                   o.t_end - o.t_start), default=None)


def _row(entry_id: int, recording_id: int, chunk_id: int | None, o: AbsOccurrence) -> Occurrence:
    m = o.muse
    return Occurrence(
        entry_id=entry_id, recording_id=recording_id, chunk_id=chunk_id, spoken=m.spoken,
        term_raw=m.term, source=m.source, t_start=round(o.t_start, 2), t_end=round(o.t_end, 2),
        time_source=o.time_source, asr_score=o.asr_score, stage_raw=m.stage, stage_id=o.stage_id,
        visible=m.visible, visible_object_en=m.visible_object_en, visual_match=m.visual_match,
        gloss_raw=m.gloss_id, gloss_en_raw=m.gloss_en, evidence_quote=m.evidence_quote,
        confidence=m.confidence)


def refresh_best(session: Session, entry: Entry) -> None:
    occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == entry.id)))
    best = choose_best(occs)
    entry.best_occurrence_id = best.id if best else None
    entry.updated_at = utcnow()
    session.add(entry)


def clear_recording(session: Session, recording_id: int) -> set[int]:
    occs = list(session.exec(select(Occurrence).where(Occurrence.recording_id == recording_id)))
    occ_ids = [o.id for o in occs]
    if occ_ids:
        for e in session.exec(select(Entry).where(col(Entry.best_occurrence_id).in_(occ_ids))):
            e.best_occurrence_id = None
            session.add(e)
    for o in occs:
        session.delete(o)
    for s in session.exec(select(ProcessStep).where(ProcessStep.recording_id == recording_id)):
        session.delete(s)
    session.flush()
    return {o.entry_id for o in occs}


def persist_results(session: Session, recording: Recording, drafts: list[EntryDraft],
                    steps: list[StepDraft], chunk_ids: dict[int, int]) -> list[Entry]:
    previous = clear_recording(session, recording.id)
    touched: dict[int, Entry] = {}
    for d in drafts:
        entry = find_entry(session, recording.archive_id, d.canon.canon_key)
        if entry is None:
            entry = Entry(archive_id=recording.archive_id, canon_key=d.canon.canon_key, term=d.canon.term,
                          category=d.category, stage_id=d.stage_id, gloss_id=d.gloss_id, gloss_en=d.gloss_en,
                          variants_json=d.variants, pack_term_id=d.canon.pack_term_id,
                          is_novel=d.canon.is_novel, access_level=recording.consent_scope)
            session.add(entry)
            session.flush()
        elif entry.status is EntryStatus.proposed:
            entry.variants_json = sorted(set(entry.variants_json) | set(d.variants), key=str.casefold)
            session.add(entry)
        for o in d.occurrences:
            session.add(_row(entry.id, recording.id, chunk_ids.get(o.chunk_idx), o))
        touched[entry.id] = entry
    session.flush()
    for entry in touched.values():
        refresh_best(session, entry)
    for entry_id in previous - touched.keys():
        entry = session.get(Entry, entry_id)
        if entry is None:
            continue
        has_occ = session.exec(select(Occurrence.id).where(Occurrence.entry_id == entry_id)).first()
        has_events = session.exec(select(ReviewEvent.id).where(ReviewEvent.entry_id == entry_id)).first()
        if has_occ is None and entry.status is EntryStatus.proposed and has_events is None:
            session.delete(entry)
        else:
            refresh_best(session, entry)
    for i, s in enumerate(steps):
        session.add(ProcessStep(recording_id=recording.id, pack_stage_id=s.pack_stage_id, name_raw=s.name_raw,
                                t_start=round(s.t_start, 2), t_end=round(s.t_end, 2), tools_json=s.tools,
                                order=i))
    session.commit()
    return list(touched.values())
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_persist.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/empu/persist.py api/tests/test_persist.py
git commit -m "feat(db): idempotent persistence of merged entries per recording"
```

---

### Task H2-8: Orkestrator (`pipeline/run.py`)

**Files:**
- Create: `api/empu/pipeline/run.py`
- Test: `api/tests/test_run.py`

**Interfaces:**
- Consumes: semua modul H1 sampai H2-7
- Produces:
  - `JOB_STAGES: tuple[JobStatus, ...] = (normalizing, chunking, analyzing, merging, grounding, cutting)`
  - `PipelineError(RuntimeError)`
  - `StageTracker(session, job)` dengan `stage(status)` (context manager; menulis `timings_json[<stage>] = {started_at, finished_at, seconds}`) dan `update(frac: float, detail: str | None = None)`
  - `process_recording(session, job_id: int, *, client, settings, transcriber: Transcriber | None = None) -> None` (tidak melempar; kegagalan ditulis ke `job.status=failed`, `job.error="<stage>: <Type>: <pesan>"`)
  - `job.usage_json = {"muse": {input_tokens, output_tokens, reasoning_tokens}, "cached_chunks": n, "entries": n, "novel": n, "occurrences": n, "asr_retimed": n, "sam": {ok, empty, error, skipped}, "warnings": [...]}`

Urutan tahap (D7):
1. `normalizing`: `normalize_recording` → `analysis.mp4`, `display.mp4`, `duration_s`.
2. `chunking`: `plan_chunks` + `cut_chunks`, baris `chunk` di-upsert per `idx`.
3. `analyzing`: Mode B memulai transkripsi `display.mp4` di thread terpisah **bersamaan** dengan analisis Muse. Progres "segment i/n". Kalau ada segmen gagal → `PipelineError` (segmen yang sudah berhasil sudah di-cache, jadi coba lagi murah). Kalau transkripsi gagal, Mode B turun ke waktu Muse dan dicatat di `warnings`.
4. `merging`: folder `occurrences/` rekaman ini dihapus dulu (id kemunculan bisa dipakai ulang SQLite setelah penghapusan, jadi file lama tidak boleh dianggap milik kemunculan baru), lalu `build_process_map` → `merge_analyses` (dengan `realign` kalau ada transkrip) → `persist_results`.
5. `grounding`: untuk setiap entri tersentuh yang `best_occurrence`-nya dari rekaman ini: ekstrak keyframe kemunculan itu, lalu SAM (kalau `settings.sam_enabled` dan ada prompt). Selain itu `sam_status=skipped` dan UI memakai keyframe.
6. `cutting`: klip, audio, keyframe untuk semua kemunculan rekaman ini (keyframe yang sudah ada tidak dibuat ulang).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_run.py
import shutil

import pytest
from sqlmodel import select

from conftest import requires_ffmpeg
from empu.enums import JobStatus, PipelineMode, SamStatus, TimeSource
from empu.media import abs_from_rel, recording_dir, rel_to_data
from empu.models import Chunk, Entry, Job, Occurrence, ProcessStep, Recording
from empu.pipeline.run import JOB_STAGES, process_recording
from empu.pipeline.transcribe import Word
from factories import make_archive, make_recording
from fakes import FakeClient, make_raw, make_sam_raw, muse_term

PAYLOAD = {
    "speech_heard": True, "language_notes": "id", "transcript_excerpt": "ini canting",
    "terms": [
        muse_term(term="canting", spoken="canting", source="speech", t_start=2.0, t_end=2.8, stage="nglowong",
                  evidence_quote="ini namanya canting", visual_match="yes", confidence="high",
                  gloss_id="alat menorehkan lilin", gloss_en="wax pen"),
        muse_term(term="canting", spoken="tjanting", source="on_screen_text", t_start=8.0, t_end=9.0),
        muse_term(term="bethik", spoken="bethik", source="speech", t_start=5.0, t_end=5.5,
                  visible_object_en="small black bowl", visual_match="yes",
                  evidence_quote="ini namanya bethik kecil"),
    ],
    "process_steps": [{"step": "nglowong", "t_start": 0, "t_end": 12, "tools": ["canting"]}],
}
SAM = {"wooden stick with copper tip": make_sam_raw([(209, 135, 743, 340)], w=1280, h=720)}


@pytest.fixture
def job_for(session, settings, sample_video):
    def make(mode=PipelineMode.A):
        a = make_archive(session)
        r = make_recording(session, a)
        dst = recording_dir(settings.data_dir, a.id, r.id) / "original.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(sample_video, dst)
        r.original_path = rel_to_data(settings.data_dir, dst)
        job = Job(recording_id=r.id, mode=mode, model=settings.muse_model, prompt_version="analyze-v3")
        session.add_all([r, job])
        session.commit()
        return job
    return make


def entries(session):
    return {e.canon_key: e for e in session.exec(select(Entry))}


@requires_ffmpeg
def test_end_to_end_mode_a(session, settings, job_for):
    job = job_for()
    process_recording(session, job.id, client=FakeClient([make_raw(PAYLOAD)], sam=SAM), settings=settings)
    session.refresh(job)
    assert job.status is JobStatus.ready, job.error
    assert job.progress == 1.0 and set(job.timings_json) >= {s.value for s in JOB_STAGES}
    rec = session.get(Recording, job.recording_id)
    assert rec.status is JobStatus.ready and abs(rec.duration_s - 12) < 0.5
    assert session.exec(select(Chunk)).one().status == "done"
    es = entries(session)
    assert set(es) == {"term:canting", "novel:bethik"}
    canting = es["term:canting"]
    assert canting.sam_status is SamStatus.ok and abs_from_rel(settings.data_dir, canting.crop_path).exists()
    assert canting.sam_prompt == "wooden stick with copper tip"
    assert es["novel:bethik"].sam_status is SamStatus.empty and es["novel:bethik"].is_novel
    occs = session.exec(select(Occurrence)).all()
    assert len(occs) == 3
    for o in occs:
        for p in (o.clip_path, o.audio_path, o.keyframe_path):
            assert abs_from_rel(settings.data_dir, p).exists()
    assert session.exec(select(ProcessStep)).one().pack_stage_id == "nglowong"
    assert job.usage_json["entries"] == 2 and job.usage_json["sam"]["ok"] == 1


@requires_ffmpeg
def test_reprocess_uses_cache_and_does_not_duplicate(session, settings, job_for):
    job = job_for()
    process_recording(session, job.id, client=FakeClient([make_raw(PAYLOAD)], sam=SAM), settings=settings)
    again = Job(recording_id=job.recording_id, mode=PipelineMode.A, model=settings.muse_model)
    session.add(again)
    session.commit()
    client = FakeClient([])
    process_recording(session, again.id, client=client, settings=settings)
    session.refresh(again)
    assert again.status is JobStatus.ready, again.error
    assert client.uploads == [] and client.sam_calls == []
    assert len(session.exec(select(Occurrence)).all()) == 3 and len(entries(session)) == 2


@requires_ffmpeg
def test_mode_b_realigns_speech(session, settings, job_for):
    job = job_for(PipelineMode.B)
    words = [Word(9.8, 10.0, "ini"), Word(10.0, 10.3, "namanya"), Word(10.4, 10.9, "bethik"),
             Word(11.0, 11.3, "kecil")]
    process_recording(session, job.id, client=FakeClient([make_raw(PAYLOAD)], sam=SAM), settings=settings,
                      transcriber=lambda path: words)
    session.refresh(job)
    assert job.status is JobStatus.ready, job.error
    o = session.exec(select(Occurrence).where(Occurrence.term_raw == "bethik")).one()
    assert (o.t_start, o.time_source) == (10.4, TimeSource.asr)
    assert job.usage_json["asr_retimed"] >= 1


@requires_ffmpeg
def test_invalid_muse_output_fails_job_cleanly(session, settings, job_for):
    job = job_for()
    process_recording(session, job.id, client=FakeClient([make_raw("x"), make_raw("y")]), settings=settings)
    session.refresh(job)
    assert job.status is JobStatus.failed and job.error.startswith("analyzing")
    assert session.get(Recording, job.recording_id).status is JobStatus.failed


@requires_ffmpeg
def test_sam_disabled_skips(session, settings, job_for):
    job = job_for()
    settings.sam_enabled = False
    client = FakeClient([make_raw(PAYLOAD)], sam=SAM)
    process_recording(session, job.id, client=client, settings=settings)
    assert client.sam_calls == [] and entries(session)["term:canting"].sam_status is SamStatus.skipped
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_run.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.pipeline.run'`.

- [ ] **Step 3: Tulis `api/empu/pipeline/run.py`**

```python
"""Pipeline orchestrator: one job through all stages, progress written to the job row (spec 8, D7)."""

from __future__ import annotations

import shutil
import time
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from empu.cache import ResponseCache
from empu.config import Settings
from empu.enums import ChunkStatus, JobStatus, PipelineMode, SamStatus, TimeSource
from empu.media import abs_from_rel, entry_dir, occurrence_dir, recording_dir, rel_to_data
from empu.models import Archive, Chunk, Entry, Job, Occurrence, Recording, utcnow
from empu.packs import CraftPack, load_pack
from empu.persist import persist_results
from empu.pipeline.analyze import AnalyzeOptions, ChunkAnalysis, analyze_chunks, usage_totals
from empu.pipeline.chunk import ChunkSpec, cut_chunks, plan_chunks
from empu.pipeline.evidence import extract_keyframe, make_evidence
from empu.pipeline.ffmpeg import has_audio
from empu.pipeline.ground import ground_keyframe, sam_prompts_for
from empu.pipeline.merge import merge_analyses
from empu.pipeline.normalize import normalize_recording
from empu.pipeline.process_map import build_process_map
from empu.pipeline.transcribe import Transcriber, Word, realign, transcribe_cached, whisper_transcriber

JOB_STAGES = (JobStatus.normalizing, JobStatus.chunking, JobStatus.analyzing, JobStatus.merging,
              JobStatus.grounding, JobStatus.cutting)
DEFAULT_ASR_MODEL = "small"


class PipelineError(RuntimeError):
    pass


class StageTracker:
    def __init__(self, session: Session, job: Job) -> None:
        self.session, self.job = session, job
        self.current: JobStatus | None = None
        self._t0 = 0.0

    def _commit(self) -> None:
        self.session.add(self.job)
        self.session.commit()

    def update(self, frac: float, detail: str | None = None) -> None:
        idx = JOB_STAGES.index(self.current) if self.current in JOB_STAGES else 0
        self.job.progress = round(min(1.0, (idx + max(0.0, min(1.0, frac))) / len(JOB_STAGES)), 3)
        if detail is not None:
            self.job.detail = detail
        self._commit()

    @contextmanager
    def stage(self, status: JobStatus) -> Iterator[None]:
        self.current, self._t0 = status, time.monotonic()
        self.job.status = status
        self.job.timings_json = {**self.job.timings_json,
                                 status.value: {"started_at": utcnow().isoformat(), "finished_at": None}}
        self.update(0.0, "")
        yield
        self.job.timings_json = {**self.job.timings_json, status.value: {
            **self.job.timings_json[status.value], "finished_at": utcnow().isoformat(),
            "seconds": round(time.monotonic() - self._t0, 1)}}
        self.update(1.0)


def _pack_for(session: Session, rec: Recording, settings: Settings) -> CraftPack:
    archive = session.get(Archive, rec.archive_id)
    if archive is None:
        raise PipelineError(f"archive {rec.archive_id} not found")
    return load_pack(archive.craft_pack_id, settings.packs_dir)


def _upsert_chunks(session: Session, rec: Recording, specs: list[ChunkSpec], paths: list[Path],
                   data_dir: Path) -> dict[int, Chunk]:
    existing = {c.idx: c for c in session.exec(select(Chunk).where(Chunk.recording_id == rec.id))}
    rows: dict[int, Chunk] = {}
    for spec, path in zip(specs, paths, strict=True):
        row = existing.pop(spec.idx, None) or Chunk(recording_id=rec.id, idx=spec.idx, start_s=0, end_s=0, path="")
        row.start_s, row.end_s, row.path = spec.start_s, spec.end_s, rel_to_data(data_dir, path)
        row.status, row.error = ChunkStatus.pending, None
        session.add(row)
        rows[spec.idx] = row
    for stale in existing.values():
        session.delete(stale)
    session.commit()
    return rows


def _store_chunk_results(session: Session, rows: dict[int, Chunk], results: list[ChunkAnalysis],
                         data_dir: Path) -> None:
    for r in results:
        row = rows[r.spec.idx]
        row.sha256, row.file_id, row.cached = r.sha256, r.file_id, r.cached
        row.status = ChunkStatus.failed if r.error else ChunkStatus.done
        row.error, row.usage_json, row.latency_s = r.error, r.usage, r.latency_s
        row.raw_path = rel_to_data(data_dir, r.raw_path) if r.raw_path else None
        row.parsed_path = rel_to_data(data_dir, r.parsed_path) if r.parsed_path else None
        session.add(row)
    session.commit()


def _ground(session: Session, rec: Recording, entries: list[Entry], display: Path, *, client: Any,
            settings: Settings, pack: CraftPack, tracker: StageTracker) -> Counter:
    sam_cache = ResponseCache(settings.data_dir / "cache" / "sam")
    counts: Counter = Counter()
    for i, entry in enumerate(entries, start=1):
        best = session.get(Occurrence, entry.best_occurrence_id) if entry.best_occurrence_id else None
        if best is None or best.recording_id != rec.id:
            continue
        odir = occurrence_dir(settings.data_dir, rec.archive_id, rec.id, best.id)
        keyframe = extract_keyframe(display, (best.t_start + best.t_end) / 2, odir / "keyframe.jpg")
        best.keyframe_path = rel_to_data(settings.data_dir, keyframe)
        prompts = sam_prompts_for(pack, pack_term_id=entry.pack_term_id, is_novel=entry.is_novel,
                                  visible_object_en=best.visible_object_en)
        if settings.sam_enabled and prompts:
            res = ground_keyframe(client, sam_cache, keyframe, prompts,
                                  entry_dir(settings.data_dir, rec.archive_id, entry.id), model=settings.sam_model)
            entry.sam_status, entry.sam_prompt = res.status, res.prompt_used or prompts[0]
            entry.crop_path = rel_to_data(settings.data_dir, res.crop_path) if res.crop_path else None
            entry.overlay_path = rel_to_data(settings.data_dir, res.overlay_path) if res.overlay_path else None
        else:
            entry.sam_status, entry.crop_path, entry.overlay_path = SamStatus.skipped, None, None
        counts[entry.sam_status.value] += 1
        session.add_all([best, entry])
        tracker.update(i / max(1, len(entries)), f"image {i}/{len(entries)}")
    session.commit()
    return counts


def _cut(session: Session, rec: Recording, display: Path, settings: Settings, tracker: StageTracker) -> int:
    occs = list(session.exec(select(Occurrence).where(Occurrence.recording_id == rec.id)
                             .order_by(Occurrence.t_start)))
    for i, o in enumerate(occs, start=1):
        ev = make_evidence(display, o.t_start, o.t_end, rec.duration_s or o.t_end,
                           occurrence_dir(settings.data_dir, rec.archive_id, rec.id, o.id))
        o.clip_path = rel_to_data(settings.data_dir, ev.clip)
        o.audio_path = rel_to_data(settings.data_dir, ev.audio) if ev.audio else None
        o.keyframe_path = rel_to_data(settings.data_dir, ev.keyframe)
        session.add(o)
        if i % 10 == 0 or i == len(occs):
            tracker.update(i / len(occs), f"clip {i}/{len(occs)}")
    session.commit()
    return len(occs)


def process_recording(session: Session, job_id: int, *, client: Any, settings: Settings,
                      transcriber: Transcriber | None = None) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise PipelineError(f"job {job_id} not found")
    rec = session.get(Recording, job.recording_id)
    tracker = StageTracker(session, job)
    job.started_at = job.started_at or utcnow()
    job.error, job.usage_json, job.timings_json = None, {}, {}
    rec.status = JobStatus.normalizing
    session.add(rec)
    usage: dict[str, Any] = {"warnings": []}
    try:
        pack = _pack_for(session, rec, settings)
        data_dir = settings.data_dir
        rec_dir = recording_dir(data_dir, rec.archive_id, rec.id)

        with tracker.stage(JobStatus.normalizing):
            media = normalize_recording(abs_from_rel(data_dir, rec.original_path), rec_dir)
            rec.display_path = rel_to_data(data_dir, media.display_path)
            rec.analysis_path = rel_to_data(data_dir, media.analysis_path)
            rec.duration_s = round(media.duration_s, 2)
            session.add(rec)

        with tracker.stage(JobStatus.chunking):
            specs = plan_chunks(media.duration_s, settings.chunk_window_s, settings.chunk_overlap_s)
            paths = cut_chunks(media.analysis_path, specs, rec_dir / "chunks")
            rows = _upsert_chunks(session, rec, specs, paths, data_dir)

        with tracker.stage(JobStatus.analyzing), ThreadPoolExecutor(max_workers=1) as pool:
            words_future: Future[list[Word]] | None = None
            if job.mode is PipelineMode.B and has_audio(media.display_path):
                model_name = settings.transcribe_model or DEFAULT_ASR_MODEL
                language = (rec.language_hint or "id").split(",")[0].strip() or "id"
                words_future = pool.submit(transcribe_cached, media.display_path,
                                           transcriber or whisper_transcriber(model_name, language),
                                           cache_root=data_dir / "cache" / "asr", model_name=model_name)
            done = 0

            def on_done(_: ChunkAnalysis) -> None:
                nonlocal done
                done += 1
                tracker.update(done / len(specs), f"segment {done}/{len(specs)}")

            opts = AnalyzeOptions(model=settings.muse_model, structured=settings.structured_output,
                                  schema_variant=settings.structured_schema_variant)
            results = analyze_chunks(client, ResponseCache(data_dir / "cache" / "muse"), pack,
                                     list(zip(specs, paths, strict=True)), opts, out_dir=rec_dir / "muse",
                                     concurrency=settings.analyze_concurrency, on_done=on_done)
            _store_chunk_results(session, rows, results, data_dir)
            usage["muse"] = usage_totals([r.usage for r in results if not r.cached])
            usage["cached_chunks"] = sum(r.cached for r in results)
            failed = [r for r in results if r.error]
            if failed:
                raise PipelineError(f"{len(failed)}/{len(results)} segments failed: "
                                    + "; ".join(f"#{r.spec.idx}: {r.error[:200]}" for r in failed))
            words: list[Word] = []
            if words_future is not None:
                try:
                    words = words_future.result()
                except Exception as e:  # noqa: BLE001  (ASR is an aid; Mode B degrades to Muse times)
                    usage["warnings"].append(f"transcription failed, using Muse times: {e}"[:300])

        with tracker.stage(JobStatus.merging):
            shutil.rmtree(rec_dir / "occurrences", ignore_errors=True)
            steps = build_process_map(results, pack)
            retime = (lambda occs: realign(occs, words)) if words else None
            drafts = merge_analyses(results, pack, steps=steps, retime=retime)
            touched = persist_results(session, rec, drafts, steps, {i: r.id for i, r in rows.items()})
            all_occs = [o for d in drafts for o in d.occurrences]
            usage |= {"entries": len(drafts), "novel": sum(d.canon.is_novel for d in drafts),
                      "occurrences": len(all_occs),
                      "asr_retimed": sum(o.time_source is TimeSource.asr for o in all_occs)}

        with tracker.stage(JobStatus.grounding):
            usage["sam"] = dict(_ground(session, rec, touched, media.display_path, client=client,
                                        settings=settings, pack=pack, tracker=tracker))

        with tracker.stage(JobStatus.cutting):
            _cut(session, rec, media.display_path, settings, tracker)

        job.status, job.progress, job.detail, job.finished_at = JobStatus.ready, 1.0, "ready", utcnow()
        job.usage_json = usage
        rec.status = JobStatus.ready
        session.add_all([job, rec])
        session.commit()
    except Exception as e:  # noqa: BLE001  (the worker must survive; the error is shown in S3)
        session.rollback()
        job = session.get(Job, job_id)
        rec = session.get(Recording, job.recording_id)
        stage = tracker.current.value if tracker.current else "setup"
        job.status, job.finished_at = JobStatus.failed, utcnow()
        job.error = f"{stage}: {type(e).__name__}: {e}"[:2000]
        job.usage_json = usage
        rec.status = JobStatus.failed
        session.add_all([job, rec])
        session.commit()
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_run.py -q`
Expected: `5 passed` (sekitar 10–20 detik karena ffmpeg). Kalau `test_end_to_end_mode_a` gagal dengan `sam_status=empty` untuk canting, cek bahwa kunci `SAM` di tes sama persis dengan prompt pertama `sam_prompt` canting di pack. Kalau `test_reprocess_uses_cache_and_does_not_duplicate` gagal karena `sam_calls` tidak kosong, keyframe hasil ffmpeg tidak identik per byte: ubah kunci cache SAM di `ground._raw_for` memakai `f"{occurrence recording}:{t:.2f}"` alih-alih sha keyframe, dan catat alasannya di komentar.

- [ ] **Step 5: Jalankan seluruh tes dan lint**

Run: `cd api && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: semua lulus.

- [ ] **Step 6: Commit**

```bash
git add api/empu/pipeline/run.py api/tests/test_run.py
git commit -m "feat(pipeline): orchestrator with stage tracking, Mode B, grounding, cutting"
```

---

### Task H2-9: Worker (`python -m empu.worker`)

**Files:**
- Create: `api/empu/worker.py`
- Test: `api/tests/test_worker.py`

**Interfaces:**
- Consumes: `make_engine`, `init_db`, `Job`, `Recording`, `process_recording`, `MetaClient.from_settings`, `JOB_STAGES`
- Produces:
  - `claim_next_job(engine) -> int | None` (job `queued` tertua; update bersyarat `WHERE status='queued'` supaya tidak diambil dua kali)
  - `reset_stale_jobs(engine) -> int` (job berstatus tahap berjalan dikembalikan ke `queued` saat worker start; asumsi satu worker)
  - `run_once(engine, settings, *, client_factory=MetaClient.from_settings, process=process_recording) -> bool`
  - `main(poll_s: float = 1.0) -> None`; `python -m empu.worker`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_worker.py
from empu.enums import JobStatus
from empu.models import Job
from empu.worker import claim_next_job, reset_stale_jobs, run_once
from factories import make_archive, make_recording


def jobs(session, *statuses):
    a = make_archive(session)
    r = make_recording(session, a)
    out = [Job(recording_id=r.id, status=s) for s in statuses]
    session.add_all(out)
    session.commit()
    return [j.id for j in out]


def test_claim_oldest_queued_once(engine, session):
    first, second = jobs(session, JobStatus.queued, JobStatus.queued)
    assert claim_next_job(engine) == first
    assert claim_next_job(engine) == second
    assert claim_next_job(engine) is None
    session.expire_all()
    assert session.get(Job, first).status is JobStatus.normalizing
    assert session.get(Job, first).started_at is not None


def test_reset_stale(engine, session):
    stuck, done = jobs(session, JobStatus.analyzing, JobStatus.ready)
    assert reset_stale_jobs(engine) == 1
    session.expire_all()
    assert session.get(Job, stuck).status is JobStatus.queued
    assert session.get(Job, done).status is JobStatus.ready


def test_run_once_calls_process(engine, session, settings):
    (job_id,) = jobs(session, JobStatus.queued)
    seen = []
    assert run_once(engine, settings, client_factory=lambda s: "client",
                    process=lambda s, jid, client, settings: seen.append((jid, client)))
    assert seen == [(job_id, "client")]
    assert run_once(engine, settings, client_factory=lambda s: "client", process=lambda *a, **k: None) is False


def test_run_once_marks_failed_when_client_cannot_be_built(engine, session, settings):
    (job_id,) = jobs(session, JobStatus.queued)

    def no_key(s):
        raise RuntimeError("META_MODEL_API_KEY is not set")

    assert run_once(engine, settings, client_factory=no_key)
    session.expire_all()
    job = session.get(Job, job_id)
    assert job.status is JobStatus.failed and "META_MODEL_API_KEY" in job.error
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_worker.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.worker'`.

- [ ] **Step 3: Tulis `api/empu/worker.py`**

```python
"""Job worker: `python -m empu.worker`. Polls the job table and runs one job at a time."""

from __future__ import annotations

import logging
import signal
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from empu.config import Settings, get_settings
from empu.db import init_db, make_engine
from empu.enums import JobStatus
from empu.meta_client import MetaClient
from empu.models import Job, Recording, utcnow
from empu.pipeline.run import JOB_STAGES, process_recording

log = logging.getLogger("empu.worker")


def claim_next_job(engine: Engine) -> int | None:
    with Session(engine) as s:
        job_id = s.exec(select(Job.id).where(Job.status == JobStatus.queued).order_by(Job.id)).first()
        if job_id is None:
            return None
        res = s.execute(update(Job).where(col(Job.id) == job_id, col(Job.status) == JobStatus.queued)
                        .values(status=JobStatus.normalizing, started_at=utcnow(), detail="claimed"))
        s.commit()
        return job_id if res.rowcount == 1 else None


def reset_stale_jobs(engine: Engine) -> int:
    with Session(engine) as s:
        res = s.execute(update(Job).where(col(Job.status).in_(JOB_STAGES))
                        .values(status=JobStatus.queued, detail="requeued after worker restart"))
        s.commit()
        return res.rowcount


def _fail(engine: Engine, job_id: int, message: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        job.status, job.error, job.finished_at = JobStatus.failed, message[:2000], utcnow()
        rec = s.get(Recording, job.recording_id)
        rec.status = JobStatus.failed
        s.add_all([job, rec])
        s.commit()


def run_once(engine: Engine, settings: Settings, *,
             client_factory: Callable[[Settings], Any] = MetaClient.from_settings,
             process: Callable[..., None] = process_recording) -> bool:
    job_id = claim_next_job(engine)
    if job_id is None:
        return False
    log.info("job %s claimed", job_id)
    try:
        client = client_factory(settings)
    except Exception as e:  # noqa: BLE001
        _fail(engine, job_id, f"setup: {type(e).__name__}: {e}")
        log.error("job %s failed before start", job_id)
        return True
    try:
        with Session(engine) as s:
            process(s, job_id, client=client, settings=settings)
    finally:
        if hasattr(client, "close"):
            client.close()
    log.info("job %s finished", job_id)
    return True


def main(poll_s: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    engine = make_engine(settings.db_url)
    init_db(engine)
    log.info("worker started (requeued %d stale jobs)", reset_stale_jobs(engine))
    stop = False

    def _stop(*_: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while not stop:
        if not run_once(engine, settings):
            time.sleep(poll_s)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_worker.py -q`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/empu/worker.py api/tests/test_worker.py
git commit -m "feat(worker): table-backed job worker"
```

---

### Task H2-10: Intake, CLI, dan Gate 1

**Files:**
- Create: `api/empu/intake.py`
- Modify: `api/empu/cli.py`
- Test: `api/tests/test_intake.py`, `api/tests/test_cli.py` (tambah)
- Create: `docs/reference/hasil-gate1.md`
- Modify: `packs/batik_tulis.yaml` (`sam_prompt` alat lain, versi `0.1.1`), `CLAUDE.md`

**Interfaces:**
- Consumes: model DB, `Settings`, `rel_to_data`, `recording_dir`, `process_recording`, `prompt_version_for`
- Produces:
  - `IntakeError(ValueError)`
  - `RecordingMeta` (dataclass): `title`, `contributor_name=None`, `contributor_id=None`, `contributor_role=maestro`, `recorded_at=None`, `location=""`, `language_hint="id,jv"`, `consent_confirmed=False`, `consent_scope=public`, `consent_note=""`, `consent_evidence=""`, `source_kind=own_recording`, `source_url=None`, `source_creator=None`, `license=None`, `attribution=None`
  - `validate_meta(meta) -> None`: `consent_confirmed` wajib `True`; `cc_by_video` wajib `source_url`, `source_creator`, `license`, `attribution`; `internal_eval` wajib `consent_scope=private`
  - `get_or_create_archive(session, slug, *, title, pack_id, is_demo=False, is_sandbox=False) -> Archive`
  - `get_or_create_contributor(session, name, role) -> Contributor`
  - `create_recording(session, settings, archive, src: Path, meta, *, mode: PipelineMode | None = None, filename: str | None = None) -> tuple[Recording, Job]` (menyalin file ke `original.<ext>`; `filename` dipakai H3 untuk ekstensi file unggahan)
  - `enqueue_job(session, settings, recording, *, mode=None) -> Job`
  - `meta_from_license_file(path: Path, *, contributor_name: str | None = None) -> RecordingMeta` (membaca `docs/eval/lisensi/<id>.json`)
  - `find_testdata_video(testdata_dir: Path, youtube_id: str) -> Path`
  - `CC_BY_LICENSE = "CC BY 3.0"`
  - CLI: `empu db init [--reset]`, `empu ingest VIDEO --archive SLUG [...]`, `empu reprocess RECORDING_ID [--mode] [--run]`, `empu process JOB_ID`, `empu status [--archive SLUG]`

Teks atribusi CC BY yang dibuat otomatis (bahasa Inggris, karena UI Inggris):
`"<title>" by <channel> (<url>), licensed under CC BY 3.0. Trimmed and analyzed by Empu.`
`consent_evidence`: `CC BY 3.0, verified via YouTube metadata on <verified_at>`. YouTube hanya menawarkan CC BY 3.0, jadi `license = "CC BY 3.0"`.

Untuk video CC BY tanpa nama ahli yang diketahui, kontributornya channel itu sendiri dengan peran `documenter`. Kalau nama ahli di video diketahui (mis. disebut di narasi), pakai `--contributor "<nama>"` dan perannya `maestro`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_intake.py
import json

import pytest

from conftest import REPO_ROOT
from empu.enums import AccessLevel, ContributorRole, JobStatus, PipelineMode, SourceKind
from empu.intake import (
    IntakeError,
    RecordingMeta,
    create_recording,
    get_or_create_archive,
    meta_from_license_file,
    validate_meta,
)
from empu.media import abs_from_rel


def meta(**kw):
    return RecordingMeta(**({"title": "Uji", "contributor_name": "Bu Ahli", "consent_confirmed": True} | kw))


def test_consent_required():
    with pytest.raises(IntakeError, match="consent"):
        validate_meta(meta(consent_confirmed=False))


def test_cc_by_requires_attribution_fields():
    with pytest.raises(IntakeError, match="source_url"):
        validate_meta(meta(source_kind=SourceKind.cc_by_video, source_creator="c", license="CC BY 3.0",
                           attribution="a"))


def test_internal_eval_must_be_private():
    with pytest.raises(IntakeError, match="private"):
        validate_meta(meta(source_kind=SourceKind.internal_eval, consent_scope=AccessLevel.public))
    validate_meta(meta(source_kind=SourceKind.internal_eval, consent_scope=AccessLevel.private))


def test_create_recording_copies_file_and_queues_job(session, settings, tmp_path):
    src = tmp_path / "video.MOV"
    src.write_bytes(b"fake")
    a = get_or_create_archive(session, "demo", title="Demo", pack_id="batik_tulis")
    rec, job = create_recording(session, settings, a, src, meta(), mode=PipelineMode.B)
    assert rec.original_path == f"archives/{a.id}/recordings/{rec.id}/original.mov"
    assert abs_from_rel(settings.data_dir, rec.original_path).read_bytes() == b"fake"
    assert job.status is JobStatus.queued and job.mode is PipelineMode.B
    assert job.prompt_version == "analyze-v3" and rec.contributor_id is not None
    assert get_or_create_archive(session, "demo", title="x", pack_id="batik_tulis").id == a.id


def test_meta_from_license_file():
    m = meta_from_license_file(REPO_ROOT / "docs/eval/lisensi/FodqwNTWOrQ.json")
    assert m.source_kind is SourceKind.cc_by_video and m.license == "CC BY 3.0"
    assert m.source_creator == "Batik Education" and m.source_url.endswith("FodqwNTWOrQ")
    assert m.contributor_role is ContributorRole.documenter
    assert "Trimmed and analyzed by Empu" in m.attribution and m.consent_confirmed
    assert m.consent_evidence == "CC BY 3.0, verified via YouTube metadata on 2026-10-28"
    validate_meta(m)


def test_license_file_without_cc_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"id": "x", "title": "t", "channel": "c", "license": None, "webpage_url": "u"}))
    with pytest.raises(IntakeError, match="Creative Commons"):
        meta_from_license_file(p)
```

Tambahkan ke `api/tests/test_cli.py` (impor di atas file):

```python
from sqlmodel import Session, select

from empu.db import make_engine
from empu.models import Entry, Recording

ONE_TERM = {"speech_heard": True, "terms": [
    {"spoken": "canting", "term": "canting", "category": "tool", "source": "speech", "t_start": 2,
     "t_end": 3, "stage": None, "evidence_quote": "ini canting", "visible": "", "visible_object_en": None,
     "visual_match": "yes", "gloss_id": "", "gloss_en": "", "confidence": "high"}], "process_steps": []}


def test_ingest_run_end_to_end(sample_video, settings, monkeypatch):
    fake = FakeClient([make_raw(ONE_TERM)])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_client", lambda s: fake)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["db", "init"]).exit_code == 0
    r = runner.invoke(cli.app, ["ingest", str(sample_video), "--archive", "uji", "--title", "Uji",
                                "--contributor", "Bu Ahli", "--consent-confirmed", "--mode", "A", "--run"])
    assert r.exit_code == 0, r.output
    assert "ready" in r.output
    with Session(make_engine(settings.db_url)) as s:
        assert s.exec(select(Recording)).one().status == "ready"
        assert s.exec(select(Entry)).one().canon_key == "term:canting"
    assert "entries=1" in runner.invoke(cli.app, ["status", "--archive", "uji"]).output


def test_ingest_without_consent_fails(sample_video, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    r = CliRunner().invoke(cli.app, ["ingest", str(sample_video), "--archive", "uji", "--title", "Uji",
                                     "--contributor", "Bu Ahli"])
    assert r.exit_code != 0 and "consent" in r.output
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_intake.py tests/test_cli.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.intake'`.

- [ ] **Step 3: Tulis `api/empu/intake.py`**

```python
"""Create archives, contributors, recordings and jobs. Shared by the CLI and the upload API."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from empu.config import Settings
from empu.enums import AccessLevel, ContributorRole, JobStatus, PipelineMode, SourceKind
from empu.media import recording_dir, rel_to_data
from empu.models import Archive, Contributor, Job, Recording
from empu.pipeline.prompts import prompt_version_for

CC_BY_LICENSE = "CC BY 3.0"


class IntakeError(ValueError):
    pass


@dataclass
class RecordingMeta:
    title: str
    contributor_name: str | None = None
    contributor_id: int | None = None
    contributor_role: ContributorRole = ContributorRole.maestro
    recorded_at: str | None = None
    location: str = ""
    language_hint: str = "id,jv"
    consent_confirmed: bool = False
    consent_scope: AccessLevel = AccessLevel.public
    consent_note: str = ""
    consent_evidence: str = ""
    source_kind: SourceKind = SourceKind.own_recording
    source_url: str | None = None
    source_creator: str | None = None
    license: str | None = None
    attribution: str | None = None


def validate_meta(meta: RecordingMeta) -> None:
    if meta.consent_confirmed is not True:
        raise IntakeError("consent_confirmed must be true: recordings are never processed without consent")
    if not meta.title.strip():
        raise IntakeError("title is required")
    if not (meta.contributor_name or meta.contributor_id):
        raise IntakeError("contributor_name or contributor_id is required")
    if meta.source_kind is SourceKind.cc_by_video:
        missing = [f for f in ("source_url", "source_creator", "license", "attribution")
                   if not (getattr(meta, f) or "").strip()]
        if missing:
            raise IntakeError(f"cc_by_video requires {', '.join(missing)}")
    if meta.source_kind is SourceKind.internal_eval and meta.consent_scope is not AccessLevel.private:
        raise IntakeError("internal_eval recordings must use consent_scope=private")


def get_or_create_archive(session: Session, slug: str, *, title: str, pack_id: str, is_demo: bool = False,
                          is_sandbox: bool = False) -> Archive:
    archive = session.exec(select(Archive).where(Archive.slug == slug)).first()
    if archive is None:
        archive = Archive(slug=slug, title=title, craft_pack_id=pack_id, is_demo=is_demo, is_sandbox=is_sandbox)
        session.add(archive)
        session.commit()
        session.refresh(archive)
    return archive


def get_or_create_contributor(session: Session, name: str, role: ContributorRole) -> Contributor:
    c = session.exec(select(Contributor).where(Contributor.name == name)).first()
    if c is None:
        c = Contributor(name=name, role=role)
        session.add(c)
        session.commit()
        session.refresh(c)
    return c


def enqueue_job(session: Session, settings: Settings, recording: Recording, *,
                mode: PipelineMode | None = None) -> Job:
    job = Job(recording_id=recording.id, status=JobStatus.queued,
              mode=mode or PipelineMode(settings.pipeline_mode), model=settings.muse_model,
              prompt_version=prompt_version_for(True))
    recording.status = JobStatus.queued
    session.add_all([job, recording])
    session.commit()
    session.refresh(job)
    return job


def create_recording(session: Session, settings: Settings, archive: Archive, src: Path, meta: RecordingMeta,
                     *, mode: PipelineMode | None = None, filename: str | None = None) -> tuple[Recording, Job]:
    validate_meta(meta)
    contributor_id = meta.contributor_id
    if contributor_id is None:
        contributor_id = get_or_create_contributor(session, meta.contributor_name.strip(), meta.contributor_role).id
    rec = Recording(
        archive_id=archive.id, contributor_id=contributor_id, title=meta.title.strip(),
        recorded_at=meta.recorded_at, location=meta.location, language_hint=meta.language_hint,
        original_path="", consent_scope=meta.consent_scope, consent_note=meta.consent_note,
        consent_evidence=meta.consent_evidence, source_kind=meta.source_kind, source_url=meta.source_url,
        source_creator=meta.source_creator, license=meta.license, attribution=meta.attribution)
    session.add(rec)
    session.flush()
    ext = (Path(filename or src.name).suffix or ".mp4").lower()
    dst = recording_dir(settings.data_dir, archive.id, rec.id) / f"original{ext}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    rec.original_path = rel_to_data(settings.data_dir, dst)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec, enqueue_job(session, settings, rec, mode=mode)


def meta_from_license_file(path: Path, *, contributor_name: str | None = None) -> RecordingMeta:
    d = json.loads(Path(path).read_text())
    if "creative commons" not in (d.get("license") or "").lower():
        raise IntakeError(f"{Path(path).name}: license is not Creative Commons ({d.get('license')!r})")
    title, channel, url = d["title"], d["channel"], d["webpage_url"]
    return RecordingMeta(
        title=title, contributor_name=contributor_name or channel,
        contributor_role=ContributorRole.maestro if contributor_name else ContributorRole.documenter,
        consent_confirmed=True, consent_scope=AccessLevel.public,
        consent_evidence=f"{CC_BY_LICENSE}, verified via YouTube metadata on {d.get('verified_at', '?')}",
        source_kind=SourceKind.cc_by_video, source_url=url, source_creator=channel, license=CC_BY_LICENSE,
        attribution=f'"{title}" by {channel} ({url}), licensed under {CC_BY_LICENSE}. '
                    "Trimmed and analyzed by Empu.")


def find_testdata_video(testdata_dir: Path, youtube_id: str) -> Path:
    hits = sorted(p for p in Path(testdata_dir).rglob("*.mp4") if f"[{youtube_id}]" in p.name)
    if not hits:
        raise IntakeError(f"video [{youtube_id}] not found under {testdata_dir}")
    return hits[0]
```

- [ ] **Step 4: Tambahkan subperintah ke `api/empu/cli.py`**

Tambahkan impor di kepala file (gabungkan dengan impor yang sudah ada):

```python
from sqlmodel import Session, col, func, select

from empu.db import init_db, make_engine
from empu.enums import AccessLevel, ContributorRole, PipelineMode, SourceKind
from empu.intake import (
    IntakeError,
    RecordingMeta,
    create_recording,
    enqueue_job,
    get_or_create_archive,
    meta_from_license_file,
)
from empu.models import Archive, Entry, Job, Occurrence, Recording
from empu.pipeline.run import process_recording
```

Tambahkan di bawah perintah `analyze`:

```python
db_app = typer.Typer(no_args_is_help=True)
app.add_typer(db_app, name="db", help="Database commands.")


def _engine(settings: Settings):
    engine = make_engine(settings.db_url)
    init_db(engine)
    return engine


@db_app.command("init")
def db_init(reset: bool = typer.Option(False, "--reset", help="Drop all tables first.")) -> None:
    settings = get_settings()
    init_db(make_engine(settings.db_url), reset=reset)
    typer.echo(f"database ready: {settings.db_url}")


def _run_job(settings: Settings, session: Session, job_id: int) -> None:
    process_recording(session, job_id, client=make_client(settings), settings=settings)
    job = session.get(Job, job_id)
    typer.echo(f"job {job.id}: {job.status.value} {job.error or ''}")
    typer.echo(json.dumps({"timings": {k: v.get("seconds") for k, v in job.timings_json.items()},
                           "usage": job.usage_json}, ensure_ascii=False))
    if job.status.value != "ready":
        raise typer.Exit(1)


@app.command()
def ingest(
    video: Path = typer.Argument(..., exists=True, dir_okay=False),
    archive: str = typer.Option(..., "--archive", help="Archive slug (created if missing)."),
    archive_title: str | None = typer.Option(None, "--archive-title"),
    pack_id: str = typer.Option("batik_tulis", "--pack"),
    title: str | None = typer.Option(None, "--title"),
    license_file: Path | None = typer.Option(None, "--license-file", exists=True,
                                             help="docs/eval/lisensi/<id>.json for a CC BY video."),
    contributor: str | None = typer.Option(None, "--contributor"),
    role: ContributorRole = typer.Option(ContributorRole.maestro, "--role"),
    consent_confirmed: bool = typer.Option(False, "--consent-confirmed"),
    consent_scope: AccessLevel = typer.Option(AccessLevel.public, "--consent-scope"),
    consent_note: str = typer.Option("", "--consent-note"),
    consent_evidence: str = typer.Option("", "--consent-evidence"),
    source_kind: SourceKind = typer.Option(SourceKind.own_recording, "--source-kind"),
    mode: PipelineMode | None = typer.Option(None, "--mode"),
    demo: bool = typer.Option(False, "--demo", help="Mark the archive as the pinned demo archive."),
    run: bool = typer.Option(False, "--run", help="Process now instead of waiting for the worker."),
) -> None:
    """Register a recording with consent metadata and queue (or run) its job."""
    settings = get_settings()
    try:
        if license_file is not None:
            meta = meta_from_license_file(license_file, contributor_name=contributor)
            meta.title = title or meta.title
        else:
            meta = RecordingMeta(title=title or video.stem, contributor_name=contributor, contributor_role=role,
                                 consent_confirmed=consent_confirmed, consent_scope=consent_scope,
                                 consent_note=consent_note, consent_evidence=consent_evidence,
                                 source_kind=source_kind)
        with Session(_engine(settings)) as session:
            arc = get_or_create_archive(session, archive, title=archive_title or archive, pack_id=pack_id,
                                        is_demo=demo)
            rec, job = create_recording(session, settings, arc, video, meta, mode=mode)
            typer.echo(f"recording {rec.id} in archive {arc.slug}, job {job.id} queued (mode {job.mode.value})")
            if run:
                _run_job(settings, session, job.id)
    except IntakeError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e


@app.command()
def reprocess(recording_id: int, mode: PipelineMode | None = typer.Option(None, "--mode"),
              run: bool = typer.Option(False, "--run")) -> None:
    """Queue a new job for an existing recording (Muse and SAM come from cache when unchanged)."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        rec = session.get(Recording, recording_id)
        if rec is None:
            typer.echo(f"error: recording {recording_id} not found", err=True)
            raise typer.Exit(2)
        job = enqueue_job(session, settings, rec, mode=mode)
        typer.echo(f"job {job.id} queued for recording {rec.id}")
        if run:
            _run_job(settings, session, job.id)


@app.command("process")
def process_cmd(job_id: int) -> None:
    """Run one queued job in this process (debugging)."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        _run_job(settings, session, job_id)


@app.command()
def status(archive: str | None = typer.Option(None, "--archive")) -> None:
    """Print recordings, latest job, and entry counts."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        q = select(Archive)
        if archive:
            q = q.where(Archive.slug == archive)
        for arc in session.exec(q):
            ents = list(session.exec(select(Entry).where(Entry.archive_id == arc.id)))
            by_status = Counter(e.status.value for e in ents)
            by_sam = Counter(e.sam_status.value for e in ents)
            typer.echo(f"[{arc.slug}] entries={len(ents)} {dict(by_status)} sam={dict(by_sam)} "
                       f"novel={sum(e.is_novel for e in ents)}")
            for rec in session.exec(select(Recording).where(Recording.archive_id == arc.id)):
                job = session.exec(select(Job).where(Job.recording_id == rec.id)
                                   .order_by(col(Job.id).desc())).first()
                n_occ = session.exec(select(func.count()).select_from(Occurrence)
                                     .where(Occurrence.recording_id == rec.id)).one()
                job_txt = f"{job.id}:{job.status.value} {job.detail}" if job else "-"
                typer.echo(f"  rec {rec.id} '{rec.title}' {rec.status.value} occ={n_occ} job={job_txt}")
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest -q && uv run ruff check .`
Expected: semua lulus.

- [ ] **Step 6: Commit**

```bash
git add api/empu/intake.py api/empu/cli.py api/tests
git commit -m "feat(cli): intake with consent and CC BY attribution; db, ingest, reprocess, status"
```

- [ ] **Step 7: Gate 1, jalur CLI** (Muse untuk *Macam Canting* sudah di-cache dari H1; biaya hanya SAM)

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
uv run empu db init
uv run empu ingest "../data-uji/cc-by/Macam Canting dalam Batik Tulis [FodqwNTWOrQ].mp4" \
  --archive batik-tulis --archive-title "Arsip Hidup Batik Tulis" --demo \
  --license-file ../docs/eval/lisensi/FodqwNTWOrQ.json --mode B --run
uv run empu status --archive batik-tulis
```
Expected: `job 1: ready`, JSON timings per tahap dan usage (`cached_chunks: 4`, `asr_retimed` > 0), lalu `[batik-tulis] entries=N … sam={'ok': …}` dan `rec 1 … ready occ=M`.

Periksa hasilnya dengan mata (10 menit):
- Buka 5 `data/archives/1/entries/*/overlay.jpg`. Untuk setiap alat pack dengan `sam_status` `empty` atau kotak yang salah, catat istilahnya.
- Putar 5 klip `data/archives/1/recordings/1/occurrences/*/clip.mp4` dengan `source=speech`: apakah istilahnya terdengar di klip? Bandingkan beberapa yang `time_source=asr` dengan yang `muse`.

```bash
sqlite3 ../data/empu.db "select e.term, o.source, o.t_start, o.time_source, e.sam_status from occurrence o join entry e on e.id=o.entry_id order by o.t_start;"
```

- [ ] **Step 8: Gate 1, jalur worker** (berbayar: *Proses nyanting* 508 s, sekitar 8 segmen ≈ USD 0,25)

Terminal 1:
```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api && uv run python -m empu.worker
```
Terminal 2:
```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
uv run empu ingest "../data-uji/cc-by/Proses nyanting batik tulis [zyscgcTHtq8].mp4" \
  --archive batik-tulis --license-file ../docs/eval/lisensi/zyscgcTHtq8.json --mode B
while sleep 5; do uv run empu status --archive batik-tulis | tail -1; done
```
Expected: rec 2 melewati `normalizing → … → ready` di log worker dan di `status`; entri yang sama dengan rekaman 1 (mis. canting) sekarang punya kemunculan dari dua rekaman (`entries` tidak bertambah dua kali lipat). Catat waktu total dari `timings` (target ≤ 3 menit per 5 menit video; laporkan angka asli). Hentikan loop dengan Ctrl-C.

- [ ] **Step 9: Perbaiki `sam_prompt` alat yang gagal.** Untuk setiap alat yang dicatat di Step 7, tulis ulang `sam_prompt` di `packs/batik_tulis.yaml` sebagai deskripsi visual bahasa Inggris dengan 2 alternatif dipisah koma (pola Gate 0), naikkan `version` pack ke `0.1.1`, lalu:

```bash
uv run pytest tests/test_packs.py -q
uv run empu reprocess 1 --mode B --run && uv run empu reprocess 2 --mode B --run
```
Expected: Muse 100% cache (`cached_chunks` = jumlah segmen, tanpa biaya), SAM hanya dipanggil untuk prompt baru. Hitung ulang `sam ok` dan cek overlay lagi. Maksimal dua putaran; setelah itu terima hasilnya dan catat.

- [ ] **Step 10: Tulis `docs/reference/hasil-gate1.md`**

```markdown
# Hasil Gate 1 (30 Okt 2026)

| Butir | Hasil |
|---|---|
| CLI end-to-end (*Macam Canting*, 246 s, Mode B) | ready/gagal; entri N (baru n); kemunculan M; klip M/M |
| Worker end-to-end (*Proses nyanting*, 508 s, Mode B) | ready/gagal; waktu total … s (per tahap: …) |
| Penggabungan lintas rekaman | entri yang punya kemunculan dari 2 rekaman: … |
| SAM | ok/empty/error/skipped = …; prompt yang diganti: … |
| Mode B | `asr_retimed` … dari … kemunculan speech; model whisper …, waktu transkripsi … s |
| Biaya | token input/output Muse …; panggilan SAM … |

## Keputusan
- Gate 1 lulus / gagal. Kalau gagal: fitur yang dipotong sesuai spec 15 (SAM → keyframe, lintas rekaman, peta tahapan sederhana).

## Temuan untuk H3
- …
```

- [ ] **Step 11: Perbarui `CLAUDE.md`.** Bagian Perintah: tambahkan `uv run empu db init`, `uv run empu ingest <video> --archive <slug> --license-file ../docs/eval/lisensi/<id>.json --run`, `uv run empu reprocess <id> --run`, `uv run empu status`, `uv run python -m empu.worker`. Status:

```markdown
- H2 (Jum 30 Okt): Gate 1 lulus|gagal (lihat docs/reference/hasil-gate1.md). Arsip `batik-tulis` berisi 2 video CC BY. Berikutnya: H3.
```

- [ ] **Step 12: Commit**

```bash
git add packs/batik_tulis.yaml docs/reference/hasil-gate1.md CLAUDE.md
git commit -m "docs: Gate 1 results; tune SAM prompts on real keyframes"
```

---

## Selesai kalau (Gate 1)
- [ ] `cd api && uv run pytest -q` lulus tanpa jaringan; `ruff check` bersih.
- [ ] Satu video CC BY `ready` lewat `empu ingest --run`, dan satu lagi `ready` lewat worker.
- [ ] DB berisi entri, kemunculan dengan klip/audio/keyframe, crop SAM untuk alat yang visual, dan peta tahapan.
- [ ] `docs/reference/hasil-gate1.md` berisi angka asli.

## Kalau Gate 1 gagal (putuskan paling lambat Jumat 20:00 WIB)
| Gejala | Potong / tindakan |
|---|---|
| SAM tidak stabil atau lambat | `EMPU_SAM_ENABLED=false`; UI memakai keyframe; metrik SAM di H5 dilaporkan "tidak dijalankan" |
| Penggabungan lintas rekaman bermasalah | Satu arsip per rekaman (slug berbeda per `ingest`) |
| Peta tahapan berantakan | S6 menampilkan `stage_id` entri saja (dari `stage` Muse); `ProcessStep` tidak dipakai |
| Whisper terlalu lambat (> 3 menit untuk 5 menit video) | Model `base`, atau Mode A untuk demo dengan catatan jujur di Bukti |
| Worker macet | Proses demo dengan `empu ingest --run`; worker diperbaiki di H6 |
