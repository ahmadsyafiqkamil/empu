"""Write merged pipeline output for one recording into the DB. Idempotent per recording."""

from __future__ import annotations

from sqlmodel import Session, col, select

from empu.enums import EntryStatus, OccurrenceStatus
from empu.models import Entry, Occurrence, ProcessStep, Recording, ReviewEvent, utcnow
from empu.pipeline.merge import AbsOccurrence, EntryDraft, occurrence_rank
from empu.pipeline.process_map import StepDraft


def find_entry(session: Session, archive_id: int, canon_key: str) -> Entry | None:
    entry = session.exec(
        select(Entry).where(Entry.archive_id == archive_id, Entry.canon_key == canon_key)
    ).first()
    seen: set[int] = set()
    while (
        entry is not None
        and entry.status is EntryStatus.merged
        and entry.merged_into_id
        and entry.id not in seen
    ):
        seen.add(entry.id)
        entry = session.get(Entry, entry.merged_into_id)
    return entry


def choose_best(occs: list[Occurrence]) -> Occurrence | None:
    live = [o for o in occs if o.status is not OccurrenceStatus.rejected] or occs
    return max(
        live,
        key=lambda o: occurrence_rank(
            o.source, o.visual_match, o.confidence, o.t_end - o.t_start
        ),
        default=None,
    )


def _row(entry_id: int, recording_id: int, chunk_id: int | None, o: AbsOccurrence) -> Occurrence:
    m = o.muse
    return Occurrence(
        entry_id=entry_id,
        recording_id=recording_id,
        chunk_id=chunk_id,
        spoken=m.spoken,
        term_raw=m.term,
        source=m.source,
        t_start=round(o.t_start, 2),
        t_end=round(o.t_end, 2),
        time_source=o.time_source,
        asr_score=o.asr_score,
        stage_raw=m.stage,
        stage_id=o.stage_id,
        visible=m.visible,
        visible_object_en=m.visible_object_en,
        visual_match=m.visual_match,
        gloss_raw=m.gloss_id,
        gloss_en_raw=m.gloss_en,
        evidence_quote=m.evidence_quote,
        confidence=m.confidence,
    )


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


def persist_results(
    session: Session,
    recording: Recording,
    drafts: list[EntryDraft],
    steps: list[StepDraft],
    chunk_ids: dict[int, int],
) -> list[Entry]:
    previous = clear_recording(session, recording.id)
    touched: dict[int, Entry] = {}
    for d in drafts:
        entry = find_entry(session, recording.archive_id, d.canon.canon_key)
        if entry is None:
            entry = Entry(
                archive_id=recording.archive_id,
                canon_key=d.canon.canon_key,
                term=d.canon.term,
                category=d.category,
                stage_id=d.stage_id,
                gloss_id=d.gloss_id,
                gloss_en=d.gloss_en,
                variants_json=d.variants,
                pack_term_id=d.canon.pack_term_id,
                is_novel=d.canon.is_novel,
                access_level=recording.consent_scope,
            )
            session.add(entry)
            session.flush()
        elif entry.status is EntryStatus.proposed:
            merged = set(entry.variants_json) | set(d.variants)
            entry.variants_json = sorted(merged, key=str.casefold)
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
        has_events = session.exec(
            select(ReviewEvent.id).where(ReviewEvent.entry_id == entry_id)
        ).first()
        if has_occ is None and entry.status is EntryStatus.proposed and has_events is None:
            session.delete(entry)
        else:
            refresh_best(session, entry)
    for i, s in enumerate(steps):
        session.add(
            ProcessStep(
                recording_id=recording.id,
                pack_stage_id=s.pack_stage_id,
                name_raw=s.name_raw,
                t_start=round(s.t_start, 2),
                t_end=round(s.t_end, 2),
                tools_json=s.tools,
                order=i,
            )
        )
    session.commit()
    return list(touched.values())
