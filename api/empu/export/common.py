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
    entries = session.exec(
        select(Entry).where(
            Entry.archive_id == archive_id,
            ~Entry.status.in_((EntryStatus.rejected, EntryStatus.merged)),
        )
    ).all()
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
        "note": (
            "Media clips are trimmed from source recordings. "
            "CC BY sources retain creator attribution."
        ),
    }
