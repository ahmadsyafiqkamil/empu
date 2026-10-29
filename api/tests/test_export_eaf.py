from factories import make_archive, make_recording
from sqlmodel import select

from empu.enums import AccessLevel, Category, EntryStatus, Source
from empu.export.eaf_export import build_eaf
from empu.models import Entry, Occurrence


def test_eaf_has_source_tier(session):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        display_path="archives/1/recordings/1/display.mp4",
        duration_s=20,
        consent_scope=AccessLevel.public,
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="canting",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        gloss_id="pena",
        gloss_en="pen",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(
            entry_id=e.id,
            recording_id=rec.id,
            source=Source.speech,
            t_start=1.0,
            t_end=2.5,
            spoken="canting",
        )
    )
    session.commit()
    occs = list(session.exec(select(Occurrence).where(Occurrence.recording_id == rec.id)).all())
    xml = build_eaf(rec, [(e, occs)])
    assert 'TIER_ID="source"' in xml
    assert "speech" in xml and "canting" in xml
