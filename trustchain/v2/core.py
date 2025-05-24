"""Core TrustChain v2 implementation."""

import asyncio
import functools
import time
from collections import deque
from typing import Any, Callable, Dict, Optional, Union

from .config import TrustChainConfig
from .signer import Signer, SignedResponse
from .storage import MemoryStorage, Storage


class TrustChain:
    """Simple API for cryptographically signed tool responses."""
    
    def __init__(self, config: Optional[TrustChainConfig] = None):
        self.config = config or TrustChainConfig()
        self._signer = Signer(self.config.algorithm)
        self._storage = self._create_storage()
        self._tools: Dict[str, Dict[str, Any]] = {}
        
        # Nonce tracking for replay protection
        if self.config.enable_nonce:
            self._used_nonces = deque(maxlen=1000)  # Efficient with deque
    
    def _create_storage(self) -> Storage:
        """Create storage backend based on config."""
        if self.config.storage_backend == "memory":
            return MemoryStorage(self.config.max_cached_responses)
        else:
            raise ValueError(f"Unknown storage backend: {self.config.storage_backend}")
    
    def tool(self, tool_id: str, **options) -> Callable:
        """
        Decorator to create a cryptographically signed tool.
        
        Example:
            @tc.tool("weather_api")
            def get_weather(city: str):
                return {"temp": 20, "city": city}
        """
        def decorator(func: Callable) -> Callable:
            # Store tool metadata
            self._tools[tool_id] = {
                'func': func,
                'options': options,
                'created_at': time.time(),
                'call_count': 0,
            }
            
            # Create wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs) -> SignedResponse:
                    return await self._execute_tool_async(tool_id, func, args, kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs) -> SignedResponse:
                    return self._execute_tool_sync(tool_id, func, args, kwargs)
                return sync_wrapper
        
        return decorator
    
    def _execute_tool_sync(self, tool_id: str, func: Callable, args: tuple, kwargs: dict) -> SignedResponse:
        """Execute a synchronous tool and sign the response."""
        # Update call count
        self._tools[tool_id]['call_count'] += 1
        
        try:
            # Execute the tool
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Generate nonce if enabled
            nonce = None
            if self.config.enable_nonce:
                nonce = self._generate_nonce()
            
            # Sign the response
            signed_response = self._signer.sign(tool_id, result, nonce)
            
            # Store in cache if enabled
            if self.config.enable_cache:
                self._storage.store(
                    signed_response.signature_id,
                    signed_response,
                    ttl=self.config.cache_ttl
                )
            
            # Track execution time
            self._tools[tool_id]['last_execution_time'] = execution_time
            
            return signed_response
            
        except Exception as e:
            # Track errors
            self._tools[tool_id]['last_error'] = str(e)
            raise
    
    async def _execute_tool_async(self, tool_id: str, func: Callable, args: tuple, kwargs: dict) -> SignedResponse:
        """Execute an asynchronous tool and sign the response."""
        # Update call count
        self._tools[tool_id]['call_count'] += 1
        
        try:
            # Execute the tool
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Generate nonce if enabled
            nonce = None
            if self.config.enable_nonce:
                nonce = self._generate_nonce()
            
            # Sign the response
            signed_response = self._signer.sign(tool_id, result, nonce)
            
            # Store in cache if enabled
            if self.config.enable_cache:
                self._storage.store(
                    signed_response.signature_id,
                    signed_response,
                    ttl=self.config.cache_ttl
                )
            
            # Track execution time
            self._tools[tool_id]['last_execution_time'] = execution_time
            
            return signed_response
            
        except Exception as e:
            # Track errors
            self._tools[tool_id]['last_error'] = str(e)
            raise
    
    def verify(self, response: Union[SignedResponse, Dict[str, Any]]) -> bool:
        """Verify a signed response."""
        # Convert dict to SignedResponse if needed
        if isinstance(response, dict):
            response = SignedResponse(**response)
        
        # Verify signature first (before checking nonce)
        is_valid = self._signer.verify(response)
        
        # Cache verification result
        response._verified = is_valid
        
        return is_valid
    
    def _generate_nonce(self) -> str:
        """Generate a unique nonce."""
        import uuid
        nonce = str(uuid.uuid4())
        self._used_nonces.append(nonce)
        return nonce
    
    def _check_nonce(self, nonce: str) -> bool:
        """Check if nonce is valid and not already used."""
        if nonce in self._used_nonces:
            return False
        self._used_nonces.append(nonce)
        return True
    
    def get_tool_stats(self, tool_id: str) -> Dict[str, Any]:
        """Get statistics for a specific tool."""
        if tool_id not in self._tools:
            raise ValueError(f"Unknown tool: {tool_id}")
        
        tool_info = self._tools[tool_id]
        return {
            'tool_id': tool_id,
            'call_count': tool_info['call_count'],
            'created_at': tool_info['created_at'],
            'last_execution_time': tool_info.get('last_execution_time'),
            'last_error': tool_info.get('last_error'),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total_calls = sum(t['call_count'] for t in self._tools.values())
        
        return {
            'total_tools': len(self._tools),
            'total_calls': total_calls,
            'cache_size': self._storage.size() if hasattr(self._storage, 'size') else 0,
            'signer_key_id': self._signer.get_key_id(),
        }
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._storage.clear() 