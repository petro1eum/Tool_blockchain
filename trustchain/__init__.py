"""
TrustChain - Cryptographically signed AI tool responses for preventing hallucinations.

This library provides a comprehensive framework for creating verifiable AI tool responses
using cryptographic signatures, replay protection, and distributed trust registries.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher
"""

# Windows compatibility fix - must be before any asyncio imports
import asyncio
import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

print("🔧 [IMPORT DEBUG] TrustChain __init__.py starting to load", flush=True)

__version__ = "0.1.0"
__author__ = "Ed Cherednik"
__email__ = "edcherednik@gmail.com"

from trustchain.core.crypto import Ed25519KeyPair, KeyPair, get_crypto_engine

# Core imports
from trustchain.core.models import (
    ChainLink,
    KeyMetadata,
    SignatureAlgorithm,
    SignedResponse,
    TrustLevel,
    TrustMetadata,
    VerificationResult,
)
from trustchain.core.nonce import NonceManager
from trustchain.core.signatures import SignatureEngine, get_signature_engine
from trustchain.registry.base import TrustRegistry

# Registry backends
from trustchain.registry.memory import MemoryRegistry
from trustchain.tools.base import BaseTrustedTool

# Tool decorators and builders
from trustchain.tools.decorators import TrustedTool, trusted_tool

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
    ChainIntegrityError,
    KeyNotFoundError,
    NonceReplayError,
    SignatureVerificationError,
    TrustChainError,
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


print(
    "🔧 [IMPORT DEBUG] TrustChain __init__.py import completed successfully", flush=True
)
