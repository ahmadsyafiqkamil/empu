import shutil

import pytest
from conftest import requires_ffmpeg
from factories import make_archive, make_recording
from fakes import FakeClient, make_raw, make_sam_raw, muse_term
from sqlmodel import select

from empu.enums import JobStatus, PipelineMode, SamStatus, TimeSource
from empu.media import abs_from_rel, recording_dir, rel_to_data
from empu.models import Chunk, Entry, Job, Occurrence, ProcessStep, Recording
from empu.pipeline.run import JOB_STAGES, process_recording
from empu.pipeline.transcribe import Word

PAYLOAD = {
    "speech_heard": True,
    "language_notes": "id",
    "transcript_excerpt": "ini canting",
    "terms": [
        muse_term(
            term="canting",
            spoken="canting",
            source="speech",
            t_start=2.0,
            t_end=2.8,
            stage="nglowong",
            evidence_quote="ini namanya canting",
            visual_match="yes",
            confidence="high",
            gloss_id="alat menorehkan lilin",
            gloss_en="wax pen",
        ),
        muse_term(
            term="canting",
            spoken="tjanting",
            source="on_screen_text",
            t_start=8.0,
            t_end=9.0,
        ),
        muse_term(
            term="bethik",
            spoken="bethik",
            source="speech",
            t_start=5.0,
            t_end=5.5,
            visible_object_en="small black bowl",
            visual_match="yes",
            evidence_quote="ini namanya bethik kecil",
        ),
    ],
    "process_steps": [{"step": "nglowong", "t_start": 0, "t_end": 12, "tools": ["canting"]}],
}
SAM = {"wooden stick with copper tip": make_sam_raw([(209, 135, 743, 340)], w=1280, h=720)}


@pytest.fixture
def job_for(session, settings, sample_video):
    def make(mode=PipelineMode.A):
        a = make_archive(session)
        r = make_recording(session, a)
        dst = recording_dir(settings.data_dir, a.id, r.id) / "original.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(sample_video, dst)
        r.original_path = rel_to_data(settings.data_dir, dst)
        job = Job(
            recording_id=r.id,
            mode=mode,
            model=settings.muse_model,
            prompt_version="analyze-v3",
        )
        session.add_all([r, job])
        session.commit()
        return job

    return make


def entries(session):
    return {e.canon_key: e for e in session.exec(select(Entry))}


@requires_ffmpeg
def test_end_to_end_mode_a(session, settings, job_for):
    job = job_for()
    client = FakeClient([make_raw(PAYLOAD)], sam=SAM)
    process_recording(session, job.id, client=client, settings=settings)
    session.refresh(job)
    assert job.status is JobStatus.ready, job.error
    assert job.progress == 1.0 and set(job.timings_json) >= {s.value for s in JOB_STAGES}
    rec = session.get(Recording, job.recording_id)
    assert rec.status is JobStatus.ready and abs(rec.duration_s - 12) < 0.5
    assert session.exec(select(Chunk)).one().status == "done"
    es = entries(session)
    assert set(es) == {"term:canting", "novel:bethik"}
    canting = es["term:canting"]
    crop = abs_from_rel(settings.data_dir, canting.crop_path)
    assert canting.sam_status is SamStatus.ok and crop.exists()
    assert canting.sam_prompt == "wooden stick with copper tip"
    assert es["novel:bethik"].sam_status is SamStatus.empty and es["novel:bethik"].is_novel
    occs = session.exec(select(Occurrence)).all()
    assert len(occs) == 3
    for o in occs:
        for p in (o.clip_path, o.audio_path, o.keyframe_path):
            assert abs_from_rel(settings.data_dir, p).exists()
    assert session.exec(select(ProcessStep)).one().pack_stage_id == "nglowong"
    assert job.usage_json["entries"] == 2 and job.usage_json["sam"]["ok"] == 1


@requires_ffmpeg
def test_reprocess_uses_cache_and_does_not_duplicate(session, settings, job_for):
    job = job_for()
    client = FakeClient([make_raw(PAYLOAD)], sam=SAM)
    process_recording(session, job.id, client=client, settings=settings)
    again = Job(recording_id=job.recording_id, mode=PipelineMode.A, model=settings.muse_model)
    session.add(again)
    session.commit()
    client = FakeClient([])
    process_recording(session, again.id, client=client, settings=settings)
    session.refresh(again)
    assert again.status is JobStatus.ready, again.error
    assert client.uploads == [] and client.sam_calls == []
    assert len(session.exec(select(Occurrence)).all()) == 3 and len(entries(session)) == 2


@requires_ffmpeg
def test_mode_b_realigns_speech(session, settings, job_for):
    job = job_for(PipelineMode.B)
    words = [
        Word(9.8, 10.0, "ini"),
        Word(10.0, 10.3, "namanya"),
        Word(10.4, 10.9, "bethik"),
        Word(11.0, 11.3, "kecil"),
    ]
    process_recording(
        session,
        job.id,
        client=FakeClient([make_raw(PAYLOAD)], sam=SAM),
        settings=settings,
        transcriber=lambda path: words,
    )
    session.refresh(job)
    assert job.status is JobStatus.ready, job.error
    o = session.exec(select(Occurrence).where(Occurrence.term_raw == "bethik")).one()
    assert (o.t_start, o.time_source) == (10.4, TimeSource.asr)
    assert job.usage_json["asr_retimed"] >= 1


@requires_ffmpeg
def test_invalid_muse_output_fails_job_cleanly(session, settings, job_for):
    job = job_for()
    bad = FakeClient([make_raw("x"), make_raw("y")])
    process_recording(session, job.id, client=bad, settings=settings)
    session.refresh(job)
    assert job.status is JobStatus.failed and job.error.startswith("analyzing")
    assert session.get(Recording, job.recording_id).status is JobStatus.failed


@requires_ffmpeg
def test_sam_disabled_skips(session, settings, job_for):
    job = job_for()
    settings.sam_enabled = False
    client = FakeClient([make_raw(PAYLOAD)], sam=SAM)
    process_recording(session, job.id, client=client, settings=settings)
    canting = entries(session)["term:canting"]
    assert client.sam_calls == [] and canting.sam_status is SamStatus.skipped


@requires_ffmpeg
def test_sandbox_over_limit_rejected_before_transcode(session, settings, sample_video, monkeypatch):
    a = make_archive(session, is_sandbox=True)
    r = make_recording(session, a)
    dst = recording_dir(settings.data_dir, a.id, r.id) / "original.mp4"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(sample_video, dst)
    r.original_path = rel_to_data(settings.data_dir, dst)
    job = Job(
        recording_id=r.id,
        mode=PipelineMode.A,
        model=settings.muse_model,
        prompt_version="analyze-v3",
    )
    session.add_all([r, job])
    session.commit()
    settings.sandbox_max_duration_s = 3.0  # sample video is 12s

    calls: list[object] = []

    def fake_normalize(src: object, out_dir: object, **kw: object) -> None:
        calls.append(src)
        raise AssertionError("normalize_recording must not run for over-limit sandbox")

    monkeypatch.setattr("empu.pipeline.run.normalize_recording", fake_normalize)

    process_recording(session, job.id, client=FakeClient([]), settings=settings)
    session.refresh(job)
    assert job.status is JobStatus.failed
    assert "sandbox recordings are limited to 3 minutes" in job.error
    assert calls == []
