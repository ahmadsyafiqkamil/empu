from factories import make_archive, make_recording
from typer.testing import CliRunner

import empu.cli as cli
from empu.enums import SourceKind
from empu.visibility import recording_is_public


def test_recording_edit_changes_title(session, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    rec = make_recording(session, make_archive(session), title="tes")

    r = CliRunner().invoke(cli.app, ["recording", "edit", str(rec.id), "--title", "Latihan"])

    assert r.exit_code == 0, r.output
    session.refresh(rec)
    assert rec.title == "Latihan"


def test_recording_edit_can_hide_a_recording(session, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    rec = make_recording(session, make_archive(session))

    r = CliRunner().invoke(
        cli.app, ["recording", "edit", str(rec.id), "--source-kind", "internal_eval"]
    )

    assert r.exit_code == 0, r.output
    session.refresh(rec)
    assert rec.source_kind is SourceKind.internal_eval
    assert recording_is_public(rec) is False


def test_recording_edit_refuses_cc_by_without_attribution(session, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    rec = make_recording(session, make_archive(session))

    r = CliRunner().invoke(
        cli.app, ["recording", "edit", str(rec.id), "--source-kind", "cc_by_video"]
    )

    assert r.exit_code == 2
    assert "attribution" in r.output


def test_recording_edit_unknown_id(session, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    r = CliRunner().invoke(cli.app, ["recording", "edit", "9999", "--title", "x"])

    assert r.exit_code == 2
    assert "not found" in r.output


def test_recording_edit_requires_a_change(session, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    rec = make_recording(session, make_archive(session))

    r = CliRunner().invoke(cli.app, ["recording", "edit", str(rec.id)])

    assert r.exit_code == 2
    assert "nothing to change" in r.output
