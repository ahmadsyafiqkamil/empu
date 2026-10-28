"""Test doubles. Never touches the network."""

from __future__ import annotations

import json
from pathlib import Path

from empu.meta_client import AnalyzeResult, Detection, extract_json, output_text


def make_raw(payload: dict | str, usage: dict | None = None) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {
        "object": "response",
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            },
        ],
        "usage": usage or {"input_tokens": 100, "output_tokens": 20,
                           "output_tokens_details": {"reasoning_tokens": 5}},
    }


class FakeClient:
    """Mimics MetaClient. `responses` are raw Responses-API dicts, consumed in order."""

    def __init__(self, responses: list[dict] | None = None,
                 detections: list[Detection] | None = None) -> None:
        self.responses = list(responses or [])
        self.detections = detections or []
        self.uploads: list[Path] = []
        self.prompts: list[str] = []
        self.schemas: list[dict | None] = []
        self.sam_calls: list[tuple[Path, list[str]]] = []

    def upload_file(self, path: Path, mime: str = "video/mp4") -> str:
        self.uploads.append(Path(path))
        return f"file_{len(self.uploads)}"

    def analyze_video(self, file_id: str, prompt: str, *, model: str, schema: dict | None = None,
                      max_output_tokens: int = 16000) -> AnalyzeResult:
        self.prompts.append(prompt)
        self.schemas.append(schema)
        if not self.responses:
            raise AssertionError("FakeClient ran out of responses")
        raw = self.responses.pop(0)
        text = output_text(raw)
        try:
            parsed, err = extract_json(text), None
        except ValueError as e:
            parsed, err = None, str(e)
        return AnalyzeResult(raw=raw, text=text, parsed=parsed, parse_error=err,
                             usage=raw.get("usage", {}), latency_s=0.5)

    def segment_image(self, image_path: Path, prompts: list[str], *, model: str) -> list[Detection]:
        self.sam_calls.append((Path(image_path), list(prompts)))
        return list(self.detections)
