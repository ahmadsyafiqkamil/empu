import shutil
import tempfile
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from empu.api_schemas import EntryOut, RecordingOut, ReprocessIn, UploadAck
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.enums import AccessLevel, SourceKind
from empu.intake import IntakeError, RecordingMeta, create_recording, enqueue_job
from empu.models import Archive, Contributor, Entry, Job, Occurrence, Recording
from empu.serialize import entry_out, process_map_out, recording_out

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
    suffix = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    with SpooledTemporaryFile(max_size=8 * 1024 * 1024) as tmp:
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(413, f"file exceeds {settings.max_upload_mb} MB")
            tmp.write(chunk)
        tmp.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as disk:
            shutil.copyfileobj(tmp, disk)
            src = Path(disk.name)
    try:
        meta = RecordingMeta(
            title=title,
            contributor_id=contributor_id,
            contributor_name=contributor_name,
            recorded_at=recorded_at,
            location=location,
            language_hint=language_hint,
            consent_confirmed=True,
            consent_scope=consent_scope,
            consent_note=consent_note,
            consent_evidence=consent_evidence,
            source_kind=source_kind,
            source_url=source_url,
            source_creator=source_creator,
            license=license,
            attribution=attribution,
        )
        rec, job = create_recording(
            session,
            settings,
            archive,
            src,
            meta,
            filename=file.filename or f"upload{suffix}",
        )
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        src.unlink(missing_ok=True)
    return UploadAck(recording_id=rec.id, job_id=job.id)


def _load_recording(
    session: Session, recording_id: int
) -> tuple[Recording, Job | None, Contributor | None]:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "recording not found")
    job = session.exec(
        select(Job).where(Job.recording_id == rec.id).order_by(Job.id.desc())
    ).first()
    contrib = session.get(Contributor, rec.contributor_id) if rec.contributor_id else None
    return rec, job, contrib


@router.get("/api/recordings/{recording_id}", response_model=RecordingOut)
def get_recording(recording_id: int, session: Session = Depends(get_session)) -> RecordingOut:
    rec, job, contrib = _load_recording(session, recording_id)
    return recording_out(rec, job=job, contributor=contrib)


@router.get("/api/recordings/{recording_id}/entries", response_model=list[EntryOut])
def recording_entries(
    recording_id: int, session: Session = Depends(get_session)
) -> list[EntryOut]:
    rec, _, contrib = _load_recording(session, recording_id)
    occs = session.exec(select(Occurrence).where(Occurrence.recording_id == recording_id)).all()
    by_entry: dict[int, list[Occurrence]] = {}
    for o in occs:
        by_entry.setdefault(o.entry_id, []).append(o)
    out: list[EntryOut] = []
    for eid, group in by_entry.items():
        e = session.get(Entry, eid)
        if e is None or e.status.value == "merged":
            continue
        out.append(
            entry_out(
                e,
                group,
                recording_title=rec.title,
                contributor_name=contrib.name if contrib else None,
                attribution=rec.attribution,
            )
        )
    out.sort(key=lambda x: x.term)
    return out


@router.get("/api/recordings/{recording_id}/process-map")
def recording_process_map(recording_id: int, session: Session = Depends(get_session)) -> dict:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "recording not found")
    return process_map_out(session, rec, public_only=False)


@router.post("/api/recordings/{recording_id}/reprocess", response_model=UploadAck)
def reprocess(
    recording_id: int,
    body: ReprocessIn | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadAck:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "recording not found")
    job = enqueue_job(session, settings, rec, mode=body.mode if body else None)
    return UploadAck(recording_id=rec.id, job_id=job.id)
