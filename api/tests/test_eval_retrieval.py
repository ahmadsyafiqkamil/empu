from factories import make_archive

from empu.ask.index import build_index
from empu.enums import AccessLevel, Category, EntryStatus
from empu.evaluation.retrieval import (
    RetrievalQuestion,
    evaluate_retrieval,
    load_questions,
)
from empu.models import Entry


def _entry(session, archive, term: str) -> Entry:
    e = Entry(
        archive_id=archive.id,
        canon_key=f"term:{term}",
        term=term,
        category=Category.tool,
        status=EntryStatus.accepted,
        access_level=AccessLevel.public,
        gloss_id="",
        gloss_en="",
        variants_json=[],
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    return e


def _rows(session, a, terms: list[str]):
    return [build_index([(_entry(session, a, t), [])])[0] for t in terms]


def test_evaluate_counts_a_full_hit(session):
    a = make_archive(session)
    rows = _rows(session, a, ["canting", "mori"])
    qs = [RetrievalQuestion("apa itu canting?", ("canting",))]
    rep = evaluate_retrieval(qs, rows, k=1)
    assert rep.question_recall == 1.0 and rep.term_recall == 1.0
    assert rep.misses == []


def test_evaluate_reports_the_rank_of_a_miss(session):
    a = make_archive(session)
    rows = _rows(session, a, ["mori", "canting"])
    qs = [RetrievalQuestion("apa itu mori?", ("canting",))]
    rep = evaluate_retrieval(qs, rows, k=1)
    assert rep.question_recall == 0.0
    assert rep.misses[0]["missing"] == ["canting"]
    assert rep.misses[0]["rank"] == 2


def test_load_questions_parses_pipe_separated_expected(tmp_path):
    p = tmp_path / "q.csv"
    p.write_text("question,expected\napa itu canting?,canting\n,\n")
    assert load_questions(p) == [RetrievalQuestion("apa itu canting?", ("canting",))]
