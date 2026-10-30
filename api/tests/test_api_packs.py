from fastapi.testclient import TestClient
from sqlmodel import Session

from empu.app import create_app
from empu.config import Settings, get_settings
from empu.db import get_session, init_db, make_engine

VALID_YAML = """
id: tenun
version: 0.1.0
name: {id: Tenun, en: Hand-weaving}
languages: [id]
prompt_context: >
  Konteks tenun untuk analisis.
stages:
  - id: menyiapkan
    label: {id: Menyiapkan benang, en: Preparing the yarn}
    variants: [menggulung]
terms:
  - id: lungsi
    label: lungsi
    category: material
    variants: [benang lungsi]
    gloss_id: benang memanjang
    gloss_en: the warp yarn
    visual: false
    verified: false
"""


def client(tmp_path) -> TestClient:
    s = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        db_url=f"sqlite:///{tmp_path / 'empu.db'}",
        packs_dir=tmp_path / "packs",
        studio_key="studio-test",
        meta_model_api_key="k",
    )
    (s.packs_dir).mkdir(parents=True, exist_ok=True)
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


def test_create_pack_requires_key(tmp_path):
    r = client(tmp_path).post("/api/packs", json={"yaml": VALID_YAML})
    assert r.status_code == 401


def test_validate_pack(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    r = c.post("/api/packs/validate", json={"yaml": VALID_YAML}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "tenun"
    assert body["n_stages"] == 1
    assert body["n_terms"] == 1


def test_validate_pack_invalid(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    r = c.post("/api/packs/validate", json={"yaml": "not: [valid"}, headers=h)
    assert r.status_code == 400


def test_create_pack_ok(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    r = c.post("/api/packs", json={"yaml": VALID_YAML}, headers=h)
    assert r.status_code == 201
    assert r.json()["id"] == "tenun"
    assert (tmp_path / "packs" / "tenun.yaml").exists()


def test_create_pack_duplicate_conflict(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    assert c.post("/api/packs", json={"yaml": VALID_YAML}, headers=h).status_code == 201
    r = c.post("/api/packs", json={"yaml": VALID_YAML}, headers=h)
    assert r.status_code == 409


def test_create_pack_unsafe_id_rejected(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    bad = VALID_YAML.replace("id: tenun", "id: ../tenun")
    r = c.post("/api/packs", json={"yaml": bad}, headers=h)
    assert r.status_code == 400


def test_pack_source_requires_key(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/packs/batik_tulis/source")
    assert r.status_code == 401


def test_pack_source_ok(tmp_path):
    c = client(tmp_path)
    h = {"X-Studio-Key": "studio-test"}
    assert c.post("/api/packs", json={"yaml": VALID_YAML}, headers=h).status_code == 201
    r = c.get("/api/packs/tenun/source", headers=h)
    assert r.status_code == 200
    assert "id: tenun" in r.json()["yaml"]


def test_pack_source_missing_404(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/packs/nope/source", headers={"X-Studio-Key": "studio-test"})
    assert r.status_code == 404