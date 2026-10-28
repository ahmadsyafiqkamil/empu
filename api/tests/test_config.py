from empu.config import REPO_ROOT, Settings

EMPU_PKG = REPO_ROOT / "api" / "empu"


def test_defaults_derive_db_url(tmp_path):
    s = Settings(_env_file=None, data_dir=tmp_path)
    assert s.db_url == f"sqlite:///{tmp_path / 'empu.db'}"
    assert s.chunk_window_s == 75.0 and s.chunk_overlap_s == 10.0
    assert s.analyze_concurrency == 3
    assert s.muse_model == "muse-spark-1.3"
    assert s.pipeline_mode == "B"
    assert s.structured_output is True


def test_env_aliases(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPU_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPU_PIPELINE_MODE", "A")
    monkeypatch.setenv("EMPU_SAM_ENABLED", "false")
    s = Settings(_env_file=None)
    assert s.data_dir == tmp_path
    assert s.pipeline_mode == "A"
    assert s.sam_enabled is False


def test_secret_not_in_repr():
    s = Settings(_env_file=None, meta_model_api_key="sk-very-secret", studio_key="studio-secret")
    assert "sk-very-secret" not in repr(s)
    assert "studio-secret" not in repr(s)
    assert s.require_api_key() == "sk-very-secret"


def test_require_api_key_missing():
    s = Settings(_env_file=None, meta_model_api_key=None)
    try:
        s.require_api_key()
    except RuntimeError as e:
        assert "META_MODEL_API_KEY" in str(e)
    else:
        raise AssertionError("expected RuntimeError")


def test_only_config_reads_environment():
    offenders = []
    for path in EMPU_PKG.rglob("*.py"):
        if path.name == "config.py":
            continue
        text = path.read_text()
        if "os.environ" in text or "getenv(" in text or "META_MODEL_API_KEY" in text:
            offenders.append(str(path.relative_to(EMPU_PKG)))
    assert offenders == [], offenders
