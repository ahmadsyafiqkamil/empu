from empu.enums import Category, Source
from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Pred, match_mentions
from empu.evaluation.metrics import compute_metrics


def G(term, t, source=Source.speech):
    return GoldRow("c", t, t + 1, term, term, Category.tool, source, "", "", "", "s")


def P(term, t, source=Source.speech):
    return Pred(term=term, t_start=t, t_end=t + 1, source=source, spoken=term, pack_term_id=None)


def test_match_within_tol(pack):
    gold = [G("canting", 10), G("malam", 20)]
    pred = [P("tjanting", 12), P("malam", 40)]
    matches = match_mentions(gold, pred, pack, tol_s=5)
    by_term = {m.gold.term: m for m in matches}
    assert by_term["canting"].pred is not None and abs(by_term["canting"].delta) == 2
    assert by_term["malam"].pred is None


def test_metrics_speech(pack):
    gold = [G("canting", 10), G("malam", 20), G("nyamplung", 30, source=Source.on_screen_text)]
    pred = [P("canting", 11), P("hcl", 50)]
    m = compute_metrics(match_mentions(gold, pred, pack), pred, gold)
    assert m["n_gold_speech"] == 2
    assert m["speech_recall"] == 0.5
    assert m["speech_precision"] == 0.5
