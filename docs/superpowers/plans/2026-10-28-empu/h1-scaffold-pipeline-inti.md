# H1 (Kam 29 Okt): Scaffold dan Inti Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paket Python `empu` yang bisa menjalankan `empu analyze <video> --pack batik_tulis` dari CLI: normalisasi ffmpeg, potong segmen 75 s/overlap 10 s, analisis Muse per segmen (paralel, dengan cache), validasi skema v3, dan menulis JSON per segmen.

**Architecture:** `api/empu/` berisi modul kecil berbatas jelas: `config` (satu-satunya pembaca env), `packs` (craft pack + validasi), `muse_schema` (kontrak keluaran Muse), `meta_client` (satu-satunya pintu Meta API), `cache` (respons mentah), dan `pipeline/` (ffmpeg, normalize, chunk, prompts, analyze). CLI Typer di `cli.py`. Semua tes memakai fixture atau fake client.

**Tech Stack:** Python 3.12 (uv), Pydantic v2, pydantic-settings, httpx, tenacity, PyYAML, Typer, pytest, respx, ruff, ffmpeg.

## Global Constraints

Semua butir di `00-ikhtisar.md` bagian "Global Constraints" berlaku. Yang paling relevan untuk fase ini:
- Satu-satunya pembaca env/`.env` di paket `empu` adalah `api/empu/config.py`. Kunci API memakai `SecretStr`, tidak pernah dicetak atau di-log.
- Semua panggilan Meta lewat `api/empu/meta_client.py`. Cache kunci `sha256(segmen) + model + prompt_version + mode`. Kalau cache ada, tidak memanggil API.
- Tes tidak memanggil API sungguhan (respx atau `FakeClient`).
- Tidak ada istilah batik di `api/empu/**`. Istilah hanya di `packs/batik_tulis.yaml`.
- `PROMPT_VERSION = "analyze-v3"`; ablasi tanpa benih `analyze-v3-noseed`. Setiap perubahan teks prompt menaikkan versi.
- Segmen 75 s, overlap 10 s. `analysis.mp4`: 480p, H.264 CRF 28 preset veryfast, AAC mono 64 kbps. `display.mp4`: 720p, H.264, AAC, `+faststart`.
- Retry Meta API: 429, 5xx, dan error transport; maksimal 4 retry; 4xx lain tidak di-retry.

## Prasyarat
- H0 selesai: `docs/reference/hasil-gate0.md` berisi nilai env awal.
- `ffmpeg`, `ffprobe`, `uv` tersedia (`which ffmpeg ffprobe uv`).

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/pyproject.toml`, `api/.python-version` | Create | Paket, dependensi, pytest, ruff |
| `api/empu/__init__.py` | Create | Versi paket |
| `api/tests/conftest.py`, `api/tests/fakes.py` | Create | Fixture bersama, `FakeClient`, `make_raw` |
| `.env.example` | Create | Daftar variabel env tanpa nilai rahasia |
| `api/empu/config.py` | Create | `Settings`, `get_settings` |
| `api/empu/enums.py`, `api/empu/text.py` | Create | Enum bersama, `normalize` |
| `packs/batik_tulis.yaml` | Move + Modify | Dari `docs/packs/`; tambah `asr_error_examples` |
| `api/empu/packs.py` | Create | `CraftPack`, validasi, `variant_index`, `load_pack` |
| `api/empu/resources/muse-output.schema.json` | Create (salin) | Skema yang dikirim ke Muse |
| `api/empu/muse_schema.py`, `api/empu/legacy.py` | Create | Model Pydantic keluaran Muse, pemetaan enum v1 |
| `api/tests/fixtures/muse/*`, `api/tests/fixtures/sam/*` | Create (salin) | Fixture dari `hasil-v1/` dan `hasil-gate0/` |
| `api/empu/meta_client.py` | Create | `MetaClient`, retry, `output_text`, `extract_json` |
| `api/empu/cache.py` | Create | `ResponseCache`, `sha256_file` |
| `api/empu/pipeline/{__init__,ffmpeg,normalize,chunk}.py` | Create | ffmpeg, turunan media, segmen |
| `api/empu/pipeline/prompts.py` | Create | Prompt v3, transcript block Mode B |
| `api/empu/pipeline/analyze.py` | Create | Analisis per segmen, ulang sekali kalau tidak valid, paralel |
| `api/empu/cli.py` | Create | `empu analyze` |
| `CLAUDE.md` | Modify | Bagian "Perintah", Status, path pack |
| `docs/README.md`, spec | Modify | Path pack `packs/batik_tulis.yaml` |

---

### Task H1-1: Scaffold paket `api/`

**Files:**
- Create: `api/pyproject.toml`, `api/.python-version`, `api/empu/__init__.py`
- Create: `api/tests/conftest.py`, `api/tests/test_smoke.py`
- Create: `.env.example`

**Interfaces:**
- Produces: perintah `cd api && uv run pytest`; konstanta `REPO_ROOT`, `FIXTURES` dan helper `load_fixture(rel: str) -> dict` di `tests/conftest.py`. Tes lain mengimpor dengan `from conftest import …` (pytest memasukkan `api/tests` ke `sys.path` karena `tests/` tidak punya `__init__.py`; **jangan** buat `api/tests/__init__.py`).

- [ ] **Step 1: Tulis `api/pyproject.toml`**

```toml
[project]
name = "empu"
version = "0.1.0"
description = "Empu: turn a master's narrated work video into a watchable, validated craft dictionary."
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "python-multipart>=0.0.9",
  "sqlmodel>=0.0.22",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "httpx>=0.28",
  "tenacity>=9.0",
  "rapidfuzz>=3.10",
  "pympi-ling>=1.70",
  "pyyaml>=6.0",
  "pillow>=11.0",
  "typer>=0.12",
]

[project.optional-dependencies]
asr = ["faster-whisper>=1.1"]

[project.scripts]
empu = "empu.cli:app"

[dependency-groups]
dev = ["pytest>=8.3", "respx>=0.22", "ruff>=0.8", "jsonschema>=4.23"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["empu"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
markers = ["ffmpeg: needs ffmpeg/ffprobe on PATH"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
```

- [ ] **Step 2: Tulis `api/.python-version`** berisi satu baris `3.12`, dan `api/empu/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Tulis `api/tests/conftest.py` dan `api/tests/test_smoke.py`**

```python
# api/tests/conftest.py
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text())
```

```python
# api/tests/test_smoke.py
import empu


def test_package_imports():
    assert empu.__version__ == "0.1.0"
```

- [ ] **Step 4: Instal dan jalankan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/api
uv sync
uv run pytest -q
```
Expected: `uv sync` membuat `.venv` dengan Python 3.12 dan `uv.lock`; pytest `1 passed`.

- [ ] **Step 5: Tulis `.env.example`** di root repo

```dotenv
# Salin ke .env lalu isi. JANGAN commit .env.
META_MODEL_API_KEY=
STUDIO_KEY=
# Nilai di bawah ditentukan Gate 0 (docs/reference/hasil-gate0.md)
EMPU_PIPELINE_MODE=A
EMPU_STRUCTURED_OUTPUT=false
EMPU_STRUCTURED_SCHEMA_VARIANT=full
EMPU_SAM_ENABLED=true
SAM_MODEL=sam-3.1
EMPU_TRANSCRIBE_BACKEND=whisper
EMPU_TRANSCRIBE_MODEL=
# Opsional
# EMPU_DATA_DIR=/abs/path/to/data
# EMPU_TESTDATA_DIR=/abs/path/to/arsip-hidup-batik
# EMPU_ANALYZE_CONCURRENCY=3
```

- [ ] **Step 6: Lengkapi `.env` lokal** (jangan `cat`). Tambahkan baris dari `.env.example` yang belum ada, dan buat `STUDIO_KEY` acak:

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
grep -q '^STUDIO_KEY=' .env || echo "STUDIO_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')" >> .env
for k in EMPU_PIPELINE_MODE EMPU_STRUCTURED_OUTPUT EMPU_STRUCTURED_SCHEMA_VARIANT EMPU_SAM_ENABLED SAM_MODEL EMPU_TRANSCRIBE_BACKEND; do grep -q "^$k=" .env || grep "^$k=" .env.example >> .env; done
sed 's/=.*/=<set>/' .env
```
Expected: daftar nama variabel tanpa nilai. Lalu edit nilainya di editor sesuai `hasil-gate0.md`.

- [ ] **Step 7: Commit**

```bash
git add api/pyproject.toml api/.python-version api/uv.lock api/empu/__init__.py api/tests .env.example
git commit -m "chore(api): scaffold empu python package"
```

---

### Task H1-2: `config.py`, `enums.py`, `text.py`

**Files:**
- Create: `api/empu/config.py`, `api/empu/enums.py`, `api/empu/text.py`
- Modify: `api/tests/conftest.py`
- Test: `api/tests/test_config.py`, `api/tests/test_text.py`

**Interfaces:**
- Produces: `Settings`, `get_settings()`, `REPO_ROOT` (di `empu.config`); semua enum di tabel kontrak `00-ikhtisar.md` plus `CONFIDENCE_RANK: dict[Confidence, int]`; `normalize(s: str | None) -> str`; fixture pytest `settings`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_config.py
from empu.config import REPO_ROOT, Settings

EMPU_PKG = REPO_ROOT / "api" / "empu"


def test_defaults_derive_db_url(tmp_path):
    s = Settings(_env_file=None, data_dir=tmp_path)
    assert s.db_url == f"sqlite:///{tmp_path / 'empu.db'}"
    assert s.chunk_window_s == 75.0 and s.chunk_overlap_s == 10.0
    assert s.analyze_concurrency == 3
    assert s.muse_model == "muse-spark-1.3"


def test_env_aliases(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPU_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPU_PIPELINE_MODE", "B")
    monkeypatch.setenv("EMPU_SAM_ENABLED", "false")
    s = Settings(_env_file=None)
    assert s.data_dir == tmp_path
    assert s.pipeline_mode == "B"
    assert s.sam_enabled is False


def test_secret_not_in_repr():
    s = Settings(_env_file=None, meta_model_api_key="sk-very-secret", studio_key="studio-secret")
    assert "sk-very-secret" not in repr(s)
    assert "studio-secret" not in repr(s)
    assert s.require_api_key() == "sk-very-secret"


def test_require_api_key_missing():
    s = Settings(_env_file=None, meta_model_api_key=None)
    try:
        s.require_api_key()
    except RuntimeError as e:
        assert "META_MODEL_API_KEY" in str(e)
    else:
        raise AssertionError("expected RuntimeError")


def test_only_config_reads_environment():
    offenders = []
    for path in EMPU_PKG.rglob("*.py"):
        if path.name == "config.py":
            continue
        text = path.read_text()
        if "os.environ" in text or "getenv(" in text or "META_MODEL_API_KEY" in text:
            offenders.append(str(path.relative_to(EMPU_PKG)))
    assert offenders == [], offenders
```

```python
# api/tests/test_text.py
from empu.text import normalize


def test_normalize_casefold_punct_space():
    assert normalize("  Isen-Isen!! ") == "isen isen"
    assert normalize("HCl") == "hcl"
    assert normalize("snake_case_id") == "snake case id"
    assert normalize("Ngelorot,") == "ngelorot"


def test_normalize_empty():
    assert normalize(None) == ""
    assert normalize("") == ""
    assert normalize("  -- ") == ""
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_config.py tests/test_text.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.config'`.

- [ ] **Step 3: Tulis `api/empu/enums.py`**

```python
from enum import StrEnum


class Category(StrEnum):
    tool = "tool"
    tool_part = "tool_part"
    material = "material"
    dye = "dye"
    stage = "stage"
    technique = "technique"
    motif = "motif"
    other = "other"


class Source(StrEnum):
    speech = "speech"
    on_screen_text = "on_screen_text"
    visual_only = "visual_only"


class VisualMatch(StrEnum):
    yes = "yes"
    no = "no"
    not_visible = "not_visible"


class Confidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


CONFIDENCE_RANK = {Confidence.low: 0, Confidence.medium: 1, Confidence.high: 2}


class ContributorRole(StrEnum):
    maestro = "maestro"
    student = "student"
    documenter = "documenter"


class ConsentStatus(StrEnum):
    granted = "granted"
    withdrawn = "withdrawn"


class AccessLevel(StrEnum):
    public = "public"
    community = "community"
    private = "private"


class JobStatus(StrEnum):
    queued = "queued"
    normalizing = "normalizing"
    chunking = "chunking"
    analyzing = "analyzing"
    merging = "merging"
    grounding = "grounding"
    cutting = "cutting"
    ready = "ready"
    failed = "failed"


class PipelineMode(StrEnum):
    A = "A"
    B = "B"


class EntryStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    edited = "edited"
    rejected = "rejected"
    merged = "merged"


class OccurrenceStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"


class ReviewAction(StrEnum):
    accept = "accept"
    edit = "edit"
    reject = "reject"
    merge = "merge"
    restore = "restore"
    add_manual = "add_manual"


class SamStatus(StrEnum):
    ok = "ok"
    empty = "empty"
    error = "error"
    skipped = "skipped"


class ChunkStatus(StrEnum):
    pending = "pending"
    done = "done"
    failed = "failed"
```

- [ ] **Step 4: Tulis `api/empu/text.py`**

```python
import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def normalize(s: str | None) -> str:
    """Casefold, drop punctuation and underscores, collapse whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).casefold()
    s = _PUNCT.sub(" ", s).replace("_", " ")
    return _SPACE.sub(" ", s).strip()
```

- [ ] **Step 5: Tulis `api/empu/config.py`**

```python
"""Runtime settings. The only module in empu that reads the environment or .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    meta_model_api_key: SecretStr | None = Field(default=None, validation_alias="META_MODEL_API_KEY")
    studio_key: SecretStr | None = Field(default=None, validation_alias="STUDIO_KEY")
    meta_base_url: str = Field(default="https://api.meta.ai/v1", validation_alias="META_BASE_URL")
    muse_model: str = Field(default="muse-spark-1.3", validation_alias="MUSE_MODEL")
    sam_model: str = Field(default="sam-3.1", validation_alias="SAM_MODEL")

    data_dir: Path = Field(default=REPO_ROOT / "data", validation_alias="EMPU_DATA_DIR")
    packs_dir: Path = Field(default=REPO_ROOT / "packs", validation_alias="EMPU_PACKS_DIR")
    testdata_dir: Path = Field(default=REPO_ROOT / "data-uji", validation_alias="EMPU_TESTDATA_DIR")
    db_url: str = Field(default="", validation_alias="EMPU_DB_URL")

    chunk_window_s: float = Field(default=75.0, validation_alias="EMPU_CHUNK_WINDOW_S")
    chunk_overlap_s: float = Field(default=10.0, validation_alias="EMPU_CHUNK_OVERLAP_S")
    analyze_concurrency: int = Field(default=3, validation_alias="EMPU_ANALYZE_CONCURRENCY")
    pipeline_mode: Literal["A", "B"] = Field(default="A", validation_alias="EMPU_PIPELINE_MODE")
    structured_output: bool = Field(default=False, validation_alias="EMPU_STRUCTURED_OUTPUT")
    structured_schema_variant: Literal["full", "stripped"] = Field(
        default="full", validation_alias="EMPU_STRUCTURED_SCHEMA_VARIANT"
    )
    sam_enabled: bool = Field(default=True, validation_alias="EMPU_SAM_ENABLED")
    transcribe_backend: Literal["muse", "whisper"] = Field(
        default="whisper", validation_alias="EMPU_TRANSCRIBE_BACKEND"
    )
    transcribe_model: str = Field(default="", validation_alias="EMPU_TRANSCRIBE_MODEL")

    max_upload_mb: int = Field(default=500, validation_alias="EMPU_MAX_UPLOAD_MB")
    max_duration_s: float = Field(default=1200.0, validation_alias="EMPU_MAX_DURATION_S")
    sandbox_max_duration_s: float = Field(default=180.0, validation_alias="EMPU_SANDBOX_MAX_DURATION_S")
    sandbox_daily_quota: int = Field(default=30, validation_alias="EMPU_SANDBOX_DAILY_QUOTA")

    @model_validator(mode="after")
    def _derive(self) -> Settings:
        if not self.db_url:
            self.db_url = f"sqlite:///{self.data_dir / 'empu.db'}"
        return self

    def require_api_key(self) -> str:
        if self.meta_model_api_key is None or not self.meta_model_api_key.get_secret_value():
            raise RuntimeError("META_MODEL_API_KEY is not set (see .env.example)")
        return self.meta_model_api_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Tambahkan fixture `settings` ke `api/tests/conftest.py`** (impor di bagian atas file, fixture di bawah)

```python
import pytest

from empu.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        packs_dir=REPO_ROOT / "packs",
        meta_model_api_key="test-key",
        studio_key="studio-test",
        sam_enabled=True,
        structured_output=False,
    )
```

- [ ] **Step 7: Jalankan tes**

Run: `cd api && uv run pytest tests/test_config.py tests/test_text.py -q`
Expected: `7 passed`.

- [ ] **Step 8: Commit**

```bash
git add api/empu/config.py api/empu/enums.py api/empu/text.py api/tests
git commit -m "feat(api): settings, shared enums, text normalization"
```

---

### Task H1-3: Craft pack loader dan validasi

**Files:**
- Move: `docs/packs/batik_tulis.yaml` → `packs/batik_tulis.yaml`
- Modify: `packs/batik_tulis.yaml` (tambah `asr_error_examples`; perbarui `sam_prompt` canting kalau Gate 0.3 menemukan prompt lebih baik)
- Create: `api/empu/packs.py`
- Modify: `api/tests/conftest.py` (fixture `pack`)
- Modify: `CLAUDE.md`, `docs/README.md`, spec bagian 7, `spikes/gate0/common.py` (path pack)
- Test: `api/tests/test_packs.py`, `api/tests/test_no_hardcoded_terms.py`

**Interfaces:**
- Consumes: `normalize`, `Category`
- Produces:
  - `LocalizedText(id: str, en: str)`
  - `PackStage(id, label: LocalizedText, variants: list[str])` dengan properti `display_label -> str` (id dengan `_` diganti spasi)
  - `PackTerm(id, label, category: Category, variants, stage: str|None, gloss_id, gloss_en, visual: bool, sam_prompt: str|None, verified: bool)`
  - `AsrErrorExample(heard: str, correct: str)`
  - `CraftPack(id, version, name: LocalizedText, languages, prompt_context, asr_error_examples, stages, terms)` dengan `variant_index() -> dict[str, PackRef]`, `stage(id) -> PackStage | None`, `term(id) -> PackTerm | None`
  - `PackRef(kind: Literal["term","stage"], id: str)` (NamedTuple)
  - `load_pack(pack_id: str, packs_dir: Path) -> CraftPack`, `list_packs(packs_dir: Path) -> list[CraftPack]`, `PackError(ValueError)`
  - fixture pytest `pack` (session scope)

- [ ] **Step 1: Pindahkan pack dan tambahkan contoh salah-dengar ASR**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
mkdir -p packs && git mv docs/packs/batik_tulis.yaml packs/batik_tulis.yaml
```

Tambahkan blok ini di `packs/batik_tulis.yaml` tepat setelah blok `prompt_context:` (sebelum `stages:`). Contoh ini dipakai di prompt Mode B supaya kode prompt tidak berisi istilah batik:

```yaml
# Contoh salah tulis pengenal suara umum, dari subtitle otomatis YouTube di uji kelayakan.
# Dipakai di prompt Mode B. Bukan daftar koreksi otomatis.
asr_error_examples:
  - {heard: "spang King", correct: spangkring}
  - {heard: "watera gelas", correct: waterglass}
  - {heard: ngelorot, correct: nglorod}
```

Ganti baris komentar `# Saat H1, file ini dipindah ke packs/batik_tulis.yaml dan divalidasi dengan Pydantic.` menjadi `# Divalidasi oleh api/empu/packs.py (tes: api/tests/test_packs.py).`

Kalau `hasil-gate0.md` mencatat prompt SAM canting yang lebih baik, ganti `sam_prompt` pada `canting`, `canting_klowongan`, `canting_cecekan`, `canting_tembokan` dengan prompt itu.

- [ ] **Step 2: Perbarui rujukan path.** Di `CLAUDE.md` butir 4 "Baca dulu", `docs/README.md` baris tabel #8, dan spec bagian 7 struktur repo, ganti `docs/packs/batik_tulis.yaml` menjadi `packs/batik_tulis.yaml`. Di `spikes/gate0/common.py` ganti `PACK_PATH = REPO / "docs" / "packs" / "batik_tulis.yaml"` menjadi `PACK_PATH = REPO / "packs" / "batik_tulis.yaml"`.

```bash
grep -rn "docs/packs" --include=*.md --include=*.py . | grep -v "superpowers/plans"
```
Expected setelah edit: tidak ada keluaran.

- [ ] **Step 3: Tulis tes yang gagal**

```python
# api/tests/test_packs.py
import copy

import pytest
import yaml

from conftest import REPO_ROOT
from empu.packs import CraftPack, PackError, PackRef, list_packs, load_pack

PACK_FILE = REPO_ROOT / "packs" / "batik_tulis.yaml"


def raw_pack() -> dict:
    return yaml.safe_load(PACK_FILE.read_text())


def test_real_pack_loads(pack):
    assert pack.id == "batik_tulis"
    assert len(pack.stages) == 13
    assert len(pack.terms) == 42
    assert pack.asr_error_examples[0].correct == "spangkring"


def test_variant_index_resolves_terms_and_stages(pack):
    idx = pack.variant_index()
    assert idx["tjanting"] == PackRef("term", "canting")
    assert idx["canting klowongan"] == PackRef("term", "canting_klowongan")
    assert idx["ngelorot"] == PackRef("stage", "nglorod")
    assert idx["hcl"] == PackRef("term", "hcl")
    assert idx["persiapan kain"] == PackRef("stage", "persiapan_kain")


def test_lookup_helpers(pack):
    assert pack.stage("nglorod").label.en == "Wax removal by boiling"
    assert pack.term("canting").visual is True
    assert pack.stage("missing") is None
    assert pack.stage("persiapan_kain").display_label == "persiapan kain"


def test_duplicate_variant_rejected():
    data = raw_pack()
    data["terms"][1]["variants"].append("tjanting")  # already a canting variant
    with pytest.raises(ValueError, match="tjanting"):
        CraftPack.model_validate(data)


def test_variant_shared_with_stage_rejected():
    data = raw_pack()
    data["terms"][0]["variants"].append("ngelorod")
    with pytest.raises(ValueError, match="ngelorod"):
        CraftPack.model_validate(data)


def test_unknown_stage_reference_rejected():
    data = raw_pack()
    data["terms"][0]["stage"] = "no_such_stage"
    with pytest.raises(ValueError, match="no_such_stage"):
        CraftPack.model_validate(data)


def test_visual_requires_sam_prompt():
    data = raw_pack()
    data["terms"][0]["sam_prompt"] = None
    with pytest.raises(ValueError, match="sam_prompt"):
        CraftPack.model_validate(data)


def test_duplicate_ids_rejected():
    data = raw_pack()
    data["terms"].append(copy.deepcopy(data["terms"][0]))
    with pytest.raises(ValueError, match="duplicate term ids"):
        CraftPack.model_validate(data)


def test_load_pack_errors(tmp_path):
    with pytest.raises(PackError, match="not found"):
        load_pack("nope", tmp_path)
    (tmp_path / "bad.yaml").write_text("id: other\nversion: 1\n")
    with pytest.raises(PackError):
        load_pack("bad", tmp_path)


def test_list_packs():
    assert "batik_tulis" in [p.id for p in list_packs(REPO_ROOT / "packs")]
```

```python
# api/tests/test_no_hardcoded_terms.py
"""Craft knowledge lives only in packs/. No craft term may appear in api/empu/**."""

import re

from conftest import REPO_ROOT
from empu.text import normalize

ALLOW = {"finishing", "other"}


def craft_words(pack) -> set[str]:
    words = set()
    for s in pack.stages:
        words |= {normalize(s.id), *(normalize(v) for v in s.variants)}
    for t in pack.terms:
        words |= {normalize(t.id), normalize(t.label), *(normalize(v) for v in t.variants)}
    return {w for w in words if len(w) >= 4 and w not in ALLOW}


def test_no_craft_terms_in_package(pack):
    words = craft_words(pack)
    offenders = []
    for path in (REPO_ROOT / "api" / "empu").rglob("*.py"):
        text = normalize(path.read_text())
        for w in words:
            if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text):
                offenders.append(f"{path.name}: {w}")
    assert offenders == [], offenders
```

Tambahkan fixture `pack` ke `api/tests/conftest.py`:

```python
from empu.packs import CraftPack, load_pack


@pytest.fixture(scope="session")
def pack() -> CraftPack:
    return load_pack("batik_tulis", REPO_ROOT / "packs")
```

- [ ] **Step 4: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_packs.py tests/test_no_hardcoded_terms.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.packs'`.

- [ ] **Step 5: Tulis `api/empu/packs.py`**

```python
"""Craft pack loader. All craft knowledge lives in packs/*.yaml, never in code."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from empu.enums import Category
from empu.text import normalize


class PackError(ValueError):
    pass


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    en: str


class PackStage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: LocalizedText
    variants: list[str] = []

    @property
    def display_label(self) -> str:
        return self.id.replace("_", " ")


class PackTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    category: Category
    variants: list[str] = []
    stage: str | None = None
    gloss_id: str
    gloss_en: str
    visual: bool = False
    sam_prompt: str | None = None
    verified: bool = False


class AsrErrorExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heard: str
    correct: str


class PackRef(NamedTuple):
    kind: Literal["term", "stage"]
    id: str


class CraftPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    version: str
    name: LocalizedText
    languages: list[str]
    prompt_context: str
    asr_error_examples: list[AsrErrorExample] = []
    stages: list[PackStage]
    terms: list[PackTerm]

    def _forms(self) -> Iterator[tuple[PackRef, set[str]]]:
        for s in self.stages:
            yield PackRef("stage", s.id), {s.id, s.label.id, *s.variants}
        for t in self.terms:
            yield PackRef("term", t.id), {t.id, t.label, *t.variants}

    @model_validator(mode="after")
    def _check(self) -> CraftPack:
        errors: list[str] = []
        for kind, ids in (("stage", [s.id for s in self.stages]), ("term", [t.id for t in self.terms])):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                errors.append(f"duplicate {kind} ids: {dup}")
        known = {s.id for s in self.stages}
        for t in self.terms:
            if t.stage and t.stage not in known:
                errors.append(f"term {t.id}: unknown stage {t.stage}")
            if t.visual and not t.sam_prompt:
                errors.append(f"term {t.id}: visual=true requires sam_prompt")
        owner: dict[str, PackRef] = {}
        for ref, forms in self._forms():
            for form in forms:
                key = normalize(form)
                if not key:
                    continue
                prev = owner.setdefault(key, ref)
                if prev != ref:
                    errors.append(f"variant '{form}' used by {prev.kind}:{prev.id} and {ref.kind}:{ref.id}")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def variant_index(self) -> dict[str, PackRef]:
        index: dict[str, PackRef] = {}
        for ref, forms in self._forms():
            for form in forms:
                if key := normalize(form):
                    index[key] = ref
        return index

    def stage(self, stage_id: str | None) -> PackStage | None:
        return next((s for s in self.stages if s.id == stage_id), None)

    def term(self, term_id: str | None) -> PackTerm | None:
        return next((t for t in self.terms if t.id == term_id), None)


def load_pack(pack_id: str, packs_dir: Path) -> CraftPack:
    path = Path(packs_dir) / f"{pack_id}.yaml"
    if not path.exists():
        raise PackError(f"pack {pack_id!r} not found in {packs_dir}")
    try:
        pack = CraftPack.model_validate(yaml.safe_load(path.read_text()))
    except (ValidationError, ValueError) as e:
        raise PackError(f"pack {pack_id!r} is invalid: {e}") from e
    if pack.id != pack_id:
        raise PackError(f"pack file {path.name} declares id {pack.id!r}")
    return pack


def list_packs(packs_dir: Path) -> list[CraftPack]:
    return [load_pack(p.stem, packs_dir) for p in sorted(Path(packs_dir).glob("*.yaml"))]
```

- [ ] **Step 6: Jalankan tes**

Run: `cd api && uv run pytest -q`
Expected: semua lulus. Kalau `test_real_pack_loads` gagal karena bentrok varian, perbaiki data di `packs/batik_tulis.yaml`, bukan validatornya.

- [ ] **Step 7: Commit**

```bash
git add packs api/empu/packs.py api/tests CLAUDE.md docs/README.md docs/superpowers/specs/2026-10-28-empu-design.md spikes/gate0/common.py
git commit -m "feat(api): craft pack loader with validation; move pack to packs/"
```

---

### Task H1-4: Kontrak keluaran Muse, pemetaan enum v1, fixture

**Files:**
- Create: `api/empu/resources/__init__.py` (kosong), `api/empu/resources/muse-output.schema.json` (salinan)
- Create: `api/empu/muse_schema.py`, `api/empu/legacy.py`
- Create: `api/tests/fixtures/muse/`, `api/tests/fixtures/sam/` (salinan fixture)
- Test: `api/tests/test_muse_schema.py`

**Interfaces:**
- Consumes: enum `Category`, `Source`, `VisualMatch`, `Confidence`
- Produces:
  - `MuseTerm` (field persis skema v3), `MuseProcessStep(step, t_start, t_end, tools)`, `MuseSegmentOutput(speech_heard, language_notes, transcript_excerpt, terms, process_steps)`
  - `load_json_schema(variant: Literal["full","stripped"] = "full") -> dict`
  - `upgrade_v1(d: dict) -> dict`
  - Fixture: `fixtures/muse/v1/{nglowong,kontrol-musik-nglorod,proses-lengkap-ngertibatik}.json`, `fixtures/muse/v1/nglowong.raw.json`, `fixtures/muse/gate0/*.raw.json`, `fixtures/sam/sam-canting.raw.json`

- [ ] **Step 1: Salin skema dan fixture**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
mkdir -p api/empu/resources api/tests/fixtures/muse/v1 api/tests/fixtures/muse/gate0 api/tests/fixtures/sam
touch api/empu/resources/__init__.py
cp docs/reference/muse-output.schema.json api/empu/resources/
for f in nglowong kontrol-musik-nglorod proses-lengkap-ngertibatik; do cp docs/reference/uji-kelayakan/hasil-v1/$f.json api/tests/fixtures/muse/v1/; done
cp docs/reference/uji-kelayakan/hasil-v1/nglowong.raw.json api/tests/fixtures/muse/v1/
cp docs/reference/uji-kelayakan/hasil-gate0/recall-seg*.raw.json docs/reference/uji-kelayakan/hasil-gate0/structured.raw.json api/tests/fixtures/muse/gate0/ 2>/dev/null
cp docs/reference/uji-kelayakan/hasil-gate0/sam-canting.raw.json api/tests/fixtures/sam/ 2>/dev/null
ls -R api/tests/fixtures
```
Expected: tiga JSON dan satu raw di `v1/`; file Gate 0 yang tersedia di `gate0/` dan `sam/`.

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_muse_schema.py
import json

import pytest
from pydantic import ValidationError

from conftest import REPO_ROOT, load_fixture
from empu.enums import Confidence, Source, VisualMatch
from empu.legacy import upgrade_v1
from empu.muse_schema import MuseSegmentOutput, MuseTerm, load_json_schema


def term(**kw) -> dict:
    base = {
        "spoken": "x", "term": "x", "category": "tool", "source": "speech",
        "t_start": 1.0, "t_end": 2.0, "stage": None, "evidence_quote": "", "visible": "",
        "visible_object_en": None, "visual_match": "yes", "gloss_id": "", "gloss_en": "",
        "confidence": "high",
    }
    return base | kw


def test_schema_copy_matches_docs():
    docs = json.loads((REPO_ROOT / "docs/reference/muse-output.schema.json").read_text())
    assert load_json_schema() == docs


def test_stripped_schema_has_no_length_keywords():
    text = json.dumps(load_json_schema("stripped"))
    assert "maxLength" not in text and "minimum" not in text and "$schema" not in text


def test_valid_term_parses():
    t = MuseTerm.model_validate(term())
    assert t.source is Source.speech and t.confidence is Confidence.high


def test_legacy_enums_coerced():
    t = MuseTerm.model_validate(term(source="teks_layar", visual_match="tidak_terlihat", confidence="sedang"))
    assert t.source is Source.on_screen_text
    assert t.visual_match is VisualMatch.not_visible
    assert t.confidence is Confidence.medium


def test_unknown_category_falls_back_to_other():
    assert MuseTerm.model_validate(term(category="pattern")).category == "other"


def test_bad_source_rejected():
    with pytest.raises(ValidationError):
        MuseTerm.model_validate(term(source="audio"))


def test_times_sanitized_and_quote_truncated():
    t = MuseTerm.model_validate(term(t_start=-1, t_end=-3, evidence_quote="a" * 400, spoken=""))
    assert t.t_start == 0.0 and t.t_end == 0.0
    assert len(t.evidence_quote) == 160
    assert t.spoken == "x"


def test_empty_term_rejected():
    with pytest.raises(ValidationError):
        MuseTerm.model_validate(term(term="  "))


def test_segment_requires_terms_key():
    with pytest.raises(ValidationError):
        MuseSegmentOutput.model_validate({"speech_heard": True, "process_steps": []})


def test_transcript_truncated():
    out = MuseSegmentOutput.model_validate({"terms": [], "transcript_excerpt": "y" * 500})
    assert len(out.transcript_excerpt) == 300


def test_upgrade_v1_nglowong():
    out = MuseSegmentOutput.model_validate(upgrade_v1(load_fixture("muse/v1/nglowong.json")))
    assert len(out.terms) == 12
    assert all(t.source is Source.speech for t in out.terms)
    assert out.terms[0].visual_match is VisualMatch.not_visible
    assert out.transcript_excerpt.startswith("Halo teman-teman")


def test_upgrade_v1_control_has_no_terms():
    out = MuseSegmentOutput.model_validate(upgrade_v1(load_fixture("muse/v1/kontrol-musik-nglorod.json")))
    assert out.terms == [] and len(out.process_steps) > 0
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_muse_schema.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.legacy'`.

- [ ] **Step 4: Tulis `api/empu/muse_schema.py`**

```python
"""Contract for Muse output per segment (resources/muse-output.schema.json, v3).

Validation is lenient where it is safe (unknown category -> other, legacy Indonesian
enums -> English) and strict where it matters (source, term, times).
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from empu.enums import Category, Confidence, Source, VisualMatch

LEGACY_ENUMS = {
    "ucapan": "speech", "teks_layar": "on_screen_text", "visual": "visual_only",
    "ya": "yes", "tidak": "no", "tidak_terlihat": "not_visible",
    "rendah": "low", "sedang": "medium", "tinggi": "high",
}
_STRIP_KEYS = {"maxLength", "minimum", "$schema", "$id", "title", "description"}


def _enum_key(v: Any) -> Any:
    if isinstance(v, str):
        k = v.strip().lower().replace(" ", "_").replace("-", "_")
        return LEGACY_ENUMS.get(k, k)
    return v


class MuseTerm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    spoken: str = ""
    term: str
    category: Category = Category.other
    source: Source
    t_start: float
    t_end: float
    stage: str | None = None
    evidence_quote: str = ""
    visible: str = ""
    visible_object_en: str | None = None
    visual_match: VisualMatch = VisualMatch.not_visible
    gloss_id: str = ""
    gloss_en: str = ""
    confidence: Confidence = Confidence.low

    @field_validator("source", mode="before")
    @classmethod
    def _source(cls, v: Any) -> Any:
        return _enum_key(v)

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in Category.__members__ else Category.other

    @field_validator("visual_match", mode="before")
    @classmethod
    def _visual_match(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in VisualMatch.__members__ else VisualMatch.not_visible

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in Confidence.__members__ else Confidence.low

    @field_validator("visible_object_en", "stage", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        return None if isinstance(v, str) and not v.strip() else v

    @model_validator(mode="after")
    def _sanitize(self) -> MuseTerm:
        self.term = self.term.strip()
        if not self.term:
            raise ValueError("term is empty")
        self.spoken = self.spoken.strip() or self.term
        self.t_start = max(0.0, float(self.t_start))
        self.t_end = max(self.t_start, float(self.t_end))
        self.evidence_quote = self.evidence_quote[:160]
        return self


class MuseProcessStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    step: str
    t_start: float
    t_end: float
    tools: list[str] = []

    @model_validator(mode="after")
    def _sanitize(self) -> MuseProcessStep:
        self.t_start = max(0.0, float(self.t_start))
        self.t_end = max(self.t_start, float(self.t_end))
        return self


class MuseSegmentOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    speech_heard: bool = False
    language_notes: str = ""
    transcript_excerpt: str = ""
    terms: list[MuseTerm]
    process_steps: list[MuseProcessStep] = []

    @field_validator("transcript_excerpt", mode="after")
    @classmethod
    def _truncate(cls, v: str) -> str:
        return v[:300]


def _strip(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip(v) for k, v in node.items() if k not in _STRIP_KEYS}
    if isinstance(node, list):
        return [_strip(v) for v in node]
    return node


@cache
def _schema_text() -> str:
    return files("empu.resources").joinpath("muse-output.schema.json").read_text()


def load_json_schema(variant: Literal["full", "stripped"] = "full") -> dict:
    schema = json.loads(_schema_text())
    return _strip(schema) if variant == "stripped" else schema
```

- [ ] **Step 5: Tulis `api/empu/legacy.py`**

```python
"""Upgrade feasibility-test (v1) Muse output to the v3 contract. Used for fixtures only."""

from __future__ import annotations

from typing import Any


def upgrade_v1(d: dict[str, Any]) -> dict[str, Any]:
    out = {
        "speech_heard": bool(d.get("speech_heard", False)),
        "language_notes": d.get("language_notes", ""),
        "transcript_excerpt": d.get("transcript_excerpt") or d.get("transcript_first_20s", ""),
        "terms": [],
        "process_steps": d.get("process_steps", []),
    }
    for t in d.get("terms", []):
        out["terms"].append({
            "spoken": t.get("spoken", ""),
            "term": t.get("term") or t.get("spoken", ""),
            "category": t.get("category", "other"),
            "source": t.get("source", "speech"),
            "t_start": t.get("t_start", 0),
            "t_end": t.get("t_end", t.get("t_start", 0)),
            "stage": t.get("stage"),
            "evidence_quote": t.get("evidence_quote", ""),
            "visible": t.get("visible", ""),
            "visible_object_en": t.get("visible_object_en"),
            "visual_match": t.get("visual_match", "not_visible"),
            "gloss_id": t.get("gloss_id", ""),
            "gloss_en": t.get("gloss_en", ""),
            "confidence": t.get("confidence", "low"),
        })
    return out
```

- [ ] **Step 6: Jalankan tes**

Run: `cd api && uv run pytest tests/test_muse_schema.py -q`
Expected: `12 passed`.

- [ ] **Step 7: Commit**

```bash
git add api/empu/resources api/empu/muse_schema.py api/empu/legacy.py api/tests
git commit -m "feat(api): Muse v3 output contract, v1 enum upgrade, fixtures"
```

---

### Task H1-5: `meta_client.py`

**Files:**
- Create: `api/empu/meta_client.py`
- Create: `api/tests/fakes.py`
- Test: `api/tests/test_meta_client.py`

**Interfaces:**
- Consumes: `Settings.require_api_key()`, `Settings.meta_base_url`
- Produces:
  - `MetaAPIError(status_code: int | None, message: str)` dengan properti `retryable: bool`
  - `AnalyzeResult(raw: dict, text: str, parsed: dict | None, parse_error: str | None, usage: dict, latency_s: float)`
  - `Detection(label: str, score: float, bbox_xyxy: tuple[float, float, float, float], mask_png_bytes: bytes | None = None)` (dipakai H2-6)
  - `TranscriptSegment(t_start: float, t_end: float, text: str)` (dipakai H1-8 dan H2-10)
  - `output_text(resp: dict) -> str`, `extract_json(text: str) -> dict` (melempar `ValueError`)
  - `MetaClient(api_key, base_url="https://api.meta.ai/v1", *, http=None, max_retries=4, backoff_s=2.0)`; `MetaClient.from_settings(settings)`; `.upload_file(path, mime="video/mp4") -> str`; `.create_response(body, *, timeout=900) -> dict`; `.analyze_video(file_id, prompt, *, model, schema=None, max_output_tokens=16000) -> AnalyzeResult`; `.close()`
  - `tests/fakes.py`: `make_raw(payload: dict | str, usage: dict | None = None) -> dict`, `FakeClient(responses=None, detections=None)` dengan `upload_file`, `analyze_video`, `segment_image`, dan perekam `uploads`, `prompts`, `schemas`, `sam_calls`

- [ ] **Step 1: Tulis `api/tests/fakes.py`**

```python
"""Test doubles. Never touches the network."""

from __future__ import annotations

import json
from pathlib import Path

from empu.meta_client import AnalyzeResult, Detection, extract_json, output_text


def make_raw(payload: dict | str, usage: dict | None = None) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {
        "object": "response",
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]},
        ],
        "usage": usage or {"input_tokens": 100, "output_tokens": 20,
                           "output_tokens_details": {"reasoning_tokens": 5}},
    }


class FakeClient:
    """Mimics MetaClient. `responses` are raw Responses-API dicts, consumed in order."""

    def __init__(self, responses: list[dict] | None = None,
                 detections: list[Detection] | None = None) -> None:
        self.responses = list(responses or [])
        self.detections = detections or []
        self.uploads: list[Path] = []
        self.prompts: list[str] = []
        self.schemas: list[dict | None] = []
        self.sam_calls: list[tuple[Path, list[str]]] = []

    def upload_file(self, path: Path, mime: str = "video/mp4") -> str:
        self.uploads.append(Path(path))
        return f"file_{len(self.uploads)}"

    def analyze_video(self, file_id: str, prompt: str, *, model: str, schema: dict | None = None,
                      max_output_tokens: int = 16000) -> AnalyzeResult:
        self.prompts.append(prompt)
        self.schemas.append(schema)
        if not self.responses:
            raise AssertionError("FakeClient ran out of responses")
        raw = self.responses.pop(0)
        text = output_text(raw)
        try:
            parsed, err = extract_json(text), None
        except ValueError as e:
            parsed, err = None, str(e)
        return AnalyzeResult(raw=raw, text=text, parsed=parsed, parse_error=err,
                             usage=raw.get("usage", {}), latency_s=0.5)

    def segment_image(self, image_path: Path, prompts: list[str], *, model: str) -> list[Detection]:
        self.sam_calls.append((Path(image_path), list(prompts)))
        return list(self.detections)
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# api/tests/test_meta_client.py
import json

import httpx
import pytest
import respx

from conftest import FIXTURES, load_fixture
from empu.meta_client import MetaAPIError, MetaClient, extract_json, output_text
from empu.muse_schema import MuseSegmentOutput

BASE = "https://api.test/v1"


@pytest.fixture
def video(tmp_path):
    p = tmp_path / "seg.mp4"
    p.write_bytes(b"\x00fake-video")
    return p


def client() -> MetaClient:
    return MetaClient("secret-key", BASE, backoff_s=0)


@respx.mock
def test_upload_sends_auth_and_purpose(video):
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(200, json={"id": "file_1"}))
    assert client().upload_file(video) == "file_1"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer secret-key"
    assert b'name="purpose"' in req.content and b"user_data" in req.content


@respx.mock
def test_retries_429_then_succeeds(video):
    route = respx.post(f"{BASE}/files").mock(side_effect=[
        httpx.Response(429, text="slow down"), httpx.Response(200, json={"id": "file_2"})])
    assert client().upload_file(video) == "file_2"
    assert route.call_count == 2


@respx.mock
def test_gives_up_after_four_retries(video):
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(503, text="down"))
    with pytest.raises(MetaAPIError) as e:
        client().upload_file(video)
    assert e.value.status_code == 503
    assert route.call_count == 5


@respx.mock
def test_no_retry_on_400(video):
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(400, text="bad"))
    with pytest.raises(MetaAPIError):
        client().upload_file(video)
    assert route.call_count == 1


@respx.mock
def test_retries_transport_error(video):
    route = respx.post(f"{BASE}/files").mock(side_effect=[
        httpx.ConnectError("boom"), httpx.Response(200, json={"id": "file_3"})])
    assert client().upload_file(video) == "file_3"
    assert route.call_count == 2


@respx.mock
def test_analyze_video_body_and_parse():
    raw = load_fixture("muse/v1/nglowong.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    res = client().analyze_video("file_9", "PROMPT", model="muse-spark-1.3")
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "muse-spark-1.3"
    assert body["input"][0]["content"][0] == {"type": "input_video", "file_id": "file_9"}
    assert body["input"][0]["content"][1] == {"type": "input_text", "text": "PROMPT"}
    assert "text" not in body
    assert res.parse_error is None and len(res.parsed["terms"]) == 12
    assert res.usage["input_tokens"] == 36271
    assert res.latency_s >= 0


@respx.mock
def test_analyze_video_with_schema_sets_text_format():
    raw = load_fixture("muse/v1/nglowong.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    client().analyze_video("f", "P", model="m", schema={"type": "object"})
    fmt = json.loads(route.calls.last.request.content)["text"]["format"]
    assert fmt == {"type": "json_schema", "name": "empu_terms", "schema": {"type": "object"}, "strict": True}


@respx.mock
def test_analyze_video_unparseable_text_keeps_raw():
    raw = {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": "sorry, no json"}]}], "usage": {}}
    respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    res = client().analyze_video("f", "P", model="m")
    assert res.parsed is None and "no JSON" in res.parse_error and res.raw == raw


@respx.mock
def test_incomplete_response_raises_without_retry():
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(
        200, json={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}))
    with pytest.raises(MetaAPIError, match="incomplete"):
        client().analyze_video("f", "P", model="m")
    assert route.call_count == 1


def test_repr_hides_key():
    assert "secret-key" not in repr(client())


def test_output_text_and_extract_json():
    raw = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "```json\n{\"a\": 1}\n```"}]}]}
    assert extract_json(output_text(raw)) == {"a": 1}
    assert extract_json('Here you go: {"terms": []} thanks') == {"terms": []}
    echoed = '{"type": "object", "properties": {"terms": {"type": "array"}}} {"terms": [], "speech_heard": true}'
    assert extract_json(echoed) == {"terms": [], "speech_heard": True}
    assert output_text({"output_text": "{}"}) == "{}"
    with pytest.raises(ValueError):
        extract_json("[1, 2]")
    with pytest.raises(ValueError):
        extract_json("nothing")


@pytest.mark.skipif(not (FIXTURES / "muse/gate0/recall-seg0.raw.json").exists(), reason="gate0 fixture missing")
def test_gate0_v3_output_validates_without_upgrade():
    raw = load_fixture("muse/gate0/recall-seg0.raw.json")
    MuseSegmentOutput.model_validate(extract_json(output_text(raw)))
```

- [ ] **Step 3: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_meta_client.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.meta_client'`.

- [ ] **Step 4: Tulis `api/empu/meta_client.py`**

```python
"""The only gateway to the Meta Model API.

Never log request headers or the API key. Callers own caching (empu.cache).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential, wait_none

T = TypeVar("T")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


class MetaAPIError(RuntimeError):
    def __init__(self, status_code: int | None, message: str) -> None:
        super().__init__(f"Meta API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message

    @property
    def retryable(self) -> bool:
        return self.status_code == 429 or (self.status_code is not None and self.status_code >= 500)


@dataclass
class AnalyzeResult:
    raw: dict
    text: str
    parsed: dict | None
    parse_error: str | None
    usage: dict
    latency_s: float


@dataclass
class Detection:
    label: str
    score: float
    bbox_xyxy: tuple[float, float, float, float]
    mask_png_bytes: bytes | None = None


@dataclass
class TranscriptSegment:
    t_start: float
    t_end: float
    text: str


def output_text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts: list[str] = []
    for item in resp.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts)


def extract_json(text: str) -> dict:
    """Return the answer object from model text.

    Without structured output, Muse sometimes echoes the JSON schema from the prompt before
    its answer. Prefer the first object whose "terms" is a list; otherwise the first object.
    """
    cleaned = _FENCE.sub("", text.strip())
    try:
        obj: Any = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    first: dict | None = None
    for m in re.finditer(r"\{", cleaned):
        try:
            obj, _ = decoder.raw_decode(cleaned, m.start())
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("terms"), list):
            return obj
        if first is None:
            first = obj
    if first is None:
        raise ValueError("no JSON object in model output")
    return first


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, httpx.TransportError) or (isinstance(exc, MetaAPIError) and exc.retryable)


class MetaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.meta.ai/v1", *,
                 http: httpx.Client | None = None, max_retries: int = 4,
                 backoff_s: float = 2.0) -> None:
        self._http = http or httpx.Client(timeout=httpx.Timeout(900, connect=30))
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._max_retries = max_retries
        self._backoff_s = backoff_s

    def __repr__(self) -> str:
        return f"MetaClient(base_url={self._base!r})"

    @classmethod
    def from_settings(cls, settings: Any) -> MetaClient:
        return cls(settings.require_api_key(), settings.meta_base_url)

    def close(self) -> None:
        self._http.close()

    def _retry(self, fn: Callable[[], T]) -> T:
        wait = wait_exponential(multiplier=self._backoff_s, max=60) if self._backoff_s else wait_none()
        retrying = Retrying(stop=stop_after_attempt(self._max_retries + 1), wait=wait,
                            retry=retry_if_exception(_retryable), reraise=True)
        return retrying(fn)

    def _send(self, method: str, path: str, *, timeout: float, **kwargs: Any) -> dict:
        r = self._http.request(method, f"{self._base}{path}", headers=self._headers,
                               timeout=timeout, **kwargs)
        if r.status_code >= 400:
            raise MetaAPIError(r.status_code, r.text[:1000])
        return r.json()

    def upload_file(self, path: Path, mime: str = "video/mp4") -> str:
        path = Path(path)

        def send() -> dict:
            with path.open("rb") as f:
                return self._send("POST", "/files", timeout=600,
                                  files={"file": (path.name, f, mime)}, data={"purpose": "user_data"})

        return self._retry(send)["id"]

    def create_response(self, body: dict, *, timeout: float = 900) -> dict:
        raw = self._retry(lambda: self._send("POST", "/responses", timeout=timeout, json=body))
        status = raw.get("status")
        if status not in (None, "completed"):
            raise MetaAPIError(200, f"response status {status}: {raw.get('incomplete_details')}")
        return raw

    def analyze_video(self, file_id: str, prompt: str, *, model: str, schema: dict | None = None,
                      max_output_tokens: int = 16000) -> AnalyzeResult:
        body: dict[str, Any] = {
            "model": model,
            "max_output_tokens": max_output_tokens,
            "input": [{"role": "user", "content": [
                {"type": "input_video", "file_id": file_id},
                {"type": "input_text", "text": prompt},
            ]}],
        }
        if schema is not None:
            body["text"] = {"format": {"type": "json_schema", "name": "empu_terms",
                                       "schema": schema, "strict": True}}
        t0 = time.monotonic()
        raw = self.create_response(body)
        latency = time.monotonic() - t0
        text = output_text(raw)
        try:
            parsed, err = extract_json(text), None
        except ValueError as e:
            parsed, err = None, str(e)
        return AnalyzeResult(raw=raw, text=text, parsed=parsed, parse_error=err,
                             usage=raw.get("usage") or {}, latency_s=latency)
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest -q`
Expected: semua lulus, termasuk `test_gate0_v3_output_validates_without_upgrade` kalau fixture Gate 0 ada. Kalau tes Gate 0 gagal validasi, baca pesan Pydantic. Longgarkan validator `MuseTerm` hanya untuk variasi yang wajar (mis. `confidence: "Tinggi"`); jangan pernah melonggarkan `source`.

- [ ] **Step 6: Commit**

```bash
git add api/empu/meta_client.py api/tests/fakes.py api/tests/test_meta_client.py
git commit -m "feat(api): meta_client with retry, response parsing, fake client"
```

---

### Task H1-6: Cache respons mentah

**Files:**
- Create: `api/empu/cache.py`
- Test: `api/tests/test_cache.py`

**Interfaces:**
- Produces: `sha256_file(path: Path) -> str`; `ResponseCache(root: Path)` dengan `key(segment_sha256, model, prompt_version, mode) -> str` (staticmethod), `path(key) -> Path`, `get(key) -> dict | None`, `put(key, payload: dict) -> Path`. Payload yang ditulis `analyze_chunk`: `{raw, usage, latency_s, file_id, model, prompt_version, mode, created_at}`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_cache.py
import hashlib

from empu.cache import ResponseCache, sha256_file


def test_sha256_file(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"hello")
    assert sha256_file(p) == hashlib.sha256(b"hello").hexdigest()


def test_key_contains_all_parts_and_is_filesystem_safe():
    k = ResponseCache.key("abc", "muse-spark-1.3", "analyze-v3", "A")
    assert k == "abc__muse-spark-1.3__analyze-v3__A"
    assert ResponseCache.key("abc", "m/x", "v", "A") == "abc__m_x__v__A"
    keys = {ResponseCache.key(*parts) for parts in [
        ("abc", "m", "v3", "A"), ("abd", "m", "v3", "A"), ("abc", "n", "v3", "A"),
        ("abc", "m", "v4", "A"), ("abc", "m", "v3", "B")]}
    assert len(keys) == 5


def test_roundtrip_and_miss(tmp_path):
    cache = ResponseCache(tmp_path / "cache")
    assert cache.get("missing") is None
    path = cache.put("k1", {"raw": {"x": 1}, "usage": {}})
    assert path == tmp_path / "cache" / "k1.json"
    assert cache.get("k1") == {"raw": {"x": 1}, "usage": {}}
    assert list((tmp_path / "cache").glob("*.tmp")) == []
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_cache.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.cache'`.

- [ ] **Step 3: Tulis `api/empu/cache.py`**

```python
"""Raw Meta API response cache keyed by segment hash + model + prompt version + mode."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(chunk_size):
            h.update(block)
    return h.hexdigest()


class ResponseCache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def key(segment_sha256: str, model: str, prompt_version: str, mode: str) -> str:
        return "__".join(_UNSAFE.sub("_", p) for p in (segment_sha256, model, prompt_version, mode))

    def path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key: str, payload: dict) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        dst = self.path(key)
        tmp = dst.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False))
        os.replace(tmp, dst)
        return dst
```

- [ ] **Step 4: Jalankan tes**

Run: `cd api && uv run pytest tests/test_cache.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/empu/cache.py api/tests/test_cache.py
git commit -m "feat(api): raw response cache"
```

---

### Task H1-7: ffmpeg, normalisasi, dan pemotongan segmen

**Files:**
- Create: `api/empu/pipeline/__init__.py` (kosong), `api/empu/pipeline/ffmpeg.py`, `api/empu/pipeline/normalize.py`, `api/empu/pipeline/chunk.py`
- Modify: `api/tests/conftest.py` (fixture `sample_video`, marker `requires_ffmpeg`)
- Test: `api/tests/test_chunk.py`, `api/tests/test_normalize.py`

**Interfaces:**
- Produces:
  - `FFmpegError(RuntimeError)`, `run_ffmpeg(args: list[str]) -> None`, `ffmpeg_to(dst: Path, args: list[str]) -> Path` (tulis ke file sementara lalu rename), `probe_duration(path) -> float`, `probe_height(path) -> int`, `has_audio(path) -> bool`
  - `NormalizedMedia(analysis_path: Path, display_path: Path, duration_s: float)`, `normalize_recording(src, out_dir, *, strip_audio=False) -> NormalizedMedia`; konstanta `ANALYSIS_VIDEO`, `ANALYSIS_AUDIO`
  - `ChunkSpec(idx: int, start_s: float, end_s: float)` dengan properti `duration_s`; `plan_chunks(duration_s, window_s=75.0, overlap_s=10.0) -> list[ChunkSpec]`; `cut_chunk(src, spec, dst) -> Path`; `cut_chunks(src, specs, out_dir) -> list[Path]` (nama file `<idx>.mp4`)
  - Fixture `sample_video` (video 12 detik 640×360 + nada sinus), `requires_ffmpeg`

- [ ] **Step 1: Tambahkan fixture ke `api/tests/conftest.py`**

```python
import shutil
import subprocess

requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory) -> Path:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    out = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out),
    ], check=True)
    return out
```

- [ ] **Step 2: Tulis tes yang gagal untuk rencana segmen**

```python
# api/tests/test_chunk.py
import pytest

from conftest import requires_ffmpeg
from empu.pipeline.chunk import ChunkSpec, cut_chunks, plan_chunks
from empu.pipeline.ffmpeg import probe_duration


def starts(specs):
    return [s.start_s for s in specs]


def test_five_minutes_gives_five_segments():
    specs = plan_chunks(300)
    assert starts(specs) == [0, 65, 130, 195, 260]
    assert specs[-1].end_s == 300
    assert [s.idx for s in specs] == [0, 1, 2, 3, 4]


def test_241s_gives_four_segments():
    specs = plan_chunks(241)
    assert [(s.start_s, s.end_s) for s in specs] == [(0, 75), (65, 140), (130, 205), (195, 241)]


def test_short_and_boundary_durations():
    assert plan_chunks(60) == [ChunkSpec(0, 0, 60)]
    assert plan_chunks(75) == [ChunkSpec(0, 0, 75)]
    assert [(s.start_s, s.end_s) for s in plan_chunks(76)] == [(0, 75), (65, 76)]


def test_invalid_arguments():
    with pytest.raises(ValueError):
        plan_chunks(0)
    with pytest.raises(ValueError):
        plan_chunks(100, window_s=10, overlap_s=10)


def test_duration_property():
    assert ChunkSpec(1, 65, 140).duration_s == 75


@requires_ffmpeg
def test_cut_chunks_real_video(sample_video, tmp_path):
    specs = plan_chunks(12, window_s=5, overlap_s=1)
    assert starts(specs) == [0, 4, 8]
    paths = cut_chunks(sample_video, specs, tmp_path / "chunks")
    assert [p.stem for p in paths] == ["0", "1", "2"]
    assert abs(probe_duration(paths[0]) - 5) < 0.3
    assert abs(probe_duration(paths[2]) - 4) < 0.3
```

<!-- H1-7c -->
