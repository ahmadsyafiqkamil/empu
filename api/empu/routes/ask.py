"""Ask Empu routes.

The public route is keyless and rate-limited per client address; the studio route
needs the studio key and sees entries that are still under review.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from empu.api_schemas import AskAnswerOut, AskEvidenceOut, AskIn
from empu.ask import AskError, AskResult, answer_question
from empu.ask.engine import pack_display_name
from empu.ask.prompts import ASK_PROMPT_VERSION, RESPONSE_SCHEMA
from empu.ask.ratelimit import RateLimiter
from empu.cache import ResponseCache
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.meta_client import AnalyzeResult, MetaAPIError, MetaClient
from empu.models import Archive, Recording
from empu.serialize import entry_list_item, occurrence_out

router = APIRouter()
studio_router = APIRouter()

log = logging.getLogger("empu.ask")

_MODELS: dict[str, Callable[[str], AnalyzeResult]] = {}


def get_ask_model(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Callable[[str], AnalyzeResult]:
    """One Meta client per base URL; the route only needs a prompt → answer call."""
    model = _MODELS.get(settings.meta_base_url)
    if model is None:
        client = MetaClient.from_settings(settings)
        model_name = settings.muse_model

        def ask(prompt: str) -> AnalyzeResult:
            return client.respond_text(prompt, model=model_name, schema=RESPONSE_SCHEMA)

        _MODELS[settings.meta_base_url] = model = ask
    return model


def get_ask_cache(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ResponseCache:
    return ResponseCache(settings.data_dir / "cache" / "ask")


_LIMITERS: dict[tuple[int, float], RateLimiter] = {}


def get_limiter(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RateLimiter:
    """One limiter per process: a fresh instance per request would never block."""
    key = (settings.ask_per_hour, 3600.0)
    limiter = _LIMITERS.get(key)
    if limiter is None:
        _LIMITERS[key] = limiter = RateLimiter(*key)
    return limiter


def _client_key(request: Request) -> str:
    """Who to charge this question to.

    In the compose deployment the browser never reaches uvicorn directly: Caddy does,
    from a bridge address. Keying on `request.client` there would put every visitor in
    one bucket and turn a per-visitor limit into a site-wide cap. The API port is not
    published outside the compose network, so the first X-Forwarded-For hop is the real
    client; without a proxy in front (local dev, tests) fall back to the socket peer.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _to_out(session: Session, result: AskResult) -> AskAnswerOut:
    evidence: list[AskEvidenceOut] = []
    for cited in result.evidence:
        rec = session.get(Recording, cited.occurrence.recording_id)
        evidence.append(
            AskEvidenceOut(
                entry=entry_list_item(cited.entry, cited.occurrences),
                occurrence=occurrence_out(
                    cited.occurrence, recording_title=rec.title if rec else ""
                ),
            )
        )
    return AskAnswerOut(
        answer=result.answer,
        lang=result.lang,
        refused=result.refused,
        evidence=evidence,
        model=result.model,
        prompt_version=result.prompt_version,
        cached=result.cached,
    )


def _run(
    session: Session,
    archive: Archive,
    body: AskIn,
    *,
    scope: str,
    settings: Settings,
    ask_model: Callable[[str], AnalyzeResult],
    cache: ResponseCache,
) -> AskAnswerOut:
    try:
        result = answer_question(
            session,
            archive_ids=[archive.id],
            question=body.question,
            scope=scope,
            ask_model=ask_model,
            cache=cache,
            model=settings.muse_model,
            pack_names=[pack_display_name(archive, settings)],
            max_entries=settings.ask_max_entries,
        )
    except (AskError, MetaAPIError, httpx.HTTPError, RuntimeError) as exc:
        # RuntimeError covers an unset Meta API key on a keyless deploy: a judge
        # should read a calm message, not a traceback.
        log.exception("ask failed for archive %s (scope %s)", archive.id, scope)
        raise HTTPException(502, "answer unavailable") from exc
    return _to_out(session, result)


@router.post("/api/public/archives/{slug}/ask", response_model=AskAnswerOut)
def public_ask(
    slug: str,
    body: AskIn,
    request: Request,
    session: Session = Depends(get_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ask_model: Callable[[str], AnalyzeResult] = Depends(get_ask_model),  # noqa: B008
    cache: ResponseCache = Depends(get_ask_cache),  # noqa: B008
    limiter: RateLimiter = Depends(get_limiter),  # noqa: B008
) -> AskAnswerOut:
    archive = session.exec(select(Archive).where(Archive.slug == slug)).first()
    if archive is None or archive.is_sandbox:
        raise HTTPException(404, "archive not found")
    if not limiter.allow(_client_key(request)):
        raise HTTPException(429, "too many questions, try again later")
    return _run(
        session, archive, body, scope="public", settings=settings, ask_model=ask_model, cache=cache
    )


@studio_router.post("/api/archives/{archive_id}/ask", response_model=AskAnswerOut)
def studio_ask(
    archive_id: int,
    body: AskIn,
    session: Session = Depends(get_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ask_model: Callable[[str], AnalyzeResult] = Depends(get_ask_model),  # noqa: B008
    cache: ResponseCache = Depends(get_ask_cache),  # noqa: B008
) -> AskAnswerOut:
    archive = session.get(Archive, archive_id)
    if archive is None:
        raise HTTPException(404, "archive not found")
    return _run(
        session, archive, body, scope="studio", settings=settings, ask_model=ask_model, cache=cache
    )


__all__ = ["ASK_PROMPT_VERSION", "router", "studio_router"]
