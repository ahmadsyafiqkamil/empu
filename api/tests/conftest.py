import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from empu.app import create_app
from empu.config import Settings, get_settings
from empu.db import get_session, init_db, make_engine
from empu.packs import CraftPack, load_pack

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text())


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        db_url=f"sqlite:///{tmp_path / 'empu.db'}",
        packs_dir=REPO_ROOT / "packs",
        meta_model_api_key="test-key",
        studio_key="studio-test",
        sam_enabled=True,
        structured_output=False,
    )


@pytest.fixture
def engine(settings):
    eng = make_engine(settings.db_url)
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def api(session, settings):
    app = create_app()

    def _session():
        yield session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = _session
    with TestClient(app) as c:
        c.headers["X-Studio-Key"] = settings.studio_key.get_secret_value()
        yield c


@pytest.fixture(scope="session")
def pack() -> CraftPack:
    return load_pack("batik_tulis", REPO_ROOT / "packs")


requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory) -> Path:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    out = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1280x720:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "12",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ],
        check=True,
    )
    return out
