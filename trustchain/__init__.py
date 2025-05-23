"""
TrustChain - Cryptographically signed AI tool responses for preventing hallucinations.

This library provides a comprehensive framework for creating verifiable AI tool responses
using cryptographic signatures, replay protection, and distributed trust registries.
"""

__version__ = "0.1.0"
__author__ = "TrustChain Contributors"
__email__ = "info@trustchain.dev"

# Core imports
from trustchain.core.models import (
    SignedResponse,
    TrustMetadata,
    ChainLink,
    VerificationResult,
    SignatureAlgorithm,
    TrustLevel,
    KeyMetadata,
)
from trustchain.core.signatures import SignatureEngine, get_signature_engine
from trustchain.core.crypto import KeyPair, Ed25519KeyPair, get_crypto_engine
from trustchain.core.nonce import NonceManager

# Tool decorators and builders
from trustchain.tools.decorators import TrustedTool, trusted_tool
from trustchain.tools.base import BaseTrustedTool

# Registry backends
from trustchain.registry.memory import MemoryRegistry
from trustchain.registry.base import TrustRegistry

# Optional tool imports (may not exist yet)
try:
    from trustchain.tools.ai_agent import TrustedAIAgent
except ImportError:
    TrustedAIAgent = None

try:
    from trustchain.tools.chain import ChainBuilder
except ImportError:
    ChainBuilder = None

# Utilities
from trustchain.utils.exceptions import (
    TrustChainError,
    SignatureVerificationError,
    NonceReplayError,
    KeyNotFoundError,
    ChainIntegrityError,
)

# Optional imports (fail gracefully if dependencies not installed)
try:
    from trustchain.registry.redis import RedisRegistry
except ImportError:
    RedisRegistry = None

try:
    from trustchain.registry.kafka import KafkaRegistry
except ImportError:
    KafkaRegistry = None

try:
    from trustchain.integrations.langchain import make_langchain_tool
except ImportError:
    make_langchain_tool = None

try:
    from trustchain.integrations.openai import OpenAITrustedFunction
except ImportError:
    OpenAITrustedFunction = None

try:
    from trustchain.monitoring.metrics import PrometheusMetrics
except ImportError:
    PrometheusMetrics = None

# Public API
__all__ = [
    # Core classes
    "SignedResponse",
    "TrustMetadata", 
    "ChainLink",
    "VerificationResult",
    "SignatureAlgorithm",
    "TrustLevel",
    "KeyMetadata",
    "SignatureEngine",
    "get_signature_engine",
    "KeyPair",
    "Ed25519KeyPair",
    "get_crypto_engine",
    "NonceManager",
    
    # Tool framework
    "TrustedTool",
    "trusted_tool",
    "BaseTrustedTool",
    
    # Registry backends
    "TrustRegistry",
    "MemoryRegistry",
    "RedisRegistry",  # May be None
    "KafkaRegistry",  # May be None
    
    # Integrations
    "make_langchain_tool",  # May be None
    "OpenAITrustedFunction",  # May be None
    
    # Monitoring
    "PrometheusMetrics",  # May be None
    
    # Exceptions
    "TrustChainError",
    "SignatureVerificationError", 
    "NonceReplayError",
    "KeyNotFoundError",
    "ChainIntegrityError",
]

# Version info
VERSION_INFO = tuple(map(int, __version__.split(".")))

def get_version() -> str:
    """Get the current version string."""
    return __version__

def check_dependencies() -> dict:
    """Check which optional dependencies are available."""
    return {
        "redis": RedisRegistry is not None,
        "kafka": KafkaRegistry is not None,
        "langchain": make_langchain_tool is not None,
        "openai": OpenAITrustedFunction is not None,
        "monitoring": PrometheusMetrics is not None,
    } 