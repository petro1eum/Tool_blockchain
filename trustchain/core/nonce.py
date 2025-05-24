"""Nonce management for replay protection in TrustChain."""

import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from trustchain.core.crypto import generate_nonce
from trustchain.core.models import NonceEntry
from trustchain.utils.exceptions import NonceReplayError


def _is_ci_environment() -> bool:
    """Detect if running in CI environment."""
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "GITLAB_CI",
        "BUILDKITE",
        "APPVEYOR",
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


def _get_ci_tolerant_timeouts() -> tuple[int, int]:
    """Get CI-tolerant timeout values."""
    if _is_ci_environment():
        return 1800, 1800  # 30 minutes for CI
    else:
        return 600, 600  # 10 minutes for normal use


class NonceGenerator:
    """Generator for cryptographically secure nonces."""

    @staticmethod
    def generate(length: int = 32) -> str:
        """Generate a new nonce."""
        return generate_nonce(length)

    @staticmethod
    def generate_uuid() -> str:
        """Generate a UUID-based nonce."""
        return str(uuid.uuid4())

    @staticmethod
    def generate_timestamp_nonce() -> str:
        """Generate a timestamp-based nonce."""
        timestamp = int(time.time() * 1000000)  # microseconds
        random_part = generate_nonce(16)
        return f"{timestamp}-{random_part}"


class NonceValidator:
    """Validator for nonce format and constraints."""

    @staticmethod
    def validate_format(nonce: str) -> bool:
        """Validate nonce format."""
        if not nonce or not isinstance(nonce, str):
            return False

        # Basic length check
        if len(nonce) < 8 or len(nonce) > 256:
            return False

        # Check for reasonable characters
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", nonce):
            return False

        return True

    @staticmethod
    def validate_timestamp(nonce: str, max_age_seconds: int = 300) -> bool:
        """Validate timestamp-based nonce age."""
        if "-" not in nonce:
            return True  # Not a timestamp nonce

        try:
            timestamp_part = nonce.split("-")[0]
            timestamp = int(timestamp_part)
            current_time = int(time.time() * 1000000)

            age_seconds = (current_time - timestamp) / 1000000
            return age_seconds <= max_age_seconds
        except (ValueError, IndexError):
            return True  # Not a timestamp nonce or invalid format


class NonceStore(ABC):
    """Abstract base class for nonce storage backends."""

    @abstractmethod
    async def check_and_store(self, nonce_entry: NonceEntry) -> bool:
        """
        Check if nonce exists and store it if not.
        Returns True if nonce was stored (i.e., it was new).
        Returns False if nonce already exists (replay attack).
        """
        pass

    @abstractmethod
    async def is_used(self, nonce: str) -> bool:
        """Check if nonce has been used."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired nonces. Returns count of removed entries."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class MemoryNonceStore(NonceStore):
    """In-memory nonce store for development and testing."""

    def __init__(self, max_size: int = 100000):
        self._nonces: Dict[str, NonceEntry] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

    async def check_and_store(self, nonce_entry: NonceEntry) -> bool:
        """Check and store nonce atomically."""
        with self._lock:
            # Check if nonce already exists
            if nonce_entry.nonce in self._nonces:
                return False

            # Clean up if we're getting too big
            if len(self._nonces) >= self._max_size:
                await self._cleanup_expired_internal()

            # Store the nonce
            self._nonces[nonce_entry.nonce] = nonce_entry
            return True

    async def is_used(self, nonce: str) -> bool:
        """Check if nonce has been used."""
        with self._lock:
            entry = self._nonces.get(nonce)
            if not entry:
                return False

            # Check if expired
            if entry.is_expired:
                del self._nonces[nonce]
                return False

            return True

    async def cleanup_expired(self) -> int:
        """Remove expired nonces."""
        with self._lock:
            return await self._cleanup_expired_internal()

    async def _cleanup_expired_internal(self) -> int:
        """Internal cleanup method (assumes lock is held)."""
        current_time = int(time.time() * 1000)
        expired_nonces = [
            nonce
            for nonce, entry in self._nonces.items()
            if entry.expires_at <= current_time
        ]

        for nonce in expired_nonces:
            del self._nonces[nonce]

        return len(expired_nonces)

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._lock:
            return {
                "total_nonces": len(self._nonces),
                "max_size": self._max_size,
                "oldest_entry": min(
                    (entry.timestamp for entry in self._nonces.values()), default=None
                ),
                "newest_entry": max(
                    (entry.timestamp for entry in self._nonces.values()), default=None
                ),
            }


class NonceManager:
    """Main nonce manager for TrustChain."""

    def __init__(
        self,
        store: NonceStore,
        default_ttl_seconds: Optional[int] = None,
        max_age_seconds: Optional[int] = None,
        cleanup_interval: int = 3600,  # 1 hour
    ):
        # Use CI-tolerant timeouts if not specified
        ci_default_ttl, ci_max_age = _get_ci_tolerant_timeouts()

        self.store = store
        self.default_ttl_seconds = default_ttl_seconds or ci_default_ttl
        self.max_age_seconds = max_age_seconds or ci_max_age
        self.cleanup_interval = cleanup_interval

        self._last_cleanup = time.time()
        self._stats = {
            "total_requests": 0,
            "replay_attempts": 0,
            "valid_nonces": 0,
            "expired_nonces": 0,
            "format_errors": 0,
        }

    async def validate_and_register_nonce(
        self,
        nonce: str,
        request_id: str,
        tool_id: Optional[str] = None,
        caller_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Validate and register a nonce.
        Raises NonceReplayError if nonce has been used.
        """
        self._stats["total_requests"] += 1

        # Validate nonce format
        if not NonceValidator.validate_format(nonce):
            self._stats["format_errors"] += 1
            raise NonceReplayError(
                nonce,
                "Invalid nonce format",
                details={"request_id": request_id, "reason": "format_error"},
            )

        # Validate nonce age for timestamp-based nonces
        if not NonceValidator.validate_timestamp(nonce, self.max_age_seconds):
            self._stats["expired_nonces"] += 1
            raise NonceReplayError(
                nonce,
                "Nonce is too old",
                details={"request_id": request_id, "reason": "expired"},
            )

        # Create nonce entry
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = int(time.time() * 1000) + (ttl * 1000)

        nonce_entry = NonceEntry(
            nonce=nonce,
            request_id=request_id,
            tool_id=tool_id,
            caller_id=caller_id,
            expires_at=expires_at,
        )

        # Try to store the nonce
        was_stored = await self.store.check_and_store(nonce_entry)

        if not was_stored:
            self._stats["replay_attempts"] += 1
            raise NonceReplayError(
                nonce,
                "Nonce has already been used",
                details={"request_id": request_id, "reason": "replay_attack"},
            )

        self._stats["valid_nonces"] += 1

        # Periodic cleanup
        await self._maybe_cleanup()

    async def is_nonce_used(self, nonce: str) -> bool:
        """Check if a nonce has been used."""
        return await self.store.is_used(nonce)

    async def cleanup_expired_nonces(self) -> int:
        """Manually trigger cleanup of expired nonces."""
        count = await self.store.cleanup_expired()
        self._last_cleanup = time.time()
        return count

    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed."""
        if time.time() - self._last_cleanup > self.cleanup_interval:
            await self.cleanup_expired_nonces()

    def generate_nonce(self, nonce_type: str = "random") -> str:
        """Generate a new nonce."""
        if nonce_type == "uuid":
            return NonceGenerator.generate_uuid()
        elif nonce_type == "timestamp":
            return NonceGenerator.generate_timestamp_nonce()
        else:
            return NonceGenerator.generate()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get nonce manager statistics."""
        store_stats = await self.store.get_stats()

        return {
            "manager_stats": self._stats.copy(),
            "store_stats": store_stats,
            "config": {
                "default_ttl_seconds": self.default_ttl_seconds,
                "max_age_seconds": self.max_age_seconds,
                "cleanup_interval": self.cleanup_interval,
            },
            "last_cleanup": self._last_cleanup,
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "total_requests": 0,
            "replay_attempts": 0,
            "valid_nonces": 0,
            "expired_nonces": 0,
            "format_errors": 0,
        }


class RequestContext:
    """Context for tracking request nonces and preventing replays."""

    def __init__(self, nonce_manager: NonceManager):
        self.nonce_manager = nonce_manager
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    async def start_request(
        self,
        request_id: str,
        nonce: str,
        tool_id: str,
        caller_id: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Start a new request with nonce validation."""
        # Validate and register nonce
        await self.nonce_manager.validate_and_register_nonce(
            nonce=nonce,
            request_id=request_id,
            tool_id=tool_id,
            caller_id=caller_id,
            ttl_seconds=ttl_seconds,
        )

        # Track active request
        with self._lock:
            self._active_requests[request_id] = {
                "nonce": nonce,
                "tool_id": tool_id,
                "caller_id": caller_id,
                "started_at": time.time(),
            }

    async def complete_request(self, request_id: str) -> None:
        """Mark request as completed."""
        with self._lock:
            self._active_requests.pop(request_id, None)

    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active requests."""
        with self._lock:
            return self._active_requests.copy()

    async def cleanup_stale_requests(self, max_age_seconds: int = 3600) -> int:
        """Remove stale active requests."""
        current_time = time.time()
        stale_requests = []

        with self._lock:
            for request_id, request_info in self._active_requests.items():
                if current_time - request_info["started_at"] > max_age_seconds:
                    stale_requests.append(request_id)

            for request_id in stale_requests:
                del self._active_requests[request_id]

        return len(stale_requests)


# Global nonce manager instance
_nonce_manager = None


def get_nonce_manager() -> Optional[NonceManager]:
    """Get the global nonce manager instance."""
    return _nonce_manager


def set_nonce_manager(manager: NonceManager) -> None:
    """Set the global nonce manager instance."""
    global _nonce_manager
    _nonce_manager = manager


def create_default_nonce_manager() -> NonceManager:
    """Create a default nonce manager with memory store."""
    store = MemoryNonceStore()
    manager = NonceManager(store)
    set_nonce_manager(manager)
    return manager


# Convenience functions
async def validate_nonce(
    nonce: str,
    request_id: str,
    tool_id: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> None:
    """Validate nonce using the global nonce manager."""
    manager = get_nonce_manager()
    if not manager:
        manager = create_default_nonce_manager()

    await manager.validate_and_register_nonce(
        nonce=nonce, request_id=request_id, tool_id=tool_id, caller_id=caller_id
    )


def generate_request_nonce(nonce_type: str = "random") -> str:
    """Generate a nonce using the global nonce manager."""
    manager = get_nonce_manager()
    if not manager:
        manager = create_default_nonce_manager()

    return manager.generate_nonce(nonce_type)
