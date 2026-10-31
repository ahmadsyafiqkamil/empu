"""Warm the Ask cache before a demo, through the production answer path.

Nothing here writes a cache payload by hand: every entry is produced by
`answer_question`, so a warmed answer is the same answer a visitor would get.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlmodel import Session

from empu.ask.engine import AskError, answer_question
from empu.cache import ResponseCache
from empu.meta_client import AnalyzeResult, MetaAPIError


@dataclass(frozen=True)
class WarmResult:
    question: str
    refused: bool
    cached: bool
    n_evidence: int
    error: str | None


def read_questions(path: Path) -> list[str]:
    """One question per line; blank lines and `#` comments are dropped, order kept."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def warm_questions(
    session: Session,
    *,
    archive_id: int,
    questions: list[str],
    ask_model: Callable[[str], AnalyzeResult],
    cache: ResponseCache,
    model: str,
    pack_name: str,
    scope: str = "public",
) -> list[WarmResult]:
    """Answer each question in turn; one failure never stops the rest."""
    out: list[WarmResult] = []
    for question in questions:
        try:
            result = answer_question(
                session,
                archive_id=archive_id,
                question=question,
                scope=scope,
                ask_model=ask_model,
                cache=cache,
                model=model,
                pack_name=pack_name,
            )
        except (AskError, MetaAPIError, httpx.HTTPError) as exc:
            out.append(
                WarmResult(
                    question=question,
                    refused=False,
                    cached=False,
                    n_evidence=0,
                    error=str(exc),
                )
            )
            continue
        out.append(
            WarmResult(
                question=question,
                refused=result.refused,
                cached=result.cached,
                n_evidence=len(result.evidence),
                error=None,
            )
        )
    return out
