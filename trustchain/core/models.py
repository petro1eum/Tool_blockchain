"""Core data models for TrustChain."""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""
    ED25519 = "Ed25519"
    RSA_PSS = "RSA-PSS"
    ECDSA = "ECDSA"
    DILITHIUM = "Dilithium"  # Post-quantum


class SignatureFormat(str, Enum):
    """Signature encoding formats."""
    BASE64 = "base64"
    HEX = "hex"
    BINARY = "binary"


class TrustLevel(str, Enum):
    """Trust levels for verification."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestContext(BaseModel):
    """Context information for a tool request."""
    
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nonce: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    caller_id: str
    session_id: Optional[str] = None
    parent_request_id: Optional[str] = None
    chain_id: Optional[str] = None
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is reasonable."""
        now = int(time.time() * 1000)
        if abs(v - now) > 300_000:  # 5 minutes
            raise ValueError("Timestamp too far from current time")
        return v
    
    @validator('request_id', 'nonce')
    def validate_ids(cls, v):
        """Ensure IDs are non-empty strings."""
        if not v or not isinstance(v, str):
            raise ValueError("ID must be a non-empty string")
        return v


class SignatureInfo(BaseModel):
    """Cryptographic signature information."""
    
    algorithm: SignatureAlgorithm
    signature: str  # Base64 encoded signature
    public_key_id: str
    signed_hash: str  # Hash that was signed (algorithm:hash)
    signature_format: SignatureFormat = SignatureFormat.BASE64
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    
    @validator('signature', 'signed_hash')
    def validate_non_empty(cls, v):
        """Ensure critical fields are non-empty."""
        if not v or not isinstance(v, str):
            raise ValueError("Field must be a non-empty string")
        return v
    
    @validator('signed_hash')
    def validate_hash_format(cls, v):
        """Ensure hash is in format 'algorithm:hash'."""
        if ':' not in v:
            raise ValueError("Hash must be in format 'algorithm:hash'")
        return v


class TrustMetadata(BaseModel):
    """Metadata about trust and verification."""
    
    trust_level: TrustLevel = TrustLevel.MEDIUM
    verified: bool = False
    verification_timestamp: Optional[int] = None
    verifier_id: Optional[str] = None
    verification_chain: List[str] = Field(default_factory=list)
    compliance_flags: Dict[str, bool] = Field(default_factory=dict)
    
    @validator('verification_timestamp')
    def set_verification_time(cls, v):
        """Set verification timestamp if verified."""
        if v is None:
            return int(time.time() * 1000)
        return v


class ChainLink(BaseModel):
    """A link in the chain of trust."""
    
    step_number: int
    request_id: str
    tool_id: str
    parent_hash: Optional[str] = None
    link_hash: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('step_number')
    def validate_step_number(cls, v):
        """Ensure step number is non-negative."""
        if v < 0:
            raise ValueError("Step number must be non-negative")
        return v
    
    @root_validator
    def validate_chain_logic(cls, values):
        """Validate chain link logic."""
        step_number = values.get('step_number')
        parent_hash = values.get('parent_hash')
        
        if step_number == 0 and parent_hash is not None:
            raise ValueError("First step cannot have parent hash")
        if step_number > 0 and parent_hash is None:
            raise ValueError("Non-first step must have parent hash")
        
        return values


class SignedResponse(BaseModel):
    """A cryptographically signed tool response."""
    
    # Core data
    request_id: str
    tool_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    data: Any  # The actual tool response data
    
    # Cryptographic proof
    signature: SignatureInfo
    
    # Trust and chain information
    trust_metadata: TrustMetadata = Field(default_factory=TrustMetadata)
    chain_link: Optional[ChainLink] = None
    
    # Additional metadata
    execution_time_ms: Optional[float] = None
    version: str = "1.0"
    compliance_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('data')
    def validate_data(cls, v):
        """Ensure data is serializable."""
        try:
            import json
            json.dumps(v, default=str)  # Test serializability
        except (TypeError, ValueError) as e:
            raise ValueError(f"Data must be JSON serializable: {e}")
        return v
    
    def to_canonical_dict(self) -> Dict[str, Any]:
        """Convert to canonical dictionary for signing."""
        return {
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "execution_time_ms": self.execution_time_ms,
            "version": self.version,
        }
    
    def verify_signature(self, verifier_func) -> bool:
        """Verify the signature using provided verifier function."""
        try:
            canonical_data = self.to_canonical_dict()
            return verifier_func(canonical_data, self.signature)
        except Exception:
            return False
    
    @property
    def is_verified(self) -> bool:
        """Check if response is verified."""
        return self.trust_metadata.verified
    
    @property
    def age_seconds(self) -> float:
        """Get age of response in seconds."""
        return (time.time() * 1000 - self.timestamp) / 1000


class VerificationResult(BaseModel):
    """Result of signature verification."""
    
    valid: bool
    request_id: str
    tool_id: str
    signature_id: str
    verified_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    verifier_id: str
    
    # Detailed information
    algorithm_used: SignatureAlgorithm
    trust_level: TrustLevel
    chain_verified: bool = False
    chain_length: Optional[int] = None
    
    # Error information (if verification failed)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance metrics
    verification_time_ms: Optional[float] = None
    cache_hit: bool = False
    
    @classmethod
    def success(
        cls,
        request_id: str,
        tool_id: str,
        signature_id: str,
        verifier_id: str,
        algorithm: SignatureAlgorithm,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        **kwargs
    ) -> "VerificationResult":
        """Create successful verification result."""
        return cls(
            valid=True,
            request_id=request_id,
            tool_id=tool_id,
            signature_id=signature_id,
            verifier_id=verifier_id,
            algorithm_used=algorithm,
            trust_level=trust_level,
            **kwargs
        )
    
    @classmethod
    def failure(
        cls,
        request_id: str,
        tool_id: str,
        signature_id: str,
        verifier_id: str,
        error_code: str,
        error_message: str,
        algorithm: SignatureAlgorithm,
        **kwargs
    ) -> "VerificationResult":
        """Create failed verification result."""
        return cls(
            valid=False,
            request_id=request_id,
            tool_id=tool_id,
            signature_id=signature_id,
            verifier_id=verifier_id,
            algorithm_used=algorithm,
            trust_level=TrustLevel.NONE,
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )


class KeyMetadata(BaseModel):
    """Metadata for cryptographic keys."""
    
    key_id: str
    algorithm: SignatureAlgorithm
    public_key: str  # Base64 encoded public key
    tool_id: str
    
    # Validity period
    valid_from: int = Field(default_factory=lambda: int(time.time() * 1000))
    valid_until: Optional[int] = None
    
    # Status
    revoked: bool = False
    revoked_at: Optional[int] = None
    revocation_reason: Optional[str] = None
    
    # Additional metadata
    created_by: Optional[str] = None
    usage_count: int = 0
    last_used: Optional[int] = None
    key_rotation_id: Optional[str] = None
    
    @validator('valid_until')
    def validate_validity_period(cls, v, values):
        """Ensure validity period is logical."""
        if v is not None and v <= values.get('valid_from', 0):
            raise ValueError("valid_until must be after valid_from")
        return v
    
    @property
    def is_valid(self) -> bool:
        """Check if key is currently valid."""
        now = int(time.time() * 1000)
        if self.revoked:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True
    
    def revoke(self, reason: str = "Manual revocation") -> None:
        """Revoke the key."""
        self.revoked = True
        self.revoked_at = int(time.time() * 1000)
        self.revocation_reason = reason


class NonceEntry(BaseModel):
    """Entry in the nonce registry."""
    
    nonce: str
    request_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    tool_id: Optional[str] = None
    caller_id: Optional[str] = None
    expires_at: int
    
    @validator('expires_at')
    def validate_expiration(cls, v, values):
        """Ensure expiration is in the future."""
        timestamp = values.get('timestamp', int(time.time() * 1000))
        if v <= timestamp:
            raise ValueError("Expiration must be in the future")
        return v
    
    @property
    def is_expired(self) -> bool:
        """Check if nonce has expired."""
        return int(time.time() * 1000) > self.expires_at


class ChainMetadata(BaseModel):
    """Metadata for a chain of trust."""
    
    chain_id: str
    started_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    steps: List[ChainLink] = Field(default_factory=list)
    completed: bool = False
    completed_at: Optional[int] = None
    
    # Chain properties
    max_length: int = 100
    total_execution_time_ms: float = 0.0
    
    # Security
    integrity_verified: bool = False
    last_verification: Optional[int] = None
    
    @validator('steps')
    def validate_step_sequence(cls, v):
        """Ensure steps are in correct sequence."""
        for i, step in enumerate(v):
            if step.step_number != i:
                raise ValueError(f"Step {i} has incorrect step_number {step.step_number}")
        return v
    
    @property
    def length(self) -> int:
        """Get chain length."""
        return len(self.steps)
    
    @property
    def is_complete(self) -> bool:
        """Check if chain is complete."""
        return self.completed
    
    def add_step(self, step: ChainLink) -> None:
        """Add a step to the chain."""
        if len(self.steps) >= self.max_length:
            raise ValueError("Chain has reached maximum length")
        
        expected_step = len(self.steps)
        if step.step_number != expected_step:
            raise ValueError(f"Expected step {expected_step}, got {step.step_number}")
        
        self.steps.append(step)
    
    def complete(self) -> None:
        """Mark chain as completed."""
        self.completed = True
        self.completed_at = int(time.time() * 1000)
    
    def verify_integrity(self) -> bool:
        """Verify chain integrity."""
        if not self.steps:
            return True
        
        # Check first step
        first_step = self.steps[0]
        if first_step.step_number != 0 or first_step.parent_hash is not None:
            return False
        
        # Check subsequent steps
        for i in range(1, len(self.steps)):
            current = self.steps[i]
            previous = self.steps[i - 1]
            
            if current.step_number != i:
                return False
            if current.parent_hash != previous.link_hash:
                return False
        
        self.integrity_verified = True
        self.last_verification = int(time.time() * 1000)
        return True 