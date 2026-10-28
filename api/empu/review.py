from typing import Any

from sqlmodel import Session, select

from empu.api_schemas import ReviewIn
from empu.enums import AccessLevel, Category, EntryStatus, OccurrenceStatus, ReviewAction
from empu.models import Entry, Occurrence, ReviewEvent, utcnow
from empu.persist import choose_best

ALLOWED_CHANGES = {
    "term",
    "gloss_id",
    "gloss_en",
    "category",
    "stage_id",
    "access_level",
    "maestro_note",
    "variants",
}


class ReviewError(ValueError):
    pass


def _snapshot(entry: Entry) -> dict[str, Any]:
    return {
        "term": entry.term,
        "gloss_id": entry.gloss_id,
        "gloss_en": entry.gloss_en,
        "category": entry.category.value if hasattr(entry.category, "value") else entry.category,
        "stage_id": entry.stage_id,
        "access_level": getattr(entry.access_level, "value", entry.access_level),
        "maestro_note": entry.maestro_note,
        "status": getattr(entry.status, "value", entry.status),
        "variants": list(entry.variants_json or []),
        "merged_into_id": entry.merged_into_id,
    }


def _occs(session: Session, entry_id: int) -> list[Occurrence]:
    return list(session.exec(select(Occurrence).where(Occurrence.entry_id == entry_id)).all())


def apply_review(session: Session, entry_id: int, req: ReviewIn) -> Entry:
    entry = session.get(Entry, entry_id)
    if entry is None:
        raise ReviewError("entry not found")
    if req.action is ReviewAction.add_manual:
        raise ReviewError("add_manual is not available")
    before = _snapshot(entry)
    occs = _occs(session, entry.id)

    if req.action is ReviewAction.accept:
        entry.status = EntryStatus.accepted
        _set_occ_status(occs, OccurrenceStatus.accepted, req.occurrence_id)
    elif req.action is ReviewAction.edit:
        _apply_changes(entry, req.changes)
        entry.status = EntryStatus.edited
    elif req.action is ReviewAction.reject:
        entry.status = EntryStatus.rejected
        _set_occ_status(occs, OccurrenceStatus.rejected, req.occurrence_id)
    elif req.action is ReviewAction.merge:
        if not req.merge_into_id:
            raise ReviewError("merge_into_id required")
        target = session.get(Entry, req.merge_into_id)
        if target is None or target.id == entry.id:
            raise ReviewError("invalid merge target")
        for o in occs:
            o.entry_id = target.id
            session.add(o)
        entry.status = EntryStatus.merged
        entry.merged_into_id = target.id
        session.flush()
        best = choose_best(_occs(session, target.id))
        target.best_occurrence_id = best.id if best else None
        target.updated_at = utcnow()
        session.add(target)
    elif req.action is ReviewAction.restore:
        last = session.exec(
            select(ReviewEvent)
            .where(ReviewEvent.entry_id == entry.id)
            .order_by(ReviewEvent.id.desc())
        ).first()
        if last is None:
            raise ReviewError("nothing to restore")
        _restore(entry, last.before_json)
    else:
        raise ReviewError(f"unhandled action {req.action}")

    entry.updated_at = utcnow()
    session.add(entry)
    session.add(
        ReviewEvent(
            entry_id=entry.id,
            occurrence_id=req.occurrence_id,
            action=req.action,
            before_json=before,
            after_json=_snapshot(entry),
            actor=req.actor,
        )
    )
    session.commit()
    session.refresh(entry)
    return entry


def _set_occ_status(
    occs: list[Occurrence], status: OccurrenceStatus, occurrence_id: int | None
) -> None:
    for o in occs:
        if occurrence_id is None or o.id == occurrence_id:
            o.status = status


def _apply_changes(entry: Entry, changes: dict[str, Any]) -> None:
    unknown = set(changes) - ALLOWED_CHANGES
    if unknown:
        raise ReviewError(f"unknown fields: {sorted(unknown)}")
    if "variants" in changes:
        entry.variants_json = list(changes["variants"])
    for key, val in changes.items():
        if key == "variants":
            continue
        setattr(entry, key, val)


def _restore(entry: Entry, before: dict[str, Any]) -> None:
    entry.term = before.get("term", entry.term)
    entry.gloss_id = before.get("gloss_id", entry.gloss_id)
    entry.gloss_en = before.get("gloss_en", entry.gloss_en)
    entry.stage_id = before.get("stage_id")
    entry.maestro_note = before.get("maestro_note", "")
    entry.merged_into_id = before.get("merged_into_id")
    entry.variants_json = list(before.get("variants") or [])
    entry.status = EntryStatus(before["status"])
    if before.get("access_level"):
        entry.access_level = AccessLevel(before["access_level"])
    if before.get("category"):
        entry.category = Category(before["category"])
