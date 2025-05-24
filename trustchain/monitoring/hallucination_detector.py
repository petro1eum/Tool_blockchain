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
    """Extracts factual claims from LLM responses using advanced pattern matching."""

    # Core patterns that indicate tool results (harder to bypass)
    TOOL_RESULT_PATTERNS = [
        # Direct tool references
        r"(?:I\s+(?:checked|retrieved|got|fetched|called|used|executed|queried))\s+(.+?)(?:\s+(?:and|to|for))?\s*[:\-]?\s*(.+)",
        r"(?:According\s+to|Based\s+on|From|Using)\s+(?:the\s+)?(\w+)(?:\s+(?:tool|API|service|function|system))?[,:\-]?\s*(.+)",
        r"(?:The|My)\s+(\w+)\s+(?:tool|API|service|function|system|database)\s+(?:returned|shows|indicates|reports|confirms|says)[:\-\s]*(.+)",
        
        # Data presentation patterns (harder to avoid)
        r"(?:Current|Latest|Real-time|Updated)\s+(\w+)(?:\s+(?:data|information|status|price|temperature|value))?[:\s]*(.+)",
        r"(?:Live|Fresh|New)\s+(?:data|information|results)\s+(?:from|shows?|indicates?)[:\s]*(.+)",
        
        # API-specific patterns
        r"(\w+_?(?:api|API|tool|service))\s+(?:returned|gave|showed|provided|reports?)[:\s]*(.+)",
        r"(?:API|Tool|Service|System)\s+(?:call|query|request)\s+(?:returned|gave|showed)[:\s]*(.+)",
        
        # Structured data patterns
        r"(?:Data|Results?|Information|Response)(?:\s+from\s+\w+)?[:\s]*\{.+?\}",  # JSON-like
        r"(?:Status|State|Value|Price|Temperature|Count|Amount)[:\s]*[\d\$€£¥]+",  # Specific values
        
        # Time-based claims (often hallucinated)
        r"(?:As\s+of|Currently|Right\s+now|At\s+this\s+moment|Today)[:\s,]*(.+)",
        
        # Verification bypass attempts
        r"(?:The\s+(?:data|information|results?)\s+(?:shows?|indicates?|confirms?|suggests?))[:\s]*(.+)",
        r"(?:Analysis|Research|Investigation)\s+(?:shows?|reveals?|indicates?)[:\s]*(.+)",
        r"(?:Sources?|Reports?|Studies?)\s+(?:indicate|show|confirm|suggest)[:\s]*(.+)",
    ]

    # Semantic patterns that indicate claims (not just syntax)
    SEMANTIC_CLAIM_INDICATORS = [
        # Definitive statements about external data
        "temperature", "price", "cost", "value", "amount", "count", "number",
        "status", "state", "condition", "level", "rate", "percentage",
        "balance", "total", "sum", "average", "maximum", "minimum",
        "current", "latest", "updated", "recent", "new", "fresh",
        
        # Time-specific claims
        "today", "yesterday", "now", "currently", "presently", "at the moment",
        "this week", "this month", "this year", "recently", "lately",
        
        # Certainty indicators (often used in hallucinations)
        "exactly", "precisely", "specifically", "definitely", "certainly",
        "confirmed", "verified", "validated", "authenticated",
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.TOOL_RESULT_PATTERNS]
        self.semantic_indicators = [word.lower() for word in self.SEMANTIC_CLAIM_INDICATORS]

    def extract_claims(self, text: str) -> List[HallucinatedClaim]:
        """Extract factual claims from text that could be tool results."""
        claims = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for pattern-based claims
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

                    # Calculate confidence based on pattern strength
                    confidence = self._calculate_pattern_confidence(line, match, pattern)

                    claims.append(HallucinatedClaim(
                        claim_text=line,
                        tool_name=tool_name,
                        claimed_result=claimed_result,
                        context=f"Line {line_num + 1} (pattern match)",
                        confidence=confidence
                    ))

            # Check for semantic-based claims (even if no pattern matches)
            semantic_claims = self._extract_semantic_claims(line, line_num)
            claims.extend(semantic_claims)

        # Remove duplicates (same claim_text)
        seen_claims = set()
        unique_claims = []
        for claim in claims:
            if claim.claim_text not in seen_claims:
                seen_claims.add(claim.claim_text)
                unique_claims.append(claim)

        return unique_claims
    
    def _calculate_pattern_confidence(self, line: str, match: re.Match, pattern: re.Pattern) -> float:
        """Calculate confidence score for a pattern-based claim."""
        confidence = 0.3  # Base confidence for pattern match
        
        line_lower = line.lower()
        
        # Higher confidence for explicit tool references
        if any(keyword in line_lower for keyword in ['api', 'tool', 'service', 'database']):
            confidence += 0.3
        
        # Higher confidence for specific data types
        if any(keyword in line_lower for keyword in ['temperature', 'price', 'balance', 'status']):
            confidence += 0.2
        
        # Higher confidence for numbers/specific values
        if re.search(r'\d+(?:\.\d+)?', line):
            confidence += 0.2
        
        # Higher confidence for time references
        if any(keyword in line_lower for keyword in ['now', 'current', 'today', 'latest']):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_semantic_claims(self, line: str, line_num: int) -> List[HallucinatedClaim]:
        """Extract claims based on semantic content analysis."""
        claims = []
        line_lower = line.lower()
        
        # Count semantic indicators
        indicator_count = sum(1 for indicator in self.semantic_indicators if indicator in line_lower)
        
        # If line has multiple semantic indicators, it's likely a factual claim
        if indicator_count >= 2:
            # Check if line makes definitive statements
            definitive_patterns = [
                r'\bis\s+[\d\$€£¥]+',  # "is $100", "is 25°C"
                r'\bwas\s+[\d\$€£¥]+',  # "was $100"
                r'\bshows?\s+[\d\$€£¥]+',  # "shows $100"
                r'\bequals?\s+[\d\$€£¥]+',  # "equals $100"
                r'\btotal(?:s|ed|ing)?\s+[\d\$€£¥]+',  # "total $100"
                r'\bcost(?:s)?\s+[\d\$€£¥]+',  # "costs $100"
                r'\bprice(?:d)?\s+at\s+[\d\$€£¥]+',  # "priced at $100"
            ]
            
            for pattern in definitive_patterns:
                if re.search(pattern, line_lower):
                    # Calculate confidence based on semantic strength
                    confidence = min(0.4 + (indicator_count * 0.1), 0.9)
                    
                    claims.append(HallucinatedClaim(
                        claim_text=line,
                        tool_name=self._extract_implied_tool(line),
                        claimed_result=self._extract_claimed_value(line),
                        context=f"Line {line_num + 1} (semantic analysis)",
                        confidence=confidence
                    ))
                    break
        
        return claims
    
    def _extract_implied_tool(self, line: str) -> Optional[str]:
        """Try to extract implied tool name from context."""
        line_lower = line.lower()
        
        # Common tool domain mappings
        tool_mappings = {
            'weather': ['temperature', 'humidity', 'rain', 'snow', 'wind', 'forecast'],
            'stock': ['price', 'trading', 'market', 'shares', 'stocks', 'ticker'],
            'finance': ['balance', 'account', 'payment', 'transaction', 'money'],
            'database': ['record', 'entry', 'data', 'query', 'search'],
            'api': ['endpoint', 'response', 'request', 'service', 'call'],
        }
        
        for tool_type, keywords in tool_mappings.items():
            if any(keyword in line_lower for keyword in keywords):
                return f"{tool_type}_api"
        
        return None
    
    def _extract_claimed_value(self, line: str) -> str:
        """Extract the specific value being claimed."""
        # Look for numbers, currency, percentages
        value_patterns = [
            r'[\d,]+\.?\d*\s*[%°CF$€£¥]',  # Numbers with units
            r'\$[\d,]+\.?\d*',  # Currency
            r'[\d,]+\.?\d*\s*(?:percent|%)',  # Percentages
            r'[\d,]+\.?\d*',  # Plain numbers
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        
        # Fallback to last part of sentence
        words = line.split()
        if len(words) > 3:
            return ' '.join(words[-3:])
        
        return line

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