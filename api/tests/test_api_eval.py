"""Tests for the public eval summary endpoint."""

import json

import empu.routes.eval as eval_route


def test_eval_summary_returns_latest(api, tmp_path, monkeypatch):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"clips": {"x": {"speech_recall": 0.5}}}))
    monkeypatch.setattr(eval_route, "LATEST", latest)
    r = api.get("/api/eval/summary")
    assert r.status_code == 200
    assert r.json()["clips"]["x"]["speech_recall"] == 0.5


def test_eval_summary_missing_404(api, tmp_path, monkeypatch):
    monkeypatch.setattr(eval_route, "LATEST", tmp_path / "nope.json")
    r = api.get("/api/eval/summary")
    assert r.status_code == 404
