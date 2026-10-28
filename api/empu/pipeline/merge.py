"""Merge per-chunk Muse output into archive entries (spec 8.5).

Absolute times -> optional retime (Mode B) -> overlap dedup -> grouping -> best occurrence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from rapidfuzz import fuzz, process

from empu.enums import CONFIDENCE_RANK, Category, Confidence, Source, TimeSource, VisualMatch
from empu.muse_schema import MuseTerm
from empu.packs import CraftPack, PackRef
from empu.pipeline.process_map import StageMatcher, StepDraft, stage_at
from empu.text import normalize


@dataclass(frozen=True)
class CanonMatch:
    canon_key: str
    term: str
    pack_term_id: str | None
    pack_stage_id: str | None
    is_novel: bool
    method: Literal["exact", "fuzzy", "novel"]
    score: float


class Canonicalizer:
    def __init__(self, pack: CraftPack, threshold: float = 90.0) -> None:
        self.pack = pack
        self.threshold = threshold
        self.index = pack.variant_index()
        self._keys = list(self.index)

    def match(self, term: str, spoken: str = "") -> CanonMatch:
        forms = [k for k in (normalize(term), normalize(spoken)) if k]
        for key in forms:
            if key in self.index:
                return self._resolve(self.index[key], "exact", 100.0)
        best: tuple[str, float] | None = None
        for key in forms:
            hit = process.extractOne(
                key, self._keys, scorer=fuzz.ratio, score_cutoff=self.threshold
            )
            if hit is not None and (best is None or hit[1] > best[1]):
                best = (hit[0], float(hit[1]))
        if best is not None:
            return self._resolve(self.index[best[0]], "fuzzy", best[1])
        label = term.strip() or spoken.strip()
        novel_key = f"novel:{forms[0] if forms else ''}"
        return CanonMatch(novel_key, label, None, None, True, "novel", 0.0)

    def _resolve(self, ref: PackRef, method: Literal["exact", "fuzzy"], score: float) -> CanonMatch:
        if ref.kind == "term":
            t = self.pack.term(ref.id)
            assert t is not None
            return CanonMatch(f"term:{t.id}", t.label, t.id, None, False, method, score)
        s = self.pack.stage(ref.id)
        assert s is not None
        return CanonMatch(f"stage:{s.id}", s.display_label, None, s.id, False, method, score)


@dataclass
class AbsOccurrence:
    chunk_idx: int
    muse: MuseTerm
    canon: CanonMatch
    t_start: float
    t_end: float
    edge_s: float
    stage_id: str | None = None
    time_source: TimeSource = TimeSource.muse
    asr_score: float | None = None


def occurrence_rank(
    source: Source | str,
    visual_match: VisualMatch | str,
    confidence: Confidence | str,
    duration: float,
) -> tuple:
    return (
        Source(source) is Source.speech,
        VisualMatch(visual_match) is VisualMatch.yes,
        CONFIDENCE_RANK[Confidence(confidence)],
        duration,
    )


def _rank(o: AbsOccurrence) -> tuple:
    return occurrence_rank(
        o.muse.source, o.muse.visual_match, o.muse.confidence, o.t_end - o.t_start
    )


def collect_occurrences(analyses: Sequence[Any], canon: Canonicalizer) -> list[AbsOccurrence]:
    out: list[AbsOccurrence] = []
    for a in analyses:
        if a.output is None:
            continue
        spec = a.spec
        for t in a.output.terms:
            ts = min(spec.start_s + t.t_start, spec.end_s)
            te = min(max(spec.start_s + t.t_end, ts), spec.end_s)
            out.append(
                AbsOccurrence(
                    spec.idx,
                    t,
                    canon.match(t.term, t.spoken),
                    ts,
                    te,
                    edge_s=min(ts - spec.start_s, spec.end_s - te),
                )
            )
    return sorted(out, key=lambda o: (o.t_start, o.chunk_idx))


def dedup_overlap(occs: Sequence[AbsOccurrence], tol_s: float = 4.0) -> list[AbsOccurrence]:
    kept: list[AbsOccurrence] = []
    last: dict[str, int] = {}
    for o in sorted(occs, key=lambda o: (o.t_start, o.chunk_idx)):
        i = last.get(o.canon.canon_key)
        if i is not None:
            prev = kept[i]
            if prev.chunk_idx != o.chunk_idx and abs(o.t_start - prev.t_start) <= tol_s:
                if (CONFIDENCE_RANK[o.muse.confidence], o.edge_s) > (
                    CONFIDENCE_RANK[prev.muse.confidence],
                    prev.edge_s,
                ):
                    kept[i] = o
                continue
        last[o.canon.canon_key] = len(kept)
        kept.append(o)
    return kept


@dataclass
class EntryDraft:
    canon: CanonMatch
    category: Category
    stage_id: str | None
    gloss_id: str
    gloss_en: str
    variants: list[str]
    occurrences: list[AbsOccurrence]
    best_index: int

    @property
    def best(self) -> AbsOccurrence:
        return self.occurrences[self.best_index]


def _first(values: Sequence[str]) -> str:
    return next((v for v in values if v), "")


def group_entries(
    occs: Sequence[AbsOccurrence],
    pack: CraftPack,
    steps: Sequence[StepDraft] | None = None,
) -> list[EntryDraft]:
    matcher = StageMatcher(pack)
    groups: dict[str, list[AbsOccurrence]] = {}
    for o in occs:
        o.stage_id = (
            o.canon.pack_stage_id
            or matcher.resolve(o.muse.stage)
            or (stage_at(steps, o.t_start) if steps else None)
        )
        groups.setdefault(o.canon.canon_key, []).append(o)
    drafts: list[EntryDraft] = []
    for items in groups.values():
        items.sort(key=lambda o: o.t_start)
        best_i = max(range(len(items)), key=lambda i: _rank(items[i]))
        best, c = items[best_i], items[best_i].canon
        pack_term = pack.term(c.pack_term_id) if c.pack_term_id else None
        if c.pack_stage_id:
            category = Category.stage
        elif pack_term is not None:
            category = pack_term.category
        else:
            category = Counter(o.muse.category for o in items).most_common(1)[0][0]
        stages = Counter(o.stage_id for o in items if o.stage_id)
        stage_id = c.pack_stage_id or (
            stages.most_common(1)[0][0]
            if stages
            else (pack_term.stage if pack_term else None)
        )
        ordered = [best, *[o for o in items if o is not best]]
        gloss_id = _first([o.muse.gloss_id for o in ordered]) or (
            pack_term.gloss_id if pack_term else ""
        )
        gloss_en = _first([o.muse.gloss_en for o in ordered]) or (
            pack_term.gloss_en if pack_term else ""
        )
        canon_norm = normalize(c.term)
        variants = sorted(
            {
                f.strip()
                for o in items
                for f in (o.muse.spoken, o.muse.term)
                if f.strip() and normalize(f) != canon_norm
            },
            key=str.casefold,
        )
        drafts.append(
            EntryDraft(c, category, stage_id, gloss_id, gloss_en, variants, items, best_i)
        )
    return sorted(drafts, key=lambda d: d.best.t_start)


def merge_analyses(
    analyses: Sequence[Any],
    pack: CraftPack,
    *,
    steps: Sequence[StepDraft] | None = None,
    tol_s: float = 4.0,
    retime: Callable[[list[AbsOccurrence]], list[AbsOccurrence]] | None = None,
) -> list[EntryDraft]:
    occs = collect_occurrences(analyses, Canonicalizer(pack))
    if retime is not None:
        occs = retime(occs)
    return group_entries(dedup_overlap(occs, tol_s), pack, steps)
