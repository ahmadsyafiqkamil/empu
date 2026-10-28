from factories import make_archive, make_recording

from empu.enums import Category, Source
from empu.models import Entry, Occurrence


def test_list_and_review(api, session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(
        archive_id=a.id,
        canon_key="term:x",
        term="canting",
        category=Category.tool,
        is_novel=True,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    listed = api.get(f"/api/archives/{a.id}/entries", params={"is_novel": True}).json()
    assert listed[0]["term"] == "canting" and listed[0]["source"] == "speech"
    r = api.post(f"/api/entries/{e.id}/review", json={"action": "accept", "actor": "syafiq"})
    assert r.status_code == 200 and r.json()["status"] == "accepted"


def test_recording_entries_excludes_other_recordings(api, session):
    a = make_archive(session)
    rec1 = make_recording(session, a, title="First")
    rec2 = make_recording(session, a, title="Second")
    e1 = Entry(
        archive_id=a.id,
        canon_key="term:a",
        term="canting",
        category=Category.tool,
    )
    e2 = Entry(
        archive_id=a.id,
        canon_key="term:b",
        term="klowong",
        category=Category.technique,
    )
    session.add(e1)
    session.add(e2)
    session.commit()
    session.refresh(e1)
    session.refresh(e2)
    session.add(
        Occurrence(entry_id=e1.id, recording_id=rec1.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.add(
        Occurrence(entry_id=e2.id, recording_id=rec2.id, source=Source.speech, t_start=3, t_end=4)
    )
    session.commit()
    listed = api.get(f"/api/recordings/{rec1.id}/entries").json()
    assert len(listed) == 1
    assert listed[0]["id"] == e1.id and listed[0]["term"] == "canting"
