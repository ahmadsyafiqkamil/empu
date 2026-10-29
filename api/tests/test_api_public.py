from factories import make_archive, make_recording

from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.models import Entry, Occurrence


def _setup(session):
    a = make_archive(session, slug="hidup-batik", title="Living Archive", is_demo=True)
    rec = make_recording(
        session,
        a,
        consent_scope=AccessLevel.public,
        source_kind=SourceKind.cc_by_video,
        source_url="https://youtu.be/x",
        source_creator="c",
        license="CC BY 3.0",
        attribution="by c",
    )
    e = Entry(
        archive_id=a.id,
        canon_key="term:canting",
        term="canting",
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        gloss_en="wax pen",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(entry_id=e.id, recording_id=rec.id, source=Source.speech, t_start=1, t_end=2)
    )
    session.commit()
    return a, e


def test_public_list_no_key(api, session):
    _setup(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get("/api/public/archives")
    assert r.status_code == 200
    assert r.json()[0]["slug"] == "hidup-batik"


def test_proposed_not_listed(api, session):
    a, e = _setup(session)
    e.status = EntryStatus.proposed
    session.add(e)
    session.commit()
    api.headers.pop("X-Studio-Key", None)
    r = api.get("/api/public/archives/hidup-batik/entries")
    assert r.json() == []


def test_unknown_id_is_404(api, session):
    api.headers.pop("X-Studio-Key", None)
    assert api.get("/api/public/entries/99999").status_code == 404


def test_public_entry_includes_validation_label(api, session):
    a, e = _setup(session)
    api.headers.pop("X-Studio-Key", None)
    r = api.get(f"/api/public/entries/{e.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["term"] == "canting"
    assert body["validation_label"] == "Validated by the documenter"
    assert body["attribution"] == "by c"
    assert body["occurrences"][0]["source"] == "speech"