"""Tests for the eval runner (pred_from_db, run_clip, write_results) and the `empu eval` CLI."""

import csv
import json

import yaml
from factories import make_archive, make_recording
from sqlmodel import Session
from typer.testing import CliRunner

import empu.cli as cli
from empu.db import init_db, make_engine
from empu.enums import Category, Source
from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Pred
from empu.evaluation.runner import pred_from_db, run_clip, write_results
from empu.models import Entry, Occurrence


def G(term, t, source=Source.speech):
    return GoldRow("c", t, t + 1, term, term, Category.tool, source, "", "", "", "s")


def P(term, t, source=Source.speech):
    return Pred(term=term, t_start=t, t_end=t + 1, source=source, spoken=term, pack_term_id=None)


def test_pred_from_db(session):
    a = make_archive(session)
    rec = make_recording(session, a)
    e = Entry(
        archive_id=a.id,
        canon_key="term:canting",
        term="canting",
        category=Category.tool,
        pack_term_id="canting",
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    session.add(
        Occurrence(
            entry_id=e.id,
            recording_id=rec.id,
            source=Source.speech,
            t_start=10,
            t_end=12,
            spoken="canting",
        )
    )
    session.commit()

    preds = pred_from_db(session, rec.id)
    assert len(preds) == 1
    assert preds[0].term == "canting"
    assert preds[0].pack_term_id == "canting"
    assert preds[0].source is Source.speech
    assert preds[0].spoken == "canting"


def test_run_clip_baseline(pack):
    m = run_clip([G("canting", 86)], [P("canting", 86)], pack, baseline=[P("canting", 86)])
    assert m["speech_recall"] == 1.0
    assert m["baseline_speech_recall"] == 1.0


def test_run_clip_no_baseline(pack):
    m = run_clip([G("canting", 86)], [P("canting", 86)], pack)
    assert m["speech_recall"] == 1.0
    assert "baseline_speech_recall" not in m


def test_write_results_creates_parent(tmp_path):
    out = tmp_path / "a" / "b" / "r.json"
    write_results(out, {"x": [1, 2]})
    assert json.loads(out.read_text()) == {"x": [1, 2]}


# --- CLI ---


def _seed_recording(settings, source_url):
    engine = make_engine(settings.db_url)
    init_db(engine)
    with Session(engine) as s:
        a = make_archive(s)
        rec = make_recording(s, a, source_url=source_url)
        e = Entry(
            archive_id=a.id,
            canon_key="term:canting",
            term="canting",
            category=Category.tool,
            pack_term_id="canting",
        )
        s.add(e)
        s.commit()
        s.refresh(e)
        s.add(
            Occurrence(
                entry_id=e.id,
                recording_id=rec.id,
                source=Source.speech,
                t_start=84,
                t_end=88,
                spoken="canting",
            )
        )
        s.commit()
        rec_id = rec.id
    engine.dispose()
    return rec_id


def _write_gold_csv(path, clip_id="ccby-macam-canting"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "clip_id,t_start,t_end,spoken,term,category,source,stage,visible_object,note,annotator\n"
        f"{clip_id},85,87,canting,canting,tool,speech,,,ok,syafiq\n"
    )


def test_draft_gold_cli(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    set_path = tmp_path / "set.yaml"
    set_path.write_text(
        yaml.safe_dump(
            {
                "clips": [],
                "demo_cc_by": [
                    {"id": "ccby-macam-canting", "youtube_id": "FodqwNTWOrQ"},
                ],
            }
        )
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "draft.csv"
    r = CliRunner().invoke(
        cli.app,
        ["eval", "draft-gold", "ccby-macam-canting", "--set", str(set_path), "--out", str(out)],
    )
    assert r.exit_code == 0, r.output
    rows = list(csv.DictReader(out.read_text().splitlines()))
    assert len(rows) == 1
    assert rows[0]["term"] == "canting"
    assert rows[0]["clip_id"] == "ccby-macam-canting"
    assert rows[0]["annotator"] == "DRAFT"


def test_eval_run_cli(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    gold_dir = tmp_path / "gold"
    _write_gold_csv(gold_dir / "ccby-macam-canting.csv")
    set_path = tmp_path / "set.yaml"
    set_path.write_text(
        yaml.safe_dump(
            {
                "clips": [],
                "demo_cc_by": [
                    {"id": "ccby-macam-canting", "youtube_id": "FodqwNTWOrQ"},
                ],
            }
        )
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "latest.json"
    r = CliRunner().invoke(
        cli.app, ["eval", "run", "--set", str(set_path), "--gold", str(gold_dir), "--out", str(out)]
    )
    assert r.exit_code == 0, r.output
    data = json.loads(out.read_text())
    assert data["clips"]["ccby-macam-canting"]["speech_recall"] == 1.0
    assert data["pack"].startswith("batik_tulis@")
