import json
from pathlib import Path

import pytest

from empu.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text())


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        packs_dir=REPO_ROOT / "packs",
        meta_model_api_key="test-key",
        studio_key="studio-test",
        sam_enabled=True,
        structured_output=False,
    )
