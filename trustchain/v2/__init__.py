"""
TrustChain v2 - Simplified API for cryptographically signed AI tool responses.

This is a complete rewrite focusing on simplicity and performance.
"""

from .config import TrustChainConfig
from .core import TrustChain
from .signer import SignedResponse
from .storage import MemoryStorage, Storage

__version__ = "2.0.0"

__all__ = [
    "TrustChain",
    "TrustChainConfig", 
    "SignedResponse",
    "Storage",
    "MemoryStorage",
]

# Convenience function for quick start
def create_trustchain(**config_kwargs) -> TrustChain:
    """Create a TrustChain instance with custom configuration."""
    config = TrustChainConfig(**config_kwargs)
    return TrustChain(config) 