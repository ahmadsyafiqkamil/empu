from sqlmodel import Session, select

from empu.export.common import ExportScope, entries_for_scope, manifest
from empu.models import Archive, Contributor, Job, ProcessStep, Recording
from empu.packs import CraftPack


def _latest_model(session: Session, rec_ids: set[int]) -> tuple[str | None, str | None]:
    if not rec_ids:
        return None, None
    job = session.exec(
        select(Job)
        .where(Job.recording_id.in_(rec_ids), Job.model != "", Job.model.is_not(None))
        .order_by(Job.id.desc())
    ).first()
    if job is None:
        return None, None
    return job.model, job.prompt_version or None


def build_json(session: Session, archive: Archive, pack: CraftPack, scope: ExportScope) -> dict:
    rows = entries_for_scope(session, archive.id, scope)
    rec_ids = {o.recording_id for _, occs in rows for o in occs}
    recordings = [session.get(Recording, i) for i in sorted(rec_ids)]
    contrib_ids = {r.contributor_id for r in recordings if r and r.contributor_id}
    contributors = [session.get(Contributor, i) for i in contrib_ids]
    man = manifest(archive, pack, scope)
    model, prompt_version = _latest_model(session, rec_ids)
    if model:
        man["model"] = model
    if prompt_version:
        man["prompt_version"] = prompt_version
    return {
        "manifest": man,
        "contributors": [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role.value,
                "region": c.region,
                "sanggar": c.sanggar,
            }
            for c in contributors
            if c
        ],
        "recordings": [
            {
                "id": r.id,
                "title": r.title,
                "duration_s": r.duration_s,
                "consent_scope": r.consent_scope.value,
                "source_kind": r.source_kind.value,
                "source_url": r.source_url,
                "source_creator": r.source_creator,
                "license": r.license,
                "attribution": r.attribution,
                "display_path": r.display_path,
            }
            for r in recordings
            if r
        ],
        "entries": [
            {
                "id": e.id,
                "term": e.term,
                "category": e.category.value,
                "stage_id": e.stage_id,
                "gloss_id": e.gloss_id,
                "gloss_en": e.gloss_en,
                "variants": e.variants_json,
                "is_novel": e.is_novel,
                "status": e.status.value,
                "access_level": e.access_level.value,
                "occurrences": [
                    {
                        "id": o.id,
                        "recording_id": o.recording_id,
                        "spoken": o.spoken,
                        "source": o.source.value,
                        "t_start": o.t_start,
                        "t_end": o.t_end,
                        "confidence": o.confidence.value,
                        "clip_path": o.clip_path,
                        "audio_path": o.audio_path,
                        "keyframe_path": o.keyframe_path,
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
                    {
                        "name": s.name_raw,
                        "pack_stage_id": s.pack_stage_id,
                        "t_start": s.t_start,
                        "t_end": s.t_end,
                        "tools": s.tools_json,
                        "order": s.order,
                    }
                    for s in session.exec(
                        select(ProcessStep)
                        .where(ProcessStep.recording_id == rid)
                        .order_by(ProcessStep.order)
                    ).all()
                ],
            }
            for rid in sorted(rec_ids)
        ],
    }
