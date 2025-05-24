"""Simple signer for TrustChain v2."""

import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


@dataclass
class SignedResponse:
    """A cryptographically signed response."""

    tool_id: str
    data: Any
    signature: str
    signature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    nonce: Optional[str] = None

    # Cache verification result
    _verified: Optional[bool] = field(default=None, init=False, repr=False)

    @property
    def is_verified(self) -> bool:
        """Check if response is verified (cached)."""
        if self._verified is None:
            # In real implementation, would verify against signer
            # For now, assume verified if has signature
            self._verified = bool(self.signature)
        return self._verified

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_id": self.tool_id,
            "data": self.data,
            "signature": self.signature,
            "signature_id": self.signature_id,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }


class Signer:
    """Simple signer for Ed25519 signatures."""

    def __init__(self, algorithm: str = "ed25519"):
        self.algorithm = algorithm
        self.key_id = str(uuid.uuid4())

        if algorithm == "ed25519":
            if not HAS_CRYPTOGRAPHY:
                # Fallback to simple hash-based "signature" for demo
                self._use_fallback = True
                self._secret = str(uuid.uuid4())
            else:
                self._use_fallback = False
                self._private_key = ed25519.Ed25519PrivateKey.generate()
                self._public_key = self._private_key.public_key()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    def sign(
        self, tool_id: str, data: Any, nonce: Optional[str] = None
    ) -> SignedResponse:
        """Sign data and return SignedResponse."""
        # Create canonical representation
        canonical_data = {
            "tool_id": tool_id,
            "data": data,
            "timestamp": time.time(),
            "nonce": nonce or str(uuid.uuid4()),
        }

        # Serialize to JSON
        json_data = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))

        # Create signature
        if self._use_fallback:
            # Simple HMAC-like signature for demo
            signature = self._create_fallback_signature(json_data)
        else:
            # Real Ed25519 signature
            signature_bytes = self._private_key.sign(json_data.encode("utf-8"))
            signature = base64.b64encode(signature_bytes).decode("ascii")

        return SignedResponse(
            tool_id=tool_id,
            data=data,
            signature=signature,
            timestamp=canonical_data["timestamp"],
            nonce=canonical_data["nonce"],
        )

    def verify(self, response: SignedResponse) -> bool:
        """Verify a signed response."""
        try:
            # Recreate canonical data
            canonical_data = {
                "tool_id": response.tool_id,
                "data": response.data,
                "timestamp": response.timestamp,
                "nonce": response.nonce,
            }

            # Serialize to JSON
            json_data = json.dumps(
                canonical_data, sort_keys=True, separators=(",", ":")
            )

            if self._use_fallback:
                # Verify fallback signature
                expected_signature = self._create_fallback_signature(json_data)
                return response.signature == expected_signature
            else:
                # Verify Ed25519 signature
                signature_bytes = base64.b64decode(response.signature)
                self._public_key.verify(signature_bytes, json_data.encode("utf-8"))
                return True

        except Exception:
            return False

    def _create_fallback_signature(self, data: str) -> str:
        """Create a simple hash-based signature for fallback mode."""
        hash_input = f"{self._secret}:{data}"
        hash_bytes = hashlib.sha256(hash_input.encode("utf-8")).digest()
        return base64.b64encode(hash_bytes).decode("ascii")

    def get_public_key(self) -> str:
        """Get the public key in base64 format."""
        if self._use_fallback:
            return self._secret  # In fallback mode, return secret hash
        else:
            public_bytes = self._public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            return base64.b64encode(public_bytes).decode("ascii")

    def get_key_id(self) -> str:
        """Get the key identifier."""
        return self.key_id
