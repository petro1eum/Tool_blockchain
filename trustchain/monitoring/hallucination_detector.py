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


class ClaimExtractor:
    """Extracts factual claims from LLM responses."""

    # Patterns that typically indicate tool results
    TOOL_RESULT_PATTERNS = [
        r"(?:I\s+(?:checked|retrieved|got|fetched|called|used))\s+(.+?):\s*(.+)",
        r"(?:According\s+to|Based\s+on|From)\s+(\w+)(?:\s+tool)?[,:]?\s*(.+)",
        r"(?:The|My)\s+(\w+)\s+(?:tool|API|service|function)\s+(?:returned|shows|indicates)[:\s]*(.+)",
        r"(?:Weather|Temperature|Price|Data|Result|Status)(?:\s+in\s+\w+)?[:\s]*(.+)",
        r"(\w+_tool|\w+_api|\w+API)\s+(?:returned|gave|showed)[:\s]*(.+)",
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.TOOL_RESULT_PATTERNS]

    def extract_claims(self, text: str) -> List[HallucinatedClaim]:
        """Extract factual claims from text that could be tool results."""
        claims = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            for pattern in self.patterns:
                matches = pattern.finditer(line)
                for match in matches:
                    tool_name = None
                    claimed_result = match.group(0)

                    if len(match.groups()) >= 2:
                        tool_name = match.group(1)
                        claimed_result = match.group(2)
                    elif len(match.groups()) >= 1:
                        claimed_result = match.group(1)

                    claims.append(HallucinatedClaim(
                        claim_text=line,
                        tool_name=tool_name,
                        claimed_result=claimed_result,
                        context=f"Line {line_num + 1}",
                        confidence=0.5  # Uncertain by default
                    ))

        return claims

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


class VerificationRegistry:
    """Registry of verified tool results."""

    def __init__(self):
        self.verified_results: Dict[str, SignedResponse] = {}
        self.pending_verifications: Dict[str, Any] = {}

    def register_verified_result(self, response: SignedResponse) -> None:
        """Register a cryptographically verified tool result."""
        self.verified_results[response.request_id] = response

    def has_verification_for_claim(self, claim: HallucinatedClaim) -> bool:
        """Check if we have a verification for a specific claim."""
        # Simple matching - in practice, this would be more sophisticated
        for response in self.verified_results.values():
            if self._claim_matches_response(claim, response):
                return True
        return False

    def _claim_matches_response(self, claim: HallucinatedClaim, response: SignedResponse) -> bool:
        """Check if a claim matches a verified response."""
        if claim.tool_name and claim.tool_name.lower() in response.tool_id.lower():
            # Check if claimed result is similar to actual result
            claimed_str = str(claim.claimed_result).lower()
            actual_str = str(response.data).lower()
            
            # Simple similarity check - could be enhanced with NLP
            return any(word in actual_str for word in claimed_str.split() if len(word) > 3)
        
        return False


class HallucinationDetector:
    """Main detector for LLM hallucinations."""

    def __init__(self, signature_engine: SignatureEngine):
        self.signature_engine = signature_engine
        self.claim_extractor = ClaimExtractor()
        self.verification_registry = VerificationRegistry()
        self.strict_mode = False  # If True, requires verification for ALL claims

    def set_strict_mode(self, enabled: bool) -> None:
        """Enable/disable strict verification mode."""
        self.strict_mode = enabled

    def validate_response(self, response: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate an LLM response for hallucinated claims."""
        claims = self.claim_extractor.extract_claims(response)
        hallucinations = []
        verified_claims = []

        for claim in claims:
            if self.verification_registry.has_verification_for_claim(claim):
                verified_claims.append(claim.claim_text)
                claim.confidence = 1.0
            else:
                if self.strict_mode or self._looks_like_tool_result(claim):
                    hallucinations.append(claim)
                    claim.confidence = 0.0

        # Calculate overall confidence
        total_claims = len(claims)
        if total_claims == 0:
            confidence_score = 1.0  # No claims to verify
        else:
            confidence_score = len(verified_claims) / total_claims

        is_valid = len(hallucinations) == 0

        return ValidationResult(
            valid=is_valid,
            hallucinations=hallucinations,
            verified_claims=verified_claims,
            message=self._generate_validation_message(is_valid, hallucinations, verified_claims),
            confidence_score=confidence_score
        )

    def _looks_like_tool_result(self, claim: HallucinatedClaim) -> bool:
        """Determine if a claim looks like it should be a tool result."""
        # Heuristics to identify potential tool results
        indicators = [
            claim.tool_name is not None,
            any(word in claim.claim_text.lower() for word in [
                'api', 'tool', 'checked', 'retrieved', 'fetched', 
                'temperature', 'weather', 'price', 'status'
            ]),
            ':' in claim.claim_text,  # Often indicates structured data
            any(char.isdigit() for char in claim.claimed_result),  # Contains numbers
        ]
        
        return sum(indicators) >= 2

    def _generate_validation_message(self, is_valid: bool, hallucinations: List[HallucinatedClaim], verified_claims: List[str]) -> str:
        """Generate a human-readable validation message."""
        if is_valid:
            if verified_claims:
                return f"✅ All {len(verified_claims)} claims verified with cryptographic signatures"
            else:
                return "✅ No verifiable claims detected (general response)"
        else:
            unverified_count = len(hallucinations)
            return f"❌ Detected {unverified_count} unverified claim(s) that may be hallucinated"


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
def create_hallucination_detector(signature_engine: SignatureEngine) -> HallucinationDetector:
    """Create a configured hallucination detector."""
    return HallucinationDetector(signature_engine)


def validate_llm_response(response: str, detector: HallucinationDetector) -> ValidationResult:
    """Quick validation of an LLM response."""
    return detector.validate_response(response) 