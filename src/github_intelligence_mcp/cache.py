"""Cache abstraction for HTTP response caching.

Provides a simple key-value cache with TTL support. The interface is
implementation-agnostic — tools never import a concrete cache class directly.

Default TTLs per endpoint (configurable via env):

- Repository metadata: 10 minutes
- Issues: 5 minutes
- Pull requests: 5 minutes
- Commits: 2 minutes
- Contributors: 10 minutes
- Releases: 10 minutes
"""

from __future__ import annotations

import json
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from github_intelligence_mcp.logging import get_logger

_log = get_logger(__name__)

# Default TTLs in seconds
DEFAULT_TTLS: dict[str, int] = {
    "repository": 600,
    "issues": 300,
    "pull_requests": 300,
    "commits": 120,
    "contributors": 600,
    "releases": 600,
}


class Cache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return cached value or None if missing/expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store value with TTL in seconds."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a single key."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries."""


class MemoryCache(Cache):
    """In-memory cache with TTL. Good for testing and single-process use."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class SQLiteCache(Cache):
    """SQLite-backed cache. Persistent across restarts, thread-safe."""

    def __init__(self, db_path: str | Path = ".cache/github-intelligence.db") -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  expires_at REAL NOT NULL"
            ")"
        )
        self._conn.commit()

    def get(self, key: str) -> Any | None:
        row = self._conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        value_json, expires_at = row
        if time.monotonic() > expires_at:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            return None
        return json.loads(value_json)

    def set(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.monotonic() + ttl
        value_json = json.dumps(value, default=str)
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, value_json, expires_at),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class NullCache(Cache):
    """No-op cache. Always misses. Used when caching is disabled."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def clear(self) -> None:
        pass
