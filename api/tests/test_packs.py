import copy

import pytest
import yaml

from conftest import REPO_ROOT
from empu.packs import CraftPack, PackError, PackRef, list_packs, load_pack

PACK_FILE = REPO_ROOT / "packs" / "batik_tulis.yaml"


def raw_pack() -> dict:
    return yaml.safe_load(PACK_FILE.read_text())


def test_real_pack_loads(pack):
    assert pack.id == "batik_tulis"
    assert len(pack.stages) == 13
    assert len(pack.terms) == 42
    assert pack.asr_error_examples[0].correct == "spangkring"


def test_variant_index_resolves_terms_and_stages(pack):
    idx = pack.variant_index()
    assert idx["tjanting"] == PackRef("term", "canting")
    assert idx["canting klowongan"] == PackRef("term", "canting_klowongan")
    assert idx["ngelorot"] == PackRef("stage", "nglorod")
    assert idx["hcl"] == PackRef("term", "hcl")
    assert idx["persiapan kain"] == PackRef("stage", "persiapan_kain")


def test_lookup_helpers(pack):
    assert pack.stage("nglorod").label.en == "Wax removal by boiling"
    assert pack.term("canting").visual is True
    assert pack.stage("missing") is None
    assert pack.stage("persiapan_kain").display_label == "persiapan kain"


def test_duplicate_variant_rejected():
    data = raw_pack()
    data["terms"][1]["variants"].append("tjanting")  # already a canting variant
    with pytest.raises(ValueError, match="tjanting"):
        CraftPack.model_validate(data)


def test_variant_shared_with_stage_rejected():
    data = raw_pack()
    data["terms"][0]["variants"].append("ngelorod")
    with pytest.raises(ValueError, match="ngelorod"):
        CraftPack.model_validate(data)


def test_unknown_stage_reference_rejected():
    data = raw_pack()
    data["terms"][0]["stage"] = "no_such_stage"
    with pytest.raises(ValueError, match="no_such_stage"):
        CraftPack.model_validate(data)


def test_visual_requires_sam_prompt():
    data = raw_pack()
    data["terms"][0]["sam_prompt"] = None
    with pytest.raises(ValueError, match="sam_prompt"):
        CraftPack.model_validate(data)


def test_duplicate_ids_rejected():
    data = raw_pack()
    data["terms"].append(copy.deepcopy(data["terms"][0]))
    with pytest.raises(ValueError, match="duplicate term ids"):
        CraftPack.model_validate(data)


def test_load_pack_errors(tmp_path):
    with pytest.raises(PackError, match="not found"):
        load_pack("nope", tmp_path)
    (tmp_path / "bad.yaml").write_text("id: other\nversion: 1\n")
    with pytest.raises(PackError):
        load_pack("bad", tmp_path)


def test_list_packs():
    assert "batik_tulis" in [p.id for p in list_packs(REPO_ROOT / "packs")]
