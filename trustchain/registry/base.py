"""Base trust registry interface for TrustChain."""

import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from trustchain.core.models import KeyMetadata, SignatureAlgorithm
from trustchain.utils.exceptions import KeyNotFoundError, RegistryError


class TrustRegistry(ABC):
    """Abstract base class for trust registries."""

    def __init__(self, namespace: str = "trustchain"):
        self.namespace = namespace
        self._started = False

    # Lifecycle methods

    @abstractmethod
    async def start(self) -> None:
        """Initialize the trust registry."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Shutdown the trust registry."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check registry health status."""
        pass

    # Key management methods

    @abstractmethod
    async def register_key(self, key_metadata: KeyMetadata) -> None:
        """Register a new key in the registry."""
        pass

    @abstractmethod
    async def get_key(self, key_id: str) -> Optional[KeyMetadata]:
        """Retrieve key metadata by ID."""
        pass

    @abstractmethod
    async def update_key(self, key_metadata: KeyMetadata) -> None:
        """Update existing key metadata."""
        pass

    @abstractmethod
    async def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> None:
        """Revoke a key."""
        pass

    @abstractmethod
    async def list_keys(
        self,
        tool_id: Optional[str] = None,
        algorithm: Optional[SignatureAlgorithm] = None,
        valid_only: bool = True,
    ) -> List[KeyMetadata]:
        """List keys with optional filtering."""
        pass

    # Tool management methods

    @abstractmethod
    async def register_tool(self, tool_id: str, metadata: Dict[str, Any]) -> None:
        """Register a tool in the registry."""
        pass

    @abstractmethod
    async def get_tool_keys(self, tool_id: str) -> List[KeyMetadata]:
        """Get all keys for a specific tool."""
        pass

    @abstractmethod
    async def get_tool_metadata(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool."""
        pass

    # Search and discovery methods

    @abstractmethod
    async def search_keys(self, query: Dict[str, Any]) -> List[KeyMetadata]:
        """Search keys based on query parameters."""
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        pass

    # Streaming and bulk operations

    @abstractmethod
    async def stream_keys(
        self, batch_size: int = 100
    ) -> AsyncIterator[List[KeyMetadata]]:
        """Stream all keys in batches."""
        pass

    @abstractmethod
    async def bulk_register_keys(self, keys: List[KeyMetadata]) -> Dict[str, Any]:
        """Register multiple keys in a single operation."""
        pass

    # Utility methods (with default implementations)

    def is_started(self) -> bool:
        """Check if registry is started."""
        return self._started

    def validate_key_metadata(self, key_metadata: KeyMetadata) -> None:
        """Validate key metadata before operations."""
        if not key_metadata.key_id:
            raise RegistryError("Key ID is required", operation="validate")

        if not key_metadata.public_key:
            raise RegistryError("Public key is required", operation="validate")

        if not key_metadata.tool_id:
            raise RegistryError("Tool ID is required", operation="validate")

        # Validate key is not expired at creation time
        now = int(time.time() * 1000)
        if key_metadata.valid_until and key_metadata.valid_until <= now:
            raise RegistryError("Key is already expired", operation="validate")

        if key_metadata.valid_from > now:
            raise RegistryError("Key valid_from is in the future", operation="validate")

    async def get_valid_key(self, key_id: str) -> KeyMetadata:
        """Get a key and ensure it's valid."""
        key_metadata = await self.get_key(key_id)

        if not key_metadata:
            raise KeyNotFoundError(key_id)

        if not key_metadata.is_valid:
            raise RegistryError(
                f"Key is not valid: {key_metadata.revocation_reason or 'expired'}",
                operation="get_valid_key",
            )

        return key_metadata

    async def increment_key_usage(self, key_id: str) -> None:
        """Increment usage count for a key."""
        key_metadata = await self.get_key(key_id)
        if key_metadata:
            key_metadata.usage_count += 1
            key_metadata.last_used = int(time.time() * 1000)
            await self.update_key(key_metadata)

    async def get_keys_by_tool(
        self, tool_id: str, valid_only: bool = True
    ) -> List[KeyMetadata]:
        """Get all keys for a tool."""
        return await self.list_keys(tool_id=tool_id, valid_only=valid_only)

    async def cleanup_expired_keys(self) -> int:
        """Remove expired keys from registry."""
        all_keys = await self.list_keys(valid_only=False)
        expired_count = 0

        for key in all_keys:
            if not key.is_valid and key.valid_until:
                # Key has expired (not just revoked)
                now = int(time.time() * 1000)
                if key.valid_until <= now:
                    await self.revoke_key(key.key_id, "Automatic expiration")
                    expired_count += 1

        return expired_count


class CachedTrustRegistry(TrustRegistry):
    """Trust registry with caching capabilities."""

    def __init__(self, backend: TrustRegistry, cache_ttl: int = 3600):
        super().__init__(backend.namespace)
        self.backend = backend
        self.cache_ttl = cache_ttl
        self._key_cache: Dict[str, tuple[KeyMetadata, float]] = {}
        self._tool_cache: Dict[str, tuple[Dict[str, Any], float]] = {}

    async def start(self) -> None:
        """Start the backend registry."""
        await self.backend.start()
        self._started = True

    async def stop(self) -> None:
        """Stop the backend registry."""
        await self.backend.stop()
        self._started = False

    async def health_check(self) -> Dict[str, Any]:
        """Check backend health and cache stats."""
        backend_health = await self.backend.health_check()
        return {
            **backend_health,
            "cache": {
                "key_cache_size": len(self._key_cache),
                "tool_cache_size": len(self._tool_cache),
                "cache_ttl": self.cache_ttl,
            },
        }

    def _is_cache_valid(self, cached_at: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - cached_at < self.cache_ttl

    async def get_key(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key with caching."""
        # Check cache first
        if key_id in self._key_cache:
            key_metadata, cached_at = self._key_cache[key_id]
            if self._is_cache_valid(cached_at):
                return key_metadata
            else:
                # Remove expired cache entry
                del self._key_cache[key_id]

        # Fetch from backend
        key_metadata = await self.backend.get_key(key_id)

        # Cache the result (even if None)
        if key_metadata:
            self._key_cache[key_id] = (key_metadata, time.time())

        return key_metadata

    async def register_key(self, key_metadata: KeyMetadata) -> None:
        """Register key and update cache."""
        await self.backend.register_key(key_metadata)
        # Update cache
        self._key_cache[key_metadata.key_id] = (key_metadata, time.time())

    async def update_key(self, key_metadata: KeyMetadata) -> None:
        """Update key and cache."""
        await self.backend.update_key(key_metadata)
        # Update cache
        self._key_cache[key_metadata.key_id] = (key_metadata, time.time())

    async def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> None:
        """Revoke key and invalidate cache."""
        await self.backend.revoke_key(key_id, reason)
        # Remove from cache to force refresh
        self._key_cache.pop(key_id, None)

    async def get_tool_metadata(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool metadata with caching."""
        # Check cache first
        if tool_id in self._tool_cache:
            metadata, cached_at = self._tool_cache[tool_id]
            if self._is_cache_valid(cached_at):
                return metadata
            else:
                del self._tool_cache[tool_id]

        # Fetch from backend
        metadata = await self.backend.get_tool_metadata(tool_id)

        # Cache the result
        if metadata:
            self._tool_cache[tool_id] = (metadata, time.time())

        return metadata

    async def register_tool(self, tool_id: str, metadata: Dict[str, Any]) -> None:
        """Register tool and update cache."""
        await self.backend.register_tool(tool_id, metadata)
        self._tool_cache[tool_id] = (metadata, time.time())

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._key_cache.clear()
        self._tool_cache.clear()

    # Delegate all other methods to backend

    async def list_keys(
        self,
        tool_id: Optional[str] = None,
        algorithm: Optional[SignatureAlgorithm] = None,
        valid_only: bool = True,
    ) -> List[KeyMetadata]:
        return await self.backend.list_keys(tool_id, algorithm, valid_only)

    async def get_tool_keys(self, tool_id: str) -> List[KeyMetadata]:
        return await self.backend.get_tool_keys(tool_id)

    async def search_keys(self, query: Dict[str, Any]) -> List[KeyMetadata]:
        return await self.backend.search_keys(query)

    async def get_statistics(self) -> Dict[str, Any]:
        backend_stats = await self.backend.get_statistics()
        return {
            **backend_stats,
            "cache_stats": {
                "key_cache_hits": len(self._key_cache),
                "tool_cache_hits": len(self._tool_cache),
            },
        }

    async def stream_keys(
        self, batch_size: int = 100
    ) -> AsyncIterator[List[KeyMetadata]]:
        async for batch in self.backend.stream_keys(batch_size):
            yield batch

    async def bulk_register_keys(self, keys: List[KeyMetadata]) -> Dict[str, Any]:
        result = await self.backend.bulk_register_keys(keys)

        # Update cache for successfully registered keys
        for key in keys:
            self._key_cache[key.key_id] = (key, time.time())

        return result
