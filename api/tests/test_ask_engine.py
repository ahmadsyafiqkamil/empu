import pytest
from factories import make_archive, make_recording

from empu.ask.engine import AskError, answer_question, collect_entries
from empu.cache import ResponseCache
from empu.enums import (
    AccessLevel,
    Category,
    ConsentStatus,
    EntryStatus,
    OccurrenceStatus,
    Source,
)
from empu.meta_client import AnalyzeResult
from empu.models import Entry, Occurrence


def _entry(session, archive, term: str, **kw) -> Entry:
    e = Entry(
        archive_id=archive.id,
        canon_key=f"term:{term}",
        term=term,
        category=kw.pop("category", Category.tool),
        status=kw.pop("status", EntryStatus.accepted),
        access_level=kw.pop("access_level", AccessLevel.public),
        gloss_id=kw.pop("gloss_id", f"arti {term}"),
        gloss_en=kw.pop("gloss_en", f"meaning of {term}"),
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
        t_start=kw.pop("t_start", 1.0),
        t_end=kw.pop("t_end", 2.0),
        evidence_quote=kw.pop("evidence_quote", f"kutipan {entry.term}"),
        clip_path=kw.pop("clip_path", f"archives/{entry.id}/clip.mp4"),
        **kw,
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def seed(session):
    a = make_archive(session, slug="hidup-batik")
    rec = make_recording(session, a)
    accepted = _entry(session, a, "canting")
    _occ(session, accepted, rec, t_start=134.0)

    proposed = _entry(session, a, "nglorod", status=EntryStatus.proposed)
    _occ(session, proposed, rec, t_start=210.0, source=Source.visual_only)

    other_rec = make_recording(session, a, title="Withdrawn")
    withdrawn = _entry(session, a, "mori")
    _occ(session, withdrawn, other_rec)
    other_rec.consent_status = ConsentStatus.withdrawn
    session.add(other_rec)
    session.commit()

    return a, {
        "accepted": accepted,
        "proposed": proposed,
        "withdrawn": withdrawn,
        "rec": rec,
        "other_rec": other_rec,
    }


def fake_model(payload: dict, calls: list[str] | None = None):
    def call(prompt: str) -> AnalyzeResult:
        if calls is not None:
            calls.append(prompt)
        return AnalyzeResult(
            raw={},
            text="",
            parsed=payload,
            parse_error=None,
            usage={"input_tokens": 10},
            latency_s=0.1,
        )

    return call


def ask(session, tmp_path, archive, model, question="apa itu canting?", scope="public"):
    return answer_question(
        session,
        archive_id=archive.id,
        question=question,
        scope=scope,
        ask_model=model,
        cache=ResponseCache(tmp_path / "cache"),
        model="muse-test",
        pack_name="batik tulis",
    )


def test_public_scope_hides_proposed_and_withdrawn(session):
    a, ids = seed(session)

    terms = {e.term for e, _ in collect_entries(session, a.id, "public")}

    assert terms == {"canting"}


def test_studio_scope_includes_proposed_but_hides_withdrawn(session):
    a, ids = seed(session)

    terms = {e.term for e, _ in collect_entries(session, a.id, "studio")}

    assert terms == {"canting", "nglorod"}


def test_answer_hydrates_cited_entries_with_the_best_occurrence(session, tmp_path):
    a, ids = seed(session)
    entry = ids["accepted"]
    second = _occ(session, entry, ids["rec"], t_start=40.0, evidence_quote="kedua")
    entry.best_occurrence_id = second.id
    session.add(entry)
    session.commit()

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Canting adalah alat.",
                "lang": "id",
                "entry_ids": [entry.id],
                "insufficient": False,
            }
        ),
    )

    assert result.refused is False
    assert result.entry_ids == [entry.id]
    assert len(result.evidence) == 1
    assert result.evidence[0].occurrence.id == second.id
    assert len(result.evidence[0].occurrences) == 2


def test_unknown_citation_ids_are_dropped(session, tmp_path):
    a, ids = seed(session)
    entry = ids["accepted"]

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Canting.",
                "lang": "id",
                "entry_ids": [entry.id, 9999],
                "insufficient": False,
            }
        ),
    )

    assert result.entry_ids == [entry.id]
    assert [c.entry.term for c in result.evidence] == ["canting"]


def test_insufficient_clears_evidence_and_sets_refused(session, tmp_path):
    a, ids = seed(session)

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Arsip belum memuatnya.",
                "lang": "id",
                "entry_ids": [ids["accepted"].id],
                "insufficient": True,
            }
        ),
        question="bagaimana mengelas besi?",
    )

    assert result.refused is True
    assert result.evidence == []
    assert result.entry_ids == []


def test_citation_of_an_entry_outside_scope_refuses(session, tmp_path):
    a, ids = seed(session)

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Nglorod adalah meluruhkan malam.",
                "lang": "id",
                "entry_ids": [ids["proposed"].id],
                "insufficient": False,
            }
        ),
        question="apa itu nglorod?",
    )

    assert result.refused is True
    assert result.evidence == []


def test_empty_archive_skips_the_model(session, tmp_path):
    a = make_archive(session, slug="kosong")
    calls: list[str] = []

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {"answer": "should not be used", "lang": "en", "entry_ids": [], "insufficient": False},
            calls,
        ),
    )

    assert calls == []
    assert result.refused is True
    assert result.evidence == []


def test_cache_hit_skips_the_second_model_call(session, tmp_path):
    a, ids = seed(session)
    calls: list[str] = []
    model = fake_model(
        {
            "answer": "Canting adalah alat.",
            "lang": "id",
            "entry_ids": [ids["accepted"].id],
            "insufficient": False,
        },
        calls,
    )

    first = ask(session, tmp_path, a, model)
    second = ask(session, tmp_path, a, model)

    assert len(calls) == 1
    assert first.cached is False
    assert second.cached is True
    assert second.answer == first.answer


def test_withdrawal_invalidates_the_cache_and_drops_the_term(session, tmp_path):
    a = make_archive(session, slug="cache-withdraw")
    keep_rec = make_recording(session, a, title="Tetap")
    drop_rec = make_recording(session, a, title="Dicabut")
    kept = _entry(session, a, "canting")
    dropped = _entry(session, a, "mori")
    _occ(session, kept, keep_rec)
    _occ(session, dropped, drop_rec)

    calls: list[str] = []
    model = fake_model(
        {
            "answer": "Canting dan mori.",
            "lang": "id",
            "entry_ids": [kept.id, dropped.id],
            "insufficient": False,
        },
        calls,
    )

    first = ask(session, tmp_path, a, model)
    assert first.refused is False
    assert len(first.evidence) == 2

    drop_rec.consent_status = ConsentStatus.withdrawn
    session.add(drop_rec)
    session.commit()

    second = ask(session, tmp_path, a, model)

    # Withdrawal changes the visible set, so the cached answer is not reused and the
    # withdrawn term never reaches the reader as evidence.
    assert len(calls) == 2
    assert second.cached is False
    assert [c.entry.term for c in second.evidence] == ["canting"]


def test_cached_answer_with_all_citations_withdrawn_refuses(session, tmp_path):
    a = make_archive(session, slug="cache-withdraw-all")
    rec = make_recording(session, a)
    entry = _entry(session, a, "canting")
    _occ(session, entry, rec)

    calls: list[str] = []
    model = fake_model(
        {
            "answer": "Canting adalah alat.",
            "lang": "id",
            "entry_ids": [entry.id],
            "insufficient": False,
        },
        calls,
    )

    assert ask(session, tmp_path, a, model).refused is False

    rec.consent_status = ConsentStatus.withdrawn
    session.add(rec)
    session.commit()

    second = ask(session, tmp_path, a, model)

    assert len(calls) == 1
    assert second.refused is True
    assert second.evidence == []


def test_unparseable_model_output_raises_ask_error(session, tmp_path):
    a, ids = seed(session)

    def broken(prompt: str) -> AnalyzeResult:
        return AnalyzeResult(
            raw={}, text="nope", parsed=None, parse_error="no JSON", usage={}, latency_s=0.1
        )

    with pytest.raises(AskError):
        ask(session, tmp_path, a, broken)


def test_question_is_normalised_before_hashing(session, tmp_path):
    a, ids = seed(session)
    calls: list[str] = []
    model = fake_model(
        {
            "answer": "Canting.",
            "lang": "id",
            "entry_ids": [ids["accepted"].id],
            "insufficient": False,
        },
        calls,
    )

    ask(session, tmp_path, a, model, question="  apa   itu canting?  ")
    ask(session, tmp_path, a, model, question="apa itu canting?")

    assert len(calls) == 1


def test_rejected_occurrences_are_not_used_as_evidence(session, tmp_path):
    a, ids = seed(session)
    entry = ids["accepted"]
    _occ(session, entry, ids["rec"], status=OccurrenceStatus.rejected, evidence_quote="ditolak")

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {"answer": "Canting.", "lang": "id", "entry_ids": [entry.id], "insufficient": False}
        ),
    )

    quotes = [o.evidence_quote for o in result.evidence[0].occurrences]
    assert "ditolak" not in quotes


def test_public_hydration_ignores_private_scope_occurrences(session, tmp_path):
    """An entry reachable publicly must never show a clip from a non-public recording."""
    a = make_archive(session, slug="campur")
    public_rec = make_recording(session, a, title="Publik")
    private_rec = make_recording(session, a, title="Pribadi", consent_scope=AccessLevel.private)
    entry = _entry(session, a, "canting")
    public_occ = _occ(session, entry, public_rec, t_start=10.0, evidence_quote="boleh")
    private_occ = _occ(session, entry, private_rec, t_start=900.0, evidence_quote="JANGAN TAMPIL")
    entry.best_occurrence_id = private_occ.id
    session.add(entry)
    session.commit()

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {"answer": "Canting.", "lang": "id", "entry_ids": [entry.id], "insufficient": False}
        ),
    )

    assert result.refused is False
    assert result.evidence[0].occurrence.id == public_occ.id
    assert [o.id for o in result.evidence[0].occurrences] == [public_occ.id]
    assert all(o.evidence_quote != "JANGAN TAMPIL" for o in result.evidence[0].occurrences)


def test_cached_refusal_is_not_served_after_the_entry_is_accepted(session, tmp_path):
    a = make_archive(session, slug="cache-review")
    rec = make_recording(session, a)
    # One already-public entry keeps the archive non-empty, so the model is asked.
    _occ(session, _entry(session, a, "canting"), rec)
    entry = _entry(session, a, "nglorod", status=EntryStatus.proposed)
    _occ(session, entry, rec)

    calls: list[str] = []
    model = fake_model(
        {"answer": "Arsip belum memuatnya.", "lang": "id", "entry_ids": [], "insufficient": True},
        calls,
    )

    first = ask(session, tmp_path, a, model, question="apa itu nglorod?")
    assert first.refused is True
    assert len(calls) == 1

    entry.status = EntryStatus.accepted
    session.add(entry)
    session.commit()

    model_after = fake_model(
        {
            "answer": "Nglorod adalah meluruhkan malam.",
            "lang": "id",
            "entry_ids": [entry.id],
            "insufficient": False,
        },
        calls,
    )
    second = ask(session, tmp_path, a, model_after, question="apa itu nglorod?")

    assert len(calls) == 2, "the cached refusal must not survive an accepted entry"
    assert second.refused is False


def test_cached_answer_is_not_served_after_a_gloss_edit(session, tmp_path):
    a = make_archive(session, slug="cache-edit")
    rec = make_recording(session, a)
    entry = _entry(session, a, "canting")
    _occ(session, entry, rec)

    calls: list[str] = []
    model = fake_model(
        {
            "answer": "Canting versi lama.",
            "lang": "id",
            "entry_ids": [entry.id],
            "insufficient": False,
        },
        calls,
    )

    ask(session, tmp_path, a, model)

    entry.gloss_id = "arti baru"
    entry.updated_at = entry.updated_at.replace(year=2030)
    session.add(entry)
    session.commit()

    ask(session, tmp_path, a, model)

    assert len(calls) == 2


def test_merged_entry_is_dropped_from_evidence(session, tmp_path):
    """Defensive: hydration re-checks status, so a merged entry never shows a card."""
    a = make_archive(session, slug="partial")
    rec = make_recording(session, a)
    kept = _entry(session, a, "canting")
    dropped = _entry(session, a, "mori")
    _occ(session, kept, rec)
    _occ(session, dropped, rec)

    # Hydration skips merged entries; force one id into that state after collect.
    dropped.status = EntryStatus.merged
    session.add(dropped)
    session.commit()

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Canting dan mori dipakai bersama.",
                "lang": "id",
                "entry_ids": [kept.id, dropped.id],
                "insufficient": False,
            }
        ),
    )

    assert [c.entry.term for c in result.evidence] == ["canting"]
    assert result.refused is False


def test_uncited_claim_is_replaced_with_a_refusal_sentence(session, tmp_path):
    a, ids = seed(session)

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Canting adalah alat pena tembaga.",
                "lang": "id",
                "entry_ids": [9999],
                "insufficient": False,
            }
        ),
        question="apa itu canting?",
    )

    assert result.refused is True
    assert result.evidence == []
    assert result.answer != "Canting adalah alat pena tembaga."
    assert result.reason == "uncited"


def test_insufficient_keeps_the_model_sentence(session, tmp_path):
    a, ids = seed(session)

    result = ask(
        session,
        tmp_path,
        a,
        fake_model(
            {
                "answer": "Arsip belum memuatnya.",
                "lang": "id",
                "entry_ids": [],
                "insufficient": True,
            }
        ),
        question="bagaimana mengelas besi?",
    )

    assert result.refused is True
    assert result.reason == "insufficient"
    assert result.answer == "Arsip belum memuatnya."


def test_unaccepting_an_entry_hides_a_previously_cached_answer(session, tmp_path):
    a = make_archive(session, slug="unaccept")
    rec = make_recording(session, a)
    entry = _entry(session, a, "canting")
    _occ(session, entry, rec)
    payload = {
        "answer": "Canting adalah alat.",
        "lang": "id",
        "entry_ids": [entry.id],
        "insufficient": False,
    }

    assert ask(session, tmp_path, a, fake_model(payload)).refused is False

    entry.status = EntryStatus.proposed
    session.add(entry)
    session.commit()

    assert ask(session, tmp_path, a, fake_model(payload)).refused is True


def test_making_an_entry_private_hides_a_previously_cached_answer(session, tmp_path):
    a = make_archive(session, slug="private-later")
    rec = make_recording(session, a)
    entry = _entry(session, a, "canting")
    _occ(session, entry, rec)
    payload = {
        "answer": "Canting adalah alat.",
        "lang": "id",
        "entry_ids": [entry.id],
        "insufficient": False,
    }

    assert ask(session, tmp_path, a, fake_model(payload)).refused is False

    entry.access_level = AccessLevel.private
    session.add(entry)
    session.commit()

    assert ask(session, tmp_path, a, fake_model(payload)).refused is True
