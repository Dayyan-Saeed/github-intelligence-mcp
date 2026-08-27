"""Tests for the cache abstraction."""

import time

from github_intelligence_mcp.cache import MemoryCache, NullCache, SQLiteCache


def test_memory_cache_hit_and_miss() -> None:
    cache = MemoryCache()
    cache.set("k1", "v1", ttl=60)
    assert cache.get("k1") == "v1"
    assert cache.get("missing") is None


def test_memory_cache_expiry() -> None:
    cache = MemoryCache()
    cache.set("k1", "v1", ttl=1)
    # Manually set expiry in the past
    cache._store["k1"] = ("v1", time.monotonic() - 1)
    assert cache.get("k1") is None


def test_memory_cache_delete_and_clear() -> None:
    cache = MemoryCache()
    cache.set("k1", "v1", ttl=60)
    cache.set("k2", "v2", ttl=60)
    cache.delete("k1")
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"
    cache.clear()
    assert cache.get("k2") is None


def test_memory_cache_overwrite() -> None:
    cache = MemoryCache()
    cache.set("k1", "old", ttl=60)
    cache.set("k1", "new", ttl=60)
    assert cache.get("k1") == "new"


def test_null_cache_always_misses() -> None:
    cache = NullCache()
    cache.set("k1", "v1", ttl=60)
    assert cache.get("k1") is None
    cache.delete("k1")
    cache.clear()


def test_sqlite_cache_hit_and_miss(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "test.db"
    cache = SQLiteCache(db)
    cache.set("k1", "v1", ttl=60)
    assert cache.get("k1") == "v1"
    assert cache.get("missing") is None
    cache.close()


def test_sqlite_cache_expiry(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "test.db"
    cache = SQLiteCache(db)
    cache.set("k1", "v1", ttl=0)
    time.sleep(0.01)
    assert cache.get("k1") is None
    cache.close()


def test_sqlite_cache_persists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "test.db"
    cache1 = SQLiteCache(db)
    cache1.set("k1", {"nested": "value"}, ttl=60)
    cache1.close()

    cache2 = SQLiteCache(db)
    assert cache2.get("k1") == {"nested": "value"}
    cache2.close()


def test_sqlite_cache_delete_and_clear(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "test.db"
    cache = SQLiteCache(db)
    cache.set("k1", "v1", ttl=60)
    cache.set("k2", "v2", ttl=60)
    cache.delete("k1")
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"
    cache.clear()
    assert cache.get("k2") is None
    cache.close()
