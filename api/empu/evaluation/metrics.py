import statistics

from empu.enums import Source
from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Match, Pred


def compute_metrics(matches: list[Match], pred: list[Pred], gold: list[GoldRow]) -> dict:
    gold_speech = [m for m in matches if m.gold.source is Source.speech]
    hit_speech = [m for m in gold_speech if m.pred is not None]
    pred_speech = [p for p in pred if p.source is Source.speech]
    used = {id(m.pred) for m in matches if m.pred is not None}
    pred_speech_hit = sum(1 for p in pred_speech if id(p) in used)
    deltas = [m.delta for m in matches if m.delta is not None]
    n_matched = sum(1 for m in matches if m.pred is not None)
    source_ok = sum(1 for m in matches if m.pred is not None and m.pred.source is m.gold.source)
    return {
        "n_gold_speech": len(gold_speech),
        "n_pred_speech": len(pred_speech),
        "n_matched_speech": len(hit_speech),
        "speech_recall": (len(hit_speech) / len(gold_speech)) if gold_speech else None,
        "speech_precision": (pred_speech_hit / len(pred_speech)) if pred_speech else None,
        "median_time_error_s": statistics.median(deltas) if deltas else None,
        "source_accuracy": (source_ok / n_matched) if n_matched else None,
        "n_gold": len(gold),
        "n_pred": len(pred),
        "n_matched": n_matched,
    }
