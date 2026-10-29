"""Public eval summary: expose the latest honest numbers to the Evidence page."""

import json

from fastapi import APIRouter, HTTPException

from empu.config import REPO_ROOT

router = APIRouter()
LATEST = REPO_ROOT / "api" / "eval" / "results" / "latest.json"


@router.get("/api/eval/summary")
def eval_summary() -> dict:
    if not LATEST.is_file():
        raise HTTPException(404, "no eval results")
    return json.loads(LATEST.read_text())
