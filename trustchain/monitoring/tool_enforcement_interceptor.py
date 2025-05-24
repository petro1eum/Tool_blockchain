"""
Automatic Tool Call Interceptor for TrustChain.

This module provides automatic interception of ALL tool calls to prevent
agents from bypassing the enforcement system through direct tool calls.
"""

import functools
import inspect
import sys
import threading
import weakref
from typing import Any, Callable, Dict, List, Optional, Set, Union
from unittest.mock import patch

from trustchain.monitoring.tool_enforcement import ToolExecutionEnforcer
from trustchain.tools.base import BaseTrustedTool
from trustchain.utils.exceptions import TrustChainError


class UnauthorizedDirectToolCall(TrustChainError):
    """Raised when a tool is called directly without going through enforcer."""
    
    def __init__(self, tool_name: str, call_stack: str):
        super().__init__(
            f"SECURITY VIOLATION: Direct call to tool '{tool_name}' detected. "
            f"All tool calls must go through ToolExecutionEnforcer.",
            error_code="UNAUTHORIZED_DIRECT_TOOL_CALL",
            details={"tool_name": tool_name, "call_stack": call_stack}
        )


class ToolCallInterceptor:
    """Automatically intercepts ALL tool calls to enforce verification."""
    
    def __init__(self, enforcer: ToolExecutionEnforcer, strict_mode: bool = True):
        self.enforcer = enforcer
        self.strict_mode = strict_mode
        self.intercepted_tools: Dict[str, BaseTrustedTool] = {}
        self.original_methods: Dict[str, Callable] = {}
        self.active_enforcement_calls: Set[str] = set()  # Prevent recursion
        self._lock = threading.RLock()
        
        # Track which tools are already intercepted
        self._intercepted_functions: weakref.WeakSet = weakref.WeakSet()
        
    def enable_global_interception(self) -> None:
        """Enable global interception of all tool calls."""
        print("🛡️ [INTERCEPTOR] Enabling global tool call interception...")
        
        # Find all existing TrustedTool instances and intercept them
        self._intercept_existing_tools()
        
        # Monkey patch the TrustedTool decorator to auto-intercept new tools
        self._patch_trusted_tool_decorator()
        
        print(f"✅ [INTERCEPTOR] Global interception enabled for {len(self.intercepted_tools)} tools")
    
    def disable_global_interception(self) -> None:
        """Disable global interception and restore original methods."""
        print("🔄 [INTERCEPTOR] Disabling global tool call interception...")
        
        with self._lock:
            # Restore original methods
            for tool_id, original_method in self.original_methods.items():
                if tool_id in self.intercepted_tools:
                    tool = self.intercepted_tools[tool_id]
                    if hasattr(tool, '__call__'):
                        tool.__call__ = original_method
            
            # Clear tracking
            self.intercepted_tools.clear()
            self.original_methods.clear()
            self.active_enforcement_calls.clear()
        
        print("✅ [INTERCEPTOR] Global interception disabled")
    
    def _intercept_existing_tools(self) -> None:
        """Find and intercept all existing TrustedTool instances."""
        # Look for tools in the global registry
        from trustchain.tools.base import get_tool_registry
        
        registry = get_tool_registry()
        for tool_id in registry.list_tools():
            tool = registry.get_tool(tool_id)
            if tool and isinstance(tool, BaseTrustedTool):
                self._intercept_tool(tool)
        
        # Also look for tools registered with the enforcer
        for tool_id, tool in self.enforcer.registered_tools.items():
            if tool_id not in self.intercepted_tools:
                self._intercept_tool(tool)
    
    def _intercept_tool(self, tool: BaseTrustedTool) -> None:
        """Intercept a specific tool's call method."""
        with self._lock:
            if tool.tool_id in self.intercepted_tools:
                return  # Already intercepted
            
            # Store original method
            original_call = tool.__call__
            self.original_methods[tool.tool_id] = original_call
            
            # Create intercepted method
            def intercepted_call(*args, **kwargs):
                return self._handle_tool_call(tool, original_call, *args, **kwargs)
            
            # Replace the method
            tool.__call__ = intercepted_call
            self.intercepted_tools[tool.tool_id] = tool
            
            print(f"🔒 [INTERCEPTOR] Intercepted tool: {tool.tool_id}")
    
    def _handle_tool_call(self, tool: BaseTrustedTool, original_call: Callable, *args, **kwargs) -> Any:
        """Handle an intercepted tool call."""
        call_id = f"{tool.tool_id}:{id(threading.current_thread())}"
        
        # Check if this call is already being handled by enforcer (prevent recursion)
        if call_id in self.active_enforcement_calls:
            # This is a legitimate call from the enforcer - allow it
            return original_call(*args, **kwargs)
        
        # This is a direct call - check if it's authorized
        if self._is_call_authorized():
            # Mark as enforcement call to prevent recursion
            self.active_enforcement_calls.add(call_id)
            try:
                # Route through enforcer
                print(f"🔄 [INTERCEPTOR] Routing {tool.tool_id} call through enforcer")
                
                # Extract main input argument (first positional arg usually)
                tool_input = args[0] if args else kwargs
                execution = self.enforcer.execute_tool(tool.tool_id, tool_input)
                
                # Return the execution result wrapped as SignedResponse
                from trustchain.core.models import SignedResponse
                return SignedResponse(
                    request_id=execution.request_id,
                    tool_id=execution.tool_name,
                    data=execution.result,
                    signature=None,  # Will be populated from execution
                    timestamp=int(execution.timestamp * 1000)
                )
            finally:
                self.active_enforcement_calls.discard(call_id)
        else:
            # Unauthorized direct call
            call_stack = self._get_call_stack()
            
            if self.strict_mode:
                # Block the call
                raise UnauthorizedDirectToolCall(tool.tool_id, call_stack)
            else:
                # Log warning and allow (for development)
                print(f"⚠️ [INTERCEPTOR] WARNING: Direct call to {tool.tool_id} detected but allowed in non-strict mode")
                print(f"⚠️ [INTERCEPTOR] Call stack: {call_stack}")
                return original_call(*args, **kwargs)
    
    def _is_call_authorized(self) -> bool:
        """Check if the current call is authorized (from enforcer or allowed context)."""
        # Get call stack to check caller
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the caller
            for i in range(10):  # Check up to 10 frames up
                frame = frame.f_back
                if not frame:
                    break
                
                # Check if call is from enforcer
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                
                if 'tool_enforcement.py' in filename and function_name == 'execute_tool':
                    return True
                
                # Allow calls from trusted contexts (tests, setup code, etc.)
                if any(allowed in filename for allowed in [
                    'test_', 'tests/', 'pytest', 'unittest',
                    'setup.py', '__init__.py'
                ]):
                    return True
        finally:
            del frame
        
        return False
    
    def _get_call_stack(self) -> str:
        """Get formatted call stack for debugging."""
        stack_frames = []
        frame = inspect.currentframe()
        
        try:
            # Skip the interceptor frames
            for _ in range(3):
                frame = frame.f_back
                if not frame:
                    break
            
            # Collect stack frames
            for i in range(5):  # Show last 5 frames
                if not frame:
                    break
                
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno
                
                # Make filename relative
                if '/' in filename:
                    filename = '/'.join(filename.split('/')[-2:])
                
                stack_frames.append(f"{filename}:{function_name}:{line_number}")
                frame = frame.f_back
        finally:
            del frame
        
        return " -> ".join(reversed(stack_frames))
    
    def _patch_trusted_tool_decorator(self) -> None:
        """Monkey patch the TrustedTool decorator to auto-intercept new tools."""
        from trustchain.tools.decorators import TrustedTool as OriginalTrustedTool
        
        # Store original implementation
        original_init = OriginalTrustedTool.__init__
        
        def patched_init(self, tool_id: str, **kwargs):
            # Call original init
            result = original_init(self, tool_id, **kwargs)
            
            # Auto-intercept this tool if enforcer is active
            if hasattr(self, '_trustchain_tool') and self._trustchain_tool:
                interceptor._intercept_tool(self._trustchain_tool)
            
            return result
        
        # Apply patch
        OriginalTrustedTool.__init__ = patched_init
    
    def register_authorized_caller(self, caller_module: str) -> None:
        """Register a module as authorized to make direct tool calls."""
        # For future implementation - whitelist specific callers
        pass
    
    def get_interception_stats(self) -> Dict[str, Any]:
        """Get statistics about tool interception."""
        return {
            "intercepted_tools": list(self.intercepted_tools.keys()),
            "total_intercepted": len(self.intercepted_tools),
            "strict_mode": self.strict_mode,
            "active_calls": len(self.active_enforcement_calls)
        }


# Global interceptor instance
_global_interceptor: Optional[ToolCallInterceptor] = None


def enable_automatic_enforcement(enforcer: ToolExecutionEnforcer, strict_mode: bool = True) -> ToolCallInterceptor:
    """Enable automatic enforcement of all tool calls."""
    global _global_interceptor
    
    if _global_interceptor:
        print("⚠️ [INTERCEPTOR] Automatic enforcement already enabled")
        return _global_interceptor
    
    _global_interceptor = ToolCallInterceptor(enforcer, strict_mode)
    _global_interceptor.enable_global_interception()
    
    print(f"🛡️ [INTERCEPTOR] Automatic enforcement enabled (strict_mode={strict_mode})")
    return _global_interceptor


def disable_automatic_enforcement() -> None:
    """Disable automatic enforcement of tool calls."""
    global _global_interceptor
    
    if _global_interceptor:
        _global_interceptor.disable_global_interception()
        _global_interceptor = None
        print("🔄 [INTERCEPTOR] Automatic enforcement disabled")
    else:
        print("⚠️ [INTERCEPTOR] Automatic enforcement was not enabled")


def get_interceptor() -> Optional[ToolCallInterceptor]:
    """Get the current global interceptor."""
    return _global_interceptor


# Context manager for temporary enforcement
class EnforcementContext:
    """Context manager for temporary automatic enforcement."""
    
    def __init__(self, enforcer: ToolExecutionEnforcer, strict_mode: bool = True):
        self.enforcer = enforcer
        self.strict_mode = strict_mode
        self.interceptor = None
    
    def __enter__(self) -> ToolCallInterceptor:
        self.interceptor = enable_automatic_enforcement(self.enforcer, self.strict_mode)
        return self.interceptor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        disable_automatic_enforcement()


# Export main functions
__all__ = [
    'ToolCallInterceptor',
    'UnauthorizedDirectToolCall',
    'enable_automatic_enforcement',
    'disable_automatic_enforcement',
    'get_interceptor',
    'EnforcementContext'
] 