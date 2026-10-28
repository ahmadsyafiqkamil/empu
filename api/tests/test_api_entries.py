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
