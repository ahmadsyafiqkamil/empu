import json

import yaml
from factories import make_archive, make_recording
from sqlmodel import Session
from typer.testing import CliRunner

import empu.cli as cli
from empu.db import init_db, make_engine
from empu.enums import Category, Source
from empu.models import Entry, Occurrence


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
    engine.dispose()


def _write_gold(path, annotator="syafiq", clip_id="ccby-macam-canting"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "clip_id,t_start,t_end,spoken,term,category,source,stage,visible_object,note,annotator\n"
        f"{clip_id},85,87,canting,canting,tool,speech,,,ok,{annotator}\n"
    )


def _write_set(path, clips):
    path.write_text(yaml.safe_dump({"clips": [], "demo_cc_by": clips}))


def _clip(cid, youtube_id):
    return {"id": cid, "youtube_id": youtube_id}


def test_eval_run_refuses_draft_gold(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    gold_dir = tmp_path / "gold"
    _write_gold(gold_dir / "ccby-macam-canting.csv", annotator="DRAFT")
    set_path = tmp_path / "set.yaml"
    _write_set(set_path, [_clip("ccby-macam-canting", "FodqwNTWOrQ")])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "latest.json"

    r = CliRunner().invoke(
        cli.app, ["eval", "run", "--set", str(set_path), "--gold", str(gold_dir), "--out", str(out)]
    )

    assert r.exit_code == 2
    assert "DRAFT" in r.output
    assert not out.exists()


def test_eval_run_accepts_checked_gold(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    gold_dir = tmp_path / "gold"
    _write_gold(gold_dir / "ccby-macam-canting.csv")
    set_path = tmp_path / "set.yaml"
    _write_set(set_path, [_clip("ccby-macam-canting", "FodqwNTWOrQ")])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "latest.json"

    r = CliRunner().invoke(
        cli.app, ["eval", "run", "--set", str(set_path), "--gold", str(gold_dir), "--out", str(out)]
    )

    assert r.exit_code == 0, r.output
    assert out.exists()


def test_eval_run_only_limits_clips(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    gold_dir = tmp_path / "gold"
    _write_gold(gold_dir / "ccby-macam-canting.csv")
    set_path = tmp_path / "set.yaml"
    _write_set(
        set_path,
        [_clip("ccby-macam-canting", "FodqwNTWOrQ"), _clip("ccby-nyanting", "zyscgcTHtq8")],
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "latest.json"

    r = CliRunner().invoke(
        cli.app,
        [
            "eval",
            "run",
            "--set",
            str(set_path),
            "--gold",
            str(gold_dir),
            "--out",
            str(out),
            "--only",
            "ccby-macam-canting",
        ],
    )

    assert r.exit_code == 0, r.output
    payload = json.loads(out.read_text())
    assert list(payload["clips"]) == ["ccby-macam-canting"]


def test_eval_run_rejects_unknown_only(settings, tmp_path, monkeypatch):
    _seed_recording(settings, "https://www.youtube.com/watch?v=FodqwNTWOrQ")
    gold_dir = tmp_path / "gold"
    _write_gold(gold_dir / "ccby-macam-canting.csv")
    set_path = tmp_path / "set.yaml"
    _write_set(set_path, [_clip("ccby-macam-canting", "FodqwNTWOrQ")])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "latest.json"

    r = CliRunner().invoke(
        cli.app,
        [
            "eval",
            "run",
            "--set",
            str(set_path),
            "--gold",
            str(gold_dir),
            "--out",
            str(out),
            "--only",
            "tidak-ada",
        ],
    )

    assert r.exit_code == 2
    assert "unknown clip ids" in r.output
    assert not out.exists()
