# api/tests/test_muse_schema.py
import json

import pytest
from pydantic import ValidationError

from conftest import REPO_ROOT, load_fixture
from empu.enums import Confidence, Source, VisualMatch
from empu.legacy import upgrade_v1
from empu.muse_schema import MuseSegmentOutput, MuseTerm, load_json_schema


def term(**kw) -> dict:
    base = {
        "spoken": "x", "term": "x", "category": "tool", "source": "speech",
        "t_start": 1.0, "t_end": 2.0, "stage": None, "evidence_quote": "", "visible": "",
        "visible_object_en": None, "visual_match": "yes", "gloss_id": "", "gloss_en": "",
        "confidence": "high",
    }
    return base | kw


def test_schema_copy_matches_docs():
    docs = json.loads((REPO_ROOT / "docs/reference/muse-output.schema.json").read_text())
    assert load_json_schema() == docs


def test_stripped_schema_has_no_length_keywords():
    text = json.dumps(load_json_schema("stripped"))
    assert "maxLength" not in text and "minimum" not in text and "$schema" not in text


def test_valid_term_parses():
    t = MuseTerm.model_validate(term())
    assert t.source is Source.speech and t.confidence is Confidence.high


def test_legacy_enums_coerced():
    t = MuseTerm.model_validate(term(source="teks_layar", visual_match="tidak_terlihat", confidence="sedang"))
    assert t.source is Source.on_screen_text
    assert t.visual_match is VisualMatch.not_visible
    assert t.confidence is Confidence.medium


def test_unknown_category_falls_back_to_other():
    assert MuseTerm.model_validate(term(category="pattern")).category == "other"


def test_bad_source_rejected():
    with pytest.raises(ValidationError):
        MuseTerm.model_validate(term(source="audio"))


def test_times_sanitized_and_quote_truncated():
    t = MuseTerm.model_validate(term(t_start=-1, t_end=-3, evidence_quote="a" * 400, spoken=""))
    assert t.t_start == 0.0 and t.t_end == 0.0
    assert len(t.evidence_quote) == 160
    assert t.spoken == "x"


def test_empty_term_rejected():
    with pytest.raises(ValidationError):
        MuseTerm.model_validate(term(term="  "))


def test_segment_requires_terms_key():
    with pytest.raises(ValidationError):
        MuseSegmentOutput.model_validate({"speech_heard": True, "process_steps": []})


def test_transcript_truncated():
    out = MuseSegmentOutput.model_validate({"terms": [], "transcript_excerpt": "y" * 500})
    assert len(out.transcript_excerpt) == 300


def test_upgrade_v1_nglowong():
    out = MuseSegmentOutput.model_validate(upgrade_v1(load_fixture("muse/v1/nglowong.json")))
    assert len(out.terms) == 12
    assert all(t.source is Source.speech for t in out.terms)
    assert out.terms[0].visual_match is VisualMatch.not_visible
    assert out.transcript_excerpt.startswith("Halo teman-teman")


def test_upgrade_v1_control_has_no_terms():
    out = MuseSegmentOutput.model_validate(upgrade_v1(load_fixture("muse/v1/kontrol-musik-nglorod.json")))
    assert out.terms == [] and len(out.process_steps) > 0
