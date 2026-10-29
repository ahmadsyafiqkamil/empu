"""Eval runner: turn DB predictions into Preds and score them against gold."""

import json
from pathlib import Path

from sqlmodel import Session, select

from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Pred, match_mentions
from empu.evaluation.metrics import compute_metrics
from empu.models import Entry, Occurrence
from empu.packs import CraftPack


def pred_from_db(session: Session, recording_id: int) -> list[Pred]:
    occs = session.exec(select(Occurrence).where(Occurrence.recording_id == recording_id)).all()
    out = []
    for o in occs:
        e = session.get(Entry, o.entry_id)
        if e is None:
            continue
        out.append(
            Pred(
                term=e.term,
                t_start=o.t_start,
                t_end=o.t_end,
                source=o.source,
                spoken=o.spoken,
                pack_term_id=e.pack_term_id,
            )
        )
    return out


def run_clip(
    gold: list[GoldRow], pred: list[Pred], pack: CraftPack, *, baseline: list[Pred] | None = None
) -> dict:
    matches = match_mentions(gold, pred, pack)
    metrics = compute_metrics(matches, pred, gold)
    if baseline is not None:
        b = compute_metrics(match_mentions(gold, baseline, pack), baseline, gold)
        metrics["baseline_speech_recall"] = b["speech_recall"]
    return metrics


def write_results(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
