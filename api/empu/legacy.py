"""Upgrade feasibility-test (v1) Muse output to the v3 contract. Used for fixtures only."""

from __future__ import annotations

from typing import Any


def upgrade_v1(d: dict[str, Any]) -> dict[str, Any]:
    out = {
        "speech_heard": bool(d.get("speech_heard", False)),
        "language_notes": d.get("language_notes", ""),
        "transcript_excerpt": d.get("transcript_excerpt") or d.get("transcript_first_20s", ""),
        "terms": [],
        "process_steps": d.get("process_steps", []),
    }
    for t in d.get("terms", []):
        out["terms"].append({
            "spoken": t.get("spoken", ""),
            "term": t.get("term") or t.get("spoken", ""),
            "category": t.get("category", "other"),
            "source": t.get("source", "speech"),
            "t_start": t.get("t_start", 0),
            "t_end": t.get("t_end", t.get("t_start", 0)),
            "stage": t.get("stage"),
            "evidence_quote": t.get("evidence_quote", ""),
            "visible": t.get("visible", ""),
            "visible_object_en": t.get("visible_object_en"),
            "visual_match": t.get("visual_match", "not_visible"),
            "gloss_id": t.get("gloss_id", ""),
            "gloss_en": t.get("gloss_en", ""),
            "confidence": t.get("confidence", "low"),
        })
    return out
