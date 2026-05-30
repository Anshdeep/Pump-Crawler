"""
utils/cache.py -- Simple file-based JSON cache to avoid re-crawling pages
"""
import os
import json
import hashlib
from config import CACHE_DIR, CACHE_ENABLED


def _cache_path(key: str) -> str:
    hashed = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{hashed}.json")


def get(key: str):
    """Return cached value or None."""
    if not CACHE_ENABLED:
        return None
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def set(key: str, value):
    """Store value in cache."""
    if not CACHE_ENABLED:
        return
    path = _cache_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def invalidate(key: str):
    """Remove a cached entry."""
    path = _cache_path(key)
    if os.path.exists(path):
        os.remove(path)
