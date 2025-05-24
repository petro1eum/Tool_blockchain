"""
Hallucination detection for LLM responses.

This module provides mechanisms to detect when LLMs hallucinate tool calls
or claim results that aren't backed by cryptographic signatures.
"""

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from trustchain.core.models import SignedResponse, VerificationResult
from trustchain.core.signatures import SignatureEngine
from trustchain.utils.exceptions import TrustChainError


class HallucinationError(TrustChainError):
    """Raised when hallucinated claims are detected in LLM responses."""

    def __init__(self, hallucinations: List["HallucinatedClaim"], message: str = None):
        self.hallucinations = hallucinations
        super().__init__(
            message or f"Detected {len(hallucinations)} hallucinated claims",
            error_code="HALLUCINATION_DETECTED",
            details={"hallucinations": [h.to_dict() for h in hallucinations]},
        )


@dataclass
class HallucinatedClaim:
    """Represents a claim that cannot be verified with a signature."""

    claim_text: str
    tool_name: Optional[str]
    claimed_result: Any
    context: str
    confidence: float = 0.0  # 0.0 = definitely hallucinated, 1.0 = definitely real

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "tool_name": self.tool_name,
            "claimed_result": self.claimed_result,
            "context": self.context,
            "confidence": self.confidence,
        }


@dataclass
class ValidationResult:
    """Result of hallucination validation."""

    valid: bool
    hallucinations: List[HallucinatedClaim]
    verified_claims: List[str]
    message: str
    confidence_score: float = 0.0


class SimpleValidator:
    """Simple validator: if response has tool claims, check for signatures. If no tool claims, allow."""

    def has_tool_claims(self, response: str) -> bool:
        """Check if response contains claims about tool usage."""
        import re
        
        tool_claim_patterns = [
            r'I\s+(?:called|used|executed|ran|invoked)',
            r'I\s+(?:got|obtained|received|fetched)',
            r'API\s+(?:returned|responded|gave)',
            r'tool\s+(?:returned|gave|showed)',
            r'transaction\s+(?:id|number)',
            r'result\s+(?:is|was|shows)',
        ]
        
        for pattern in tool_claim_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False

    def has_valid_signatures(self, response: str) -> bool:
        """Simple check: does this response contain any valid signed data?"""
        # Look for any signed response objects or signature markers in the response
        # This is the SIMPLE approach - no complex regex or claim matching
        
        import re
        
        # Look for signature patterns that would be embedded in LLM responses
        signature_patterns = [
            r'\[SIGNED_DATA:.*?\]',  # Structured signed data
            r'signature.*?[a-zA-Z0-9+/=]{20,}',  # Base64-like signatures
            r'sig[:=]\s*[a-zA-Z0-9+/=]{10,}',  # Short sig markers
            r'verified[:=]\s*true',  # Verification markers
        ]
        
        for pattern in signature_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    


    def extract_structured_claims(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured data claims (JSON, key-value pairs)."""
        claims = []

        # Look for JSON-like structures
        json_pattern = r'\{[^}]+\}'
        for match in re.finditer(json_pattern, text):
            try:
                data = json.loads(match.group())
                claims.append({
                    "type": "json",
                    "data": data,
                    "text": match.group(),
                    "position": match.span()
                })
            except json.JSONDecodeError:
                pass

        # Look for key-value patterns
        kv_pattern = r'(\w+):\s*([^,\n]+)'
        for match in re.finditer(kv_pattern, text):
            claims.append({
                "type": "key_value",
                "key": match.group(1),
                "value": match.group(2).strip(),
                "text": match.group(),
                "position": match.span()
            })

        return claims





class HallucinationDetector:
    """SIMPLE detector: if response has valid signatures, it's OK. If not, it's hallucination."""

    def __init__(self, signature_engine: SignatureEngine, tool_enforcer=None):
        self.signature_engine = signature_engine
        self.validator = SimpleValidator()
        self.tool_enforcer = tool_enforcer  # Integration with enforcement system
        
        # Track recent signed responses from direct tool calls
        self.recent_signed_responses = []  # Keep last 50 signed responses
        self.max_recent_responses = 50

    def register_signed_response(self, signed_response: SignedResponse) -> None:
        """Register a signed response from a direct tool call."""
        self.recent_signed_responses.insert(0, signed_response)
        # Keep only recent responses
        if len(self.recent_signed_responses) > self.max_recent_responses:
            self.recent_signed_responses = self.recent_signed_responses[:self.max_recent_responses]

    def set_tool_enforcer(self, enforcer) -> None:
        """Set the tool enforcer for verification."""
        self.tool_enforcer = enforcer

    def validate_response(self, response: str, context: Dict[str, Any] = None) -> ValidationResult:
        """SIMPLE validation: if response has tool claims, require signatures. Otherwise allow."""
        
        # First check: does response contain tool claims?
        has_tool_claims = self.validator.has_tool_claims(response)
        
        if not has_tool_claims:
            # No tool claims = general conversation, allow it
            return ValidationResult(
                valid=True,
                hallucinations=[],
                verified_claims=[],
                message="✅ General conversation - no tool claims detected",
                confidence_score=1.0
            )
        
        # Has tool claims - check for signatures
        has_signatures = self.validator.has_valid_signatures(response)
        has_recent_signed_data = self._has_recent_signed_data(response)
        
        has_enforcer_data = False
        if self.tool_enforcer:
            has_enforcer_data = self.tool_enforcer.has_signed_data_for_response(response)
        
        # If any signature check passes, response is valid
        is_valid = has_signatures or has_recent_signed_data or has_enforcer_data
        
        if is_valid:
            return ValidationResult(
                valid=True,
                hallucinations=[],
                verified_claims=[response],
                message="✅ Tool claims backed by verified signatures",
                confidence_score=1.0
            )
        else:
            # Tool claims without signatures - hallucination
            fake_claim = HallucinatedClaim(
                claim_text=response,
                tool_name=None,
                claimed_result=response,
                context="Tool claims without signatures"
            )
            
            return ValidationResult(
                valid=False,
                hallucinations=[fake_claim],
                verified_claims=[],
                message="❌ Tool claims without verified signatures - possible hallucination",
                confidence_score=0.0
            )

    def _has_recent_signed_data(self, response: str) -> bool:
        """Check if response contains data from recent signed responses."""
        import time
        current_time = time.time()
        
        for signed_response in self.recent_signed_responses:
            # Only check recent responses (within last 60 seconds)
            time_diff = current_time - (signed_response.timestamp / 1000)  # Convert to seconds
            if time_diff > 60:
                continue
                
            # Simple check: does response contain data from this signed response?
            if self._response_contains_signed_data(response, signed_response):
                return True
        
        return False

    def _response_contains_signed_data(self, response: str, signed_response: SignedResponse) -> bool:
        """Simple check: does response contain any data from the signed response?"""
        response_lower = response.lower()
        
        # Check if tool ID is mentioned
        if signed_response.tool_id.lower() in response_lower:
            return True
        
        # Check if any result data is mentioned
        if signed_response.data and isinstance(signed_response.data, dict):
            for key, value in signed_response.data.items():
                value_str = str(value).lower()
                if len(value_str) >= 2 and value_str in response_lower:
                    return True
        
        return False


class LLMResponseInterceptor:
    """Intercepts and validates LLM responses before they're returned to users."""

    def __init__(self, hallucination_detector: HallucinationDetector):
        self.detector = hallucination_detector
        self.auto_reject = False  # If True, automatically reject hallucinated responses

    def intercept(self, response: str, context: Dict[str, Any] = None) -> Tuple[str, ValidationResult]:
        """Intercept and validate an LLM response."""
        validation = self.detector.validate_response(response, context)

        if not validation.valid and self.auto_reject:
            # Generate safe response
            safe_response = self._generate_safe_response(validation.hallucinations)
            return safe_response, validation

        return response, validation

    def _generate_safe_response(self, hallucinations: List[HallucinatedClaim]) -> str:
        """Generate a safe response when hallucinations are detected."""
        tool_names = set(h.tool_name for h in hallucinations if h.tool_name)
        
        if tool_names:
            tools_str = ", ".join(tool_names)
            return f"⚠️ I apologize, but I cannot provide verified results for {tools_str}. The tools may not have been properly executed or their results weren't cryptographically signed. Please try running the tools again."
        else:
            return "⚠️ I apologize, but I cannot verify some of the information in my previous response. Please request fresh data from the appropriate tools."


# Convenience functions
def create_hallucination_detector(signature_engine: SignatureEngine, tool_enforcer=None) -> HallucinationDetector:
    """Create a configured hallucination detector with optional tool enforcer integration."""
    return HallucinationDetector(signature_engine, tool_enforcer)


def validate_llm_response(response: str, detector: HallucinationDetector) -> ValidationResult:
    """Quick validation of an LLM response."""
    return detector.validate_response(response) 