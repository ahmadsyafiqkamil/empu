# api/tests/test_analyze.py
import json

import pytest
from conftest import load_fixture
from fakes import FakeClient, make_raw

from empu.cache import ResponseCache
from empu.legacy import upgrade_v1
from empu.meta_client import MetaAPIError
from empu.pipeline.analyze import AnalyzeOptions, analyze_chunk, analyze_chunks, usage_totals
from empu.pipeline.chunk import ChunkSpec

GOOD = upgrade_v1(load_fixture("muse/v1/nglowong.json"))
OPTS = AnalyzeOptions(model="muse-spark-1.3")
SPEC = ChunkSpec(0, 0.0, 75.0)


@pytest.fixture
def cache(tmp_path):
    return ResponseCache(tmp_path / "cache")


def chunk_file(tmp_path, idx=0):
    p = tmp_path / "chunks" / f"{idx}.mp4"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(f"chunk-{idx}".encode())
    return p


def run(client, cache, pack, tmp_path, opts=OPTS, spec=SPEC, **kw):
    return analyze_chunk(
        client,
        cache,
        pack,
        spec,
        chunk_file(tmp_path, spec.idx),
        opts,
        seg_total=1,
        out_dir=tmp_path / "muse",
        **kw,
    )


def test_writes_raw_and_parsed(tmp_path, pack, cache):
    client = FakeClient([make_raw(GOOD)])
    res = run(client, cache, pack, tmp_path)
    assert res.error is None and not res.cached and res.attempts == 1
    assert len(res.output.terms) == 12
    assert json.loads((tmp_path / "muse/0.json").read_text())["terms"][0]["source"] == "speech"
    assert (tmp_path / "muse/0.raw.json").exists()
    assert "segmen 1/1" in client.prompts[0] and client.schemas == [None]
    assert res.cache_key.endswith("__muse-spark-1.3__analyze-v3__A")


def test_cache_hit_skips_api(tmp_path, pack, cache):
    run(FakeClient([make_raw(GOOD)]), cache, pack, tmp_path)
    client = FakeClient([])
    res = run(client, cache, pack, tmp_path)
    assert res.cached and client.uploads == [] and len(res.output.terms) == 12


def test_invalid_then_valid_retries_once_same_upload(tmp_path, pack, cache):
    client = FakeClient([make_raw("not json"), make_raw(GOOD)])
    res = run(client, cache, pack, tmp_path)
    assert res.error is None and res.attempts == 2
    assert len(client.uploads) == 1
    assert "tidak valid" in client.prompts[1]
    assert res.usage["input_tokens"] == 200


def test_invalid_twice_is_error_and_not_cached(tmp_path, pack, cache):
    client = FakeClient([make_raw("nope"), make_raw({"no_terms": 1})])
    res = run(client, cache, pack, tmp_path)
    assert res.output is None and "terms" in res.error
    assert cache.get(res.cache_key) is None
    assert (tmp_path / "muse/0.raw.json").exists()


def test_bad_items_dropped_not_fatal(tmp_path, pack, cache):
    bad = {"term": " ", "source": "speech", "t_start": 1, "t_end": 2}
    payload = GOOD | {
        "terms": GOOD["terms"][:2] + [bad],
        "process_steps": [{"step": "x", "t_start": "?", "t_end": 1}],
    }
    res = run(FakeClient([make_raw(payload)]), cache, pack, tmp_path)
    assert len(res.output.terms) == 2 and res.output.process_steps == [] and res.dropped == 2


def test_structured_sends_schema(tmp_path, pack, cache):
    client = FakeClient([make_raw(GOOD)])
    run(client, cache, pack, tmp_path, opts=AnalyzeOptions(model="m", structured=True))
    assert client.schemas[0]["type"] == "object"


def test_noseed_uses_own_version_and_cache_key(tmp_path, pack, cache):
    client = FakeClient([make_raw(GOOD), make_raw(GOOD)])
    a = run(client, cache, pack, tmp_path)
    b = run(client, cache, pack, tmp_path, opts=AnalyzeOptions(model="muse-spark-1.3", seeds=False))
    assert b.prompt_version == "analyze-v3-noseed" and a.cache_key != b.cache_key
    assert "CONTOH ISTILAH" not in client.prompts[1]


def test_api_error_captured(tmp_path, pack, cache):
    class Boom(FakeClient):
        def upload_file(self, path, mime="video/mp4"):
            raise MetaAPIError(503, "down")

    res = run(Boom(), cache, pack, tmp_path)
    assert res.output is None and "503" in res.error


def test_analyze_chunks_parallel_ordered_with_callback(tmp_path, pack, cache):
    items = [(ChunkSpec(i, i * 65.0, i * 65.0 + 75), chunk_file(tmp_path, i)) for i in range(3)]
    done = []
    res = analyze_chunks(
        FakeClient([make_raw(GOOD)] * 3),
        cache,
        pack,
        items,
        OPTS,
        out_dir=tmp_path / "muse",
        concurrency=3,
        on_done=done.append,
    )
    assert [r.spec.idx for r in res] == [0, 1, 2] and len(done) == 3


def test_usage_totals():
    u = [
        {"input_tokens": 10, "output_tokens": 3, "output_tokens_details": {"reasoning_tokens": 2}},
        {"input_tokens": 5},
    ]
    assert usage_totals(u) == {"input_tokens": 15, "output_tokens": 3, "reasoning_tokens": 2}
