# api/tests/test_prompts.py
from empu.meta_client import TranscriptSegment
from empu.pipeline.prompts import build_prompt, prompt_version_for


def prompt(pack, **kw):
    return build_prompt(pack, seg_index=2, seg_total=5, seg_duration=75.0, **kw)


def test_versions():
    assert prompt_version_for(True) == "analyze-v3"
    assert prompt_version_for(False) == "analyze-v3-noseed"
    assert prompt_version_for(True, transcript=True) == "analyze-v3-asr"
    assert prompt_version_for(False, transcript=True) == "analyze-v3-asr-noseed"


def test_prompt_has_segment_info_context_stages_and_schema(pack):
    p = prompt(pack)
    assert "segmen 2/5" in p and "berdurasi 75 detik" in p
    assert pack.name.id in p
    assert pack.prompt_context.strip() in p
    for s in pack.stages:
        assert f"- {s.id} — {s.label.id}" in p
    assert '"evidence_quote"' in p
    assert "TRANSKRIP OTOMATIS" not in p


def test_seed_block_lists_terms_with_variants(pack):
    p = prompt(pack)
    assert "CONTOH ISTILAH YANG MUNGKIN MUNCUL" in p
    first = pack.terms[0]
    others = [v for v in first.variants if v.casefold() != first.label.casefold()]
    assert f"- {first.label} (varian: {', '.join(others)})" in p


def test_noseed_drops_only_the_seed_block(pack):
    p = prompt(pack, seeds=False)
    assert "CONTOH ISTILAH" not in p
    assert all(f"- {s.id} — " in p for s in pack.stages)


def test_pack_glosses_never_in_prompt(pack):
    p = prompt(pack)
    assert not [t.id for t in pack.terms if t.gloss_id in p or t.gloss_en in p]


def test_transcript_block_before_task_and_uses_pack_examples(pack):
    tr = [TranscriptSegment(1.0, 3.5, "ini namanya spang King")]
    p = prompt(pack, transcript=tr)
    ex = pack.asr_error_examples[0]
    assert f'"{ex.correct}" ditulis "{ex.heard}"' in p
    assert "[1.0–3.5] ini namanya spang King" in p
    assert p.index("TRANSKRIP OTOMATIS") < p.index("TUGAS")
