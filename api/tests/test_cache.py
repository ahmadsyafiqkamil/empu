import hashlib

from empu.cache import ResponseCache, sha256_file


def test_sha256_file(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"hello")
    assert sha256_file(p) == hashlib.sha256(b"hello").hexdigest()


def test_key_contains_all_parts_and_is_filesystem_safe():
    k = ResponseCache.key("abc", "muse-spark-1.3", "analyze-v3", "A")
    assert k == "abc__muse-spark-1.3__analyze-v3__A"
    assert ResponseCache.key("abc", "m/x", "v", "A") == "abc__m_x__v__A"
    keys = {ResponseCache.key(*parts) for parts in [
        ("abc", "m", "v3", "A"), ("abd", "m", "v3", "A"), ("abc", "n", "v3", "A"),
        ("abc", "m", "v4", "A"), ("abc", "m", "v3", "B")]}
    assert len(keys) == 5


def test_roundtrip_and_miss(tmp_path):
    cache = ResponseCache(tmp_path / "cache")
    assert cache.get("missing") is None
    path = cache.put("k1", {"raw": {"x": 1}, "usage": {}})
    assert path == tmp_path / "cache" / "k1.json"
    assert cache.get("k1") == {"raw": {"x": 1}, "usage": {}}
    assert list((tmp_path / "cache").glob("*.tmp")) == []
