import csv
import io

from factories import make_archive, make_recording

from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.export.common import entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.json_export import build_json
from empu.models import Entry, Occurrence


def test_scope_public_hides_proposed(session, pack):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.cc_by_video,
        source_url="u",
        source_creator="c",
        license="CC BY 3.0",
        attribution="a",
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.proposed,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    assert entries_for_scope(session, a.id, "public") == []
    assert len(entries_for_scope(session, a.id, "all")) == 1


def test_csv_has_source_column(session, pack):
    a = make_archive(session)
    rec = make_recording(session, a, consent_scope=AccessLevel.public,
                         source_kind=SourceKind.own_recording)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="canting",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        gloss_id="pena",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(
            entry_id=e.id,
            recording_id=rec.id,
            source=Source.on_screen_text,
            t_start=5,
            t_end=6,
        )
    )
    session.commit()
    text = build_csv(entries_for_scope(session, a.id, "public"), session)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["source"] == "on_screen_text"
    assert "clip_path" in rows[0]


def test_json_includes_attribution_for_cc_by(session, pack):
    a = make_archive(session)
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.cc_by_video,
        source_url="https://youtu.be/x",
        source_creator="Batik Education",
        license="CC BY 3.0",
        attribution="by Batik Education",
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="x",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    doc = build_json(session, a, pack, "public")
    assert doc["recordings"][0]["license"] == "CC BY 3.0"
    assert doc["entries"][0]["occurrences"][0]["source"] == "speech"