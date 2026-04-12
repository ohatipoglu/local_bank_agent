"""
Thread-safe agent factory and cache with per-model instance management.
Replaces global mutable agent state with proper concurrency control.
"""

import threading
import time
from typing import Any

from core.exceptions import AgentInitializationError


class AgentCacheEntry:
    """Represents a cached agent instance with metadata."""

    def __init__(self, agent, model_name: str, created_at: float):
        self.agent = agent
        self.model_name = model_name
        self.created_at = created_at
        self.last_accessed = time.time()
        self.use_count = 0

    def touch(self):
        """Update access timestamp."""
        self.last_accessed = time.time()
        self.use_count += 1


class AgentCache:
    """
    Thread-safe cache for LangChain agent instances.

    Provides:
    - Per-model agent caching with locking
    - Automatic eviction of stale entries
    - Maximum cache size enforcement
    - Statistics tracking
    """

    def __init__(self, max_size: int = 5, ttl_seconds: int = 1800):
        """
        Initialize agent cache.

        Args:
            max_size: Maximum number of cached agent instances
            ttl_seconds: Time-to-live for cached entries (30 min default)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, AgentCacheEntry] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "creations": 0,
        }

    def get_or_create(self, model_name: str, factory_func, *args, **kwargs) -> Any:
        """
        Get cached agent or create new one via factory function.

        Args:
            model_name: Ollama model name (cache key)
            factory_func: Callable that creates agent instance
            *args: Arguments to pass to factory
            **kwargs: Keyword arguments to pass to factory

        Returns:
            Agent instance
        """
        with self._lock:
            # Check if valid cached entry exists
            entry = self._cache.get(model_name)
            if entry and not self._is_expired(entry):
                entry.touch()
                self._stats["hits"] += 1
                return entry.agent

            # Cache miss or expired: create new agent
            self._stats["misses"] += 1

            # Evict if at capacity
            if len(self._cache) >= self.max_size and model_name not in self._cache:
                self._evict_oldest()

            # Create new agent via factory
            try:
                agent = factory_func(*args, **kwargs)
                entry = AgentCacheEntry(agent, model_name, time.time())
                self._cache[model_name] = entry
                self._stats["creations"] += 1
                return agent
            except Exception as e:
                raise AgentInitializationError(
                    f"Failed to create agent for model '{model_name}': {e}"
                ) from e

    def invalidate(self, model_name: str) -> bool:
        """
        Remove specific model from cache.

        Args:
            model_name: Model name to invalidate

        Returns:
            True if entry was removed
        """
        with self._lock:
            if model_name in self._cache:
                del self._cache[model_name]
                return True
            return False

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss/eviction counts
        """
        with self._lock:
            return {
                **self._stats,
                "cached_models": list(self._cache.keys()),
                "cache_size": len(self._cache),
                "max_size": self.max_size,
            }

    def _is_expired(self, entry: AgentCacheEntry) -> bool:
        """Check if cache entry has expired."""
        return (time.time() - entry.created_at) > self.ttl_seconds

    def _evict_oldest(self):
        """Evict oldest non-recently-used entry. Must be called within lock."""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[oldest_key]
        self._stats["evictions"] += 1


# Global agent cache instance
agent_cache = AgentCache(max_size=5, ttl_seconds=1800)
