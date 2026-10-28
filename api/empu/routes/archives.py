from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from empu.api_schemas import ArchiveIn, ArchiveOut
from empu.db import get_session
from empu.enums import EntryStatus
from empu.intake import IntakeError, get_or_create_archive
from empu.models import Archive, Entry, Recording
from empu.serialize import archive_out

router = APIRouter()


def _stats(session: Session, archive_id: int) -> tuple[int, int]:
    n_rec = session.exec(
        select(func.count()).select_from(Recording).where(Recording.archive_id == archive_id)
    ).one()
    n_val = session.exec(
        select(func.count())
        .select_from(Entry)
        .where(
            Entry.archive_id == archive_id,
            Entry.status.in_((EntryStatus.accepted, EntryStatus.edited)),
        )
    ).one()
    return int(n_rec), int(n_val)


@router.get("/api/archives", response_model=list[ArchiveOut])
def list_archives(session: Session = Depends(get_session)) -> list[ArchiveOut]:
    rows = session.exec(select(Archive).order_by(Archive.is_demo.desc(), Archive.id)).all()
    return [
        archive_out(
            a,
            recording_count=_stats(session, a.id)[0],
            validated_count=_stats(session, a.id)[1],
        )
        for a in rows
    ]


@router.post("/api/archives", response_model=ArchiveOut, status_code=201)
def create_archive(body: ArchiveIn, session: Session = Depends(get_session)) -> ArchiveOut:
    try:
        a = get_or_create_archive(
            session,
            body.slug,
            title=body.title,
            pack_id=body.craft_pack_id,
        )
    except IntakeError as e:
        raise HTTPException(400, str(e)) from e
    if body.description:
        a.description = body.description
        a.owner_name = body.owner_name
        session.add(a)
        session.commit()
        session.refresh(a)
    return archive_out(a)


@router.get("/api/archives/{archive_id}", response_model=ArchiveOut)
def get_archive(archive_id: int, session: Session = Depends(get_session)) -> ArchiveOut:
    a = session.get(Archive, archive_id)
    if a is None:
        raise HTTPException(404, "archive not found")
    n_rec, n_val = _stats(session, a.id)
    return archive_out(a, recording_count=n_rec, validated_count=n_val)
