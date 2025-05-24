"""Configuration for TrustChain v2."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TrustChainConfig:
    """Main configuration for TrustChain."""

    # Crypto settings
    algorithm: str = "ed25519"

    # Cache settings
    cache_ttl: int = 3600  # 1 hour
    max_cached_responses: int = 100

    # Security settings
    enable_nonce: bool = True
    nonce_ttl: int = 300  # 5 minutes

    # Performance settings
    enable_cache: bool = True

    # Hallucination detection patterns
    tool_claim_patterns: List[str] = field(
        default_factory=lambda: [
            r"I\s+(?:called|used|executed|ran|invoked)",
            r"I\s+(?:got|obtained|received|fetched)",
            r"API\s+(?:returned|responded|gave)",
            r"tool\s+(?:returned|gave|showed)",
            r"transaction\s+(?:id|number)",
            r"result\s+(?:is|was|shows)",
        ]
    )

    # Storage backend
    storage_backend: str = "memory"  # Options: memory, redis
    redis_url: Optional[str] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.algorithm not in ["ed25519", "rsa", "ecdsa"]:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")

        if self.cache_ttl <= 0:
            raise ValueError("cache_ttl must be positive")

        if self.max_cached_responses <= 0:
            raise ValueError("max_cached_responses must be positive")
