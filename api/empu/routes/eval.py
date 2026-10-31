"""Public eval summary: expose the latest honest numbers to the Evidence page."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _latest_path(package_file: str | Path) -> Path:
    """`api/eval/results/latest.json`, whether the API sits in the repo or in the image at /app."""
    return Path(package_file).resolve().parents[2] / "eval" / "results" / "latest.json"


LATEST = _latest_path(__file__)


@router.get("/api/eval/summary")
def eval_summary() -> dict:
    if not LATEST.is_file():
        raise HTTPException(404, "no eval results")
    return json.loads(LATEST.read_text())
