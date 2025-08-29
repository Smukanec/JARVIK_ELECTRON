import time
import importlib.util
import pathlib


spec = importlib.util.spec_from_file_location(
    "fura_client", pathlib.Path(__file__).resolve().parents[1] / "app" / "fura_client.py"
)
fura_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fura_client)


def test_cache_write_and_read(tmp_path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(fura_client, "CACHE_FILE", str(cache_path))
    with fura_client._open_cache() as cache:
        cache["foo"] = {"timestamp": time.time(), "data": {"x": 1}}
    with fura_client._open_cache() as cache:
        assert cache["foo"]["data"] == {"x": 1}


def test_cache_eviction(tmp_path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(fura_client, "CACHE_FILE", str(cache_path))
    monkeypatch.setattr(fura_client, "CACHE_MAX_ITEMS", 2)
    now = time.time()
    with fura_client._open_cache() as cache:
        cache["a"] = {"timestamp": now - 3, "data": 1}
        cache["b"] = {"timestamp": now - 2, "data": 2}
        cache["c"] = {"timestamp": now - 1, "data": 3}
        fura_client._prune_cache(cache)
        assert "a" not in cache
        assert len(cache) == 2

