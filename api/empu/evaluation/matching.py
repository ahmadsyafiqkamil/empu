from dataclasses import dataclass

from empu.enums import Source
from empu.evaluation.gold import GoldRow
from empu.packs import CraftPack
from empu.pipeline.merge import Canonicalizer


@dataclass(frozen=True)
class Pred:
    term: str
    t_start: float
    t_end: float
    source: Source
    spoken: str
    pack_term_id: str | None


@dataclass
class Match:
    gold: GoldRow
    pred: Pred | None
    delta: float | None


def _mid(a: float, b: float) -> float:
    return (a + b) / 2


def match_mentions(
    gold: list[GoldRow], pred: list[Pred], pack: CraftPack, *, tol_s: float = 5.0
) -> list[Match]:
    canon = Canonicalizer(pack)
    gkeys = [canon.match(g.term, g.spoken).canon_key for g in gold]
    pkeys = [canon.match(p.term, p.spoken).canon_key for p in pred]
    pairs: list[tuple[float, int, int]] = []
    for i, g in enumerate(gold):
        gm = _mid(g.t_start, g.t_end)
        for j, p in enumerate(pred):
            if gkeys[i] != pkeys[j]:
                continue
            d = abs(gm - _mid(p.t_start, p.t_end))
            if d <= tol_s:
                pairs.append((d, i, j))
    pairs.sort()
    used_g: set[int] = set()
    used_p: set[int] = set()
    found: dict[int, tuple[Pred, float]] = {}
    for d, i, j in pairs:
        if i in used_g or j in used_p:
            continue
        used_g.add(i)
        used_p.add(j)
        found[i] = (pred[j], d)
    return [
        Match(g, found[i][0], found[i][1]) if i in found else Match(g, None, None)
        for i, g in enumerate(gold)
    ]
