"""Entry index for Ask Empu.

One `IndexEntry` per entry that the caller is allowed to see. This module owns no
visibility rules: whoever calls it passes the entries it may use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rapidfuzz import fuzz

from empu.models import Entry, Occurrence

QUOTE_LIMIT = 160
MAX_EVIDENCE = 2
TERM_HIT_BOOST = 30
VARIANT_HIT_BOOST = 20


@dataclass(frozen=True)
class ArchiveLabel:
    """What a row needs to say which archive it came from."""

    slug: str
    title: str


@dataclass(frozen=True)
class Evidence:
    source: str
    quote: str
    t_start: float


@dataclass(frozen=True)
class IndexEntry:
    id: int
    term: str
    category: str
    stage_id: str | None
    gloss_id: str
    gloss_en: str
    status: str
    variants: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    archive_slug: str = ""
    archive_title: str = ""


def _quote(occ: Occurrence) -> str:
    text = (occ.evidence_quote or "").strip() or (occ.visible or "").strip()
    return text[:QUOTE_LIMIT]


def _ordered(entry: Entry, occurrences: list[Occurrence]) -> list[Occurrence]:
    best = [o for o in occurrences if o.id is not None and o.id == entry.best_occurrence_id]
    rest = [o for o in occurrences if o not in best]
    return (best + rest)[:MAX_EVIDENCE]


def build_index(
    entries: list[tuple[Entry, list[Occurrence]]],
    archives: Mapping[int, ArchiveLabel] | None = None,
) -> list[IndexEntry]:
    labels = archives or {}
    rows: list[IndexEntry] = []
    for entry, occurrences in entries:
        label = labels.get(entry.archive_id)
        rows.append(
            IndexEntry(
                id=entry.id or 0,
                term=entry.term,
                category=getattr(entry.category, "value", str(entry.category)),
                stage_id=entry.stage_id,
                gloss_id=entry.gloss_id,
                gloss_en=entry.gloss_en,
                status=getattr(entry.status, "value", str(entry.status)),
                variants=tuple(entry.variants_json or []),
                evidence=tuple(
                    Evidence(
                        source=getattr(o.source, "value", str(o.source)),
                        quote=_quote(o),
                        t_start=o.t_start,
                    )
                    for o in _ordered(entry, occurrences)
                ),
                archive_slug=label.slug if label else "",
                archive_title=label.title if label else "",
            )
        )
    return rows


def _blob(row: IndexEntry) -> str:
    parts = [row.term, row.gloss_id, row.gloss_en, row.category, row.stage_id or ""]
    parts += [e.quote for e in row.evidence]
    parts += list(row.variants)
    return " ".join(p for p in parts if p)


def _score(question: str, row: IndexEntry) -> float:
    q = question.casefold()
    score = fuzz.token_set_ratio(_blob(row), question)
    if row.term.casefold() in q:
        score += TERM_HIT_BOOST
    if any(v.casefold() in q for v in row.variants if v.strip()):
        score += VARIANT_HIT_BOOST
    return score


def rank_rows(question: str, rows: list[IndexEntry]) -> list[IndexEntry]:
    """Every row, best first. Ranking only — callers decide how many to keep."""
    return sorted(rows, key=lambda r: (-_score(question, r), r.id))


def prefilter(question: str, rows: list[IndexEntry], limit: int = 60) -> list[IndexEntry]:
    """Keep the most likely rows, always in id order so the prompt is deterministic."""
    if len(rows) <= limit:
        return sorted(rows, key=lambda r: r.id)
    ranked = rank_rows(question, rows)[:limit]
    return sorted(ranked, key=lambda r: r.id)
