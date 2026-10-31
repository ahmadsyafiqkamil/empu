"""Answer an Ask Empu question from cited entries only.

Invariants this module enforces, independent of the model:

- The model only ever sees rows the caller is allowed to show.
- A cited id that was not in the rows that were sent is dropped.
- Evidence is always re-read from the database, so a consent withdrawal or a
  rejected occurrence takes effect even when the text answer came from cache.
- No valid citation means `refused`: the answer is shown, the evidence is empty.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from sqlmodel import Session, select

from empu.ask.index import IndexEntry, build_index, prefilter
from empu.ask.prompts import ASK_PROMPT_VERSION, build_prompt
from empu.cache import ResponseCache
from empu.enums import ConsentStatus, EntryStatus, OccurrenceStatus
from empu.meta_client import AnalyzeResult
from empu.models import Archive, Entry, Occurrence, Recording
from empu.visibility import public_entries

REFUSAL_NO_ENTRIES = "This archive has no published terms yet, so there is nothing to answer from."

STUDIO_SKIP_STATUSES = (EntryStatus.rejected, EntryStatus.merged)


class AskError(RuntimeError):
    """The model could not produce a usable answer."""


@dataclass(frozen=True)
class Cited:
    entry: Entry
    occurrences: list[Occurrence]
    occurrence: Occurrence


@dataclass(frozen=True)
class AskResult:
    answer: str
    lang: str
    refused: bool
    entry_ids: list[int]
    evidence: list[Cited]
    model: str
    prompt_version: str
    cached: bool
    usage: dict


def _studio_occurrences(session: Session, entry_id: int) -> list[Occurrence]:
    occs = session.exec(select(Occurrence).where(Occurrence.entry_id == entry_id)).all()
    out: list[Occurrence] = []
    for o in occs:
        if o.status is OccurrenceStatus.rejected:
            continue
        rec = session.get(Recording, o.recording_id)
        if rec is None or rec.consent_status is not ConsentStatus.granted:
            continue
        arch = session.get(Archive, rec.archive_id)
        if arch is not None and arch.is_sandbox:
            continue
        out.append(o)
    return out


def collect_entries(
    session: Session, archive_id: int, scope: str
) -> list[tuple[Entry, list[Occurrence]]]:
    """Entries this scope may answer from, with their usable occurrences.

    `public` delegates to empu.visibility — never re-implement those rules here.
    `studio` is the review surface: includes proposed and private entries, still
    hides consent-withdrawn recordings, rejected entries and sandboxes.
    """
    if scope == "public":
        return public_entries(session, archive_id)

    if scope != "studio":
        raise ValueError(f"unknown scope {scope!r}")

    entries = session.exec(select(Entry).where(Entry.archive_id == archive_id)).all()
    out: list[tuple[Entry, list[Occurrence]]] = []
    for entry in entries:
        if entry.status in STUDIO_SKIP_STATUSES:
            continue
        occs = _studio_occurrences(session, entry.id)
        if not occs:
            continue
        out.append((entry, occs))
    out.sort(key=lambda pair: pair[0].term.casefold())
    return out


def _cache_key(scope: str, archive_id: int, question: str, model: str) -> str:
    digest = hashlib.sha256(f"{scope}|{archive_id}|{question.casefold()}".encode()).hexdigest()
    return ResponseCache.key(digest, model, ASK_PROMPT_VERSION, scope)


def _hydrate(
    session: Session, rows_by_id: dict[int, IndexEntry], cited_ids: list[int]
) -> list[Cited]:
    """Re-read cited entries from the database so visibility is never stale."""
    out: list[Cited] = []
    for entry_id in cited_ids:
        row = rows_by_id.get(entry_id)
        if row is None:
            continue
        entry = session.get(Entry, entry_id)
        if entry is None:
            continue
        if entry.status in STUDIO_SKIP_STATUSES:
            continue
        occs = _studio_occurrences(session, entry_id)
        if not occs:
            continue
        best = next((o for o in occs if o.id == entry.best_occurrence_id), occs[0])
        out.append(Cited(entry=entry, occurrences=occs, occurrence=best))
    return out


def answer_question(
    session: Session,
    *,
    archive_id: int,
    question: str,
    scope: str,
    ask_model: Callable[[str], AnalyzeResult],
    cache: ResponseCache,
    model: str,
    pack_name: str,
    max_entries: int = 60,
) -> AskResult:
    question = " ".join(question.split())
    entries = collect_entries(session, archive_id, scope)

    if not entries:
        return AskResult(
            answer=REFUSAL_NO_ENTRIES,
            lang="en",
            refused=True,
            entry_ids=[],
            evidence=[],
            model=model,
            prompt_version=ASK_PROMPT_VERSION,
            cached=False,
            usage={},
        )

    rows = prefilter(question, build_index(entries), limit=max_entries)
    rows_by_id = {row.id: row for row in rows}
    key = _cache_key(scope, archive_id, question, model)

    cached = cache.get(key)
    if cached is not None:
        payload = cached.get("parsed") or {}
        usage = cached.get("usage") or {}
        from_cache = True
    else:
        prompt = build_prompt(rows, question, pack_name=pack_name, scope=scope)
        result = ask_model(prompt)
        if result.parsed is None:
            raise AskError(result.parse_error or "model returned no JSON")
        payload = result.parsed
        usage = result.usage
        cache.put(key, {"parsed": payload, "usage": usage})
        from_cache = False

    answer = str(payload.get("answer") or "").strip()
    lang = str(payload.get("lang") or "en")
    cited_raw = payload.get("entry_ids") or []
    cited_ids: list[int] = []
    for value in cited_raw if isinstance(cited_raw, list) else []:
        try:
            entry_id = int(value)
        except (TypeError, ValueError):
            continue
        if entry_id in rows_by_id and entry_id not in cited_ids:
            cited_ids.append(entry_id)

    evidence = _hydrate(session, rows_by_id, cited_ids)
    refused = bool(payload.get("insufficient")) or not evidence

    if refused:
        return AskResult(
            answer=answer,
            lang=lang,
            refused=True,
            entry_ids=[],
            evidence=[],
            model=model,
            prompt_version=ASK_PROMPT_VERSION,
            cached=from_cache,
            usage=usage,
        )

    return AskResult(
        answer=answer,
        lang=lang,
        refused=False,
        entry_ids=[c.entry.id for c in evidence],
        evidence=evidence,
        model=model,
        prompt_version=ASK_PROMPT_VERSION,
        cached=from_cache,
        usage=usage,
    )
