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
        raise IntakeError(
            "consent_confirmed must be true: recordings are never processed without consent"
        )
    if not meta.title.strip():
        raise IntakeError("title is required")
    if not (meta.contributor_name or meta.contributor_id):
        raise IntakeError("contributor_name or contributor_id is required")
    if meta.source_kind is SourceKind.cc_by_video:
        missing = [
            f
            for f in ("source_url", "source_creator", "license", "attribution")
            if not (getattr(meta, f) or "").strip()
        ]
        if missing:
            raise IntakeError(f"cc_by_video requires {', '.join(missing)}")
    if (
        meta.source_kind is SourceKind.internal_eval
        and meta.consent_scope is not AccessLevel.private
    ):
        raise IntakeError("internal_eval recordings must use consent_scope=private")


def get_or_create_archive(
    session: Session,
    slug: str,
    *,
    title: str,
    pack_id: str,
    is_demo: bool = False,
    is_sandbox: bool = False,
) -> Archive:
    archive = session.exec(select(Archive).where(Archive.slug == slug)).first()
    if archive is None:
        archive = Archive(
            slug=slug,
            title=title,
            craft_pack_id=pack_id,
            is_demo=is_demo,
            is_sandbox=is_sandbox,
        )
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


def enqueue_job(
    session: Session,
    settings: Settings,
    recording: Recording,
    *,
    mode: PipelineMode | None = None,
) -> Job:
    job = Job(
        recording_id=recording.id,
        status=JobStatus.queued,
        mode=mode or PipelineMode(settings.pipeline_mode),
        model=settings.muse_model,
        prompt_version=prompt_version_for(True),
    )
    recording.status = JobStatus.queued
    session.add_all([job, recording])
    session.commit()
    session.refresh(job)
    return job


def create_recording(
    session: Session,
    settings: Settings,
    archive: Archive,
    src: Path,
    meta: RecordingMeta,
    *,
    mode: PipelineMode | None = None,
    filename: str | None = None,
) -> tuple[Recording, Job]:
    validate_meta(meta)
    contributor_id = meta.contributor_id
    if contributor_id is None:
        contributor_id = get_or_create_contributor(
            session, meta.contributor_name.strip(), meta.contributor_role
        ).id
    rec = Recording(
        archive_id=archive.id,
        contributor_id=contributor_id,
        title=meta.title.strip(),
        recorded_at=meta.recorded_at,
        location=meta.location,
        language_hint=meta.language_hint,
        original_path="",
        consent_scope=meta.consent_scope,
        consent_note=meta.consent_note,
        consent_evidence=meta.consent_evidence,
        source_kind=meta.source_kind,
        source_url=meta.source_url,
        source_creator=meta.source_creator,
        license=meta.license,
        attribution=meta.attribution,
    )
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
        lic = d.get("license")
        raise IntakeError(f"{Path(path).name}: license is not Creative Commons ({lic!r})")
    title, channel, url = d["title"], d["channel"], d["webpage_url"]
    return RecordingMeta(
        title=title,
        contributor_name=contributor_name or channel,
        contributor_role=(
            ContributorRole.maestro if contributor_name else ContributorRole.documenter
        ),
        consent_confirmed=True,
        consent_scope=AccessLevel.public,
        consent_evidence=(
            f"{CC_BY_LICENSE}, verified via YouTube metadata on {d.get('verified_at', '?')}"
        ),
        source_kind=SourceKind.cc_by_video,
        source_url=url,
        source_creator=channel,
        license=CC_BY_LICENSE,
        attribution=(
            f'"{title}" by {channel} ({url}), licensed under {CC_BY_LICENSE}. '
            "Trimmed and analyzed by Empu."
        ),
    )


def find_testdata_video(testdata_dir: Path, youtube_id: str) -> Path:
    hits = sorted(p for p in Path(testdata_dir).rglob("*.mp4") if f"[{youtube_id}]" in p.name)
    if not hits:
        raise IntakeError(f"video [{youtube_id}] not found under {testdata_dir}")
    return hits[0]
