from factories import make_archive, make_recording

from empu.enums import Category, Confidence, Source, VisualMatch
from empu.models import Entry, Occurrence
from empu.serialize import entry_out, media_url, occurrence_out


def test_media_url():
    assert media_url(None) is None
    assert media_url("archives/1/display.mp4") == "/media/archives/1/display.mp4"


def test_occurrence_keeps_source(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(archive_id=a.id, canon_key="term:x", term="x", category=Category.tool)
    session.add(e)
    session.commit()
    session.refresh(e)
    o = Occurrence(
        entry_id=e.id,
        recording_id=rec.id,
        source=Source.on_screen_text,
        t_start=1,
        t_end=2,
        spoken="X",
        term_raw="x",
        visual_match=VisualMatch.yes,
        confidence=Confidence.high,
        clip_path="archives/1/recordings/1/occurrences/1/clip.mp4",
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    d = occurrence_out(o)
    assert d.source == "on_screen_text"
    assert d.clip_url == "/media/archives/1/recordings/1/occurrences/1/clip.mp4"
    assert "source" in d.model_dump()


def test_entry_out_includes_best_and_occurrences(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="canting",
        category=Category.tool,
        gloss_id="pena malam",
        gloss_en="wax pen",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    o = Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=3, t_end=4)
    session.add(o)
    session.commit()
    session.refresh(o)
    e.best_occurrence_id = o.id
    session.add(e)
    session.commit()
    session.refresh(e)
    d = entry_out(e, [o], recording_title=rec.title)
    assert d.term == "canting" and d.occurrences[0].source == "speech"
    assert d.best_occurrence.source == "speech"
