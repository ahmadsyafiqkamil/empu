import pytest
from factories import make_archive, make_recording

from empu.ask import AskError
from empu.ask.engine import REFUSAL_NO_ENTRIES
from empu.ask.ratelimit import RateLimiter
from empu.enums import AccessLevel, Category, EntryStatus, Source, SourceKind
from empu.meta_client import AnalyzeResult
from empu.models import Entry, Occurrence
from empu.routes.ask import get_ask_model


def _payload(
    answer="Canting adalah alat pena tembaga.", entry_ids=(), lang="id", insufficient=False
) -> dict:
    return {
        "answer": answer,
        "lang": lang,
        "entry_ids": list(entry_ids),
        "insufficient": insufficient,
    }


def _entry(session, archive, term: str, **kw) -> Entry:
    e = Entry(
        archive_id=archive.id,
        canon_key=f"term:{term}",
        term=term,
        category=kw.pop("category", Category.tool),
        status=kw.pop("status", EntryStatus.accepted),
        access_level=kw.pop("access_level", AccessLevel.public),
        gloss_id=kw.pop("gloss_id", "alat pena tembaga"),
        gloss_en=kw.pop("gloss_en", "copper-tipped pen"),
        crop_path=kw.pop("crop_path", None),
        **kw,
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    return e


def _occ(session, entry, recording, **kw) -> Occurrence:
    o = Occurrence(
        entry_id=entry.id,
        recording_id=recording.id,
        source=kw.pop("source", Source.speech),
        t_start=kw.pop("t_start", 134.0),
        t_end=kw.pop("t_end", 136.0),
        evidence_quote=kw.pop("evidence_quote", "ini namanya canting"),
        clip_path=kw.pop("clip_path", f"occurrences/{entry.id}/clip.mp4"),
        keyframe_path=kw.pop("keyframe_path", f"occurrences/{entry.id}/keyframe.jpg"),
        **kw,
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def setup_public(session):
    a = make_archive(session, slug="hidup-batik", title="Arsip Hidup")
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
    accepted = _entry(session, a, "canting", crop_path=f"entries/{1}/crop.png")
    _occ(session, accepted, rec)
    proposed = _entry(session, a, "nglorod", status=EntryStatus.proposed)
    _occ(session, proposed, rec, t_start=210.0, source=Source.visual_only)
    return a, accepted, proposed


def use_model(api, payload):
    api.app.dependency_overrides[get_ask_model] = lambda: (
        lambda prompt: AnalyzeResult(
            raw={},
            text="",
            parsed=payload,
            parse_error=None,
            usage={"input_tokens": 10},
            latency_s=0.1,
        )
    )


def test_public_ask_returns_answer_and_evidence_with_media_urls(api, session):
    a, entry, _ = setup_public(session)
    use_model(api, _payload(entry_ids=[entry.id]))

    r = api.post("/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"})

    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Canting adalah alat pena tembaga."
    assert body["lang"] == "id"
    assert body["refused"] is False
    assert body["prompt_version"] == "ask-v1"
    assert body["cached"] is False
    evidence = body["evidence"]
    assert len(evidence) == 1
    assert evidence[0]["entry"]["term"] == "canting"
    assert evidence[0]["occurrence"]["clip_url"].startswith("/media/")
    assert evidence[0]["occurrence"]["keyframe_url"].startswith("/media/")
    assert evidence[0]["entry"]["crop_url"].startswith("/media/")


def test_public_ask_keeps_the_source_label(api, session):
    a, entry, _ = setup_public(session)
    use_model(api, _payload(entry_ids=[entry.id]))

    body = api.post(
        "/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"}
    ).json()

    assert body["evidence"][0]["occurrence"]["source"] == "speech"
    assert body["evidence"][0]["occurrence"]["time_source"] in ("asr", "muse")


def test_public_ask_refused_has_no_evidence(api, session):
    a, entry, _ = setup_public(session)
    use_model(api, _payload(answer="Arsip belum memuatnya.", entry_ids=[], insufficient=True))

    body = api.post(
        "/api/public/archives/hidup-batik/ask", json={"question": "Bagaimana mengelas besi?"}
    ).json()

    assert body["refused"] is True
    assert body["evidence"] == []


def test_public_ask_drops_evidence_from_proposed_entries(api, session):
    a, entry, proposed = setup_public(session)
    use_model(api, _payload(entry_ids=[proposed.id, entry.id]))

    body = api.post(
        "/api/public/archives/hidup-batik/ask", json={"question": "Apa itu nglorod?"}
    ).json()

    terms = [e["entry"]["term"] for e in body["evidence"]]
    assert terms == ["canting"]
    assert proposed.id not in [e["entry"]["id"] for e in body["evidence"]]


def test_public_ask_refuses_when_only_proposed_was_cited(api, session):
    a, entry, proposed = setup_public(session)
    use_model(api, _payload(entry_ids=[proposed.id]))

    body = api.post(
        "/api/public/archives/hidup-batik/ask", json={"question": "Apa itu nglorod?"}
    ).json()

    assert body["refused"] is True
    assert body["evidence"] == []


def test_public_ask_404_for_sandbox_archive(api, session):
    make_archive(session, slug="sandbox", title="Judge sandbox", is_sandbox=True)

    r = api.post("/api/public/archives/sandbox/ask", json={"question": "apa itu canting?"})

    assert r.status_code == 404


def test_public_ask_404_for_unknown_archive(api, session):
    r = api.post("/api/public/archives/tidak-ada/ask", json={"question": "apa itu canting?"})
    assert r.status_code == 404


@pytest.mark.parametrize("question", ["", "a", "   ", "x" * 501])
def test_public_ask_422_for_unusable_question(api, session, question):
    setup_public(session)
    r = api.post("/api/public/archives/hidup-batik/ask", json={"question": question})
    assert r.status_code == 422


def test_public_ask_429_after_the_limit(api, session):
    a, entry, _ = setup_public(session)
    use_model(api, _payload(entry_ids=[entry.id]))
    from empu.routes.ask import get_limiter

    shared_limiter = RateLimiter(1, 3600)
    api.app.dependency_overrides[get_limiter] = lambda: shared_limiter

    first = api.post("/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"})
    second = api.post("/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"})

    assert first.status_code == 200
    assert second.status_code == 429


def test_default_limiter_is_shared_between_requests(settings):
    from empu.routes.ask import get_limiter

    assert get_limiter(settings) is get_limiter(settings)


def test_public_ask_502_when_model_fails(api, session):
    a, entry, _ = setup_public(session)

    def boom(prompt: str):
        raise AskError("no JSON")

    api.app.dependency_overrides[get_ask_model] = lambda: boom

    r = api.post("/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"})

    assert r.status_code == 502


def test_public_ask_empty_archive_refuses_without_calling_the_model(api, session):
    make_archive(session, slug="kosong", title="Kosong")
    calls: list[str] = []

    def model(prompt: str):
        calls.append(prompt)
        return AnalyzeResult(
            raw={}, text="", parsed=_payload(), parse_error=None, usage={}, latency_s=0.0
        )

    api.app.dependency_overrides[get_ask_model] = lambda: model

    body = api.post("/api/public/archives/kosong/ask", json={"question": "Apa itu canting?"}).json()

    assert calls == []
    assert body["refused"] is True
    assert body["answer"] == REFUSAL_NO_ENTRIES


def test_public_ask_works_without_a_studio_key(api, session):
    a, entry, _ = setup_public(session)
    use_model(api, _payload(entry_ids=[entry.id]))
    api.headers.pop("X-Studio-Key", None)

    r = api.post("/api/public/archives/hidup-batik/ask", json={"question": "Apa itu canting?"})

    assert r.status_code == 200
