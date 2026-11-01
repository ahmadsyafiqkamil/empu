from factories import make_archive, make_recording

from empu.ask.warm import read_questions, warm_questions
from empu.cache import ResponseCache
from empu.enums import AccessLevel, Category, EntryStatus, Source
from empu.meta_client import AnalyzeResult, MetaAPIError
from empu.models import Entry, Occurrence


def _entry(session, archive, term: str) -> Entry:
    e = Entry(
        archive_id=archive.id,
        canon_key=f"term:{term}",
        term=term,
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        gloss_id=f"arti {term}",
        gloss_en=f"meaning of {term}",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    return e


def _occ(session, entry, recording) -> Occurrence:
    o = Occurrence(
        entry_id=entry.id,
        recording_id=recording.id,
        source=Source.speech,
        t_start=1.0,
        t_end=2.0,
        evidence_quote=f"kutipan {entry.term}",
        clip_path=f"archives/{entry.id}/clip.mp4",
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def seed_two_public_entries(session):
    a = make_archive(session, slug="uji")
    rec = make_recording(session, a)
    first = _entry(session, a, "canting")
    _occ(session, first, rec)
    second = _entry(session, a, "mori")
    _occ(session, second, rec)
    return a, [first.id, second.id]


def fake_model(payloads: list[dict], calls: list[str]):
    queue = list(payloads)

    def call(prompt: str) -> AnalyzeResult:
        calls.append(prompt)
        payload = queue.pop(0) if queue else payloads[-1]
        return AnalyzeResult(
            raw={},
            text="",
            parsed=payload,
            parse_error=None,
            usage={"input_tokens": 10},
            latency_s=0.1,
        )

    return call


def test_read_questions_skips_blanks_comments_and_duplicates(tmp_path):
    p = tmp_path / "q.txt"
    p.write_text("apa itu canting\n\n# catatan\n  apa itu canting  \ncara nglorod\n")
    assert read_questions(p) == ["apa itu canting", "cara nglorod"]


def test_warm_fills_the_cache_and_reports_it(session, tmp_path):
    a, ids = seed_two_public_entries(session)
    calls: list[str] = []
    model = fake_model(
        [{"answer": "Canting.", "lang": "id", "entry_ids": [ids[0]], "insufficient": False}],
        calls,
    )
    cache = ResponseCache(tmp_path / "cache")

    first = warm_questions(
        session,
        archive_ids=[a.id],
        questions=["apa itu canting"],
        ask_model=model,
        cache=cache,
        model="muse-test",
        pack_names=["batik tulis"],
    )
    second = warm_questions(
        session,
        archive_ids=[a.id],
        questions=["apa itu canting"],
        ask_model=model,
        cache=cache,
        model="muse-test",
        pack_names=["batik tulis"],
    )

    assert len(calls) == 1
    assert first[0].cached is False and first[0].refused is False
    assert second[0].cached is True


def test_one_failure_does_not_stop_the_rest(session, tmp_path):
    a, ids = seed_two_public_entries(session)

    def model(prompt: str):
        if "GAGAL" in prompt:
            raise MetaAPIError(500, "boom")
        return AnalyzeResult(
            raw={},
            text="",
            parsed={"answer": "ok", "lang": "id", "entry_ids": [ids[0]], "insufficient": False},
            parse_error=None,
            usage={},
            latency_s=0.0,
        )

    out = warm_questions(
        session,
        archive_ids=[a.id],
        questions=["apa itu GAGAL", "apa itu canting"],
        ask_model=model,
        cache=ResponseCache(tmp_path / "c"),
        model="muse-test",
        pack_names=["batik tulis"],
    )

    assert out[0].error is not None
    assert out[1].error is None and out[1].refused is False


class _FakeAskClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def respond_text(self, prompt: str, *, model: str, schema=None, **kw) -> AnalyzeResult:
        self.calls += 1
        return AnalyzeResult(
            raw={},
            text="",
            parsed=self.payload,
            parse_error=None,
            usage={},
            latency_s=0.0,
        )


def test_ask_warm_reports_per_question(session, settings, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import empu.cli as cli

    a, ids = seed_two_public_entries(session)
    qfile = tmp_path / "q.txt"
    qfile.write_text("apa itu canting\napa itu mori\n", encoding="utf-8")
    fake = _FakeAskClient(
        {"answer": "ok", "lang": "id", "entry_ids": [ids[0]], "insufficient": False}
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_client", lambda s: fake)

    r = CliRunner().invoke(cli.app, ["ask", "warm", "--archive", "uji", "--questions", str(qfile)])

    assert r.exit_code == 0, r.output
    assert "warmed 2 of 2" in r.output
    assert "model calls" in r.output


def test_ask_warm_without_archive_covers_every_archive(session, settings, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import empu.cli as cli

    seed_two_public_entries(session)
    b = make_archive(session, slug="gamelan")
    rec = make_recording(session, b)
    _occ(session, _entry(session, b, "saron"), rec)

    qfile = tmp_path / "q.txt"
    qfile.write_text("apa itu saron\n", encoding="utf-8")
    seen: list[str] = []

    class Client:
        def respond_text(self, prompt: str, *, model: str, schema=None, **kw) -> AnalyzeResult:
            seen.append(prompt)
            return AnalyzeResult(
                raw={},
                text="",
                parsed={
                    "answer": "ok",
                    "lang": "id",
                    "entry_ids": [],
                    "insufficient": True,
                },
                parse_error=None,
                usage={},
                latency_s=0.0,
            )

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_client", lambda s: Client())

    r = CliRunner().invoke(cli.app, ["ask", "warm", "--questions", str(qfile)])

    assert r.exit_code == 0, r.output
    assert "canting" in seen[0]
    assert "saron" in seen[0]


def test_ask_warm_unknown_archive(tmp_path, settings, monkeypatch):
    from typer.testing import CliRunner

    import empu.cli as cli

    qfile = tmp_path / "q.txt"
    qfile.write_text("apa itu canting\n", encoding="utf-8")
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    r = CliRunner().invoke(
        cli.app, ["ask", "warm", "--archive", "tidak-ada", "--questions", str(qfile)]
    )

    assert r.exit_code == 2
    assert "not found" in r.output
