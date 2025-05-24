"""Storage backends for TrustChain v2."""

import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Dict, Optional


class Storage(ABC):
    """Abstract storage interface."""

    @abstractmethod
    def store(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value by key."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored values."""
        pass


class MemoryStorage(Storage):
    """In-memory storage with LRU eviction and TTL support."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._data: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def store(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL."""
        # Clean expired entries first
        self._clean_expired()

        # LRU eviction if at capacity
        if len(self._data) >= self.max_size and key not in self._data:
            self._data.popitem(last=False)  # Remove oldest

        # Store with expiration time
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        self._data[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }

        # Move to end (most recently used)
        self._data.move_to_end(key)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        if key not in self._data:
            return None

        entry = self._data[key]

        # Check expiration
        if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
            del self._data[key]
            return None

        # Move to end (most recently used)
        self._data.move_to_end(key)
        return entry["value"]

    def delete(self, key: str) -> None:
        """Delete a value by key."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Clear all stored values."""
        self._data.clear()

    def _clean_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._data.items()
            if entry["expires_at"] is not None and current_time > entry["expires_at"]
        ]
        for key in expired_keys:
            del self._data[key]

    def size(self) -> int:
        """Get current number of stored items."""
        self._clean_expired()
        return len(self._data)

    def stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        self._clean_expired()
        return {
            "size": len(self._data),
            "max_size": self.max_size,
            "oldest_key": next(iter(self._data)) if self._data else None,
            "newest_key": next(reversed(self._data)) if self._data else None,
        }
