"""
Tool Execution Enforcement for TrustChain.

This module provides enforcement mechanisms that ensure ALL tool executions
are tracked, signed, and can be verified against agent claims.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from threading import RLock

from trustchain.core.models import SignedResponse
from trustchain.core.signatures import SignatureEngine
from trustchain.tools.base import BaseTrustedTool
from trustchain.monitoring.hallucination_detector import (
    HallucinatedClaim, 
    ClaimExtractor,
    ValidationResult
)
from trustchain.utils.exceptions import TrustChainError


class UnauthorizedToolExecution(TrustChainError):
    """Raised when a tool is executed outside the enforcement system."""
    
    def __init__(self, tool_name: str, message: str = None):
        super().__init__(
            message or f"Unauthorized execution of tool '{tool_name}' - use ToolExecutionEnforcer",
            error_code="UNAUTHORIZED_TOOL_EXECUTION",
            details={"tool_name": tool_name}
        )


@dataclass
class ToolExecution:
    """Record of a tool execution with cryptographic proof."""
    
    request_id: str
    tool_name: str
    tool_input: Any
    result: Any
    signature: str
    timestamp: float
    execution_time_ms: float
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "result": self.result,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
            "verified": self.verified
        }

    def matches_claim(self, claim: HallucinatedClaim) -> float:
        """Calculate similarity score between this execution and a claim (0.0-1.0)."""
        score = 0.0
        
        # Tool name matching (very important)
        if claim.tool_name:
            if claim.tool_name.lower() in self.tool_name.lower():
                score += 0.5
            elif any(part in self.tool_name.lower() for part in claim.tool_name.lower().split('_')):
                score += 0.3
        
        # API reference patterns
        claim_text_lower = claim.claim_text.lower()
        
        # Check for API/tool references in claim
        if any(keyword in claim_text_lower for keyword in ['api', 'tool', 'checked', 'retrieved', 'called']):
            if 'weather' in claim_text_lower and 'weather' in self.tool_name.lower():
                score += 0.4
            elif 'stock' in claim_text_lower and 'stock' in self.tool_name.lower():
                score += 0.4
            elif 'news' in claim_text_lower and 'news' in self.tool_name.lower():
                score += 0.4
        
        # Input context matching (location, symbol, etc.)
        input_text = str(self.tool_input).lower()
        if input_text in claim_text_lower or any(word in claim_text_lower for word in input_text.split() if len(word) > 2):
            score += 0.3
        
        # Result data matching
        if isinstance(self.result, dict):
            result_values = []
            for value in self.result.values():
                if isinstance(value, (str, int, float)):
                    result_values.append(str(value).lower())
            
            # Check if any result values appear in the claim
            for value in result_values:
                if value in claim_text_lower:
                    score += 0.2
                    break
        
        # Temporal proximity bonus (claims about recent executions more likely to match)
        import time
        time_diff = abs(time.time() - self.timestamp)
        if time_diff < 10:  # Within 10 seconds
            score += 0.1
        
        return min(score, 1.0)


class ToolExecutionRegistry:
    """Central registry of all tool executions with cryptographic proofs."""
    
    def __init__(self):
        self.executions: Dict[str, ToolExecution] = {}
        self.executions_by_tool: Dict[str, List[str]] = {}
        self.recent_executions: List[str] = []  # Most recent first
        self._lock = RLock()
        
    def register_execution(self, execution: ToolExecution) -> None:
        """Register a new tool execution."""
        with self._lock:
            self.executions[execution.request_id] = execution
            
            # Index by tool name
            if execution.tool_name not in self.executions_by_tool:
                self.executions_by_tool[execution.tool_name] = []
            self.executions_by_tool[execution.tool_name].append(execution.request_id)
            
            # Track recent executions (keep last 100)
            self.recent_executions.insert(0, execution.request_id)
            if len(self.recent_executions) > 100:
                self.recent_executions = self.recent_executions[:100]
    
    def find_matching_executions(self, claim: HallucinatedClaim, 
                                min_score: float = 0.4) -> List[Tuple[ToolExecution, float]]:
        """Find executions that might match a claim."""
        matches = []
        
        with self._lock:
            # Check recent executions first (most likely to match)
            for request_id in self.recent_executions[:20]:  # Check last 20
                execution = self.executions.get(request_id)
                if execution:
                    score = execution.matches_claim(claim)
                    if score >= min_score:
                        matches.append((execution, score))
        
        # Sort by score (highest first)
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def get_execution(self, request_id: str) -> Optional[ToolExecution]:
        """Get execution by request ID."""
        with self._lock:
            return self.executions.get(request_id)
    
    def get_recent_executions(self, limit: int = 10) -> List[ToolExecution]:
        """Get most recent executions."""
        with self._lock:
            recent_ids = self.recent_executions[:limit]
            return [self.executions[rid] for rid in recent_ids if rid in self.executions]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            return {
                "total_executions": len(self.executions),
                "tools_used": len(self.executions_by_tool),
                "recent_count": len(self.recent_executions),
                "tools": {tool: len(executions) for tool, executions in self.executions_by_tool.items()}
            }


class ToolExecutionEnforcer:
    """Enforces that all tool executions go through verification."""
    
    def __init__(self, signature_engine: SignatureEngine):
        self.signature_engine = signature_engine
        self.registry = ToolExecutionRegistry()
        self.registered_tools: Dict[str, BaseTrustedTool] = {}
        self.enforcement_enabled = True
        
        # Create default signer if it doesn't exist
        if "default" not in signature_engine._signers:
            try:
                from trustchain.core.models import SignatureAlgorithm
                signature_engine.create_signer("default", SignatureAlgorithm.ED25519)
            except Exception as e:
                print(f"⚠️ Warning: Could not create default signer: {e}")
        
    def register_tool(self, tool: BaseTrustedTool) -> None:
        """Register a tool for enforcement."""
        self.registered_tools[tool.tool_id] = tool
        
    def execute_tool(self, tool_name: str, tool_input: Any, 
                    context: Optional[Dict[str, Any]] = None) -> ToolExecution:
        """Execute a tool through the enforcement system."""
        if tool_name not in self.registered_tools:
            raise ValueError(f"Tool '{tool_name}' not registered with enforcer")
        
        tool = self.registered_tools[tool_name]
        request_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Execute the actual tool (handle both sync and async)
            if hasattr(tool, 'execute'):
                result = tool.execute(tool_input)
                
                # Handle async results
                import inspect
                if inspect.iscoroutine(result):
                    import asyncio
                    result = asyncio.get_event_loop().run_until_complete(result)
            else:
                # Fallback for function-based tools
                result = tool(tool_input)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Create signed response using proper method
            signed_response = self.signature_engine.sign_response(
                signer_id="default",
                request_id=request_id,
                tool_id=tool_name,
                data=result,
                execution_time_ms=execution_time
            )
            
            # Create execution record
            execution = ToolExecution(
                request_id=request_id,
                tool_name=tool_name,
                tool_input=tool_input,
                result=result,
                signature=signed_response.signature.signature,
                timestamp=time.time(),
                execution_time_ms=execution_time,
                verified=True
            )
            
            # Register the execution
            self.registry.register_execution(execution)
            
            return execution
            
        except Exception as e:
            # Even failed executions are recorded
            execution_time = (time.time() - start_time) * 1000
            
            error_result = {
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            execution = ToolExecution(
                request_id=request_id,
                tool_name=tool_name,
                tool_input=tool_input,
                result=error_result,
                signature="",
                timestamp=time.time(),
                execution_time_ms=execution_time,
                verified=False
            )
            
            self.registry.register_execution(execution)
            raise
    
    def verify_claim_against_executions(self, claim: HallucinatedClaim) -> Optional[ToolExecution]:
        """Verify if a claim matches any registered execution."""
        matches = self.registry.find_matching_executions(claim, min_score=0.5)
        
        if matches:
            # Return the best match if it's reasonably confident
            best_execution, score = matches[0]
            if score >= 0.5:  # Moderate confidence threshold
                return best_execution
        
        return None


@dataclass
class VerificationProof:
    """Proof that a claim is backed by a real tool execution."""
    
    claim_text: str
    execution: ToolExecution
    confidence_score: float
    verification_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "execution": self.execution.to_dict(),
            "confidence_score": self.confidence_score,
            "verification_url": self.verification_url
        }


class ResponseVerifier:
    """Verifies agent responses against recorded tool executions."""
    
    def __init__(self, enforcer: ToolExecutionEnforcer):
        self.enforcer = enforcer
        self.claim_extractor = ClaimExtractor()
        
    def verify_response(self, response: str) -> Tuple[str, List[VerificationProof], List[HallucinatedClaim]]:
        """Verify a response and add proof markers."""
        claims = self.claim_extractor.extract_claims(response)
        proofs = []
        unverified_claims = []
        verified_response = response
        
        for claim in claims:
            execution = self.enforcer.verify_claim_against_executions(claim)
            
            if execution:
                # Create proof
                confidence = execution.matches_claim(claim)
                proof = VerificationProof(
                    claim_text=claim.claim_text,
                    execution=execution,
                    confidence_score=confidence,
                    verification_url=f"/verify/{execution.request_id}"
                )
                proofs.append(proof)
                
                # Add verification marker to response
                marker = f" [✓ Verified: {execution.request_id[:8]}]"
                verified_response = verified_response.replace(
                    claim.claim_text,
                    claim.claim_text + marker
                )
            else:
                # Mark as unverified
                unverified_claims.append(claim)
                marker = " [❌ UNVERIFIED - POSSIBLE HALLUCINATION]"
                verified_response = verified_response.replace(
                    claim.claim_text,
                    claim.claim_text + marker
                )
        
        return verified_response, proofs, unverified_claims
    
    def format_verification_summary(self, proofs: List[VerificationProof], 
                                  unverified: List[HallucinatedClaim]) -> str:
        """Generate a human-readable verification summary."""
        total_claims = len(proofs) + len(unverified)
        verified_count = len(proofs)
        
        if total_claims == 0:
            return "✅ No tool claims detected in response"
        
        summary = f"\n📋 Verification Summary:\n"
        summary += f"   Total claims: {total_claims}\n"
        summary += f"   Verified: {verified_count}\n"
        summary += f"   Unverified: {len(unverified)}\n"
        
        if proofs:
            summary += f"\n✅ Verified Claims:\n"
            for proof in proofs:
                summary += f"   - {proof.execution.tool_name} ({proof.execution.request_id[:8]}) - {proof.confidence_score:.1%} confidence\n"
        
        if unverified:
            summary += f"\n❌ Unverified Claims:\n"
            for claim in unverified:
                summary += f"   - {claim.claim_text}\n"
        
        return summary


class EnforcedAgent:
    """Wrapper that enforces tool execution verification for any agent."""
    
    def __init__(self, agent: Any, enforcer: ToolExecutionEnforcer, strict_mode: bool = False):
        self.agent = agent
        self.enforcer = enforcer
        self.verifier = ResponseVerifier(enforcer)
        self.strict_mode = strict_mode
        
    def run(self, input_query: str, **kwargs) -> Dict[str, Any]:
        """Run agent with tool enforcement."""
        # Execute the agent normally
        raw_response = self.agent.run(input_query, **kwargs)
        
        # Verify the response
        verified_response, proofs, unverified = self.verifier.verify_response(raw_response)
        
        # In strict mode, reject responses with unverified claims
        if self.strict_mode and unverified:
            verified_response = (
                f"⚠️ I cannot provide this information as some claims could not be verified. "
                f"Detected {len(unverified)} unverified claim(s). Please ensure all tools are "
                f"executed through the proper verification system."
            )
        
        # Add verification summary
        summary = self.verifier.format_verification_summary(proofs, unverified)
        
        return {
            "response": verified_response,
            "verification_summary": summary,
            "proofs": [p.to_dict() for p in proofs],
            "unverified_claims": [c.to_dict() for c in unverified],
            "fully_verified": len(unverified) == 0,
            "total_executions": len(self.enforcer.registry.executions)
        }


# Convenience functions
def create_tool_enforcer(signature_engine: SignatureEngine, tools: List[BaseTrustedTool] = None) -> ToolExecutionEnforcer:
    """Create a tool execution enforcer with optional pre-registered tools."""
    enforcer = ToolExecutionEnforcer(signature_engine)
    
    if tools:
        for tool in tools:
            enforcer.register_tool(tool)
    
    return enforcer


def wrap_agent_with_enforcement(agent: Any, enforcer: ToolExecutionEnforcer, 
                               strict_mode: bool = False) -> EnforcedAgent:
    """Wrap any agent with tool execution enforcement."""
    return EnforcedAgent(agent, enforcer, strict_mode) 