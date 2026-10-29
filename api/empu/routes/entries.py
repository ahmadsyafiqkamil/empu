from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, or_, select

from empu.api_schemas import EntryListItem, EntryOut, ReviewIn
from empu.auth import AuthContext, optional_studio, require_studio
from empu.db import get_session
from empu.enums import EntryStatus, Source
from empu.models import Archive, Contributor, Entry, Occurrence, Recording
from empu.review import ReviewError, apply_review
from empu.serialize import entry_list_item, entry_out

router = APIRouter()


@router.get("/api/archives/{archive_id}/entries", response_model=list[EntryListItem])
def list_entries(
    archive_id: int,
    status: EntryStatus | None = None,
    source: Source | None = None,
    is_novel: bool | None = None,
    stage: str | None = None,
    q: str | None = None,
    _auth: AuthContext = Depends(require_studio),
    session: Session = Depends(get_session),
) -> list[EntryListItem]:
    stmt = select(Entry).where(Entry.archive_id == archive_id, Entry.status != EntryStatus.merged)
    if status:
        stmt = stmt.where(Entry.status == status)
    if is_novel is not None:
        stmt = stmt.where(Entry.is_novel == is_novel)
    if stage:
        stmt = stmt.where(Entry.stage_id == stage)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                col(Entry.term).ilike(like),
                col(Entry.gloss_id).ilike(like),
                col(Entry.gloss_en).ilike(like),
            )
        )
    entries = session.exec(stmt.order_by(Entry.term)).all()
    out = []
    for e in entries:
        occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
        if source and not any(o.source is source for o in occs):
            continue
        out.append(entry_list_item(e, occs))
    return out


@router.get("/api/entries/{entry_id}", response_model=EntryOut)
def get_entry(
    entry_id: int,
    _auth: AuthContext = Depends(require_studio),
    session: Session = Depends(get_session),
) -> EntryOut:
    e = session.get(Entry, entry_id)
    if e is None:
        raise HTTPException(404, "entry not found")
    occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
    rec = session.get(Recording, occs[0].recording_id) if occs else None
    contrib = session.get(Contributor, rec.contributor_id) if rec and rec.contributor_id else None
    return entry_out(
        e,
        occs,
        recording_title=rec.title if rec else "",
        contributor_name=contrib.name if contrib else None,
        attribution=rec.attribution if rec else None,
    )


@router.post("/api/entries/{entry_id}/review", response_model=EntryOut)
def review_entry(
    entry_id: int,
    body: ReviewIn,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(optional_studio),
) -> EntryOut:
    if not auth.has_key:
        e = session.get(Entry, entry_id)
        arch = session.get(Archive, e.archive_id) if e else None
        if not (arch and arch.is_sandbox):
            raise HTTPException(401, "studio key required")
    try:
        e = apply_review(session, entry_id, body)
    except ReviewError as err:
        raise HTTPException(400, str(err)) from err
    occs = list(session.exec(select(Occurrence).where(Occurrence.entry_id == e.id)).all())
    return entry_out(e, occs)
