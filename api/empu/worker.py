"""Job worker: `python -m empu.worker`. Polls the job table and runs one job at a time."""

from __future__ import annotations

import logging
import signal
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from empu.config import Settings, get_settings
from empu.db import init_db, make_engine
from empu.enums import JobStatus
from empu.meta_client import MetaClient
from empu.models import Job, Recording, utcnow
from empu.pipeline.run import JOB_STAGES, process_recording

log = logging.getLogger("empu.worker")


def claim_next_job(engine: Engine) -> int | None:
    with Session(engine) as s:
        job_id = s.exec(
            select(Job.id).where(Job.status == JobStatus.queued).order_by(Job.id)
        ).first()
        if job_id is None:
            return None
        res = s.execute(
            update(Job)
            .where(col(Job.id) == job_id, col(Job.status) == JobStatus.queued)
            .values(status=JobStatus.normalizing, started_at=utcnow(), detail="claimed")
        )
        s.commit()
        return job_id if res.rowcount == 1 else None


def reset_stale_jobs(engine: Engine) -> int:
    with Session(engine) as s:
        res = s.execute(
            update(Job)
            .where(col(Job.status).in_(JOB_STAGES))
            .values(status=JobStatus.queued, detail="requeued after worker restart")
        )
        s.commit()
        return res.rowcount


def _fail(engine: Engine, job_id: int, message: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        job.status, job.error, job.finished_at = JobStatus.failed, message[:2000], utcnow()
        rec = s.get(Recording, job.recording_id)
        rec.status = JobStatus.failed
        s.add_all([job, rec])
        s.commit()


def run_once(
    engine: Engine,
    settings: Settings,
    *,
    client_factory: Callable[[Settings], Any] = MetaClient.from_settings,
    process: Callable[..., None] = process_recording,
) -> bool:
    job_id = claim_next_job(engine)
    if job_id is None:
        return False
    log.info("job %s claimed", job_id)
    try:
        client = client_factory(settings)
    except Exception as e:  # noqa: BLE001
        _fail(engine, job_id, f"setup: {type(e).__name__}: {e}")
        log.error("job %s failed before start", job_id)
        return True
    try:
        with Session(engine) as s:
            process(s, job_id, client=client, settings=settings)
    finally:
        if hasattr(client, "close"):
            client.close()
    log.info("job %s finished", job_id)
    return True


def main(poll_s: float = 1.0) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    settings = get_settings()
    engine = make_engine(settings.db_url)
    init_db(engine)
    log.info("worker started (requeued %d stale jobs)", reset_stale_jobs(engine))
    stop = False

    def _stop(*_: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while not stop:
        if not run_once(engine, settings):
            time.sleep(poll_s)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
