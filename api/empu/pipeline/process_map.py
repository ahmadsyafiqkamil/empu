"""Process map: Muse process_steps from all chunks, resolved to pack stages, on one timeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz, process

from empu.packs import CraftPack
from empu.text import normalize

MERGE_GAP_S = 5.0


class StageMatcher:
    def __init__(self, pack: CraftPack, threshold: float = 90.0) -> None:
        self.index = {k: ref.id for k, ref in pack.variant_index().items() if ref.kind == "stage"}
        self._keys = list(self.index)
        self.threshold = threshold

    def resolve(self, name: str | None) -> str | None:
        key = normalize(name)
        if not key:
            return None
        if key in self.index:
            return self.index[key]
        hit = process.extractOne(key, self._keys, scorer=fuzz.ratio, score_cutoff=self.threshold)
        if hit is not None:
            return self.index[hit[0]]
        words = key.split()
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i : i + n])
                if gram in self.index:
                    return self.index[gram]
        return None


@dataclass
class StepDraft:
    pack_stage_id: str | None
    name_raw: str
    t_start: float
    t_end: float
    tools: list[str] = field(default_factory=list)
    order: int = 0


def _same_stage(a: StepDraft, b: StepDraft) -> bool:
    if b.pack_stage_id is not None:
        return a.pack_stage_id == b.pack_stage_id
    return a.pack_stage_id is None and normalize(a.name_raw) == normalize(b.name_raw)


def build_process_map(analyses: Sequence[Any], pack: CraftPack) -> list[StepDraft]:
    matcher = StageMatcher(pack)
    raw: list[StepDraft] = []
    for a in analyses:
        if a.output is None:
            continue
        spec = a.spec
        for st in a.output.process_steps:
            ts = min(spec.start_s + st.t_start, spec.end_s)
            te = min(max(spec.start_s + st.t_end, ts), spec.end_s)
            raw.append(StepDraft(matcher.resolve(st.step), st.step.strip(), ts, te, list(st.tools)))
    raw.sort(key=lambda d: (d.t_start, d.t_end))
    merged: list[StepDraft] = []
    for d in raw:
        prev = merged[-1] if merged else None
        if prev is not None and _same_stage(prev, d) and d.t_start <= prev.t_end + MERGE_GAP_S:
            prev.t_end = max(prev.t_end, d.t_end)
            prev.tools += [t for t in d.tools if t not in prev.tools]
        else:
            merged.append(d)
    for i, d in enumerate(merged):
        d.order = i
    return merged


def stage_at(steps: Sequence[StepDraft], t: float) -> str | None:
    hits = [s for s in steps if s.pack_stage_id and s.t_start <= t <= s.t_end]
    return max(hits, key=lambda s: s.t_start).pack_stage_id if hits else None
