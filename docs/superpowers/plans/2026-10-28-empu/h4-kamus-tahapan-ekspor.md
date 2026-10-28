# H4 (Min 1 Nov): Visibilitas Publik, Kamus, Peta Tahapan, Ekspor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kamus publik menampilkan hanya entri tervalidasi berizin, lengkap dengan klip, atribusi, peta tahapan per rekaman, dan ekspor JSON/CSV/ELAN/ZIP.

**Architecture:** Satu modul `visibility.py` adalah satu-satunya sumber aturan publik. API publik (`/api/public/*`) dan ekspor `scope=public` memanggil fungsi yang sama. `scope=all` butuh studio key (D3). Frontend mode **Mori**: S1 beranda, S5 kamus+detail, S6 peta tahapan; S7 ekspor mode Malam. Layout dan copy: `desain.md`. Kalau pukul 17:00, S5b + S5 dulu, baru S1.

**Tech Stack:** FastAPI, pympi-ling, zipfile, Next.js 16.

## Global Constraints

Semua butir `00-ikhtisar.md`. Khusus fase ini:
- Publik hanya jika `entry.status ∈ {accepted, edited}` **dan** `entry.access_level = public` **dan** rekaman sumber `consent_status = granted` **dan** `consent_scope = public` **dan** `source_kind ≠ internal_eval`.
- Rekaman `cc_by_video` wajib `source_url`, `source_creator`, `license`, `attribution` sebelum publik.
- Kemunculan dari rekaman dicabut tidak pernah tampil. Kalau kemunculan publik suatu entri habis, entri ikut tersembunyi.
- Label `source` wajib di JSON, CSV, ELAN, UI.
- D3: `scope=all` = semua entri kecuali `rejected`/`merged`, termasuk `proposed` dan `private`; kemunculan izin-dicabut tetap dikecualikan.
- "Validated by the expert · {name}" hanya jika `review_event.actor` bukan documenter. `DOCUMENTER_ACTORS = {"documenter", "syafiq"}`. Copy persis `desain.md`.
- Visual: Mori, Fraunces untuk kata kepala, bukti sebelum glosa, `CropView` bingkai tetap, atribusi kartu di detail. Jangan pakai kerangka S1/S5 di bawah kalau bertentangan dengan `desain.md`.

## Prasyarat
- H3: Studio bisa Accept. ≥5 entri `accepted` pada arsip demo CC BY.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/visibility.py` | Create | aturan publik |
| `api/empu/media.py` | Modify | `can_access_media` memakai visibility |
| `api/empu/api_schemas.py` | Modify | `validation_label` pada `EntryOut` |
| `api/empu/routes/public.py` | Create | `/api/public/*` |
| `api/empu/export/{__init__,common,json_export,csv_export,eaf_export,zip_export}.py` | Create | ekspor |
| `api/empu/routes/exports.py` | Create | `GET /api/archives/{id}/export` |
| `api/empu/app.py` | Modify | pasang router publik + export |
| `web/app/page.tsx` | Modify | S1 |
| `web/app/d/[slug]/page.tsx` | Create | kamus |
| `web/app/d/[slug]/[id]/page.tsx` | Create | detail |
| `web/app/d/[slug]/map/[recordingId]/page.tsx` | Create | peta tahapan |
| `web/app/studio/export/page.tsx` | Create | S7 |

---

### Task H4-1: `visibility.py` dan media publik

**Files:**
- Create: `api/empu/visibility.py`
- Modify: `api/empu/media.py`
- Test: `api/tests/test_visibility.py`

**Interfaces:**
- Consumes: `Recording`, `Entry`, `Occurrence`, `ReviewEvent`
- Produces: `DOCUMENTER_ACTORS`; `recording_is_public(rec) -> bool`; `occurrence_is_public(occ, rec) -> bool`; `public_occurrences(session, entry_id) -> list[Occurrence]`; `entry_is_public(entry, public_occs) -> bool`; `public_entries(session, archive_id) -> list[tuple[Entry, list[Occurrence]]]`; `validated_by_expert(session, entry_id) -> bool`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# api/tests/test_visibility.py
from empu.enums import AccessLevel, Category, ConsentStatus, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence
from empu.visibility import entry_is_public, public_entries, public_occurrences, recording_is_public
from factories import make_archive, make_recording


def _pub_rec(session, a, **kw):
    return make_recording(
        session, a,
        consent_status=ConsentStatus.granted, consent_scope=AccessLevel.public,
        source_kind=SourceKind.cc_by_video, source_url="https://youtu.be/x",
        source_creator="Batik Education", license="CC BY 3.0",
        attribution="clip by Batik Education", **kw,
    )


def test_internal_eval_never_public(session):
    a = make_archive(session)
    rec = make_recording(session, a, source_kind=SourceKind.internal_eval,
                         consent_scope=AccessLevel.private)
    assert recording_is_public(rec) is False


def test_cc_by_missing_attribution_not_public(session):
    a = make_archive(session)
    rec = make_recording(session, a, source_kind=SourceKind.cc_by_video, source_url="https://x",
                         consent_scope=AccessLevel.public)
    assert recording_is_public(rec) is False


def test_entry_hidden_when_no_public_occurrence(session):
    a = make_archive(session)
    rec = _pub_rec(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    assert public_occurrences(session, e.id)
    rec.consent_status = ConsentStatus.withdrawn
    session.add(rec); session.commit()
    assert public_occurrences(session, e.id) == []
    assert entry_is_public(e, []) is False


def test_proposed_not_public():
    e = Entry(archive_id=1, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.proposed, access_level=AccessLevel.public)
    assert entry_is_public(e, []) is False


def test_public_entries_skips_rejected(session):
    a = make_archive(session)
    rec = _pub_rec(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.rejected, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    assert public_entries(session, a.id) == []
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd api && uv run pytest tests/test_visibility.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'empu.visibility'`.

- [ ] **Step 3: Tulis `api/empu/visibility.py`**

```python
from sqlmodel import Session, select

from empu.enums import AccessLevel, ConsentStatus, EntryStatus, OccurrenceStatus, SourceKind
from empu.models import Entry, Occurrence, Recording, ReviewEvent

DOCUMENTER_ACTORS = {"documenter", "syafiq"}


def recording_is_public(rec: Recording) -> bool:
    if rec.consent_status is not ConsentStatus.granted:
        return False
    if rec.consent_scope is not AccessLevel.public:
        return False
    if rec.source_kind is SourceKind.internal_eval:
        return False
    if rec.source_kind is SourceKind.cc_by_video:
        return all([rec.source_url, rec.source_creator, rec.license, rec.attribution])
    return True


def occurrence_is_public(occ: Occurrence, rec: Recording) -> bool:
    if occ.status is OccurrenceStatus.rejected:
        return False
    return recording_is_public(rec)


def public_occurrences(session: Session, entry_id: int) -> list[Occurrence]:
    occs = session.exec(select(Occurrence).where(Occurrence.entry_id == entry_id)).all()
    out: list[Occurrence] = []
    for o in occs:
        rec = session.get(Recording, o.recording_id)
        if rec is not None and occurrence_is_public(o, rec):
            out.append(o)
    return out


def entry_is_public(entry: Entry, public_occs: list[Occurrence]) -> bool:
    if entry.status not in (EntryStatus.accepted, EntryStatus.edited):
        return False
    if entry.access_level is not AccessLevel.public:
        return False
    return len(public_occs) > 0


def public_entries(session: Session, archive_id: int) -> list[tuple[Entry, list[Occurrence]]]:
    entries = session.exec(select(Entry).where(Entry.archive_id == archive_id)).all()
    result = []
    for e in entries:
        occs = public_occurrences(session, e.id)
        if entry_is_public(e, occs):
            result.append((e, occs))
    result.sort(key=lambda pair: pair[0].term.casefold())
    return result


def validated_by_expert(session: Session, entry_id: int) -> bool:
    events = session.exec(select(ReviewEvent).where(ReviewEvent.entry_id == entry_id)).all()
    return any(ev.actor.strip().lower() not in DOCUMENTER_ACTORS for ev in events)
```

- [ ] **Step 4: Ganti `can_access_media` di `api/empu/media.py`**

Impor di atas: `from empu.visibility import entry_is_public, public_occurrences, recording_is_public` dan `from empu.models import Entry, Recording`. Fungsi lengkap:

```python
def can_access_media(session: Session, rel_path: str, *, has_key: bool) -> bool:
    rel = rel_path.lstrip("/")
    parts = PurePosixPath(rel).parts
    if has_key:
        if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "recordings":
            try:
                rec = session.get(Recording, int(parts[3]))
            except ValueError:
                return False
            return rec is not None and rec.consent_status is not ConsentStatus.withdrawn
        return bool(parts) and parts[0] == "archives"
    if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "recordings":
        try:
            rec = session.get(Recording, int(parts[3]))
        except ValueError:
            return False
        return rec is not None and recording_is_public(rec)
    if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "entries":
        try:
            entry = session.get(Entry, int(parts[3]))
        except ValueError:
            return False
        if entry is None:
            return False
        return entry_is_public(entry, public_occurrences(session, entry.id))
    return False
```

- [ ] **Step 5: Jalankan tes**

Run: `cd api && uv run pytest tests/test_visibility.py tests/test_api_media.py -q`
Expected: lulus. Tambah tes di `test_api_media.py`: rekaman publik, `TestClient` tanpa kunci, `GET /media/{display}` → 200.

- [ ] **Step 6: Commit**

```bash
git add api/empu/visibility.py api/empu/media.py api/tests
git commit -m "feat(api): public visibility rules; media access without studio key"
```

---

### Task H4-2: API publik

**Files:**
- Create: `api/empu/routes/public.py`
- Modify: `api/empu/app.py`, `api/empu/api_schemas.py` (`validation_label: str = "validated by the documenter"` pada `EntryOut`), `api/empu/serialize.py` (parameter `validation_label: str | None = None`)
- Test: `api/tests/test_api_public.py`

**Interfaces:**
- Produces: `GET /api/public/archives`, `/archives/{slug}`, `/archives/{slug}/entries`, `/entries/{id}` tanpa auth. 404 (bukan 401) untuk yang tidak publik.

- [ ] **Step 1: Tes**

```python
# api/tests/test_api_public.py
from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence
from factories import make_archive, make_recording


def _setup(session):
    a = make_archive(session, slug="hidup-batik", title="Living Archive", is_demo=True)
    rec = make_recording(
        session, a, consent_scope=AccessLevel.public, source_kind=SourceKind.cc_by_video,
        source_url="https://youtu.be/x", source_creator="c", license="CC BY 3.0",
        attribution="by c",
    )
    e = Entry(archive_id=a.id, canon_key="term:canting", term="canting", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public, gloss_en="wax pen")
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    return a, e


def test_public_list_no_key(api, session):
    _setup(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get("/api/public/archives")
    assert r.status_code == 200 and r.json()[0]["slug"] == "hidup-batik"


def test_proposed_not_listed(api, session):
    a, e = _setup(session)
    e.status = EntryStatus.proposed
    session.add(e); session.commit()
    api.headers.pop("X-Studio-Key", None)
    r = api.get("/api/public/archives/hidup-batik/entries")
    assert r.json() == []


def test_unknown_id_is_404(api, session):
    api.headers.pop("X-Studio-Key", None)
    assert api.get("/api/public/entries/99999").status_code == 404
```

- [ ] **Step 2: Jalankan, pastikan gagal** (404 semua path).

- [ ] **Step 3: Implementasi**

```python
# api/empu/routes/public.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from empu.api_schemas import ArchiveOut, EntryListItem, EntryOut
from empu.db import get_session
from empu.models import Archive, Contributor, Entry, Recording
from empu.serialize import archive_out, entry_list_item, entry_out
from empu.visibility import entry_is_public, public_entries, public_occurrences, validated_by_expert

router = APIRouter()


def _archive_by_slug(session: Session, slug: str) -> Archive:
    a = session.exec(select(Archive).where(Archive.slug == slug)).first()
    if a is None:
        raise HTTPException(404, "archive not found")
    return a


@router.get("/api/public/archives", response_model=list[ArchiveOut])
def list_public_archives(session: Session = Depends(get_session)) -> list[ArchiveOut]:
    rows = session.exec(select(Archive).order_by(Archive.is_demo.desc(), Archive.id)).all()
    out = []
    for a in rows:
        pubs = public_entries(session, a.id)
        if not pubs and not a.is_demo:
            continue
        n_rec = len({o.recording_id for _, occs in pubs for o in occs})
        out.append(archive_out(a, recording_count=n_rec, validated_count=len(pubs)))
    return out


@router.get("/api/public/archives/{slug}", response_model=ArchiveOut)
def get_public_archive(slug: str, session: Session = Depends(get_session)) -> ArchiveOut:
    a = _archive_by_slug(session, slug)
    pubs = public_entries(session, a.id)
    n_rec = len({o.recording_id for _, occs in pubs for o in occs})
    return archive_out(a, recording_count=n_rec, validated_count=len(pubs))


@router.get("/api/public/archives/{slug}/entries", response_model=list[EntryListItem])
def public_archive_entries(
    slug: str, q: str | None = None, category: str | None = None, stage: str | None = None,
    session: Session = Depends(get_session),
) -> list[EntryListItem]:
    a = _archive_by_slug(session, slug)
    items = []
    for e, occs in public_entries(session, a.id):
        if category and e.category.value != category:
            continue
        if stage and e.stage_id != stage:
            continue
        if q:
            blob = f"{e.term} {e.gloss_id} {e.gloss_en}".casefold()
            if q.casefold() not in blob:
                continue
        items.append(entry_list_item(e, occs))
    return items


@router.get("/api/public/entries/{entry_id}", response_model=EntryOut)
def get_public_entry(entry_id: int, session: Session = Depends(get_session)) -> EntryOut:
    e = session.get(Entry, entry_id)
    if e is None:
        raise HTTPException(404, "not found")
    occs = public_occurrences(session, e.id)
    if not entry_is_public(e, occs):
        raise HTTPException(404, "not found")
    rec = session.get(Recording, occs[0].recording_id)
    contrib = session.get(Contributor, rec.contributor_id) if rec and rec.contributor_id else None
    label = "validated by the expert" if validated_by_expert(session, e.id) else "validated by the documenter"
    return entry_out(
        e, occs, recording_title=rec.title if rec else "",
        contributor_name=contrib.name if contrib else None,
        attribution=rec.attribution if rec else None,
        validation_label=label,
    )
```

`entry_out` di H3 belum punya `validation_label`. Tambah argumen terakhir default `None`; kalau diisi, set `EntryOut.validation_label`.

`app.py`: `app.include_router(public.router)` tanpa `require_studio`.

- [ ] **Step 4:** `cd api && uv run pytest tests/test_api_public.py tests/test_serialize.py -q` → lulus.

```bash
git add api/empu/routes/public.py api/empu/app.py api/empu/api_schemas.py api/empu/serialize.py api/tests
git commit -m "feat(api): public archive and entry endpoints"
```

---

### Task H4-3: Ekspor JSON dan CSV

**Files:**
- Create: `api/empu/export/__init__.py` (kosong), `common.py`, `json_export.py`, `csv_export.py`
- Test: `api/tests/test_export.py`

**Interfaces:**
- `ExportScope = Literal["public", "all"]`
- `entries_for_scope(session, archive_id, scope) -> list[tuple[Entry, list[Occurrence]]]`
- `manifest(archive, pack, scope) -> dict`
- `build_json(session, archive, pack, scope) -> dict`
- `build_csv(rows, session) -> str` dengan header spec 12

- [ ] **Step 1: Tes**

```python
# api/tests/test_export.py
import csv
import io

from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.export.common import entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.json_export import build_json
from empu.models import Entry, Occurrence
from factories import make_archive, make_recording


def test_scope_public_hides_proposed(session, pack):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.cc_by_video, source_url="u",
                         source_creator="c", license="CC BY 3.0", attribution="a")
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.proposed, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    assert entries_for_scope(session, a.id, "public") == []
    assert len(entries_for_scope(session, a.id, "all")) == 1


def test_csv_has_source_column(session, pack):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.own_recording)
    e = Entry(archive_id=a.id, canon_key="term:x", term="canting", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public, gloss_id="pena")
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.on_screen_text,
                           t_start=5, t_end=6))
    session.commit()
    text = build_csv(entries_for_scope(session, a.id, "public"), session)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["source"] == "on_screen_text"
    assert "clip_path" in rows[0]


def test_json_includes_attribution_for_cc_by(session, pack):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.cc_by_video, source_url="https://youtu.be/x",
                         source_creator="Batik Education", license="CC BY 3.0",
                         attribution="by Batik Education")
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    doc = build_json(session, a, pack, "public")
    assert doc["recordings"][0]["license"] == "CC BY 3.0"
    assert doc["entries"][0]["occurrences"][0]["source"] == "speech"
```

- [ ] **Step 2: Fail, lalu implementasi**

```python
# api/empu/export/common.py
from datetime import UTC, datetime
from typing import Literal

from sqlmodel import Session, select

from empu.enums import ConsentStatus, EntryStatus
from empu.models import Archive, Entry, Occurrence, Recording
from empu.packs import CraftPack
from empu.visibility import public_entries

ExportScope = Literal["public", "all"]


def entries_for_scope(session: Session, archive_id: int, scope: ExportScope):
    if scope == "public":
        return public_entries(session, archive_id)
    entries = session.exec(select(Entry).where(
        Entry.archive_id == archive_id,
        ~Entry.status.in_((EntryStatus.rejected, EntryStatus.merged)),
    )).all()
    rows = []
    for e in entries:
        occs = []
        for o in session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all():
            rec = session.get(Recording, o.recording_id)
            if rec is None or rec.consent_status is ConsentStatus.withdrawn:
                continue
            occs.append(o)
        rows.append((e, occs))
    return rows


def manifest(archive: Archive, pack: CraftPack, scope: ExportScope) -> dict:
    return {
        "archive": archive.title,
        "archive_slug": archive.slug,
        "craft_pack": {"id": pack.id, "version": pack.version},
        "scope": scope,
        "exported_at": datetime.now(UTC).isoformat(),
        "license": archive.license,
        "note": "Media clips are trimmed from source recordings. CC BY sources retain creator attribution.",
    }
```

```python
# api/empu/export/csv_export.py
import csv
import io

from sqlmodel import Session

from empu.models import Contributor, Recording

HEADERS = [
    "term", "category", "stage", "gloss_id", "gloss_en", "variants", "is_novel",
    "status", "access_level", "maestro", "recording", "t_start", "t_end", "source",
    "confidence", "clip_path",
]


def build_csv(rows, session: Session) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADERS)
    w.writeheader()
    for entry, occs in rows:
        variants = "|".join(entry.variants_json or [])
        targets = occs or [None]
        for o in targets:
            rec = session.get(Recording, o.recording_id) if o else None
            contrib = session.get(Contributor, rec.contributor_id) if rec and rec.contributor_id else None
            w.writerow({
                "term": entry.term, "category": entry.category.value, "stage": entry.stage_id or "",
                "gloss_id": entry.gloss_id, "gloss_en": entry.gloss_en, "variants": variants,
                "is_novel": entry.is_novel, "status": entry.status.value,
                "access_level": entry.access_level.value,
                "maestro": contrib.name if contrib else "",
                "recording": rec.title if rec else "",
                "t_start": o.t_start if o else "", "t_end": o.t_end if o else "",
                "source": o.source.value if o else "",
                "confidence": o.confidence.value if o else "",
                "clip_path": (o.clip_path or "") if o else "",
            })
    return buf.getvalue()
```

```python
# api/empu/export/json_export.py
from sqlmodel import Session, select

from empu.export.common import ExportScope, entries_for_scope, manifest
from empu.models import Archive, Contributor, ProcessStep, Recording
from empu.packs import CraftPack


def build_json(session: Session, archive: Archive, pack: CraftPack, scope: ExportScope) -> dict:
    rows = entries_for_scope(session, archive.id, scope)
    rec_ids = {o.recording_id for _, occs in rows for o in occs}
    recordings = [session.get(Recording, i) for i in sorted(rec_ids)]
    contrib_ids = {r.contributor_id for r in recordings if r and r.contributor_id}
    contributors = [session.get(Contributor, i) for i in contrib_ids]
    return {
        "manifest": manifest(archive, pack, scope),
        "contributors": [
            {"id": c.id, "name": c.name, "role": c.role.value, "region": c.region, "sanggar": c.sanggar}
            for c in contributors if c
        ],
        "recordings": [
            {
                "id": r.id, "title": r.title, "duration_s": r.duration_s,
                "consent_scope": r.consent_scope.value, "source_kind": r.source_kind.value,
                "source_url": r.source_url, "source_creator": r.source_creator,
                "license": r.license, "attribution": r.attribution,
                "display_path": r.display_path,
            }
            for r in recordings if r
        ],
        "entries": [
            {
                "id": e.id, "term": e.term, "category": e.category.value, "stage_id": e.stage_id,
                "gloss_id": e.gloss_id, "gloss_en": e.gloss_en, "variants": e.variants_json,
                "is_novel": e.is_novel, "status": e.status.value, "access_level": e.access_level.value,
                "occurrences": [
                    {
                        "id": o.id, "recording_id": o.recording_id, "spoken": o.spoken,
                        "source": o.source.value, "t_start": o.t_start, "t_end": o.t_end,
                        "confidence": o.confidence.value, "clip_path": o.clip_path,
                        "audio_path": o.audio_path, "keyframe_path": o.keyframe_path,
                    }
                    for o in occs
                ],
            }
            for e, occs in rows
        ],
        "process_maps": [
            {
                "recording_id": rid,
                "steps": [
                    {"name": s.name_raw, "pack_stage_id": s.pack_stage_id,
                     "t_start": s.t_start, "t_end": s.t_end, "tools": s.tools_json, "order": s.order}
                    for s in session.exec(
                        select(ProcessStep).where(ProcessStep.recording_id == rid).order_by(ProcessStep.order)
                    ).all()
                ],
            }
            for rid in sorted(rec_ids)
        ],
    }
```

- [ ] **Step 3:** `cd api && uv run pytest tests/test_export.py -q` → 3 passed.

```bash
git add api/empu/export api/tests/test_export.py
git commit -m "feat(export): JSON and CSV with source labels and CC BY fields"
```

---

### Task H4-4: Ekspor ELAN

**Files:**
- Create: `api/empu/export/eaf_export.py`
- Test: `api/tests/test_export_eaf.py`

**Interfaces:** `build_eaf(rec: Recording, rows) -> str`. Tier: `term`, `spoken`, `gloss-id`, `gloss-en`, `source`, `stage`. Media: `display.mp4`.

- [ ] **Step 1: Tes**

```python
# api/tests/test_export_eaf.py
from sqlmodel import select

from empu.enums import AccessLevel, Category, EntryStatus, Source
from empu.export.eaf_export import build_eaf
from empu.models import Entry, Occurrence
from factories import make_archive, make_recording


def test_eaf_has_source_tier(session):
    a = make_archive(session)
    rec = make_recording(session, a, display_path="archives/1/recordings/1/display.mp4",
                         duration_s=20, consent_scope=AccessLevel.public)
    e = Entry(archive_id=a.id, canon_key="term:x", term="canting", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public,
              gloss_id="pena", gloss_en="pen")
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech,
                           t_start=1.0, t_end=2.5, spoken="canting"))
    session.commit()
    occs = list(session.exec(select(Occurrence).where(Occurrence.recording_id == rec.id)).all())
    xml = build_eaf(rec, [(e, occs)])
    assert 'TIER_ID="source"' in xml
    assert "speech" in xml and "canting" in xml
```

- [ ] **Step 2: Implementasi**

```python
# api/empu/export/eaf_export.py
import os
import tempfile
from pathlib import Path

import pympi

from empu.models import Recording


def build_eaf(rec: Recording, rows: list) -> str:
    eaf = pympi.Elan.Eaf()
    media = rec.display_path or "display.mp4"
    eaf.add_linked_file(file_path=media, relpath=Path(media).name, mimetype="video/mp4")
    for tier in ("term", "spoken", "gloss-id", "gloss-en", "source", "stage"):
        if tier not in getattr(eaf, "tiers", {}):
            try:
                eaf.add_tier(tier)
            except Exception:
                pass
    for entry, occs in rows:
        for o in occs:
            if o.recording_id != rec.id:
                continue
            start = int(o.t_start * 1000)
            end = int(max(o.t_end, o.t_start + 0.1) * 1000)
            eaf.add_annotation("term", start, end, entry.term)
            eaf.add_annotation("spoken", start, end, o.spoken or entry.term)
            eaf.add_annotation("gloss-id", start, end, entry.gloss_id)
            eaf.add_annotation("gloss-en", start, end, entry.gloss_en)
            eaf.add_annotation("source", start, end, o.source.value)
            eaf.add_annotation("stage", start, end, entry.stage_id or o.stage_id or "")
    fd, path = tempfile.mkstemp(suffix=".eaf")
    os.close(fd)
    try:
        eaf.to_file(path)
        return Path(path).read_text()
    finally:
        os.unlink(path)
```

Jangan `except Exception` kosong kalau `add_tier` punya error spesifik. Kalau pympi sudah membuat `default` tier, `add_tier("term")` cukup. Tes akan gagal kalau nama atribut XML berbeda — sesuaikan assert ke keluaran pympi sungguhan (`TIER_ID` vs `TIER ID`).

- [ ] **Step 3:** pytest lulus. Commit `feat(export): ELAN eaf with source and stage tiers`.

---

### Task H4-5: ZIP + route ekspor

**Files:**
- Create: `api/empu/export/zip_export.py`, `api/empu/routes/exports.py`
- Modify: `app.py`
- Test: `api/tests/test_api_export.py`

**Interfaces:** `build_zip(session, archive, pack, scope, settings) -> bytes`; `GET /api/archives/{id}/export?format=json|csv|eaf|zip&scope=public|all`. `scope=all` tanpa kunci → 401.

- [ ] **Step 1: Tes**

```python
# api/tests/test_api_export.py
from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence
from factories import make_archive, make_recording


def test_all_scope_requires_key(api, session):
    a = make_archive(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/archives/{a.id}/export", params={"format": "json", "scope": "all"})
    assert r.status_code == 401


def test_public_json_ok(api, session):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.own_recording)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool,
              status=EntryStatus.accepted, access_level=AccessLevel.public)
    session.add(e); session.commit(); session.refresh(e)
    session.add(Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2))
    session.commit()
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/archives/{a.id}/export", params={"format": "json", "scope": "public"})
    assert r.status_code == 200
    assert r.json()["entries"][0]["occurrences"][0]["source"] == "speech"
```

- [ ] **Step 2: Implementasi**

```python
# api/empu/export/zip_export.py
import io
import json
import zipfile

from sqlmodel import Session

from empu.config import Settings
from empu.export.common import ExportScope, entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.eaf_export import build_eaf
from empu.export.json_export import build_json
from empu.media import abs_from_rel
from empu.models import Archive, Recording
from empu.packs import CraftPack


def build_zip(session: Session, archive: Archive, pack: CraftPack, scope: ExportScope,
              settings: Settings) -> bytes:
    rows = entries_for_scope(session, archive.id, scope)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("empu-dataset.json", json.dumps(build_json(session, archive, pack, scope),
                                                   ensure_ascii=False, indent=1))
        z.writestr("entries.csv", build_csv(rows, session))
        rec_ids = {o.recording_id for _, occs in rows for o in occs}
        for rid in rec_ids:
            rec = session.get(Recording, rid)
            if rec is None:
                continue
            subset = [(e, [o for o in occs if o.recording_id == rid]) for e, occs in rows]
            z.writestr(f"{rid}.eaf", build_eaf(rec, subset))
        copied: set[str] = set()
        for e, occs in rows:
            paths = [e.crop_path, e.overlay_path]
            for o in occs:
                paths.extend([o.clip_path, o.audio_path, o.keyframe_path])
            for rel in paths:
                if not rel or rel in copied:
                    continue
                try:
                    src = abs_from_rel(settings.data_dir, rel)
                except ValueError:
                    continue
                if src.is_file():
                    z.write(src, arcname=f"media/{rel}")
                    copied.add(rel)
        z.writestr("README.txt", _readme(archive, pack, rows, session))
    return buf.getvalue()


def _readme(archive: Archive, pack: CraftPack, rows, session: Session) -> str:
    lines = [
        f"Empu export — {archive.title}",
        f"Craft pack: {pack.id} {pack.version}",
        "Clips are trimmed from the source recordings.",
        "",
        "Attribution:",
    ]
    seen: set[int] = set()
    for _, occs in rows:
        for o in occs:
            rec = session.get(Recording, o.recording_id)
            if rec and rec.attribution and rec.id not in seen:
                seen.add(rec.id)
                extra = f" Source: {rec.source_url}" if rec.source_url else ""
                lines.append(f"- {rec.attribution}{extra}")
    lines += [
        "",
        "Data remains with the makers and their community (CARE principles).",
        "Not for sale or third-party model training without permission.",
        "",
    ]
    return "\n".join(lines)
```

```python
# api/empu/routes/exports.py
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session

from empu.auth import optional_studio
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.export.common import ExportScope, entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.eaf_export import build_eaf
from empu.export.json_export import build_json
from empu.export.zip_export import build_zip
from empu.models import Archive, Recording
from empu.packs import load_pack

router = APIRouter()


@router.get("/api/archives/{archive_id}/export")
def export_archive(
    archive_id: int,
    format: str = Query(..., pattern="^(json|csv|eaf|zip)$"),
    scope: ExportScope = Query("public"),
    session: Session = Depends(get_session),
    auth=Depends(optional_studio),
    settings: Settings = Depends(get_settings),
):
    if scope == "all" and not auth.has_key:
        raise HTTPException(401, "studio key required for scope=all")
    archive = session.get(Archive, archive_id)
    if archive is None:
        raise HTTPException(404, "archive not found")
    pack = load_pack(archive.craft_pack_id, settings.packs_dir)
    if format == "json":
        body = json.dumps(build_json(session, archive, pack, scope), ensure_ascii=False, indent=1)
        return Response(body, media_type="application/json")
    if format == "csv":
        return Response(build_csv(entries_for_scope(session, archive.id, scope), session),
                        media_type="text/csv")
    if format == "eaf":
        rows = entries_for_scope(session, archive.id, scope)
        rec_ids = {o.recording_id for _, occs in rows for o in occs}
        if len(rec_ids) != 1:
            raise HTTPException(400, "eaf export needs exactly one recording in scope; use zip")
        rec = session.get(Recording, next(iter(rec_ids)))
        return Response(build_eaf(rec, rows), media_type="application/xml")
    data = build_zip(session, archive, pack, scope, settings)
    return Response(
        data, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{archive.slug}-{scope}.zip"'},
    )
```

`app.include_router(exports.router)` tanpa `require_studio`.

- [ ] **Step 3:** pytest lulus. Commit `feat(api): archive export json/csv/eaf/zip`.

---

### Task H4-6: S1 Beranda

**Files:**
- Modify: `web/app/page.tsx`
- Create: `web/public/design/` (salin `nyanting-canting-122s.jpg` + `contoh-crop-canting.png` dari `docs/design/aset/`) + `web/public/design/README.md` (teks `aset/ATRIBUSI.md`)

Jangan fetch lewat `localhost:3000` (loop rewrite). Server component fetch `EMPU_API_ORIGIN`. Layout **persis** `desain.md` S1: hero wordmark + tagline + paragraf brief + 3 CTA + frame asli dengan kartu entri menempel + 3 langkah + 4 prinsip + kartu arsip + visi + footer. Jangan pakai kerangka satu-paragraf di bawah sebagai produk akhir — itu tulang saja.

Copy wajib:
- Tagline: `Capture what masters know, before it's gone.`
- Paragraf: brief bagian 8
- Tombol: `Open the Batik Tulis archive` · `Try it with a 3-minute clip` · `See the evidence`
- Langkah 2 adalah satu-satunya tempat nama model ditonjolkan
- Visi: `Batik today. Weaving and gamelan next. Every craft that was never written down.`
- Footer: atribusi CC BY + kredit hackathon + `Documenter studio`

```tsx
// web/app/page.tsx
import Link from "next/link";
import type { Archive } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function Home() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => []);
  return (
    <main className="mx-auto max-w-3xl p-8">
      <p className="font-display text-3xl">empu<span className="text-[var(--wax)]">.</span></p>
      <h1 className="mt-2 max-w-xl font-display text-4xl">Capture what masters know, before it's gone.</h1>
      <p className="mt-4 max-w-xl text-[var(--muted)]">
        Empu turns a master&apos;s narrated work video into a watchable craft dictionary. Every term links to the original speech, a short clip of the movement, and the real tool, cropped from the original frame. AI proposes; a person decides.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/d/hidup-batik" className="bg-[var(--accent)] px-4 py-2 text-white">
          Open the Batik Tulis archive
        </Link>
        <Link href="/try" className="border border-[var(--line)] px-4 py-2">Try it with a 3-minute clip</Link>
        <Link href="/evidence" className="border border-[var(--line)] px-4 py-2">See the evidence</Link>
      </div>
      <ul className="mt-12 space-y-4">
        {archives.map((a) => (
          <li key={a.id} className="border border-[var(--line)] p-4">
            <Link href={`/d/${a.slug}`} className="text-xl">{a.title}</Link>
            <p className="text-sm text-[var(--muted)]">
              {a.validated_count} validated terms · {a.recording_count} recordings
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-16 text-sm"><Link href="/studio">Documenter studio →</Link></p>
    </main>
  );
}
```

Commit: `feat(web): public home with demo archive card`.

---

### Task H4-7: S5 Kamus + S5b detail

**Files:**
- Create: `web/app/d/[slug]/page.tsx`, `web/app/d/[slug]/[id]/page.tsx`, `web/components/EntryRow.tsx`, `web/components/EntryCardPublic.tsx`
- Modify: `web/lib/types.ts` (`validation_label?: string`)

Prioritas desain: **S5b dulu**, lalu S5. Kalau pukul 17:00, jangan mulai S6 sebelum detail punya klip + crop + source + atribusi.

Layout S5b (`desain.md`): HP satu kolom; desktop `grid-cols-2` bukti kiri / arti kanan. Urutan: breadcrumb `Living Archive · Batik Tulis` → term `font-display` + `PronounceButton` → chip kategori/tahap → `Also heard as` → `EvidenceClip` + `CropView` → kutipan (`said at` / `shown on screen at`) → `gloss_en` lalu `gloss_id` berlabel "Bahasa Indonesia" → confidence + `New term` → `ValidationLabel` → `AttributionLine` card → "Heard in n recordings" → tautan peta. 404: copy empty state, bukan "Not found."

S5: header arsip (jumlah, versi pack dari `/api/packs`, sumber CC BY, Process map, Download). Search + chip kategori + New terms only. HP `EntryRow` (thumb 56 px). Desktop grid 3 kolom. Kelompok A–Z. Empty: "No public entries yet. Terms appear here after a person accepts them."

- [ ] **Step 1: List**

```tsx
// web/app/d/[slug]/page.tsx
import Link from "next/link";
import type { Entry } from "@/lib/types";
import { SourceBadge } from "@/components/SourceBadge";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function DictionaryPage({
  params, searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ q?: string; category?: string; stage?: string }>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const qs = new URLSearchParams();
  if (sp.q) qs.set("q", sp.q);
  if (sp.category) qs.set("category", sp.category);
  if (sp.stage) qs.set("stage", sp.stage);
  const entries: Entry[] = await fetch(
    `${API}/api/public/archives/${slug}/entries?${qs}`, { cache: "no-store" },
  ).then((r) => r.json());
  return (
    <main className="mx-auto max-w-3xl p-6">
      <form className="mb-6">
        <input name="q" defaultValue={sp.q} placeholder="Search terms"
               className="w-full border border-[var(--line)] bg-transparent p-2" />
      </form>
      <ul className="divide-y divide-[var(--line)]">
        {entries.map((e) => (
          <li key={e.id} className="flex items-center gap-3 py-3">
            {e.keyframe_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt="" src={e.keyframe_url} className="h-12 w-12 object-cover" />
            )}
            <Link href={`/d/${slug}/${e.id}`} className="text-lg">{e.term}</Link>
            <SourceBadge source={e.source} />
            {e.is_novel && <span className="text-xs">New term</span>}
            <span className="ml-auto text-sm text-[var(--muted)]">{e.gloss_en}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 2: Detail**

```tsx
// web/app/d/[slug]/[id]/page.tsx
import { SourceBadge } from "@/components/SourceBadge";
import type { Entry } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";
export const dynamic = "force-dynamic";

export default async function EntryPage({ params }: { params: Promise<{ slug: string; id: string }> }) {
  const { id } = await params;
  const r = await fetch(`${API}/api/public/entries/${id}`, { cache: "no-store" });
  if (!r.ok) {
    return (
      <p className="p-8">
        This entry isn&apos;t public. It may still be under review, or its recording&apos;s consent was withdrawn.
      </p>
    );
  }
  const e: Entry = await r.json();
  // Compose with EvidenceClip, CropView, PronounceButton, AttributionLine, ValidationLabel (H3-6b).
  // Evidence column first. Do not render gloss above the clip.
  return (
    <article className="mx-auto grid max-w-5xl gap-8 p-6 lg:grid-cols-2">
      <div className="space-y-4">
        {e.clip_url && <video src={e.clip_url} controls className="aspect-video w-full bg-[var(--surface)]" />}
        {/* CropView: crop_url / overlay_url / keyframe_url + sam_status */}
      </div>
      <div className="space-y-4">
        <h1 className="font-display text-4xl">{e.term}</h1>
        <SourceBadge source={e.source} />
        {e.best_occurrence?.audio_url && <audio src={e.best_occurrence.audio_url} controls />}
        <p>{e.gloss_en}</p>
        <p className="text-sm text-[var(--muted)]"><span className="block text-xs">Bahasa Indonesia</span>{e.gloss_id}</p>
        {e.variants?.length > 0 && <p className="text-sm">Also heard as: <em>{e.variants.join(", ")}</em></p>}
        {e.attribution && <p className="text-xs text-[var(--muted)]">{e.attribution}</p>}
        <p className="text-xs">{e.validation_label ?? "Validated by the documenter"}</p>
        <ul className="text-sm">
          {(e.occurrences ?? []).map((o) => (
            <li key={o.id}>{o.recording_title} · {o.t_start.toFixed(1)}s · {o.source}</li>
          ))}
        </ul>
      </div>
    </article>
  );
}
```

- [ ] **Step 3:** `pnpm lint`. Commit `feat(web): public dictionary and entry pages with attribution`.

---

### Task H4-8: S6 Peta tahapan

**Files:**
- Modify: `api/empu/routes/recordings.py`, `api/empu/routes/public.py`
- Create: `web/app/d/[slug]/map/[recordingId]/page.tsx`
- Test: `api/tests/test_api_process_map.py`

**Interfaces:** `GET /api/recordings/{id}/process-map` (studio key); `GET /api/public/recordings/{id}/process-map` (404 kalau rekaman tidak publik).

```python
# bentuk respons
{"recording_id": 1, "title": "...", "duration_s": 246, "steps": [
  {"pack_stage_id": "nglowong", "name": "nglowong", "t_start": 10, "t_end": 40,
   "entries": [{"id": 3, "term": "canting", "keyframe_url": "/media/..."}]}
]}
```

- [ ] **Step 1: Fungsi bersama di `api/empu/serialize.py`**

```python
def process_map_out(session, rec: Recording, *, public_only: bool) -> dict:
    from empu.models import Entry, Occurrence, ProcessStep
    from empu.visibility import entry_is_public, public_occurrences, recording_is_public
    if public_only and not recording_is_public(rec):
        return {}
    steps = session.exec(select(ProcessStep).where(ProcessStep.recording_id == rec.id)
                         .order_by(ProcessStep.order)).all()
    occs = session.exec(select(Occurrence).where(Occurrence.recording_id == rec.id)).all()
    out_steps = []
    for s in steps:
        linked, seen = [], set()
        for o in occs:
            hit = o.stage_id == s.pack_stage_id or (s.t_start <= o.t_start <= s.t_end)
            if not hit or o.entry_id in seen:
                continue
            e = session.get(Entry, o.entry_id)
            if e is None:
                continue
            if public_only and not entry_is_public(e, public_occurrences(session, e.id)):
                continue
            seen.add(o.entry_id)
            linked.append({"id": e.id, "term": e.term, "keyframe_url": media_url(o.keyframe_path)})
        out_steps.append({"pack_stage_id": s.pack_stage_id, "name": s.name_raw,
                          "t_start": s.t_start, "t_end": s.t_end, "entries": linked})
    return {"recording_id": rec.id, "title": rec.title, "duration_s": rec.duration_s, "steps": out_steps}
```

Impor `select` di atas `serialize.py`. Route studio memanggil ini dengan `public_only=False`. Route publik: 404 kalau dict kosong karena rekaman tidak publik.

UI: `ProcessMapBand` — desktop timeline horizontal (label lokal + `label_en`, thumbnail istilah); HP daftar vertikal. Klik istilah → `/d/{slug}/{id}`. Empty entries OK.

Commit: `feat: process map API and public timeline`.

---

### Task H4-9: S7 UI ekspor + Status

**Files:**
- Create: `web/app/studio/export/page.tsx`
- Modify: `CLAUDE.md`

```tsx
"use client";
import { useEffect, useState } from "react";
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { apiGet, getStudioKey } from "@/lib/api";
import type { Archive } from "@/lib/types";

function Form() {
  const [archives, setArchives] = useState<Archive[]>([]);
  useEffect(() => { apiGet<Archive[]>("/api/archives").then(setArchives); }, []);
  return (
    <form className="mx-auto max-w-md space-y-3 p-8" onSubmit={(e) => {
      e.preventDefault();
      const fd = new FormData(e.currentTarget);
      const url = `/api/archives/${fd.get("archive_id")}/export?format=${fd.get("format")}&scope=${fd.get("scope")}`;
      window.location.href = url;
    }}>
      <h1 className="text-2xl">Export</h1>
      <select name="archive_id" className="w-full border border-[var(--line)] bg-transparent p-2">
        {archives.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
      </select>
      {/* Four cards, not a naked <select>: JSON dataset · CSV table · ELAN .eaf · ZIP + clips/crops/README */}
      <select name="format" className="w-full border border-[var(--line)] bg-transparent p-2">
        <option value="json">JSON</option>
        <option value="csv">CSV</option>
        <option value="eaf">ELAN</option>
        <option value="zip">ZIP</option>
      </select>
      <fieldset>
        <label className="block text-sm"><input type="radio" name="scope" value="public" defaultChecked /> Public entries only</label>
        {getStudioKey() && (
          <label className="block text-sm"><input type="radio" name="scope" value="all" /> Everything except rejected (studio)</label>
        )}
      </fieldset>
      <p className="text-xs text-[var(--muted)]">Every export includes creator attribution and the license.</p>
      <button className="bg-[var(--accent)] px-4 py-2 text-[var(--bg)]">Download</button>
    </form>
  );
}

export default function ExportPage() {
  return <StudioKeyGate><Form /></StudioKeyGate>;
}
```

Kalau kreator membalas: review 10 entri dengan `actor=<nama kreator>`. Kalau tidak: biarkan documenter. Catat di `docs/00-konteks-hackathon.md`.

CLAUDE.md Status: `H4 (Min 1 Nov): kamus publik + ekspor JSON/CSV/ELAN. Berikutnya: H5 evaluasi + halaman Bukti.`

```bash
git add web CLAUDE.md docs/00-konteks-hackathon.md
git commit -m "feat(web): export page; dictionary live on demo archive"
```

---

## Selesai kalau
- [ ] `/d/hidup-batik` menampilkan entri accepted dengan klip, `SourceBadge` ikon+teks, `CropView` (atau full frame), atribusi CC BY, mode Mori.
- [ ] Detail: bukti sebelum glosa; 404 memakai copy empty state, bukan "Not found."
- [ ] Entri proposed tidak tampil tanpa kunci.
- [ ] ZIP `scope=public` berisi JSON+CSV+eaf+media+README atribusi.
- [ ] `scope=all` tanpa kunci 401.
- [ ] Beranda: 3 CTA brief, bukan "Try the batik tulis archive".

## Kalau pukul 17:00 belum
Potong ELAN (JSON+CSV wajib). Jangan potong kamus.
