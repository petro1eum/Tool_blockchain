"""
LangChain integration for TrustChain verified tools.

This module provides LangChain tools and agents that are cryptographically
verified and protected against hallucinations.
"""

import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, Union

try:
    from langchain.agents import AgentExecutor, BaseMultiActionAgent, BaseSingleActionAgent
    from langchain.callbacks import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish
    from langchain.tools import BaseTool, Tool
    from langchain.tools.base import ToolException
    from pydantic import BaseModel, Field
    
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Create dummy classes for when LangChain is not installed
    class BaseTool:
        pass
    
    class Tool:
        pass
    
    class BaseCallbackHandler:
        pass
    
    class AgentExecutor:
        pass
    
    class AgentAction:
        pass
    
    class AgentFinish:
        pass
    
    class Field:
        def __init__(self, *args, **kwargs):
            pass
        
        def __call__(self, *args, **kwargs):
            return None
    
    LANGCHAIN_AVAILABLE = False

from trustchain.core.models import SignedResponse
from trustchain.core.signatures import SignatureEngine
from trustchain.monitoring.hallucination_detector import (
    HallucinationDetector, 
    LLMResponseInterceptor,
    ValidationResult,
    HallucinationError
)
from trustchain.tools.base import BaseTrustedTool
from trustchain.utils.exceptions import TrustChainError


class TrustedLangChainTool(BaseTool if LANGCHAIN_AVAILABLE else object):
    """A LangChain tool that produces cryptographically signed results."""
    
    name: str = Field(...)
    description: str = Field(...)
    trusted_tool: BaseTrustedTool = Field(...)
    signature_engine: SignatureEngine = Field(...)
    
    class Config:
        arbitrary_types_allowed = True

    def __init__(self, trusted_tool: BaseTrustedTool, signature_engine: SignatureEngine, **kwargs):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed. Install with: pip install langchain")
        
        super().__init__(
            name=trusted_tool.tool_id,
            description=trusted_tool.description or f"Verified tool: {trusted_tool.tool_id}",
            trusted_tool=trusted_tool,
            signature_engine=signature_engine,
            **kwargs
        )

    def _run(self, *args, **kwargs) -> str:
        """Execute the trusted tool and return signed result."""
        try:
            # Generate request ID for this execution
            request_id = str(uuid.uuid4())
            
            # Execute the trusted tool
            result = self.trusted_tool.execute(*args, **kwargs)
            
            # Create signed response
            signed_response = SignedResponse(
                request_id=request_id,
                tool_id=self.trusted_tool.tool_id,
                data=result,
                signature=self.signature_engine.sign_data(result, self.trusted_tool.tool_id)
            )
            
            # Register with hallucination detector if available
            if hasattr(self, '_hallucination_detector'):
                self._hallucination_detector.verification_registry.register_verified_result(signed_response)
            
            # Return result with verification metadata
            return json.dumps({
                "result": result,
                "verification": {
                    "request_id": request_id,
                    "tool_id": self.trusted_tool.tool_id,
                    "signature": signed_response.signature.signature,
                    "verified": True,
                    "timestamp": signed_response.timestamp
                }
            })
            
        except Exception as e:
            raise ToolException(f"Trusted tool execution failed: {str(e)}")

    async def _arun(self, *args, **kwargs) -> str:
        """Async version of _run."""
        # For now, just run synchronously
        # In future, could implement proper async execution
        return self._run(*args, **kwargs)

    def set_hallucination_detector(self, detector: HallucinationDetector) -> None:
        """Associate this tool with a hallucination detector."""
        self._hallucination_detector = detector


class VerifiedAgentCallbackHandler(BaseCallbackHandler if LANGCHAIN_AVAILABLE else object):
    """Callback handler that validates agent responses for hallucinations."""
    
    def __init__(self, interceptor: LLMResponseInterceptor):
        if not LANGCHAIN_AVAILABLE:
            return
        
        super().__init__()
        self.interceptor = interceptor
        self.validation_results: List[ValidationResult] = []

    def on_agent_finish(self, finish: "AgentFinish", **kwargs: Any) -> Any:
        """Validate the agent's final response."""
        if not LANGCHAIN_AVAILABLE:
            return
        
        output = finish.return_values.get('output', '')
        if isinstance(output, str):
            validated_output, validation = self.interceptor.intercept(output)
            self.validation_results.append(validation)
            
            if not validation.valid:
                # Modify the finish to include validation warning
                finish.return_values['output'] = validated_output
                finish.return_values['validation'] = {
                    'valid': validation.valid,
                    'confidence_score': validation.confidence_score,
                    'message': validation.message,
                    'hallucinations': [h.to_dict() for h in validation.hallucinations]
                }

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        """Validate LLM responses."""
        if not LANGCHAIN_AVAILABLE:
            return
        
        # This could be enhanced to validate intermediate LLM outputs
        pass


class VerifiedAgentExecutor(AgentExecutor if LANGCHAIN_AVAILABLE else object):
    """Enhanced AgentExecutor with hallucination detection."""
    
    def __init__(
        self, 
        agent: Union["BaseSingleActionAgent", "BaseMultiActionAgent"],
        tools: List[BaseTool],
        hallucination_detector: HallucinationDetector,
        strict_mode: bool = False,
        **kwargs
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")
        
        # Create interceptor
        interceptor = LLMResponseInterceptor(hallucination_detector)
        interceptor.auto_reject = strict_mode
        
        # Add verification callback
        callbacks = kwargs.get('callbacks', [])
        callbacks.append(VerifiedAgentCallbackHandler(interceptor))
        kwargs['callbacks'] = callbacks
        
        super().__init__(agent=agent, tools=tools, **kwargs)
        
        self.hallucination_detector = hallucination_detector
        self.interceptor = interceptor
        
        # Associate detector with trusted tools
        for tool in tools:
            if isinstance(tool, TrustedLangChainTool):
                tool.set_hallucination_detector(hallucination_detector)

    def run(self, inputs: Union[str, Dict[str, Any]], **kwargs) -> str:
        """Run with hallucination validation."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")
        
        # Execute normally
        result = super().run(inputs, **kwargs)
        
        # Final validation
        if isinstance(result, str):
            validated_result, validation = self.interceptor.intercept(result)
            
            if not validation.valid and self.interceptor.auto_reject:
                raise HallucinationError(
                    validation.hallucinations,
                    f"Agent response contains {len(validation.hallucinations)} hallucinated claims"
                )
            
            return validated_result
        
        return result


def make_langchain_tool(
    trusted_tool: BaseTrustedTool,
    signature_engine: SignatureEngine,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> BaseTool:
    """Convert a TrustChain trusted tool to a LangChain tool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed. Install with: pip install langchain")
    
    return TrustedLangChainTool(
        trusted_tool=trusted_tool,
        signature_engine=signature_engine,
        name=name or trusted_tool.tool_id,
        description=description or trusted_tool.description or f"Verified tool: {trusted_tool.tool_id}"
    )


def create_verified_agent_executor(
    agent: Union["BaseSingleActionAgent", "BaseMultiActionAgent"],
    trusted_tools: List[BaseTrustedTool],
    signature_engine: SignatureEngine,
    hallucination_detector: HallucinationDetector,
    strict_mode: bool = False,
    **kwargs
) -> "VerifiedAgentExecutor":
    """Create a verified agent executor with trusted tools."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")
    
    # Convert trusted tools to LangChain tools
    langchain_tools = [
        make_langchain_tool(tool, signature_engine) 
        for tool in trusted_tools
    ]
    
    return VerifiedAgentExecutor(
        agent=agent,
        tools=langchain_tools,
        hallucination_detector=hallucination_detector,
        strict_mode=strict_mode,
        **kwargs
    )


# Utility functions for common patterns
def wrap_existing_tool(
    langchain_tool: BaseTool,
    signature_engine: SignatureEngine,
    tool_id: Optional[str] = None
) -> TrustedLangChainTool:
    """Wrap an existing LangChain tool to make it cryptographically verified."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")
    
    class WrappedTrustedTool(BaseTrustedTool):
        def __init__(self, original_tool: BaseTool):
            super().__init__(
                tool_id=tool_id or original_tool.name,
                description=original_tool.description
            )
            self.original_tool = original_tool
        
        def execute(self, *args, **kwargs):
            return self.original_tool._run(*args, **kwargs)
    
    wrapped_tool = WrappedTrustedTool(langchain_tool)
    
    return TrustedLangChainTool(
        trusted_tool=wrapped_tool,
        signature_engine=signature_engine
    )


# Export main functions
__all__ = [
    'TrustedLangChainTool',
    'VerifiedAgentExecutor', 
    'VerifiedAgentCallbackHandler',
    'make_langchain_tool',
    'create_verified_agent_executor',
    'wrap_existing_tool',
    'LANGCHAIN_AVAILABLE'
] 