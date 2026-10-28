from fastapi.testclient import TestClient
from sqlmodel import Session

from empu.app import create_app
from empu.config import Settings, get_settings
from empu.db import get_session, init_db, make_engine


def client(tmp_path) -> TestClient:
    s = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        studio_key="studio-test",
        meta_model_api_key="k",
    )
    engine = make_engine(s.db_url)
    init_db(engine)
    app = create_app()
    app.dependency_overrides = {}

    def _session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[get_session] = _session
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
