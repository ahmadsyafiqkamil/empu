from fastapi.testclient import TestClient

from empu.app import create_app
from empu.config import Settings
from empu.db import init_db, make_engine


def client(tmp_path) -> TestClient:
    s = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        studio_key="studio-test",
        meta_model_api_key="k",
    )
    init_db(make_engine(s.db_url))
    app = create_app()
    app.dependency_overrides = {}
    from empu.config import get_settings

    app.dependency_overrides[get_settings] = lambda: s
    return TestClient(app)


def test_health_no_key(tmp_path):
    r = client(tmp_path).get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_studio_route_401_without_key(tmp_path):
    r = client(tmp_path).get("/api/archives")
    assert r.status_code == 401


def test_studio_route_ok_with_key(tmp_path):
    r = client(tmp_path).get("/api/archives", headers={"X-Studio-Key": "studio-test"})
    assert r.status_code == 200
    assert r.json() == []
