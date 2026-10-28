from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from empu.api_schemas import JobOut
from empu.db import get_session
from empu.models import Job
from empu.serialize import job_out

router = APIRouter()


@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job_out(job)
