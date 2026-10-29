"""Public visibility rules — the single source of truth for what the public may see.

Every public API route and every `scope=public` export funnels through the
functions here. A term is public only when its entry is validated and public,
its source recording has granted public consent, and it has at least one
public occurrence.
"""

from __future__ import annotations

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


def expert_actor(session: Session, entry_id: int) -> str | None:
    events = session.exec(select(ReviewEvent).where(ReviewEvent.entry_id == entry_id)).all()
    for ev in events:
        actor = ev.actor.strip()
        if actor.lower() not in DOCUMENTER_ACTORS:
            return actor
    return None


def validation_label_for(session: Session, entry_id: int) -> str:
    actor = expert_actor(session, entry_id)
    if actor:
        return f"Validated by the expert · {actor}"
    return "Validated by the documenter"