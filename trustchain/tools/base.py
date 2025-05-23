"""Base classes for trusted tools in TrustChain."""

import time
import uuid
import functools
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union, List
import asyncio
import inspect

from trustchain.core.models import (
    SignedResponse, 
    RequestContext as RequestContextModel,
    SignatureAlgorithm,
    TrustLevel
)
from trustchain.core.signatures import get_signature_engine, SignatureEngine
from trustchain.core.nonce import get_nonce_manager, generate_request_nonce
from trustchain.registry.base import TrustRegistry
from trustchain.registry.memory import MemoryRegistry
from trustchain.utils.exceptions import (
    ToolExecutionError,
    NonceReplayError,
    SignatureVerificationError
)


class BaseTrustedTool(ABC):
    """Base class for trusted tools."""
    
    def __init__(
        self,
        tool_id: str,
        registry: Optional[TrustRegistry] = None,
        signature_engine: Optional[SignatureEngine] = None,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        require_nonce: bool = True,
        auto_register: bool = True
    ):
        self.tool_id = tool_id
        self.algorithm = algorithm
        self.trust_level = trust_level
        self.require_nonce = require_nonce
        self._started = False
        
        # Set up registry
        if registry is None:
            registry = MemoryRegistry()
        self.registry = registry
        
        # Set up signature engine
        if signature_engine is None:
            signature_engine = get_signature_engine()
            if signature_engine is None:
                from trustchain.core.signatures import SignatureEngine
                signature_engine = SignatureEngine(self.registry)
        self.signature_engine = signature_engine
        
        # Tool metadata
        self.metadata = {
            "tool_id": tool_id,
            "algorithm": algorithm.value,
            "trust_level": trust_level.value,
            "require_nonce": require_nonce,
            "created_at": int(time.time() * 1000)
        }
        
        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "signature_failures": 0,
            "nonce_failures": 0,
            "total_execution_time_ms": 0.0
        }
        
        # Auto-register if requested
        if auto_register:
            asyncio.create_task(self._auto_register())
    
    async def _auto_register(self) -> None:
        """Automatically register the tool and create signing key."""
        try:
            # Start registry if not started
            if not self.registry.is_started():
                await self.registry.start()
            
            # Create signer
            signer = self.signature_engine.create_signer(
                self.tool_id, 
                self.algorithm
            )
            
            # Register tool in registry
            await self.registry.register_tool(self.tool_id, self.metadata)
            
            # Get public key and register it
            public_key_b64 = self.signature_engine.get_signer_public_key(self.tool_id)
            if public_key_b64:
                from trustchain.core.models import KeyMetadata
                
                key_metadata = KeyMetadata(
                    key_id=signer.get_public_key_id(),
                    algorithm=self.algorithm,
                    public_key=public_key_b64,
                    tool_id=self.tool_id,
                    created_by=f"auto-registration-{self.tool_id}"
                )
                
                await self.registry.register_key(key_metadata)
            
            self._started = True
            
        except Exception as e:
            # Auto-registration failed, but tool can still work
            print(f"Warning: Auto-registration failed for tool {self.tool_id}: {e}")
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the tool functionality."""
        pass
    
    async def __call__(
        self,
        *args,
        request_id: Optional[str] = None,
        nonce: Optional[str] = None,
        caller_id: str = "unknown",
        verify_response: bool = True,
        **kwargs
    ) -> SignedResponse:
        """Call the tool and return a signed response."""
        start_time = time.time()
        
        # Generate request context
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        if nonce is None and self.require_nonce:
            nonce = generate_request_nonce()
        
        # Update stats
        self.stats["total_calls"] += 1
        
        try:
            # Validate nonce if required
            if self.require_nonce and nonce:
                from trustchain.core.nonce import validate_nonce
                await validate_nonce(nonce, request_id, self.tool_id, caller_id)
            
            # Execute the tool
            result = await self.execute(*args, **kwargs)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            self.stats["total_execution_time_ms"] += execution_time_ms
            
            # Sign the response
            signed_response = self.signature_engine.sign_response(
                signer_id=self.tool_id,
                request_id=request_id,
                tool_id=self.tool_id,
                data=result,
                execution_time_ms=execution_time_ms
            )
            
            # Verify the signature if requested
            if verify_response:
                verification_result = self.signature_engine.verify_response(signed_response)
                if not verification_result.valid:
                    self.stats["signature_failures"] += 1
                    raise SignatureVerificationError(
                        f"Response signature verification failed: {verification_result.error_message}",
                        tool_id=self.tool_id
                    )
            
            self.stats["successful_calls"] += 1
            return signed_response
            
        except NonceReplayError as e:
            self.stats["nonce_failures"] += 1
            self.stats["failed_calls"] += 1
            raise e
        
        except Exception as e:
            self.stats["failed_calls"] += 1
            raise ToolExecutionError(
                self.tool_id,
                f"Tool execution failed: {str(e)}",
                original_error=e
            )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        return {
            "tool_id": self.tool_id,
            "stats": self.stats.copy(),
            "metadata": self.metadata.copy(),
            "avg_execution_time_ms": (
                self.stats["total_execution_time_ms"] / max(1, self.stats["successful_calls"])
            ),
            "success_rate": (
                self.stats["successful_calls"] / max(1, self.stats["total_calls"])
            )
        }
    
    async def reset_statistics(self) -> None:
        """Reset execution statistics."""
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "signature_failures": 0,
            "nonce_failures": 0,
            "total_execution_time_ms": 0.0
        }


class FunctionTrustedTool(BaseTrustedTool):
    """Trusted tool that wraps a function."""
    
    def __init__(
        self,
        tool_id: str,
        func: Callable,
        description: Optional[str] = None,
        **kwargs
    ):
        super().__init__(tool_id, **kwargs)
        self.func = func
        self.description = description or f"Trusted tool: {tool_id}"
        
        # Update metadata with function info
        self.metadata.update({
            "description": self.description,
            "function_name": getattr(func, '__name__', 'unknown'),
            "is_async": asyncio.iscoroutinefunction(func)
        })
    
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the wrapped function."""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(*args, **kwargs)
        else:
            # Run synchronous function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.func(*args, **kwargs))


class MultiSignatureTool(BaseTrustedTool):
    """Tool that requires multiple signatures."""
    
    def __init__(
        self,
        tool_id: str,
        required_signers: List[str],
        threshold: int,
        **kwargs
    ):
        super().__init__(tool_id, **kwargs)
        self.required_signers = required_signers
        self.threshold = threshold
        
        if threshold > len(required_signers):
            raise ValueError("Threshold cannot exceed number of required signers")
        
        # Update metadata
        self.metadata.update({
            "multi_signature": True,
            "required_signers": required_signers,
            "threshold": threshold
        })
    
    async def _auto_register(self) -> None:
        """Register multi-signature tool."""
        await super()._auto_register()
        
        # Create multi-signer
        try:
            self.signature_engine.create_multi_signer(
                self.tool_id,
                self.required_signers,
                self.threshold
            )
        except Exception as e:
            print(f"Warning: Failed to create multi-signer for {self.tool_id}: {e}")
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute with multi-signature verification."""
        pass


class ToolRegistry:
    """Registry for managing trusted tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTrustedTool] = {}
    
    def register_tool(self, tool: BaseTrustedTool) -> None:
        """Register a trusted tool."""
        self._tools[tool.tool_id] = tool
    
    def get_tool(self, tool_id: str) -> Optional[BaseTrustedTool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)
    
    def list_tools(self) -> List[str]:
        """List all registered tool IDs."""
        return list(self._tools.keys())
    
    async def call_tool(
        self,
        tool_id: str,
        *args,
        **kwargs
    ) -> SignedResponse:
        """Call a tool by ID."""
        tool = self.get_tool(tool_id)
        if not tool:
            raise ToolExecutionError(tool_id, f"Tool not found: {tool_id}")
        
        return await tool(*args, **kwargs)
    
    async def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all tools."""
        stats = {}
        for tool_id, tool in self._tools.items():
            stats[tool_id] = await tool.get_statistics()
        return stats


# Global tool registry
_global_tool_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_tool_registry


def register_tool(tool: BaseTrustedTool) -> None:
    """Register a tool in the global registry."""
    _global_tool_registry.register_tool(tool) 