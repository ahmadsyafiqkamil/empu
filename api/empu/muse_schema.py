"""Contract for Muse output per segment (resources/muse-output.schema.json, v3).

Validation is lenient where it is safe (unknown category -> other, legacy Indonesian
enums -> English) and strict where it matters (source, term, times).
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from empu.enums import Category, Confidence, Source, VisualMatch

LEGACY_ENUMS = {
    "ucapan": "speech", "teks_layar": "on_screen_text", "visual": "visual_only",
    "ya": "yes", "tidak": "no", "tidak_terlihat": "not_visible",
    "rendah": "low", "sedang": "medium", "tinggi": "high",
}
_STRIP_KEYS = {"maxLength", "minimum", "$schema", "$id", "title", "description"}


def _enum_key(v: Any) -> Any:
    if isinstance(v, str):
        k = v.strip().lower().replace(" ", "_").replace("-", "_")
        return LEGACY_ENUMS.get(k, k)
    return v


class MuseTerm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    spoken: str = ""
    term: str
    category: Category = Category.other
    source: Source
    t_start: float
    t_end: float
    stage: str | None = None
    evidence_quote: str = ""
    visible: str = ""
    visible_object_en: str | None = None
    visual_match: VisualMatch = VisualMatch.not_visible
    gloss_id: str = ""
    gloss_en: str = ""
    confidence: Confidence = Confidence.low

    @field_validator("source", mode="before")
    @classmethod
    def _source(cls, v: Any) -> Any:
        return _enum_key(v)

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in Category.__members__ else Category.other

    @field_validator("visual_match", mode="before")
    @classmethod
    def _visual_match(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in VisualMatch.__members__ else VisualMatch.not_visible

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence(cls, v: Any) -> Any:
        k = _enum_key(v)
        return k if k in Confidence.__members__ else Confidence.low

    @field_validator("visible_object_en", "stage", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        return None if isinstance(v, str) and not v.strip() else v

    @model_validator(mode="after")
    def _sanitize(self) -> MuseTerm:
        self.term = self.term.strip()
        if not self.term:
            raise ValueError("term is empty")
        self.spoken = self.spoken.strip() or self.term
        self.t_start = max(0.0, float(self.t_start))
        self.t_end = max(self.t_start, float(self.t_end))
        self.evidence_quote = self.evidence_quote[:160]
        return self


class MuseProcessStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    step: str
    t_start: float
    t_end: float
    tools: list[str] = []

    @model_validator(mode="after")
    def _sanitize(self) -> MuseProcessStep:
        self.t_start = max(0.0, float(self.t_start))
        self.t_end = max(self.t_start, float(self.t_end))
        return self


class MuseSegmentOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    speech_heard: bool = False
    language_notes: str = ""
    transcript_excerpt: str = ""
    terms: list[MuseTerm]
    process_steps: list[MuseProcessStep] = []

    @field_validator("transcript_excerpt", mode="after")
    @classmethod
    def _truncate(cls, v: str) -> str:
        return v[:300]


def _strip(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip(v) for k, v in node.items() if k not in _STRIP_KEYS}
    if isinstance(node, list):
        return [_strip(v) for v in node]
    return node


@cache
def _schema_text() -> str:
    return files("empu.resources").joinpath("muse-output.schema.json").read_text()


def load_json_schema(variant: Literal["full", "stripped"] = "full") -> dict:
    schema = json.loads(_schema_text())
    return _strip(schema) if variant == "stripped" else schema
