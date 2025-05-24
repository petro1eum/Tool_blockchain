"""Compatibility layer for migration from v1 to v2."""

import warnings
from typing import Any, Callable, Optional

from trustchain.v2 import TrustChain, TrustChainConfig, SignedResponse

# Global instance for backward compatibility
_default_trustchain: Optional[TrustChain] = None


def get_default_trustchain() -> TrustChain:
    """Get or create default TrustChain instance."""
    global _default_trustchain
    if _default_trustchain is None:
        _default_trustchain = TrustChain()
    return _default_trustchain


def TrustedTool(
    tool_id: str,
    description: Optional[str] = None,
    registry: Optional[Any] = None,
    signature_engine: Optional[Any] = None,
    algorithm: str = "ED25519",
    trust_level: str = "MEDIUM",
    require_nonce: bool = True,
    auto_register: bool = True,
    register_globally: bool = True,
    **kwargs
) -> Callable:
    """
    Compatibility wrapper for old TrustedTool decorator.
    
    Maps old API to new TrustChain.tool() decorator.
    """
    warnings.warn(
        "TrustedTool is deprecated. Use @trustchain.tool() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Get or create TrustChain instance
    tc = get_default_trustchain()
    
    # Map old parameters to new config if needed
    if require_nonce != tc.config.enable_nonce:
        tc.config.enable_nonce = require_nonce
    
    # Return new decorator
    return tc.tool(tool_id, description=description, **kwargs)


def trusted_tool(tool_id: str, **kwargs):
    """Compatibility alias for TrustedTool."""
    return TrustedTool(tool_id, **kwargs)


# Map old classes to new ones
class MemoryRegistry:
    """Compatibility wrapper for old MemoryRegistry."""
    
    def __init__(self):
        warnings.warn(
            "MemoryRegistry is deprecated. TrustChain v2 has built-in storage.",
            DeprecationWarning,
            stacklevel=2
        )


class SignatureEngine:
    """Compatibility wrapper for old SignatureEngine."""
    
    def __init__(self, registry=None):
        warnings.warn(
            "SignatureEngine is deprecated. Use TrustChain directly.",
            DeprecationWarning,
            stacklevel=2
        )
        self._tc = get_default_trustchain()
    
    def verify_response(self, response: Any) -> Any:
        """Verify a response."""
        # Convert old response format to new if needed
        if hasattr(response, 'to_dict'):
            response_dict = response.to_dict()
            new_response = SignedResponse(**response_dict)
        else:
            new_response = response
            
        is_valid = self._tc.verify(new_response)
        
        # Return a mock VerificationResult for compatibility
        return type('VerificationResult', (), {
            'valid': is_valid,
            'algorithm_used': type('Algorithm', (), {'value': 'Ed25519'})(),
            'trust_level': type('TrustLevel', (), {'value': 'MEDIUM'})(),
            'verification_time_ms': 1.0,
        })()


def get_signature_engine() -> SignatureEngine:
    """Compatibility function for getting signature engine."""
    warnings.warn(
        "get_signature_engine() is deprecated. Use TrustChain directly.",
        DeprecationWarning,
        stacklevel=2
    )
    return SignatureEngine()


# Enum compatibility
class TrustLevel:
    """Compatibility enum for trust levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignatureAlgorithm:
    """Compatibility enum for algorithms."""
    ED25519 = "Ed25519"
    RSA_PSS = "RSA-PSS"
    ECDSA = "ECDSA"


# Export compatibility symbols
__all__ = [
    "TrustedTool",
    "trusted_tool",
    "MemoryRegistry",
    "SignatureEngine",
    "get_signature_engine",
    "TrustLevel",
    "SignatureAlgorithm",
] 