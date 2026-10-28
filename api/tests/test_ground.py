import pytest
from fakes import FakeClient, make_sam_raw
from PIL import Image

from empu.cache import ResponseCache
from empu.enums import SamStatus
from empu.meta_client import MetaAPIError
from empu.pipeline.ground import crop_box, ground_keyframe, sam_prompts_for


@pytest.fixture
def keyframe(tmp_path):
    p = tmp_path / "keyframe.jpg"
    Image.new("RGB", (854, 480), (120, 90, 60)).save(p)
    return p


def test_sam_prompts_for(pack):
    assert sam_prompts_for(pack, pack_term_id="canting", is_novel=False, visible_object_en="x") == [
        "wooden stick with copper tip",
        "pen with wooden handle",
    ]
    assert (
        sam_prompts_for(pack, pack_term_id="waterglass", is_novel=False, visible_object_en="jar")
        == []
    )
    assert sam_prompts_for(
        pack, pack_term_id=None, is_novel=True, visible_object_en="small bowl"
    ) == ["small bowl"]
    assert sam_prompts_for(pack, pack_term_id=None, is_novel=True, visible_object_en=None) == []
    assert sam_prompts_for(pack, pack_term_id=None, is_novel=False, visible_object_en="pot") == []


def test_crop_box_pads_15_percent_and_clamps():
    bbox = (209 / 854, 135 / 480, 743 / 854, 340 / 480)
    assert crop_box((854, 480), bbox) == (128, 104, 823, 371)
    assert crop_box((100, 100), (0.0, 0.0, 1.0, 1.0)) == (0, 0, 100, 100)


def test_ground_tries_prompts_in_order_and_caches(tmp_path, keyframe):
    cache = ResponseCache(tmp_path / "sam-cache")
    client = FakeClient(sam={"second": make_sam_raw([(209, 135, 743, 340), (10, 10, 50, 50)])})
    res = ground_keyframe(
        client, cache, keyframe, ["first", "second", "third"], tmp_path / "e", model="sam-3.1"
    )
    assert res.status is SamStatus.ok and res.prompt_used == "second" and len(res.detections) == 2
    assert [c[1] for c in client.sam_calls] == [["first"], ["second"]]
    with Image.open(res.crop_path) as im:
        assert im.size == (823 - 128, 371 - 104)
    assert res.overlay_path.exists()
    again = FakeClient()
    res2 = ground_keyframe(
        again, cache, keyframe, ["first", "second"], tmp_path / "e2", model="sam-3.1"
    )
    assert res2.status is SamStatus.ok and again.sam_calls == []


def test_ground_empty_skipped_error(tmp_path, keyframe):
    cache = ResponseCache(tmp_path / "c")
    empty = ground_keyframe(FakeClient(), cache, keyframe, ["x"], tmp_path / "e", model="m")
    assert empty.status is SamStatus.empty
    skipped = ground_keyframe(FakeClient(), cache, keyframe, [], tmp_path / "e", model="m")
    assert skipped.status is SamStatus.skipped

    class Boom(FakeClient):
        def segment_image_raw(self, image_path, prompt, *, model):
            raise MetaAPIError(500, "sam down")

    res = ground_keyframe(Boom(), cache, keyframe, ["y"], tmp_path / "e", model="m")
    assert res.status is SamStatus.error and "500" in res.error and res.crop_path is None
