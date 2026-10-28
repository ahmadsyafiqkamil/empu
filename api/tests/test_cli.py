# api/tests/test_cli.py
import json

from conftest import load_fixture
from fakes import FakeClient, make_raw
from sqlmodel import Session, select
from typer.testing import CliRunner

import empu.cli as cli
from empu.db import make_engine
from empu.legacy import upgrade_v1
from empu.models import Entry, Recording

GOOD = upgrade_v1(load_fixture("muse/v1/nglowong.json"))

ONE_TERM = {
    "speech_heard": True,
    "terms": [
        {
            "spoken": "canting",
            "term": "canting",
            "category": "tool",
            "source": "speech",
            "t_start": 2,
            "t_end": 3,
            "stage": None,
            "evidence_quote": "ini canting",
            "visible": "",
            "visible_object_en": None,
            "visual_match": "yes",
            "gloss_id": "",
            "gloss_en": "",
            "confidence": "high",
        }
    ],
    "process_steps": [],
}


def test_analyze_end_to_end_with_fake(sample_video, tmp_path, settings, monkeypatch):
    fake = FakeClient([make_raw(GOOD)])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_client", lambda s: fake)
    out = tmp_path / "run"
    r = CliRunner().invoke(
        cli.app, ["analyze", str(sample_video), "--pack", "batik_tulis", "--out", str(out)]
    )
    assert r.exit_code == 0, r.output
    summary = json.loads((out / "summary.json").read_text())
    assert summary["prompt_version"] == "analyze-v3"
    assert summary["chunks"][0]["n_terms"] == 12
    assert summary["chunks"][0]["by_source"]["speech"] == 12
    assert (out / "muse/0.json").exists() and (out / "media/display.mp4").exists()
    assert len(fake.uploads) == 1


def test_ingest_run_end_to_end(sample_video, settings, monkeypatch):
    fake = FakeClient([make_raw(ONE_TERM)])
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_client", lambda s: fake)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["db", "init"]).exit_code == 0
    r = runner.invoke(
        cli.app,
        [
            "ingest",
            str(sample_video),
            "--archive",
            "uji",
            "--title",
            "Uji",
            "--contributor",
            "Bu Ahli",
            "--consent-confirmed",
            "--mode",
            "A",
            "--run",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "ready" in r.output
    with Session(make_engine(settings.db_url)) as s:
        assert s.exec(select(Recording)).one().status == "ready"
        assert s.exec(select(Entry)).one().canon_key == "term:canting"
    assert "entries=1" in runner.invoke(cli.app, ["status", "--archive", "uji"]).output


def test_ingest_without_consent_fails(sample_video, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    r = CliRunner().invoke(
        cli.app,
        [
            "ingest",
            str(sample_video),
            "--archive",
            "uji",
            "--title",
            "Uji",
            "--contributor",
            "Bu Ahli",
        ],
    )
    assert r.exit_code != 0 and "consent" in r.output


def test_analyze_unknown_pack_fails_cleanly(sample_video, tmp_path, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    r = CliRunner().invoke(
        cli.app, ["analyze", str(sample_video), "--pack", "nope", "--out", str(tmp_path)]
    )
    assert r.exit_code != 0 and "not found" in r.output
