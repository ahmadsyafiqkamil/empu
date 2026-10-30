from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from empu.api_schemas import ArchiveOut, EntryListItem, EntryOut
from empu.db import get_session
from empu.models import Archive, Contributor, Entry, Recording
from empu.serialize import archive_out, entry_list_item, entry_out, process_map_out
from empu.visibility import (
    entry_is_public,
    public_entries,
    public_occurrences,
    validation_label_for,
)

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
        if a.is_sandbox:
            continue
        pubs = public_entries(session, a.id)
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
    slug: str,
    q: str | None = None,
    category: str | None = None,
    stage: str | None = None,
    is_novel: bool | None = None,
    session: Session = Depends(get_session),
) -> list[EntryListItem]:
    a = _archive_by_slug(session, slug)
    items = []
    for e, occs in public_entries(session, a.id):
        if category and e.category.value != category:
            continue
        if stage and e.stage_id != stage:
            continue
        if is_novel is not None and bool(e.is_novel) is not is_novel:
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
    return entry_out(
        e,
        occs,
        recording_title=rec.title if rec else "",
        contributor_name=contrib.name if contrib else None,
        attribution=rec.attribution if rec else None,
        validation_label=validation_label_for(session, e.id),
    )


@router.get("/api/public/recordings/{recording_id}/process-map")
def public_recording_process_map(
    recording_id: int, session: Session = Depends(get_session)
) -> dict:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise HTTPException(404, "not found")
    out = process_map_out(session, rec, public_only=True)
    if not out:
        raise HTTPException(404, "not found")
    return out
