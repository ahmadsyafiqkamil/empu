# api/tests/test_meta_client.py
import json

import httpx
import pytest
import respx
from conftest import FIXTURES, load_fixture

from empu.meta_client import MetaAPIError, MetaClient, extract_json, output_text
from empu.muse_schema import MuseSegmentOutput

BASE = "https://api.test/v1"


@pytest.fixture
def video(tmp_path):
    p = tmp_path / "seg.mp4"
    p.write_bytes(b"\x00fake-video")
    return p


def client() -> MetaClient:
    return MetaClient("secret-key", BASE, backoff_s=0)


@respx.mock
def test_upload_sends_auth_and_purpose(video):
    route = respx.post(f"{BASE}/files").mock(
        return_value=httpx.Response(200, json={"id": "file_1"})
    )
    assert client().upload_file(video) == "file_1"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer secret-key"
    assert b'name="purpose"' in req.content and b"user_data" in req.content


@respx.mock
def test_retries_429_then_succeeds(video):
    route = respx.post(f"{BASE}/files").mock(side_effect=[
        httpx.Response(429, text="slow down"), httpx.Response(200, json={"id": "file_2"})])
    assert client().upload_file(video) == "file_2"
    assert route.call_count == 2


@respx.mock
def test_gives_up_after_four_retries(video):
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(503, text="down"))
    with pytest.raises(MetaAPIError) as e:
        client().upload_file(video)
    assert e.value.status_code == 503
    assert route.call_count == 5


@respx.mock
def test_no_retry_on_400(video):
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(400, text="bad"))
    with pytest.raises(MetaAPIError):
        client().upload_file(video)
    assert route.call_count == 1


@respx.mock
def test_retries_transport_error(video):
    route = respx.post(f"{BASE}/files").mock(side_effect=[
        httpx.ConnectError("boom"), httpx.Response(200, json={"id": "file_3"})])
    assert client().upload_file(video) == "file_3"
    assert route.call_count == 2


@respx.mock
def test_analyze_video_body_and_parse():
    raw = load_fixture("muse/v1/nglowong.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    res = client().analyze_video("file_9", "PROMPT", model="muse-spark-1.3")
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "muse-spark-1.3"
    assert body["input"][0]["content"][0] == {"type": "input_video", "file_id": "file_9"}
    assert body["input"][0]["content"][1] == {"type": "input_text", "text": "PROMPT"}
    assert "text" not in body
    assert res.parse_error is None and len(res.parsed["terms"]) == 12
    assert res.usage["input_tokens"] == 36271
    assert res.latency_s >= 0


@respx.mock
def test_analyze_video_with_schema_sets_text_format():
    raw = load_fixture("muse/v1/nglowong.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    client().analyze_video("f", "P", model="m", schema={"type": "object"})
    fmt = json.loads(route.calls.last.request.content)["text"]["format"]
    assert fmt == {
        "type": "json_schema",
        "name": "empu_terms",
        "schema": {"type": "object"},
        "strict": True,
    }


@respx.mock
def test_analyze_video_unparseable_text_keeps_raw():
    raw = {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": "sorry, no json"}]}], "usage": {}}
    respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    res = client().analyze_video("f", "P", model="m")
    assert res.parsed is None and "no JSON" in res.parse_error and res.raw == raw


@respx.mock
def test_incomplete_response_raises_without_retry():
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(
        200, json={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}))
    with pytest.raises(MetaAPIError, match="incomplete"):
        client().analyze_video("f", "P", model="m")
    assert route.call_count == 1


def test_repr_hides_key():
    assert "secret-key" not in repr(client())


def test_output_text_and_extract_json():
    raw = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "```json\n{\"a\": 1}\n```"}],
            }
        ]
    }
    assert extract_json(output_text(raw)) == {"a": 1}
    assert extract_json('Here you go: {"terms": []} thanks') == {"terms": []}
    echoed = (
        '{"type": "object", "properties": {"terms": {"type": "array"}}} '
        '{"terms": [], "speech_heard": true}'
    )
    assert extract_json(echoed) == {"terms": [], "speech_heard": True}
    assert output_text({"output_text": "{}"}) == "{}"
    with pytest.raises(ValueError):
        extract_json("[1, 2]")
    with pytest.raises(ValueError):
        extract_json("nothing")


@pytest.mark.skipif(
    not (FIXTURES / "muse/gate0/recall-seg0.raw.json").exists(),
    reason="gate0 fixture missing",
)
def test_gate0_v3_output_validates_without_upgrade():
    raw = load_fixture("muse/gate0/recall-seg0.raw.json")
    MuseSegmentOutput.model_validate(extract_json(output_text(raw)))


@respx.mock
def test_respond_text_sends_text_only_and_parses():
    raw = load_fixture("ask/probe.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    res = client().respond_text("PROMPT", model="muse-spark-1.3", schema={"type": "object"})
    body = json.loads(route.calls.last.request.content)
    assert body["input"] == [{"role": "user", "content": [{"type": "input_text", "text": "PROMPT"}]}]
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "empu_answer",
        "schema": {"type": "object"},
        "strict": True,
    }
    assert res.parse_error is None
    assert set(res.parsed) == {"answer", "lang", "entry_ids", "insufficient"}
    assert res.usage


@respx.mock
def test_respond_text_without_schema_omits_text_format():
    raw = load_fixture("ask/probe.raw.json")
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    client().respond_text("P", model="m")
    assert "text" not in json.loads(route.calls.last.request.content)
