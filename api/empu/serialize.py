from datetime import datetime

from empu.api_schemas import (
    ArchiveOut,
    ContributorOut,
    EntryListItem,
    EntryOut,
    JobOut,
    JobStageOut,
    OccurrenceOut,
    RecordingOut,
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
        id=o.id,
        entry_id=o.entry_id,
        recording_id=o.recording_id,
        recording_title=recording_title,
        spoken=o.spoken,
        term_raw=o.term_raw,
        source=o.source,
        t_start=o.t_start,
        t_end=o.t_end,
        time_source=o.time_source,
        stage_id=o.stage_id,
        visible=o.visible,
        visible_object_en=o.visible_object_en,
        visual_match=o.visual_match,
        evidence_quote=o.evidence_quote,
        confidence=o.confidence,
        status=o.status,
        clip_url=media_url(o.clip_path),
        audio_url=media_url(o.audio_path),
        keyframe_url=media_url(o.keyframe_path),
    )


def _best(e: Entry, occs: list[Occurrence]) -> Occurrence | None:
    return next((o for o in occs if o.id == e.best_occurrence_id), occs[0] if occs else None)


def entry_list_item(
    e: Entry, occs: list[Occurrence], *, recording_title: str = ""
) -> EntryListItem:
    best = _best(e, occs)
    return EntryListItem(
        id=e.id,
        term=e.term,
        category=e.category,
        stage_id=e.stage_id,
        gloss_id=e.gloss_id,
        gloss_en=e.gloss_en,
        is_novel=e.is_novel,
        status=e.status,
        access_level=e.access_level,
        source=best.source if best else None,
        confidence=best.confidence if best else None,
        n_occurrences=len(occs),
        crop_url=media_url(e.crop_path),
        keyframe_url=media_url(best.keyframe_path) if best else None,
        clip_url=media_url(best.clip_path) if best else None,
    )


def entry_out(
    e: Entry,
    occs: list[Occurrence],
    *,
    recording_title: str = "",
    contributor_name: str | None = None,
    attribution: str | None = None,
) -> EntryOut:
    item = entry_list_item(e, occs, recording_title=recording_title)
    best = _best(e, occs)
    return EntryOut(
        **item.model_dump(),
        variants=list(e.variants_json or []),
        pack_term_id=e.pack_term_id,
        maestro_note=e.maestro_note,
        sam_status=e.sam_status,
        overlay_url=media_url(e.overlay_path),
        best_occurrence=occurrence_out(best, recording_title=recording_title) if best else None,
        occurrences=[occurrence_out(o, recording_title=recording_title) for o in occs],
        attribution=attribution,
        contributor_name=contributor_name,
    )


def job_out(job: Job) -> JobOut:
    timings = job.timings_json or {}
    failed_stage = (
        (job.error or "").split(":", 1)[0].strip() if job.status is JobStatus.failed else ""
    )
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
        stages.append(
            JobStageOut(
                name=st.value,
                status=status,
                started_at=_ts(info.get("started_at")),
                finished_at=_ts(info.get("finished_at")),
                seconds=info.get("seconds"),
            )
        )
    return JobOut(
        id=job.id,
        recording_id=job.recording_id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        error=job.error,
        mode=job.mode,
        stages=stages,
    )


def _ts(v: object) -> datetime | None:
    if isinstance(v, datetime) or v is None:
        return v
    try:
        return datetime.fromisoformat(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def recording_out(
    rec: Recording,
    *,
    job: Job | None = None,
    contributor: Contributor | None = None,
) -> RecordingOut:
    return RecordingOut(
        id=rec.id,
        archive_id=rec.archive_id,
        title=rec.title,
        duration_s=rec.duration_s,
        status=rec.status,
        consent_status=rec.consent_status,
        consent_scope=rec.consent_scope,
        source_kind=rec.source_kind,
        source_url=rec.source_url,
        source_creator=rec.source_creator,
        license=rec.license,
        attribution=rec.attribution,
        contributor=contributor_out(contributor),
        job=job_out(job) if job else None,
        display_url=media_url(rec.display_path),
    )


def archive_out(
    a: Archive, *, recording_count: int = 0, validated_count: int = 0
) -> ArchiveOut:
    return ArchiveOut(
        id=a.id,
        slug=a.slug,
        title=a.title,
        craft_pack_id=a.craft_pack_id,
        description=a.description,
        is_demo=a.is_demo,
        recording_count=recording_count,
        validated_count=validated_count,
    )
