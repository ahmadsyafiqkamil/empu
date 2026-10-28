import json

import pytest
from conftest import REPO_ROOT

from empu.enums import AccessLevel, ContributorRole, JobStatus, PipelineMode, SourceKind
from empu.intake import (
    IntakeError,
    RecordingMeta,
    create_recording,
    get_or_create_archive,
    meta_from_license_file,
    validate_meta,
)
from empu.media import abs_from_rel


def meta(**kw):
    base = {"title": "Uji", "contributor_name": "Bu Ahli", "consent_confirmed": True}
    return RecordingMeta(**(base | kw))


def test_consent_required():
    with pytest.raises(IntakeError, match="consent"):
        validate_meta(meta(consent_confirmed=False))


def test_cc_by_requires_attribution_fields():
    with pytest.raises(IntakeError, match="source_url"):
        validate_meta(
            meta(
                source_kind=SourceKind.cc_by_video,
                source_creator="c",
                license="CC BY 3.0",
                attribution="a",
            )
        )


def test_internal_eval_must_be_private():
    with pytest.raises(IntakeError, match="private"):
        validate_meta(meta(source_kind=SourceKind.internal_eval, consent_scope=AccessLevel.public))
    validate_meta(meta(source_kind=SourceKind.internal_eval, consent_scope=AccessLevel.private))


def test_create_recording_copies_file_and_queues_job(session, settings, tmp_path):
    src = tmp_path / "video.MOV"
    src.write_bytes(b"fake")
    a = get_or_create_archive(session, "demo", title="Demo", pack_id="batik_tulis")
    rec, job = create_recording(session, settings, a, src, meta(), mode=PipelineMode.B)
    assert rec.original_path == f"archives/{a.id}/recordings/{rec.id}/original.mov"
    assert abs_from_rel(settings.data_dir, rec.original_path).read_bytes() == b"fake"
    assert job.status is JobStatus.queued and job.mode is PipelineMode.B
    assert job.prompt_version == "analyze-v3" and rec.contributor_id is not None
    assert get_or_create_archive(session, "demo", title="x", pack_id="batik_tulis").id == a.id


def test_meta_from_license_file():
    m = meta_from_license_file(REPO_ROOT / "docs/eval/lisensi/FodqwNTWOrQ.json")
    assert m.source_kind is SourceKind.cc_by_video and m.license == "CC BY 3.0"
    assert m.source_creator == "Batik Education" and m.source_url.endswith("FodqwNTWOrQ")
    assert m.contributor_role is ContributorRole.documenter
    assert "Trimmed and analyzed by Empu" in m.attribution and m.consent_confirmed
    assert m.consent_evidence == "CC BY 3.0, verified via YouTube metadata on 2026-10-28"
    validate_meta(m)


def test_license_file_without_cc_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps({"id": "x", "title": "t", "channel": "c", "license": None, "webpage_url": "u"})
    )
    with pytest.raises(IntakeError, match="Creative Commons"):
        meta_from_license_file(p)
