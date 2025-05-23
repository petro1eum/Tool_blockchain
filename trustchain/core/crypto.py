"""Cryptographic engine for TrustChain."""

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Union

import nacl.encoding
import nacl.signing
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from trustchain.core.models import SignatureAlgorithm, SignatureFormat
from trustchain.utils.exceptions import CryptoError


class KeyPair(ABC):
    """Abstract base class for cryptographic key pairs."""

    def __init__(self, algorithm: SignatureAlgorithm):
        self.algorithm = algorithm
        self._private_key: Any = None
        self._public_key: Any = None
        self._key_id: Optional[str] = None

    @abstractmethod
    def generate(self) -> None:
        """Generate a new key pair."""
        pass

    @abstractmethod
    def sign(self, data: bytes) -> bytes:
        """Sign data with the private key."""
        pass

    @abstractmethod
    def verify(
        self, data: bytes, signature: bytes, public_key: Optional[bytes] = None
    ) -> bool:
        """Verify signature with the public key."""
        pass

    @abstractmethod
    def export_private_key(
        self, format: str = "pem", password: Optional[str] = None
    ) -> bytes:
        """Export private key in specified format."""
        pass

    @abstractmethod
    def export_public_key(self, format: str = "pem") -> bytes:
        """Export public key in specified format."""
        pass

    @abstractmethod
    def import_private_key(
        self, key_data: bytes, password: Optional[str] = None
    ) -> None:
        """Import private key from data."""
        pass

    @abstractmethod
    def import_public_key(self, key_data: bytes) -> None:
        """Import public key from data."""
        pass

    @property
    def key_id(self) -> str:
        """Get the key identifier."""
        if self._key_id is None:
            # Generate key ID from public key hash
            public_key_bytes = self.export_public_key("raw")
            key_hash = hashlib.sha256(public_key_bytes).hexdigest()[:16]
            self._key_id = f"{self.algorithm.value.lower()}-{key_hash}"
        return self._key_id

    @property
    def has_private_key(self) -> bool:
        """Check if private key is available."""
        return self._private_key is not None

    @property
    def has_public_key(self) -> bool:
        """Check if public key is available."""
        return self._public_key is not None


class Ed25519KeyPair(KeyPair):
    """Ed25519 key pair implementation using PyNaCl."""

    def __init__(self):
        super().__init__(SignatureAlgorithm.ED25519)

    def generate(self) -> None:
        """Generate a new Ed25519 key pair."""
        try:
            self._private_key = nacl.signing.SigningKey.generate()
            self._public_key = self._private_key.verify_key
        except Exception as e:
            raise CryptoError(
                f"Failed to generate Ed25519 key pair: {e}",
                algorithm="Ed25519",
                operation="generate",
            )

    def sign(self, data: bytes) -> bytes:
        """Sign data with Ed25519 private key."""
        if not self.has_private_key:
            raise CryptoError(
                "Private key not available for signing",
                algorithm="Ed25519",
                operation="sign",
            )

        try:
            signed = self._private_key.sign(data, encoder=nacl.encoding.RawEncoder)
            return signed.signature
        except Exception as e:
            raise CryptoError(
                f"Failed to sign data: {e}", algorithm="Ed25519", operation="sign"
            )

    def verify(
        self, data: bytes, signature: bytes, public_key: Optional[bytes] = None
    ) -> bool:
        """Verify Ed25519 signature."""
        try:
            if public_key:
                verify_key = nacl.signing.VerifyKey(
                    public_key, encoder=nacl.encoding.RawEncoder
                )
            else:
                if not self.has_public_key:
                    raise CryptoError(
                        "Public key not available for verification",
                        algorithm="Ed25519",
                        operation="verify",
                    )
                verify_key = self._public_key

            verify_key.verify(data, signature, encoder=nacl.encoding.RawEncoder)
            return True
        except Exception:
            return False

    def export_private_key(
        self, format: str = "pem", password: Optional[str] = None
    ) -> bytes:
        """Export Ed25519 private key."""
        if not self.has_private_key:
            raise CryptoError(
                "Private key not available",
                algorithm="Ed25519",
                operation="export_private",
            )

        try:
            if format.lower() == "raw":
                return bytes(self._private_key)
            elif format.lower() == "base64":
                return base64.b64encode(bytes(self._private_key))
            elif format.lower() == "pem":
                # Convert to cryptography format for PEM export
                crypto_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                    bytes(self._private_key)
                )
                encryption = NoEncryption()
                if password:
                    from cryptography.hazmat.primitives.serialization import (
                        BestAvailableEncryption,
                    )

                    encryption = BestAvailableEncryption(password.encode())

                return crypto_private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.PKCS8,
                    encryption_algorithm=encryption,
                )
            else:
                raise CryptoError(
                    f"Unsupported export format: {format}",
                    algorithm="Ed25519",
                    operation="export_private",
                )
        except Exception as e:
            raise CryptoError(
                f"Failed to export private key: {e}",
                algorithm="Ed25519",
                operation="export_private",
            )

    def export_public_key(self, format: str = "pem") -> bytes:
        """Export Ed25519 public key."""
        if not self.has_public_key:
            raise CryptoError(
                "Public key not available",
                algorithm="Ed25519",
                operation="export_public",
            )

        try:
            if format.lower() == "raw":
                return bytes(self._public_key)
            elif format.lower() == "base64":
                return base64.b64encode(bytes(self._public_key))
            elif format.lower() == "pem":
                # Convert to cryptography format for PEM export
                crypto_public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                    bytes(self._public_key)
                )
                return crypto_public_key.public_bytes(
                    encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
                )
            else:
                raise CryptoError(
                    f"Unsupported export format: {format}",
                    algorithm="Ed25519",
                    operation="export_public",
                )
        except Exception as e:
            raise CryptoError(
                f"Failed to export public key: {e}",
                algorithm="Ed25519",
                operation="export_public",
            )

    def import_private_key(
        self, key_data: bytes, password: Optional[str] = None
    ) -> None:
        """Import Ed25519 private key."""
        try:
            if len(key_data) == 32:  # Raw private key
                self._private_key = nacl.signing.SigningKey(key_data)
            elif key_data.startswith(b"-----BEGIN"):  # PEM format
                # Use cryptography to parse PEM, then convert to PyNaCl
                crypto_private_key = serialization.load_pem_private_key(
                    key_data, password=password.encode() if password else None
                )
                if not isinstance(crypto_private_key, ed25519.Ed25519PrivateKey):
                    raise CryptoError(
                        "Key is not Ed25519",
                        algorithm="Ed25519",
                        operation="import_private",
                    )

                raw_key = crypto_private_key.private_bytes(
                    encoding=Encoding.Raw,
                    format=PrivateFormat.Raw,
                    encryption_algorithm=NoEncryption(),
                )
                self._private_key = nacl.signing.SigningKey(raw_key)
            else:
                # Try base64 decode
                try:
                    raw_key = base64.b64decode(key_data)
                    self._private_key = nacl.signing.SigningKey(raw_key)
                except Exception:
                    raise CryptoError(
                        "Unsupported private key format",
                        algorithm="Ed25519",
                        operation="import_private",
                    )

            # Derive public key
            self._public_key = self._private_key.verify_key

        except Exception as e:
            if isinstance(e, CryptoError):
                raise
            raise CryptoError(
                f"Failed to import private key: {e}",
                algorithm="Ed25519",
                operation="import_private",
            )

    def import_public_key(self, key_data: bytes) -> None:
        """Import Ed25519 public key."""
        try:
            if len(key_data) == 32:  # Raw public key
                self._public_key = nacl.signing.VerifyKey(key_data)
            elif key_data.startswith(b"-----BEGIN"):  # PEM format
                crypto_public_key = serialization.load_pem_public_key(key_data)
                if not isinstance(crypto_public_key, ed25519.Ed25519PublicKey):
                    raise CryptoError(
                        "Key is not Ed25519",
                        algorithm="Ed25519",
                        operation="import_public",
                    )

                raw_key = crypto_public_key.public_bytes(
                    encoding=Encoding.Raw, format=PublicFormat.Raw
                )
                self._public_key = nacl.signing.VerifyKey(raw_key)
            else:
                # Try base64 decode
                try:
                    raw_key = base64.b64decode(key_data)
                    self._public_key = nacl.signing.VerifyKey(raw_key)
                except Exception:
                    raise CryptoError(
                        "Unsupported public key format",
                        algorithm="Ed25519",
                        operation="import_public",
                    )

        except Exception as e:
            if isinstance(e, CryptoError):
                raise
            raise CryptoError(
                f"Failed to import public key: {e}",
                algorithm="Ed25519",
                operation="import_public",
            )


class RSAKeyPair(KeyPair):
    """RSA key pair implementation using cryptography."""

    def __init__(self, key_size: int = 2048):
        super().__init__(SignatureAlgorithm.RSA_PSS)
        self.key_size = key_size

    def generate(self) -> None:
        """Generate a new RSA key pair."""
        try:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=self.key_size
            )
            self._public_key = self._private_key.public_key()
        except Exception as e:
            raise CryptoError(
                f"Failed to generate RSA key pair: {e}",
                algorithm="RSA-PSS",
                operation="generate",
            )

    def sign(self, data: bytes) -> bytes:
        """Sign data with RSA-PSS."""
        if not self.has_private_key:
            raise CryptoError(
                "Private key not available for signing",
                algorithm="RSA-PSS",
                operation="sign",
            )

        try:
            signature = self._private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return signature
        except Exception as e:
            raise CryptoError(
                f"Failed to sign data: {e}", algorithm="RSA-PSS", operation="sign"
            )

    def verify(
        self, data: bytes, signature: bytes, public_key: Optional[bytes] = None
    ) -> bool:
        """Verify RSA-PSS signature."""
        try:
            if public_key:
                verify_key = serialization.load_der_public_key(public_key)
            else:
                if not self.has_public_key:
                    raise CryptoError(
                        "Public key not available for verification",
                        algorithm="RSA-PSS",
                        operation="verify",
                    )
                verify_key = self._public_key

            verify_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    def export_private_key(
        self, format: str = "pem", password: Optional[str] = None
    ) -> bytes:
        """Export RSA private key."""
        if not self.has_private_key:
            raise CryptoError(
                "Private key not available",
                algorithm="RSA-PSS",
                operation="export_private",
            )

        try:
            encryption = NoEncryption()
            if password:
                from cryptography.hazmat.primitives.serialization import (
                    BestAvailableEncryption,
                )

                encryption = BestAvailableEncryption(password.encode())

            if format.lower() == "pem":
                return self._private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.PKCS8,
                    encryption_algorithm=encryption,
                )
            elif format.lower() == "der":
                return self._private_key.private_bytes(
                    encoding=Encoding.DER,
                    format=PrivateFormat.PKCS8,
                    encryption_algorithm=encryption,
                )
            else:
                raise CryptoError(
                    f"Unsupported export format: {format}",
                    algorithm="RSA-PSS",
                    operation="export_private",
                )
        except Exception as e:
            raise CryptoError(
                f"Failed to export private key: {e}",
                algorithm="RSA-PSS",
                operation="export_private",
            )

    def export_public_key(self, format: str = "pem") -> bytes:
        """Export RSA public key."""
        if not self.has_public_key:
            raise CryptoError(
                "Public key not available",
                algorithm="RSA-PSS",
                operation="export_public",
            )

        try:
            if format.lower() == "pem":
                return self._public_key.public_bytes(
                    encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
                )
            elif format.lower() == "der":
                return self._public_key.public_bytes(
                    encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo
                )
            else:
                raise CryptoError(
                    f"Unsupported export format: {format}",
                    algorithm="RSA-PSS",
                    operation="export_public",
                )
        except Exception as e:
            raise CryptoError(
                f"Failed to export public key: {e}",
                algorithm="RSA-PSS",
                operation="export_public",
            )

    def import_private_key(
        self, key_data: bytes, password: Optional[str] = None
    ) -> None:
        """Import RSA private key."""
        try:
            self._private_key = serialization.load_pem_private_key(
                key_data, password=password.encode() if password else None
            )
            if not isinstance(self._private_key, rsa.RSAPrivateKey):
                raise CryptoError(
                    "Key is not RSA", algorithm="RSA-PSS", operation="import_private"
                )

            self._public_key = self._private_key.public_key()

        except Exception as e:
            if isinstance(e, CryptoError):
                raise
            raise CryptoError(
                f"Failed to import private key: {e}",
                algorithm="RSA-PSS",
                operation="import_private",
            )

    def import_public_key(self, key_data: bytes) -> None:
        """Import RSA public key."""
        try:
            self._public_key = serialization.load_pem_public_key(key_data)
            if not isinstance(self._public_key, rsa.RSAPublicKey):
                raise CryptoError(
                    "Key is not RSA", algorithm="RSA-PSS", operation="import_public"
                )

        except Exception as e:
            if isinstance(e, CryptoError):
                raise
            raise CryptoError(
                f"Failed to import public key: {e}",
                algorithm="RSA-PSS",
                operation="import_public",
            )


class CryptoEngine:
    """Main cryptographic engine for TrustChain."""

    def __init__(self):
        self._key_pairs: Dict[str, KeyPair] = {}

    def create_key_pair(
        self, algorithm: SignatureAlgorithm, key_id: Optional[str] = None, **kwargs
    ) -> KeyPair:
        """Create a new key pair."""
        if algorithm == SignatureAlgorithm.ED25519:
            key_pair = Ed25519KeyPair()
        elif algorithm == SignatureAlgorithm.RSA_PSS:
            key_size = kwargs.get("key_size", 2048)
            key_pair = RSAKeyPair(key_size)
        else:
            raise CryptoError(
                f"Unsupported algorithm: {algorithm}",
                algorithm=algorithm.value,
                operation="create_key_pair",
            )

        key_pair.generate()

        if key_id:
            key_pair._key_id = key_id

        # Store the key pair
        self._key_pairs[key_pair.key_id] = key_pair

        return key_pair

    def get_key_pair(self, key_id: str) -> Optional[KeyPair]:
        """Get a key pair by ID."""
        return self._key_pairs.get(key_id)

    def import_key_pair(
        self,
        key_id: str,
        algorithm: SignatureAlgorithm,
        private_key_data: Optional[bytes] = None,
        public_key_data: Optional[bytes] = None,
        password: Optional[str] = None,
    ) -> KeyPair:
        """Import a key pair from data."""
        if algorithm == SignatureAlgorithm.ED25519:
            key_pair = Ed25519KeyPair()
        elif algorithm == SignatureAlgorithm.RSA_PSS:
            key_pair = RSAKeyPair()
        else:
            raise CryptoError(
                f"Unsupported algorithm: {algorithm}",
                algorithm=algorithm.value,
                operation="import_key_pair",
            )

        key_pair._key_id = key_id

        if private_key_data:
            key_pair.import_private_key(private_key_data, password)

        if public_key_data:
            key_pair.import_public_key(public_key_data)

        self._key_pairs[key_id] = key_pair
        return key_pair

    def hash_data(
        self, data: Union[str, bytes, Dict[str, Any]], algorithm: str = "sha256"
    ) -> str:
        """Hash data using specified algorithm."""
        if isinstance(data, dict):
            import json

            data = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        elif isinstance(data, str):
            data = data.encode()

        if algorithm.lower() == "sha256":
            hash_obj = hashlib.sha256(data)
        elif algorithm.lower() == "sha512":
            hash_obj = hashlib.sha512(data)
        elif algorithm.lower() == "blake2b":
            hash_obj = hashlib.blake2b(data)
        else:
            raise CryptoError(
                f"Unsupported hash algorithm: {algorithm}",
                algorithm=algorithm,
                operation="hash",
            )

        return f"{algorithm.lower()}:{hash_obj.hexdigest()}"

    def generate_nonce(self, length: int = 32) -> str:
        """Generate a cryptographically secure nonce."""
        return secrets.token_urlsafe(length)

    def constant_time_compare(self, a: Union[str, bytes], b: Union[str, bytes]) -> bool:
        """Constant-time comparison to prevent timing attacks."""
        if isinstance(a, str):
            a = a.encode()
        if isinstance(b, str):
            b = b.encode()

        return secrets.compare_digest(a, b)

    def list_key_pairs(self) -> Dict[str, Dict[str, Any]]:
        """List all available key pairs."""
        result = {}
        for key_id, key_pair in self._key_pairs.items():
            result[key_id] = {
                "algorithm": key_pair.algorithm.value,
                "has_private_key": key_pair.has_private_key,
                "has_public_key": key_pair.has_public_key,
            }
        return result

    def remove_key_pair(self, key_id: str) -> bool:
        """Remove a key pair."""
        if key_id in self._key_pairs:
            del self._key_pairs[key_id]
            return True
        return False


# Global crypto engine instance
_crypto_engine = None


def get_crypto_engine() -> CryptoEngine:
    """Get the global crypto engine instance."""
    global _crypto_engine
    if _crypto_engine is None:
        _crypto_engine = CryptoEngine()
    return _crypto_engine


# Convenience functions
def create_key_pair(algorithm: SignatureAlgorithm, **kwargs) -> KeyPair:
    """Create a new key pair using the global crypto engine."""
    return get_crypto_engine().create_key_pair(algorithm, **kwargs)


def hash_data(
    data: Union[str, bytes, Dict[str, Any]], algorithm: str = "sha256"
) -> str:
    """Hash data using the global crypto engine."""
    return get_crypto_engine().hash_data(data, algorithm)


def generate_nonce(length: int = 32) -> str:
    """Generate a nonce using the global crypto engine."""
    return get_crypto_engine().generate_nonce(length)
