"""Baseline ASR: subtitle YouTube (VTT) dipetakan ke varian pack.

Dipakai sebagai pembanding jujur di halaman Bukti: seberapa banyak istilah yang bisa
ditangkap kalau hanya mengandalkan subtitle otomatis YouTube + pencocokan varian pack,
tanpa pipeline Muse.
"""

import re
from pathlib import Path

from empu.enums import Source
from empu.evaluation.matching import Pred
from empu.packs import CraftPack
from empu.pipeline.merge import Canonicalizer

TS = re.compile(r"(\d+):(\d+):(\d+[.,]\d+)\s-->\s(\d+):(\d+):(\d+[.,]\d+)")


def _sec(h: str, m: str, s: str) -> float:
    return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))


def parse_vtt(path: Path) -> list[Pred]:
    text = Path(path).read_text(encoding="utf-8")
    cues: list[Pred] = []
    for block in re.split(r"\n\s*\n", text):
        match = TS.search(block)
        if not match:
            continue
        t0 = _sec(*match.group(1, 2, 3))
        t1 = _sec(*match.group(4, 5, 6))
        lines = [
            ln.strip()
            for ln in block.splitlines()
            if ln.strip()
            and "-->" not in ln
            and ln.strip() != "WEBVTT"
            and not ln.strip().isdigit()
        ]
        spoken = " ".join(lines)
        if not spoken or spoken.startswith("NOTE"):
            continue
        cues.append(
            Pred(
                term=spoken,
                t_start=t0,
                t_end=t1,
                source=Source.speech,
                spoken=spoken,
                pack_term_id=None,
            )
        )
    return cues


def baseline_against_pack(cues: list[Pred], pack: CraftPack) -> list[Pred]:
    canon = Canonicalizer(pack)
    out: list[Pred] = []
    for cue in cues:
        hit = canon.match(cue.term, cue.spoken)
        if hit.method == "novel":
            continue
        out.append(
            Pred(
                term=hit.term,
                t_start=cue.t_start,
                t_end=cue.t_end,
                source=Source.speech,
                spoken=cue.spoken,
                pack_term_id=hit.pack_term_id,
            )
        )
    return out
