import json

import httpx
import respx

from conftest import load_fixture
from empu.meta_client import MetaClient, output_text, parse_sam_boxes

BASE = "https://api.test/v1"


def test_parse_row_fixture_four_boxes():
    raw = load_fixture("sam/sam-canting-row.raw.json")["response"]
    dets = parse_sam_boxes(output_text(raw), label="wooden stick with copper tip")
    assert len(dets) == 4
    assert dets[0].label == "wooden stick with copper tip" and dets[0].score == 1.0
    x1, y1, x2, y2 = dets[3].bbox_xyxy
    assert (round(x1 * 854), round(y1 * 480), round(x2 * 854), round(y2 * 480)) == (553, 265, 736, 425)


def test_parse_ignores_degenerate_and_garbage():
    text = "<|box;x1=5;y1=5;x2=5;y2=9;w=10;h=10|> junk <|box;x1=1;y1=1;x2=4;y2=4;w=10;h=10|>"
    assert [d.bbox_xyxy for d in parse_sam_boxes(text)] == [(0.1, 0.1, 0.4, 0.4)]
    assert parse_sam_boxes("no boxes") == []


@respx.mock
def test_segment_image_raw_body(tmp_path):
    img = tmp_path / "k.jpg"
    img.write_bytes(b"\xff\xd8fakejpeg")
    raw = load_fixture("sam/sam-canting-closeup.raw.json")["response"]
    route = respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=raw))
    client = MetaClient("k", BASE, backoff_s=0)
    dets = client.segment_image(img, ["pen with wooden handle"], model="sam-3.1")
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "sam-3.1" and body["stream"] is False
    content = body["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "pen with wooden handle"}
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")
    assert len(dets) == 1
