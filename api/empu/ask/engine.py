"""Answer an Ask Empu question from cited entries only.

Invariants this module enforces, independent of the model:

- The model only ever sees rows the caller is allowed to show.
- A cited id that was not in the rows that were sent is dropped.
- Evidence is always re-read from the database, so a consent withdrawal or a
  rejected occurrence takes effect even when the text answer came from cache.
- A refusal says why: `insufficient` keeps the model's own sentence, `uncited` replaces
  it, because a claim with no visible evidence must never reach the reader.
- If any cited entry can no longer be shown, the whole answer is refused: the
  sentence is atomic and cannot be trimmed to match the surviving evidence.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from sqlmodel import Session, select

from empu.ask.index import IndexEntry, build_index, prefilter
from empu.ask.prompts import ASK_PROMPT_VERSION, MAX_CITATIONS, build_prompt
from empu.cache import ResponseCache
from empu.config import Settings
from empu.enums import ConsentStatus, EntryStatus, OccurrenceStatus
from empu.meta_client import AnalyzeResult
from empu.models import Archive, Entry, Occurrence, Recording
from empu.packs import PackError, load_pack
from empu.visibility import entry_is_public, public_entries, public_occurrences

REFUSAL_NO_ENTRIES = "This archive has no published terms yet, so there is nothing to answer from."

REFUSAL_UNCITED = "I couldn't tie that answer to a term the archive can show, so I won't give one."

STUDIO_SKIP_STATUSES = (EntryStatus.rejected, EntryStatus.merged)


def pack_display_name(archive: Archive, settings: Settings) -> str:
    """The craft pack's English name, or its id when the pack cannot be read."""
    try:
        return load_pack(archive.craft_pack_id, settings.packs_dir).name.en
    except (PackError, AttributeError, KeyError):
        return archive.craft_pack_id


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
    reason: str | None = None


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


def _revision(entries: list[tuple[Entry, list[Occurrence]]]) -> str:
    """Fingerprint of everything that can change what the model is allowed to say.

    Acceptance changes which entries are in the list; an edit changes `updated_at`.
    Without this, a refusal cached while a term was `proposed` outlives the review
    that accepted it — which is exactly the sequence a demo runs through.
    """
    parts = sorted(
        f"{entry.id}:{entry.updated_at.isoformat() if entry.updated_at else ''}"
        for entry, _ in entries
    )
    return "|".join(parts)


def _cache_key(scope: str, archive_id: int, question: str, model: str, revision: str) -> str:
    digest = hashlib.sha256(
        f"{scope}|{archive_id}|{revision}|{question.casefold()}".encode()
    ).hexdigest()
    return ResponseCache.key(digest, model, ASK_PROMPT_VERSION, scope)


def _hydrate(
    session: Session,
    rows_by_id: dict[int, IndexEntry],
    cited_ids: list[int],
    *,
    scope: str,
) -> list[Cited]:
    """Re-read cited entries from the database so visibility is never stale.

    The occurrence set must be built with the same rules as the entry set: an entry
    can be public through one recording and private through another, and the public
    card must never show the private one.
    """
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
        if scope == "public":
            occs = public_occurrences(session, entry_id)
            if not entry_is_public(entry, occs):
                continue
        else:
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
    key = _cache_key(scope, archive_id, question, model, _revision(entries))

    cached = cache.get(key)
    if cached is not None:
        payload = cached.get("parsed") or {}
        usage = cached.get("usage") or {}
        from_cache = True
    else:
        prompt = build_prompt(rows, question, pack_names=[pack_name], scope=scope)
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
    # Keep the model's own order: the first ids are the ones it leaned on.
    cited_ids = cited_ids[:MAX_CITATIONS]

    evidence = _hydrate(session, rows_by_id, cited_ids, scope=scope)

    if payload.get("insufficient"):
        reason: str | None = "insufficient"
    elif not evidence or len(evidence) < len(cited_ids):
        reason = "uncited"
    else:
        reason = None

    if reason is not None:
        return AskResult(
            answer=answer if reason == "insufficient" else REFUSAL_UNCITED,
            lang=lang,
            refused=True,
            entry_ids=[],
            evidence=[],
            model=model,
            prompt_version=ASK_PROMPT_VERSION,
            cached=from_cache,
            usage=usage,
            reason=reason,
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
