"""Judge sandbox: keyless upload to a private, unlisted archive with a daily quota."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, func, select

from empu.api_schemas import UploadAck
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.enums import AccessLevel, SourceKind
from empu.intake import IntakeError, RecordingMeta, create_recording, get_or_create_archive
from empu.models import Archive, Job, Recording
from empu.packs import list_packs

router = APIRouter()


def _default_pack_id(settings: Settings) -> str:
    ids = sorted(p.id for p in list_packs(settings.packs_dir))
    if not ids:
        raise HTTPException(500, "no craft packs available")
    return ids[0]


def ensure_sandbox_archive(session: Session, settings: Settings) -> Archive:
    return get_or_create_archive(
        session,
        "sandbox",
        title="Judge sandbox",
        pack_id=_default_pack_id(settings),
        is_sandbox=True,
    )


def sandbox_quota_remaining(session: Session, settings: Settings) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    arch = session.exec(select(Archive).where(Archive.slug == "sandbox")).first()
    if arch is None:
        return settings.sandbox_daily_quota
    n = session.exec(
        select(func.count())
        .select_from(Job)
        .join(Recording)
        .where(Recording.archive_id == arch.id, Job.created_at >= start)
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
    arch = ensure_sandbox_archive(session, settings)
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
        meta = RecordingMeta(
            title=title,
            consent_confirmed=True,
            consent_scope=AccessLevel.public,
            source_kind=SourceKind.own_recording,
            contributor_name="Sandbox visitor",
        )
        rec, job = create_recording(
            session, settings, arch, src, meta, filename=file.filename or "upload.mp4"
        )
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        src.unlink(missing_ok=True)
    return UploadAck(recording_id=rec.id, job_id=job.id)
