from factories import make_archive, make_recording

from empu.enums import JobStatus
from empu.models import Job
from empu.worker import claim_next_job, reset_stale_jobs, run_once


def jobs(session, *statuses):
    a = make_archive(session)
    r = make_recording(session, a)
    out = [Job(recording_id=r.id, status=s) for s in statuses]
    session.add_all(out)
    session.commit()
    return [j.id for j in out]


def test_claim_oldest_queued_once(engine, session):
    first, second = jobs(session, JobStatus.queued, JobStatus.queued)
    assert claim_next_job(engine) == first
    assert claim_next_job(engine) == second
    assert claim_next_job(engine) is None
    session.expire_all()
    assert session.get(Job, first).status is JobStatus.normalizing
    assert session.get(Job, first).started_at is not None


def test_reset_stale(engine, session):
    stuck, done = jobs(session, JobStatus.analyzing, JobStatus.ready)
    assert reset_stale_jobs(engine) == 1
    session.expire_all()
    assert session.get(Job, stuck).status is JobStatus.queued
    assert session.get(Job, done).status is JobStatus.ready


def test_run_once_calls_process(engine, session, settings):
    (job_id,) = jobs(session, JobStatus.queued)
    seen = []
    assert run_once(
        engine,
        settings,
        client_factory=lambda s: "client",
        process=lambda s, jid, client, settings: seen.append((jid, client)),
    )
    assert seen == [(job_id, "client")]
    assert (
        run_once(
            engine,
            settings,
            client_factory=lambda s: "client",
            process=lambda *a, **k: None,
        )
        is False
    )


def test_run_once_marks_failed_when_client_cannot_be_built(engine, session, settings):
    (job_id,) = jobs(session, JobStatus.queued)

    def no_key(s):
        raise RuntimeError("META_MODEL_API_KEY is not set")

    assert run_once(engine, settings, client_factory=no_key)
    session.expire_all()
    job = session.get(Job, job_id)
    assert job.status is JobStatus.failed and "META_MODEL_API_KEY" in job.error
