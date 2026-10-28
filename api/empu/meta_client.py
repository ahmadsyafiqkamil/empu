"""The only gateway to the Meta Model API.

Never log request headers or the API key. Callers own caching (empu.cache).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential, wait_none

T = TypeVar("T")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


class MetaAPIError(RuntimeError):
    def __init__(self, status_code: int | None, message: str) -> None:
        super().__init__(f"Meta API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message

    @property
    def retryable(self) -> bool:
        return self.status_code == 429 or (self.status_code is not None and self.status_code >= 500)


@dataclass
class AnalyzeResult:
    raw: dict
    text: str
    parsed: dict | None
    parse_error: str | None
    usage: dict
    latency_s: float


@dataclass
class Detection:
    label: str
    score: float
    bbox_xyxy: tuple[float, float, float, float]
    mask_png_bytes: bytes | None = None


@dataclass
class TranscriptSegment:
    t_start: float
    t_end: float
    text: str


def output_text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts: list[str] = []
    for item in resp.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts)


def extract_json(text: str) -> dict:
    """Return the answer object from model text.

    Without structured output, Muse sometimes echoes the JSON schema from the prompt before
    its answer. Prefer the first object whose "terms" is a list; otherwise the first object.
    """
    cleaned = _FENCE.sub("", text.strip())
    try:
        obj: Any = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    first: dict | None = None
    for m in re.finditer(r"\{", cleaned):
        try:
            obj, _ = decoder.raw_decode(cleaned, m.start())
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("terms"), list):
            return obj
        if first is None:
            first = obj
    if first is None:
        raise ValueError("no JSON object in model output")
    return first


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, httpx.TransportError) or (isinstance(exc, MetaAPIError) and exc.retryable)


class MetaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.meta.ai/v1", *,
                 http: httpx.Client | None = None, max_retries: int = 4,
                 backoff_s: float = 2.0) -> None:
        self._http = http or httpx.Client(timeout=httpx.Timeout(900, connect=30))
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._max_retries = max_retries
        self._backoff_s = backoff_s

    def __repr__(self) -> str:
        return f"MetaClient(base_url={self._base!r})"

    @classmethod
    def from_settings(cls, settings: Any) -> MetaClient:
        return cls(settings.require_api_key(), settings.meta_base_url)

    def close(self) -> None:
        self._http.close()

    def _retry(self, fn: Callable[[], T]) -> T:
        wait = wait_exponential(multiplier=self._backoff_s, max=60) if self._backoff_s else wait_none()
        retrying = Retrying(stop=stop_after_attempt(self._max_retries + 1), wait=wait,
                            retry=retry_if_exception(_retryable), reraise=True)
        return retrying(fn)

    def _send(self, method: str, path: str, *, timeout: float, **kwargs: Any) -> dict:
        r = self._http.request(method, f"{self._base}{path}", headers=self._headers,
                               timeout=timeout, **kwargs)
        if r.status_code >= 400:
            raise MetaAPIError(r.status_code, r.text[:1000])
        return r.json()

    def upload_file(self, path: Path, mime: str = "video/mp4") -> str:
        path = Path(path)

        def send() -> dict:
            with path.open("rb") as f:
                return self._send("POST", "/files", timeout=600,
                                  files={"file": (path.name, f, mime)}, data={"purpose": "user_data"})

        return self._retry(send)["id"]

    def create_response(self, body: dict, *, timeout: float = 900) -> dict:
        raw = self._retry(lambda: self._send("POST", "/responses", timeout=timeout, json=body))
        status = raw.get("status")
        if status not in (None, "completed"):
            raise MetaAPIError(200, f"response status {status}: {raw.get('incomplete_details')}")
        return raw

    def analyze_video(self, file_id: str, prompt: str, *, model: str, schema: dict | None = None,
                      max_output_tokens: int = 16000) -> AnalyzeResult:
        body: dict[str, Any] = {
            "model": model,
            "max_output_tokens": max_output_tokens,
            "input": [{"role": "user", "content": [
                {"type": "input_video", "file_id": file_id},
                {"type": "input_text", "text": prompt},
            ]}],
        }
        if schema is not None:
            body["text"] = {"format": {"type": "json_schema", "name": "empu_terms",
                                       "schema": schema, "strict": True}}
        t0 = time.monotonic()
        raw = self.create_response(body)
        latency = time.monotonic() - t0
        text = output_text(raw)
        try:
            parsed, err = extract_json(text), None
        except ValueError as e:
            parsed, err = None, str(e)
        return AnalyzeResult(raw=raw, text=text, parsed=parsed, parse_error=err,
                             usage=raw.get("usage") or {}, latency_s=latency)
