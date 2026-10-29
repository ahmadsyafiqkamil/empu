from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from empu.api_schemas import JobOut
from empu.auth import AuthContext, optional_studio
from empu.db import get_session
from empu.models import Archive, Job, Recording
from empu.serialize import job_out

router = APIRouter()


@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(optional_studio),
) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if not auth.has_key:
        rec = session.get(Recording, job.recording_id)
        arch = session.get(Archive, rec.archive_id) if rec else None
        if not (arch and arch.is_sandbox):
            raise HTTPException(401, "studio key required")
    return job_out(job)
