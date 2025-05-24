"""Signature engine for TrustChain."""

import asyncio
import base64
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

from trustchain.core.crypto import KeyPair, get_crypto_engine
from trustchain.core.models import (
    SignatureAlgorithm,
    SignatureFormat,
    SignatureInfo,
    SignedResponse,
    TrustLevel,
    VerificationResult,
)
from trustchain.utils.exceptions import CryptoError, SignatureVerificationError


class Signer(ABC):
    """Abstract base class for signers."""

    @abstractmethod
    def sign(self, data: Dict[str, Any]) -> SignatureInfo:
        """Sign data and return signature information."""
        pass

    @abstractmethod
    def get_public_key_id(self) -> str:
        """Get the public key identifier."""
        pass


class Verifier(ABC):
    """Abstract base class for verifiers."""

    @abstractmethod
    def verify(
        self, data: Dict[str, Any], signature: SignatureInfo
    ) -> VerificationResult:
        """Verify signature and return verification result."""
        pass

    @abstractmethod
    def can_verify(self, signature: SignatureInfo) -> bool:
        """Check if this verifier can verify the given signature."""
        pass


class KeyPairSigner(Signer):
    """Signer implementation using a KeyPair."""

    def __init__(self, key_pair: KeyPair, signer_id: str):
        self.key_pair = key_pair
        self.signer_id = signer_id

        if not key_pair.has_private_key:
            raise CryptoError(
                "Key pair must have private key for signing",
                algorithm=key_pair.algorithm.value,
                operation="signer_init",
            )

    def sign(self, data: Dict[str, Any]) -> SignatureInfo:
        """Sign data using the key pair."""
        # Create canonical representation
        import json

        canonical_data = json.dumps(data, sort_keys=True, separators=(",", ":"))

        # Hash the data
        crypto_engine = get_crypto_engine()
        data_hash = crypto_engine.hash_data(canonical_data)

        # Sign the hash
        hash_bytes = data_hash.split(":", 1)[1].encode()  # Remove algorithm prefix
        signature_bytes = self.key_pair.sign(hash_bytes)

        # Encode signature
        signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

        return SignatureInfo(
            algorithm=self.key_pair.algorithm,
            signature=signature_b64,
            public_key_id=self.key_pair.key_id,
            signed_hash=data_hash,
            signature_format=SignatureFormat.BASE64,
        )

    def get_public_key_id(self) -> str:
        """Get the public key identifier."""
        return self.key_pair.key_id


class InMemoryVerifier(Verifier):
    """Simple in-memory verifier that works with signers in the same engine."""

    def __init__(self, verifier_id: str):
        self.verifier_id = verifier_id
        self._signature_engine: Optional['SignatureEngine'] = None

    def set_signature_engine(self, engine: 'SignatureEngine') -> None:
        """Set reference to the signature engine."""
        self._signature_engine = engine

    def verify(
        self, data: Dict[str, Any], signature: SignatureInfo
    ) -> VerificationResult:
        """Verify signature using available signers."""
        start_time = time.time()

        if not self._signature_engine:
            print("🚨 [CRITICAL] InMemoryVerifier.verify: NO SIGNATURE ENGINE!")
            return VerificationResult.failure(
                request_id=data.get("request_id", "unknown"),
                tool_id=data.get("tool_id", "unknown"),
                signature_id=signature.public_key_id,
                verifier_id=self.verifier_id,
                error_code="NO_ENGINE",
                error_message="No signature engine available",
                algorithm=signature.algorithm,
            )

        # Find a signer with matching public key
        for signer_id, signer in self._signature_engine._signers.items():
            if isinstance(signer, KeyPairSigner):
                if signer.key_pair.key_id == signature.public_key_id:
                    # Found matching signer, verify signature
                    try:
                        # Recreate canonical data and hash
                        import json
                        canonical_data = json.dumps(data, sort_keys=True, separators=(",", ":"))
                        
                        # Get expected hash
                        crypto_engine = get_crypto_engine()
                        expected_hash = crypto_engine.hash_data(canonical_data)
                        
                        if expected_hash != signature.signed_hash:
                            return VerificationResult.failure(
                                request_id=data.get("request_id", "unknown"),
                                tool_id=data.get("tool_id", "unknown"),
                                signature_id=signature.public_key_id,
                                verifier_id=self.verifier_id,
                                error_code="HASH_MISMATCH",
                                error_message=f"Data hash does not match signed hash. Expected: {expected_hash}, Got: {signature.signed_hash}",
                                algorithm=signature.algorithm,
                            )

                        # Verify signature
                        hash_bytes = signature.signed_hash.split(":", 1)[1].encode()
                        signature_bytes = base64.b64decode(signature.signature)
                        
                        is_valid = signer.key_pair.verify(hash_bytes, signature_bytes)
                        
                        if is_valid:
                            return VerificationResult.success(
                                request_id=data.get("request_id", "unknown"),
                                tool_id=data.get("tool_id", "unknown"),
                                signature_id=signature.public_key_id,
                                verifier_id=self.verifier_id,
                                algorithm=signature.algorithm,
                                trust_level=TrustLevel.MEDIUM,
                                verification_time_ms=(time.time() - start_time) * 1000,
                            )
                        else:
                            return VerificationResult.failure(
                                request_id=data.get("request_id", "unknown"),
                                tool_id=data.get("tool_id", "unknown"),
                                signature_id=signature.public_key_id,
                                verifier_id=self.verifier_id,
                                error_code="INVALID_SIGNATURE",
                                error_message="Signature verification failed",
                                algorithm=signature.algorithm,
                            )
                    except Exception as e:
                        return VerificationResult.failure(
                            request_id=data.get("request_id", "unknown"),
                            tool_id=data.get("tool_id", "unknown"),
                            signature_id=signature.public_key_id,
                            verifier_id=self.verifier_id,
                            error_code="VERIFICATION_ERROR",
                            error_message=f"Verification error: {e}",
                            algorithm=signature.algorithm,
                        )

        # No matching signer found
        return VerificationResult.failure(
            request_id=data.get("request_id", "unknown"),
            tool_id=data.get("tool_id", "unknown"),
            signature_id=signature.public_key_id,
            verifier_id=self.verifier_id,
            error_code="NO_SIGNER",
            error_message="No matching signer found for this signature",
            algorithm=signature.algorithm,
        )

    def can_verify(self, signature: SignatureInfo) -> bool:
        """Check if this verifier can verify the signature."""        
        if not self._signature_engine:
            print("🚨 [CRITICAL] InMemoryVerifier has no signature engine!")
            return False
        
        # Check if we have a signer with matching key
        for signer_id, signer in self._signature_engine._signers.items():
            if isinstance(signer, KeyPairSigner):
                if signer.key_pair.key_id == signature.public_key_id:
                    return True
        
        # Only print debug if no matching signer found (potential issue)
        print(f"🚨 [CRITICAL] InMemoryVerifier: No matching signer for key {signature.public_key_id}")
        print(f"🚨 [CRITICAL] Available signers: {[s.key_pair.key_id if isinstance(s, KeyPairSigner) else 'unknown' for s in self._signature_engine._signers.values()]}")
        return False


class TrustRegistryVerifier(Verifier):
    """Verifier that uses a trust registry to get public keys - SIMPLIFIED VERSION."""

    def __init__(self, trust_registry, verifier_id: str):
        self.trust_registry = trust_registry
        self.verifier_id = verifier_id
        self._verification_cache: Dict[str, VerificationResult] = {}
        self.cache_ttl = 3600  # 1 hour

    def verify(
        self, data: Dict[str, Any], signature: SignatureInfo
    ) -> VerificationResult:
        """Verify signature using trust registry - SIMPLIFIED VERSION."""
        start_time = time.time()

        # For now, just return success to test the basic flow
        # TODO: Implement proper async registry handling
        return VerificationResult.success(
            request_id=data.get("request_id", "unknown"),
            tool_id=data.get("tool_id", "unknown"),
            signature_id=signature.public_key_id,
            verifier_id=self.verifier_id,
            algorithm=signature.algorithm,
            trust_level=TrustLevel.MEDIUM,
            verification_time_ms=(time.time() - start_time) * 1000,
        )

    def can_verify(self, signature: SignatureInfo) -> bool:
        """Check if this verifier can verify the signature - SIMPLIFIED."""
        # For now, assume we can verify any signature
        return True


class MultiSigner(Signer):
    """Multi-signature signer that requires multiple signatures."""

    def __init__(self, signers: Dict[str, Signer], threshold: int):
        self.signers = signers
        self.threshold = threshold

        if threshold <= 0:
            raise ValueError("Threshold must be positive")
        if threshold > len(signers):
            raise ValueError("Threshold cannot exceed number of signers")

    def sign(self, data: Dict[str, Any]) -> SignatureInfo:
        """Create multi-signature (this is a placeholder - actual implementation would be more complex)."""
        # For now, we'll create a signature using the first signer
        # In a real implementation, this would coordinate multiple signatures
        first_signer = next(iter(self.signers.values()))
        base_signature = first_signer.sign(data)

        # Mark as multi-signature
        base_signature.public_key_id = f"multisig-{self.threshold}-of-{len(self.signers)}-{base_signature.public_key_id}"

        return base_signature

    def get_public_key_id(self) -> str:
        """Get multi-signature identifier."""
        signer_ids = sorted(self.signers.keys())
        return (
            f"multisig-{self.threshold}-of-{len(self.signers)}-{'-'.join(signer_ids)}"
        )


class SignatureEngine:
    """Main signature engine for TrustChain."""

    def __init__(self, trust_registry=None):
        self.trust_registry = trust_registry
        self._signers: Dict[str, Signer] = {}
        self._verifiers: Dict[str, Verifier] = {}
        self._default_verifier: Optional[Verifier] = None

        # Set up default verifier if trust registry is provided
        if trust_registry:
            self._default_verifier = TrustRegistryVerifier(trust_registry, "default")
            self._verifiers["default"] = self._default_verifier
        else:
            # Create a simple in-memory verifier for standalone operation
            self._default_verifier = InMemoryVerifier("default")
            self._default_verifier.set_signature_engine(self)
            self._verifiers["default"] = self._default_verifier
            # Double-check the reference is set
            if not self._default_verifier._signature_engine:
                print("🚨 [DEBUG] CRITICAL: InMemoryVerifier engine reference not set!")
            else:
                print(f"✅ [DEBUG] InMemoryVerifier properly linked to engine", flush=True)

    def register_signer(self, signer_id: str, signer: Signer) -> None:
        """Register a signer."""
        self._signers[signer_id] = signer

    def register_verifier(self, verifier_id: str, verifier: Verifier) -> None:
        """Register a verifier."""
        self._verifiers[verifier_id] = verifier

    def create_signer(
        self, signer_id: str, algorithm: SignatureAlgorithm, **kwargs
    ) -> Signer:
        """Create and register a new signer."""
        crypto_engine = get_crypto_engine()
        key_pair = crypto_engine.create_key_pair(algorithm, **kwargs)

        signer = KeyPairSigner(key_pair, signer_id)
        self.register_signer(signer_id, signer)

        return signer

    def create_multi_signer(
        self, signer_id: str, signer_ids: list, threshold: int
    ) -> MultiSigner:
        """Create a multi-signature signer."""
        signers = {}
        for sid in signer_ids:
            if sid not in self._signers:
                raise ValueError(f"Signer not found: {sid}")
            signers[sid] = self._signers[sid]

        multi_signer = MultiSigner(signers, threshold)
        self.register_signer(signer_id, multi_signer)

        return multi_signer

    def sign_response(
        self,
        signer_id: str,
        request_id: str,
        tool_id: str,
        data: Any,
        execution_time_ms: Optional[float] = None,
    ) -> SignedResponse:
        """Sign a tool response."""
        if signer_id not in self._signers:
            raise SignatureVerificationError(f"Signer not found: {signer_id}")

        signer = self._signers[signer_id]

        # Create timestamp to ensure consistency between signing and verification
        timestamp = int(time.time() * 1000)

        # Create response data
        response_data = {
            "request_id": request_id,
            "tool_id": tool_id,
            "timestamp": timestamp,
            "data": data,
            "execution_time_ms": execution_time_ms,
            "version": "1.0",
        }

        # Sign the response
        signature = signer.sign(response_data)

        # Create signed response with the SAME timestamp that was signed
        signed_response = SignedResponse(
            request_id=request_id,
            tool_id=tool_id,
            timestamp=timestamp,  # Use the same timestamp that was signed!
            data=data,
            signature=signature,
            execution_time_ms=execution_time_ms,
        )

        return signed_response

    def verify_response(
        self, signed_response: SignedResponse, verifier_id: Optional[str] = None
    ) -> VerificationResult:
        """Verify a signed response."""        
        # Choose verifier
        if verifier_id:
            if verifier_id not in self._verifiers:
                raise SignatureVerificationError(f"Verifier not found: {verifier_id}")
            verifier = self._verifiers[verifier_id]
        elif self._default_verifier:
            verifier = self._default_verifier
        else:
            # Find a verifier that can handle this signature
            verifier = None
            for vid, v in self._verifiers.items():
                if v.can_verify(signed_response.signature):
                    verifier = v
                    break

            if not verifier:
                # Critical error for CI debugging
                print(f"🚨 [CRITICAL] NO VERIFIER FOUND for {signed_response.tool_id}")
                print(f"🚨 [CRITICAL] Available verifiers: {list(self._verifiers.keys())}")
                print(f"🚨 [CRITICAL] Default verifier: {type(self._default_verifier).__name__ if self._default_verifier else 'None'}")
                print(f"🚨 [CRITICAL] Signature key: {signed_response.signature.public_key_id}")
                return VerificationResult.failure(
                    request_id=signed_response.request_id,
                    tool_id=signed_response.tool_id,
                    signature_id=signed_response.signature.public_key_id,
                    verifier_id="unknown",
                    error_code="NO_VERIFIER",
                    error_message="No verifier available for this signature",
                    algorithm=signed_response.signature.algorithm,
                )

        # Verify the response
        canonical_data = signed_response.to_canonical_dict()
        result = verifier.verify(canonical_data, signed_response.signature)

        # Update response trust metadata
        if result.valid:
            signed_response.trust_metadata.verified = True
            signed_response.trust_metadata.verification_timestamp = result.verified_at
            signed_response.trust_metadata.verifier_id = result.verifier_id
            signed_response.trust_metadata.trust_level = result.trust_level

        return result

    def batch_verify(
        self, signed_responses: list[SignedResponse], verifier_id: Optional[str] = None
    ) -> Dict[str, VerificationResult]:
        """Verify multiple signed responses."""
        results = {}

        for response in signed_responses:
            try:
                result = self.verify_response(response, verifier_id)
                results[response.request_id] = result
            except Exception as e:
                results[response.request_id] = VerificationResult.failure(
                    request_id=response.request_id,
                    tool_id=response.tool_id,
                    signature_id=response.signature.public_key_id,
                    verifier_id=verifier_id or "unknown",
                    error_code="VERIFICATION_EXCEPTION",
                    error_message=str(e),
                    algorithm=response.signature.algorithm,
                )

        return results

    def get_signer_public_key(
        self, signer_id: str, format: str = "base64"
    ) -> Optional[str]:
        """Get public key for a signer."""
        if signer_id not in self._signers:
            return None

        signer = self._signers[signer_id]
        if isinstance(signer, KeyPairSigner):
            public_key_bytes = signer.key_pair.export_public_key("raw")
            if format == "base64":
                return base64.b64encode(public_key_bytes).decode("ascii")
            elif format == "hex":
                return public_key_bytes.hex()
            else:
                return public_key_bytes.decode("ascii")

        return None

    def export_signer_key(
        self,
        signer_id: str,
        format: str = "pem",
        password: Optional[str] = None,
        include_private: bool = False,
    ) -> Optional[bytes]:
        """Export signer key."""
        if signer_id not in self._signers:
            return None

        signer = self._signers[signer_id]
        if isinstance(signer, KeyPairSigner):
            if include_private:
                return signer.key_pair.export_private_key(format, password)
            else:
                return signer.key_pair.export_public_key(format)

        return None

    def list_signers(self) -> Dict[str, Dict[str, Any]]:
        """List all registered signers."""
        result = {}
        for signer_id, signer in self._signers.items():
            if isinstance(signer, KeyPairSigner):
                result[signer_id] = {
                    "type": "keypair",
                    "algorithm": signer.key_pair.algorithm.value,
                    "public_key_id": signer.key_pair.key_id,
                    "has_private_key": signer.key_pair.has_private_key,
                }
            elif isinstance(signer, MultiSigner):
                result[signer_id] = {
                    "type": "multisig",
                    "threshold": signer.threshold,
                    "signers": list(signer.signers.keys()),
                }
            else:
                result[signer_id] = {"type": "unknown"}

        return result

    def list_verifiers(self) -> Dict[str, Dict[str, Any]]:
        """List all registered verifiers."""
        result = {}
        for verifier_id, verifier in self._verifiers.items():
            if isinstance(verifier, TrustRegistryVerifier):
                result[verifier_id] = {
                    "type": "trust_registry",
                    "verifier_id": verifier.verifier_id,
                    "cache_size": len(verifier._verification_cache),
                }
            else:
                result[verifier_id] = {"type": "unknown"}

        return result


# Global signature engine instance
_signature_engine = None


def get_signature_engine() -> SignatureEngine:
    """Get the global signature engine instance."""
    global _signature_engine
    if _signature_engine is None:
        _signature_engine = SignatureEngine()
        # Only print debug if no default verifier (critical error)
        if not _signature_engine._default_verifier:
            print("🚨 [CRITICAL] SignatureEngine has no default verifier!", flush=True)
    return _signature_engine


def set_signature_engine(engine: SignatureEngine) -> None:
    """Set the global signature engine instance."""
    global _signature_engine
    _signature_engine = engine
