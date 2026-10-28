# api/tests/test_cli.py
import json

from conftest import load_fixture
from fakes import FakeClient, make_raw
from typer.testing import CliRunner

import empu.cli as cli
from empu.legacy import upgrade_v1

GOOD = upgrade_v1(load_fixture("muse/v1/nglowong.json"))


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


def test_analyze_unknown_pack_fails_cleanly(sample_video, tmp_path, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    r = CliRunner().invoke(
        cli.app, ["analyze", str(sample_video), "--pack", "nope", "--out", str(tmp_path)]
    )
    assert r.exit_code != 0 and "not found" in r.output
