# H6 (Sel 3 Nov): Izin End-to-End, Sandbox, Deploy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pencabutan izin menyembunyikan turunan; juri punya sandbox 3 menit; URL publik stabil dengan arsip demo tervalidasi; README siap juri.

**Architecture:** `withdraw_consent` set `consent_status=withdrawn` (visibility H4 menyembunyikan). Sandbox = arsip `is_sandbox=True`, upload tanpa studio key, kuota harian, durasi ≤ 180 s. Produksi: Docker Compose (web, api, worker, caddy). `/media` produksi: Caddy `file_server` + `forward_auth` ke `/api/media-auth` (D6); fallback proxy ke FastAPI.

**Tech Stack:** FastAPI, Docker, Caddy 2, SQLite volume.

## Global Constraints

Semua butir `00-ikhtisar.md`. File tidak dihapus saat cabut izin. Sandbox tidak tampil di daftar publik. Rahasia hanya di `.env`. Video tidak di-commit.
- `/try` mode Mori, `UploadForm variant="try"`, copy sandbox brief, izin tetap wajib, kuota habis: "Today's sandbox uploads are used up. The archive is still open to explore."
- Cabut izin: `ConfirmDialog` copy brief, bukan `window.confirm`.
- Polesan H6 = empty state yang belum ada. **Jangan redesign token/layout** — itu H3/H4. Kalau Mori belum kebaca, itu utang H4, bukan pekerjaan Selasa malam.

## Prasyarat
Gate 2: `latest.json` ada. Kamus demo berisi entri accepted.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/consent.py` | Create | `withdraw_consent` |
| `api/empu/routes/recordings.py` | Modify | POST withdraw |
| `api/empu/routes/sandbox.py` | Create | upload tanpa key |
| `api/empu/routes/jobs.py` | Modify | job sandbox tanpa key |
| `api/empu/routes/public.py` | Modify | skip `is_sandbox` |
| `api/empu/pipeline/run.py` | Modify | batas 180 s sandbox |
| `deploy/*` | Create | compose, Caddy, Dockerfiles |
| `README.md` | Create | juri |
| `web/app/try/page.tsx` | Create | form sandbox |

---

### Task H6-1: Cabut izin

**Files:**
- Create: `api/empu/consent.py`
- Modify: `api/empu/routes/recordings.py`, `web/components/Studio.tsx`
- Test: `api/tests/test_consent.py`

**Interfaces:** `withdraw_consent(session, recording_id: int) -> Recording`

- [ ] **Step 1: Tes**

```python
# api/tests/test_consent.py
from empu.consent import withdraw_consent
from empu.enums import AccessLevel, Category, ConsentStatus, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence
from empu.visibility import public_entries, public_occurrences
from factories import make_archive, make_recording


def test_withdraw_hides_public_entries(session):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.own_recording)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
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
```

Tambah `consent_status` ke `RecordingOut` (H3 sudah punya).

- [ ] **Step 2: Fail, lalu**

```python
# api/empu/consent.py
from sqlmodel import Session

from empu.enums import ConsentStatus
from empu.models import Recording, utcnow


def withdraw_consent(session: Session, recording_id: int) -> Recording:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise ValueError("recording not found")
    rec.consent_status = ConsentStatus.withdrawn
    rec.consent_withdrawn_at = utcnow()
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec
```

Route (butuh studio key, sudah di router recordings):

```python
from empu.consent import withdraw_consent

@router.post("/api/recordings/{recording_id}/withdraw-consent", response_model=RecordingOut)
def withdraw(recording_id: int, session: Session = Depends(get_session)) -> RecordingOut:
    try:
        rec = withdraw_consent(session, recording_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    rec, job, contrib = _load_recording(session, rec.id)
    return recording_out(rec, job=job, contributor=contrib)
```

Studio: tombol yang `confirm("Hide this recording from the public dictionary?")` lalu POST.

- [ ] **Step 3:** pytest lulus. Commit `feat: withdraw consent hides public descendants`.

---

### Task H6-2: Sandbox juri

**Files:**
- Create: `api/empu/routes/sandbox.py`
- Modify: `jobs.py`, `public.py`, `pipeline/run.py`
- Test: `api/tests/test_sandbox.py`

**Interfaces:**
- `ensure_sandbox_archive(session, settings) -> Archive` slug `sandbox`, `is_sandbox=True`, `is_demo=False`
- `sandbox_quota_remaining(session, settings) -> int`
- `POST /api/sandbox/recordings` tanpa key, Form sama seperti upload (consent wajib)
- Job/recording/entries sandbox: GET tanpa key **hanya** jika `archive.is_sandbox`

- [ ] **Step 1: Tes**

```python
# api/tests/test_sandbox.py
from empu.models import Archive, Recording


def test_sandbox_upload_without_key(api, tmp_path, session):
    api.headers.pop("X-Studio-Key", None)
    r = api.post(
        "/api/sandbox/recordings",
        data={"title": "Judge clip", "consent_confirmed": "true"},
        files={"file": ("a.mp4", b"xxxxx", "video/mp4")},
    )
    assert r.status_code == 201
    rec = session.get(Recording, r.json()["recording_id"])
    arch = session.get(Archive, rec.archive_id)
    assert arch.is_sandbox is True


def test_sandbox_hidden_from_public_list(api, session):
    api.headers.pop("X-Studio-Key", None)
    # ensure sandbox exists
    api.post("/api/sandbox/recordings",
             data={"title": "x", "consent_confirmed": "true"},
             files={"file": ("a.mp4", b"xxxxx", "video/mp4")})
    slugs = [a["slug"] for a in api.get("/api/public/archives").json()]
    assert "sandbox" not in slugs


def test_non_sandbox_job_still_401(api, session):
    from factories import make_archive, make_recording
    from empu.models import Job
    from empu.enums import JobStatus
    a = make_archive(session)
    rec = make_recording(session, a)
    job = Job(recording_id=rec.id, status=JobStatus.queued)
    session.add(job); session.commit(); session.refresh(job)
    api.headers.pop("X-Studio-Key", None)
    assert api.get(f"/api/jobs/{job.id}").status_code == 401
```

- [ ] **Step 2: Implementasi**

```python
# api/empu/routes/sandbox.py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, func, select
from datetime import UTC, datetime

from empu.api_schemas import UploadAck
from empu.auth import optional_studio
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.enums import AccessLevel, SourceKind
from empu.intake import IntakeError, RecordingMeta, create_recording, get_or_create_archive
from empu.models import Archive, Job, Recording

router = APIRouter()


def ensure_sandbox_archive(session: Session) -> Archive:
    return get_or_create_archive(session, "sandbox", title="Judge sandbox",
                                 pack_id="batik_tulis", is_sandbox=True)


def sandbox_quota_remaining(session: Session, settings: Settings) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    arch = session.exec(select(Archive).where(Archive.slug == "sandbox")).first()
    if arch is None:
        return settings.sandbox_daily_quota
    n = session.exec(
        select(func.count()).select_from(Job).join(Recording).where(
            Recording.archive_id == arch.id, Job.created_at >= start)
    ).one()
    return max(0, settings.sandbox_daily_quota - int(n))


@router.post("/api/sandbox/recordings", response_model=UploadAck, status_code=201)
async def sandbox_upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    consent_confirmed: str = Form(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadAck:
    if consent_confirmed.strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(400, "consent_confirmed must be true")
    if sandbox_quota_remaining(session, settings) <= 0:
        raise HTTPException(429, "daily sandbox quota reached")
    arch = ensure_sandbox_archive(session)
    # reuse size check from recordings.upload_recording: write to temp then create_recording
    from pathlib import Path
    import tempfile, shutil
    suffix = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    max_bytes = min(settings.max_upload_mb, 80) * 1024 * 1024
    total = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as disk:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(413, "sandbox upload too large")
            disk.write(chunk)
        src = Path(disk.name)
    try:
        meta = RecordingMeta(title=title, consent_confirmed=True, consent_scope=AccessLevel.public,
                             source_kind=SourceKind.own_recording, contributor_name="Sandbox visitor")
        rec, job = create_recording(session, settings, arch, src, meta, filename=file.filename or "upload.mp4")
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        src.unlink(missing_ok=True)
    return UploadAck(recording_id=rec.id, job_id=job.id)
```

Pindahkan `tempfile, shutil, Path` ke atas. `optional_studio` diimpor tidak dipakai — hapus.

`jobs.py`: ganti `require_studio` di app.py untuk jobs router. Lepas dependency global; di handler:

```python
from empu.auth import optional_studio
from empu.models import Archive, Recording

@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session),
            auth=Depends(optional_studio)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    rec = session.get(Recording, job.recording_id)
    arch = session.get(Archive, rec.archive_id) if rec else None
    if not auth.has_key and not (arch and arch.is_sandbox):
        raise HTTPException(401, "studio key required")
    return job_out(job)
```

Sama untuk `GET /api/recordings/{id}` dan `GET /api/recordings/{id}/entries` dan `POST /api/entries/{id}/review` jika arsip sandbox. Review sandbox tanpa key: izinkan `actor=judge`.

`public.py` list: `if a.is_sandbox: continue`.

`process_recording` setelah probe duration:

```python
arch = session.get(Archive, recording.archive_id)
if arch and arch.is_sandbox and media.duration_s > settings.sandbox_max_duration_s:
    raise PipelineError("sandbox recordings are limited to 3 minutes")
```

`app.include_router(sandbox.router)` tanpa studio key.

Web `/try`: salin UploadForm tanpa StudioKeyGate, POST `/api/sandbox/recordings`, redirect `/studio/jobs/{id}`. StudioKeyGate harus membiarkan halaman job sandbox (kalau 401, tampilkan progress tanpa key — fetch tanpa header).

Commit: `feat: judge sandbox upload with daily quota`.

---

### Task H6-3: Docker + Caddy

**Files:**
- Create: `deploy/api.Dockerfile`, `deploy/web.Dockerfile`, `deploy/docker-compose.yml`, `deploy/Caddyfile`, `.dockerignore`

```dockerfile
# deploy/api.Dockerfile
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY api/pyproject.toml api/uv.lock api/.python-version /app/
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY api/empu /app/empu
COPY packs /packs
ENV EMPU_PACKS_DIR=/packs PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "empu.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# deploy/web.Dockerfile
FROM node:24-bookworm-slim AS deps
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
FROM deps AS build
COPY web ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build
FROM node:24-bookworm-slim
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web/.next/standalone ./
COPY --from=build /web/.next/static ./.next/static
COPY --from=build /web/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

Next harus `output: "standalone"` di `next.config.ts` (tambah di H3-6 sekarang kalau belum: `output: "standalone"`).

```yaml
# deploy/docker-compose.yml
services:
  api:
    build: { context: .., dockerfile: deploy/api.Dockerfile }
    env_file: ../.env
    environment:
      EMPU_DATA_DIR: /data
      EMPU_PACKS_DIR: /packs
    volumes: ["../data:/data"]
    restart: unless-stopped
  worker:
    build: { context: .., dockerfile: deploy/api.Dockerfile }
    command: uv run python -m empu.worker
    env_file: ../.env
    environment:
      EMPU_DATA_DIR: /data
      EMPU_PACKS_DIR: /packs
    volumes: ["../data:/data"]
    restart: unless-stopped
  web:
    build: { context: .., dockerfile: deploy/web.Dockerfile }
    environment:
      EMPU_API_ORIGIN: http://api:8000
    restart: unless-stopped
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ../data:/srv/media
      - caddy_data:/data
    environment:
      EMPU_DOMAIN: ${EMPU_DOMAIN}
    depends_on: [api, web]
volumes:
  caddy_data:
```

```
# deploy/Caddyfile
{$EMPU_DOMAIN} {
  encode gzip
  handle /api/* {
    reverse_proxy api:8000
  }
  handle /media/* {
    reverse_proxy api:8000
  }
  handle {
    reverse_proxy web:3000
  }
}
```

Mulai dengan proxy `/media` ke API (Range sudah terbukti). Jangan habiskan hari pada `forward_auth`. Kalau sempat dan lulus tes seek: ganti handle `/media` ke `file_server` + `forward_auth uri /api/media-auth` dengan `root * /srv/media` dan `uri strip_prefix /media`.

`.dockerignore` di root: `.venv`, `data-uji`, `arsip-hidup-batik`, `.env`, `web/node_modules`, `web/.next`.

Uji: `docker compose -f deploy/docker-compose.yml up --build` → `curl -f http://localhost/api/health`.

Commit: `chore(deploy): compose, Caddy, Dockerfiles`.

---

### Task H6-4: Deploy VPS, seed, README

Rsync `data/empu.db` dan `data/archives/` ke VPS (hasil validasi lokal). Jangan proses ulang berbayar di server kecuali cache Muse ikut tersalin (`data/cache/`).

`README.md`:

```markdown
# Empu — Batik Tulis Edition

Capture what masters know, before it's gone.

Empu turns a master's narrated work video into a watchable, validated craft dictionary. Each term links to the original speech, a motion clip, and a crop of the real tool. AI proposes; a human decides. Nothing is public until a validator accepts it.

**Live:** https://<domain>
**Dictionary:** /d/hidup-batik · **Evidence:** /evidence · **Try (3 min):** /try

## Attribution
Demo clips are YouTube videos under CC BY 3.0. Creators: Batik Education; TEBAK teras batik kaindra. Clips are trimmed. Full credit is on each entry.

## Validation
"Validated by the expert" means the recording's maker checked that entry. Other public entries were validated by the documenter.

## Stack
Muse Spark 1.3 · SAM 3.1 (original-frame crops) · faster-whisper (time realignment) · YAML craft packs (no batik terms hardcoded in pipeline code)

## Local
See CLAUDE.md. Copy `.env.example` to `.env`.
```

Polesan UI maksimal 60 menit: empty state kamus, 404 entri, kuota sandbox, fokus keyboard `--wax`. Token/layout sudah di H3–H4 (`desain.md`). Jangan redesign. Jangan ganti tagline.

CLAUDE.md: `H6 (Sel 3 Nov): URL publik + sandbox + README. Berikutnya: H7 demo dan submission.`

## Selesai kalau
- [ ] HTTPS membuka kamus demo
- [ ] Withdraw diuji: entri hilang dari `/d/...`
- [ ] Sandbox 1 klip pendek tanpa key (atau dipotong)
- [ ] README di root

## Kalau pukul 17:00 belum
Sandbox dipotong. URL + kamus demo + Bukti tidak boleh.
