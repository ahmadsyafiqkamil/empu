"""Retrieval measurement for Ask Empu.

Answers one question with numbers: of the entries that a correct answer needs,
how many actually survived ranking into the list handed to the model? Nothing
here touches the answer path — it only reads `rank_rows`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from empu.ask.index import IndexEntry, rank_rows


@dataclass(frozen=True)
class RetrievalQuestion:
    question: str
    expected: tuple[str, ...]


def load_questions(path: Path) -> list[RetrievalQuestion]:
    """Read `question,expected` rows; `expected` is pipe separated."""
    out: list[RetrievalQuestion] = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            question = (row.get("question") or "").strip()
            raw = (row.get("expected") or "").strip()
            expected = tuple(part.strip() for part in raw.split("|") if part.strip())
            if not question or not expected:
                continue
            out.append(RetrievalQuestion(question=question, expected=expected))
    return out


@dataclass(frozen=True)
class RetrievalReport:
    n_questions: int
    n_rows: int
    k: int
    question_recall: float
    term_recall: float
    misses: list[dict] = field(default_factory=list)


def evaluate_retrieval(
    questions: list[RetrievalQuestion],
    rows: list[IndexEntry],
    *,
    k: int = 4,
) -> RetrievalReport:
    """Fraction of questions whose every expected term lands in the top `k`."""
    hits = 0
    term_total = 0
    term_found = 0
    misses: list[dict] = []

    for q in questions:
        ranked = rank_rows(q.question, rows)
        ranked_terms = [r.term.casefold() for r in ranked]
        top = set(ranked_terms[: max(k, 0)])
        missing = [e for e in q.expected if e.casefold() not in top]
        term_total += len(q.expected)
        term_found += len(q.expected) - len(missing)
        if not missing:
            hits += 1
            continue
        first = missing[0].casefold()
        rank = ranked_terms.index(first) + 1 if first in ranked_terms else None
        misses.append({"question": q.question, "missing": missing, "rank": rank})

    n = len(questions)
    return RetrievalReport(
        n_questions=n,
        n_rows=len(rows),
        k=k,
        question_recall=hits / n if n else 0.0,
        term_recall=term_found / term_total if term_total else 0.0,
        misses=misses,
    )