"""Decorators for creating trusted tools in TrustChain."""

import functools
from typing import Any, Callable, Optional, List, Union

from trustchain.core.models import SignatureAlgorithm, TrustLevel
from trustchain.tools.base import FunctionTrustedTool, MultiSignatureTool, register_tool
from trustchain.registry.base import TrustRegistry
from trustchain.core.signatures import SignatureEngine


def TrustedTool(
    tool_id: str,
    description: Optional[str] = None,
    registry: Optional[TrustRegistry] = None,
    signature_engine: Optional[SignatureEngine] = None,
    algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519,
    trust_level: TrustLevel = TrustLevel.MEDIUM,
    require_nonce: bool = True,
    auto_register: bool = True,
    register_globally: bool = True,
    multi_sig: bool = False,
    required_signatures: Optional[List[str]] = None,
    threshold: Optional[int] = None,
):
    """
    Decorator to create a trusted tool from a function.

    Args:
        tool_id: Unique identifier for the tool
        description: Optional description of the tool
        registry: Trust registry to use (defaults to memory registry)
        signature_engine: Signature engine to use
        algorithm: Cryptographic algorithm for signatures
        trust_level: Trust level for the tool
        require_nonce: Whether to require nonce for replay protection
        auto_register: Whether to automatically register the tool
        register_globally: Whether to register in global tool registry
        multi_sig: Whether to use multi-signature
        required_signatures: List of required signers for multi-sig
        threshold: Minimum number of signatures required for multi-sig

    Example:
        @TrustedTool("weather_api_v1")
        async def get_weather(location: str) -> dict:
            return {"temperature": 15, "humidity": 60, "location": location}
    """

    def decorator(func: Callable) -> Callable:
        # Create the appropriate tool type
        if multi_sig:
            if not required_signatures or not threshold:
                raise ValueError(
                    "Multi-signature tools require required_signatures and threshold"
                )

            class MultiSigFunctionTool(MultiSignatureTool):
                def __init__(self):
                    super().__init__(
                        tool_id=tool_id,
                        required_signers=required_signatures,
                        threshold=threshold,
                        registry=registry,
                        signature_engine=signature_engine,
                        algorithm=algorithm,
                        trust_level=trust_level,
                        require_nonce=require_nonce,
                        auto_register=auto_register,
                    )
                    self.func = func
                    self.description = (
                        description or f"Multi-signature trusted tool: {tool_id}"
                    )

                    # Update metadata
                    self.metadata.update(
                        {
                            "description": self.description,
                            "function_name": getattr(func, "__name__", "unknown"),
                        }
                    )

                async def execute(self, *args, **kwargs) -> Any:
                    """Execute the wrapped function with multi-signature."""
                    import asyncio

                    if asyncio.iscoroutinefunction(self.func):
                        return await self.func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(
                            None, lambda: self.func(*args, **kwargs)
                        )

            tool = MultiSigFunctionTool()
        else:
            tool = FunctionTrustedTool(
                tool_id=tool_id,
                func=func,
                description=description,
                registry=registry,
                signature_engine=signature_engine,
                algorithm=algorithm,
                trust_level=trust_level,
                require_nonce=require_nonce,
                auto_register=auto_register,
            )

        # Register globally if requested
        if register_globally:
            register_tool(tool)

        # Create wrapper function that calls the tool
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract TrustChain-specific arguments
            request_id = kwargs.pop("request_id", None)
            nonce = kwargs.pop("nonce", None)
            caller_id = kwargs.pop("caller_id", "unknown")
            verify_response = kwargs.pop("verify_response", True)

            # Call the tool
            return await tool(
                *args,
                request_id=request_id,
                nonce=nonce,
                caller_id=caller_id,
                verify_response=verify_response,
                **kwargs,
            )

        # Attach tool instance to the wrapper for direct access
        wrapper._trustchain_tool = tool
        wrapper.tool_id = tool_id
        wrapper.get_statistics = tool.get_statistics
        wrapper.reset_statistics = tool.reset_statistics

        return wrapper

    return decorator


def trusted_tool(tool_id: str, **kwargs):
    """
    Simple decorator alias for TrustedTool.

    Example:
        @trusted_tool("simple_calculator")
        def add_numbers(a: int, b: int) -> int:
            return a + b
    """
    return TrustedTool(tool_id, **kwargs)


def high_security_tool(tool_id: str, **kwargs):
    """
    Decorator for high-security tools with enhanced protection.

    Example:
        @high_security_tool("financial_transaction")
        async def process_payment(amount: float, recipient: str) -> dict:
            return {"transaction_id": "tx_123", "status": "completed"}
    """
    kwargs.setdefault("trust_level", TrustLevel.HIGH)
    kwargs.setdefault("algorithm", SignatureAlgorithm.ED25519)
    kwargs.setdefault("require_nonce", True)

    return TrustedTool(tool_id, **kwargs)


def multi_signature_tool(
    tool_id: str, required_signatures: List[str], threshold: int, **kwargs
):
    """
    Decorator for multi-signature tools.

    Example:
        @multi_signature_tool(
            "critical_operation",
            required_signatures=["security", "compliance", "operations"],
            threshold=2
        )
        async def critical_operation(data: dict) -> dict:
            return {"approved": True}
    """
    kwargs.update(
        {
            "multi_sig": True,
            "required_signatures": required_signatures,
            "threshold": threshold,
            "trust_level": TrustLevel.CRITICAL,
        }
    )

    return TrustedTool(tool_id, **kwargs)


def low_latency_tool(tool_id: str, **kwargs):
    """
    Decorator for low-latency tools with minimal overhead.

    Example:
        @low_latency_tool("quick_lookup")
        def lookup_value(key: str) -> str:
            return cache.get(key, "not_found")
    """
    kwargs.setdefault("require_nonce", False)  # Skip nonce for speed
    kwargs.setdefault("trust_level", TrustLevel.LOW)
    kwargs.setdefault("auto_register", False)  # Skip auto-registration

    return TrustedTool(tool_id, **kwargs)


def audit_tool(tool_id: str, **kwargs):
    """
    Decorator for audit-critical tools with maximum security.

    Example:
        @audit_tool("compliance_check")
        async def check_compliance(transaction: dict) -> dict:
            return {"compliant": True, "audit_trail": "..."}
    """
    kwargs.setdefault("trust_level", TrustLevel.CRITICAL)
    kwargs.setdefault("algorithm", SignatureAlgorithm.ED25519)
    kwargs.setdefault("require_nonce", True)

    return TrustedTool(tool_id, **kwargs)


def experimental_tool(tool_id: str, **kwargs):
    """
    Decorator for experimental tools with relaxed security.

    Example:
        @experimental_tool("beta_feature")
        def beta_function(data: dict) -> dict:
            return {"result": "experimental"}
    """
    kwargs.setdefault("trust_level", TrustLevel.LOW)
    kwargs.setdefault("require_nonce", False)
    kwargs.setdefault("auto_register", False)

    return TrustedTool(tool_id, **kwargs)


# Convenience functions for dynamic tool creation


def create_trusted_function(func: Callable, tool_id: str, **kwargs) -> Callable:
    """
    Dynamically create a trusted tool from an existing function.

    Example:
        def my_function(x: int) -> int:
            return x * 2

        trusted_func = create_trusted_function(my_function, "doubler")
    """
    decorator = TrustedTool(tool_id, **kwargs)
    return decorator(func)


def create_tool_from_class_method(
    obj: Any, method_name: str, tool_id: str, **kwargs
) -> Callable:
    """
    Create a trusted tool from a class method.

    Example:
        class Calculator:
            def add(self, a: int, b: int) -> int:
                return a + b

        calc = Calculator()
        trusted_add = create_tool_from_class_method(calc, "add", "calculator_add")
    """
    method = getattr(obj, method_name)
    if not callable(method):
        raise ValueError(f"Method {method_name} is not callable")

    return create_trusted_function(method, tool_id, **kwargs)


def batch_create_tools(functions: dict, **default_kwargs) -> dict:
    """
    Create multiple trusted tools from a dictionary of functions.

    Example:
        functions = {
            "add": lambda a, b: a + b,
            "multiply": lambda a, b: a * b,
            "divide": lambda a, b: a / b if b != 0 else None
        }

        tools = batch_create_tools(functions, trust_level=TrustLevel.MEDIUM)
    """
    tools = {}

    for tool_id, func in functions.items():
        tools[tool_id] = create_trusted_function(func, tool_id, **default_kwargs)

    return tools


# Tool discovery and inspection


def get_tool_info(tool_func: Callable) -> dict:
    """
    Get information about a trusted tool function.

    Example:
        @TrustedTool("example")
        def example_tool():
            pass

        info = get_tool_info(example_tool)
    """
    if not hasattr(tool_func, "_trustchain_tool"):
        raise ValueError("Function is not a TrustChain tool")

    tool = tool_func._trustchain_tool
    return {
        "tool_id": tool.tool_id,
        "algorithm": tool.algorithm.value,
        "trust_level": tool.trust_level.value,
        "require_nonce": tool.require_nonce,
        "metadata": tool.metadata.copy(),
    }


def is_trusted_tool(func: Callable) -> bool:
    """
    Check if a function is a trusted tool.

    Example:
        @TrustedTool("example")
        def example_tool():
            pass

        assert is_trusted_tool(example_tool) == True
    """
    return hasattr(func, "_trustchain_tool") and hasattr(func, "tool_id")
