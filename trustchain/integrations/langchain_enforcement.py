"""
LangChain Enforcement Integration for TrustChain.

This module provides automatic tool execution enforcement for LangChain agents,
ensuring all tool calls are tracked and can be verified against agent claims.
"""

import json
from typing import Any, Dict, List, Optional, Union

try:
    from langchain.agents import (
        AgentExecutor,
        BaseMultiActionAgent,
        BaseSingleActionAgent,
    )
    from langchain.callbacks import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish
    from langchain.tools import BaseTool
    from langchain.tools.base import ToolException

    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Create dummy classes for when LangChain is not installed
    class BaseTool:
        pass

    class BaseCallbackHandler:
        pass

    class AgentExecutor:
        pass

    class AgentAction:
        pass

    class AgentFinish:
        pass

    LANGCHAIN_AVAILABLE = False

from trustchain.monitoring.tool_enforcement import (
    ResponseVerifier,
    ToolExecutionEnforcer,
    UnauthorizedToolExecution,
)
from trustchain.tools.base import BaseTrustedTool


class EnforcedLangChainTool(BaseTool if LANGCHAIN_AVAILABLE else object):
    """LangChain tool that routes through ToolExecutionEnforcer."""

    def __init__(self, enforcer: ToolExecutionEnforcer, tool_name: str, **kwargs):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")

        self.enforcer = enforcer
        self.tool_name = tool_name

        if tool_name not in enforcer.registered_tools:
            raise ValueError(f"Tool '{tool_name}' not registered with enforcer")

        trusted_tool = enforcer.registered_tools[tool_name]

        super().__init__(
            name=tool_name,
            description=trusted_tool.description or f"Enforced tool: {tool_name}",
            **kwargs,
        )

    def _run(self, tool_input: str, **kwargs) -> str:
        """Execute through the enforcer."""
        try:
            execution = self.enforcer.execute_tool(self.tool_name, tool_input)

            # Return formatted result with verification info
            return json.dumps(
                {
                    "result": execution.result,
                    "verification": {
                        "request_id": execution.request_id,
                        "verified": execution.verified,
                        "timestamp": execution.timestamp,
                        "signature": (
                            execution.signature[:16] + "..."
                            if execution.signature
                            else None
                        ),
                    },
                }
            )

        except Exception as e:
            raise ToolException(f"Enforced tool execution failed: {str(e)}")

    async def _arun(self, tool_input: str, **kwargs) -> str:
        """Async version (currently synchronous)."""
        return self._run(tool_input, **kwargs)


class ToolEnforcementCallbackHandler(
    BaseCallbackHandler if LANGCHAIN_AVAILABLE else object
):
    """Callback handler that enforces tool execution tracking."""

    def __init__(self, enforcer: ToolExecutionEnforcer, strict_mode: bool = False):
        if not LANGCHAIN_AVAILABLE:
            return

        super().__init__()
        self.enforcer = enforcer
        self.verifier = ResponseVerifier(enforcer)
        self.strict_mode = strict_mode
        self.current_executions = {}

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Track tool start."""
        tool_name = serialized.get("name", "unknown")

        # Verify tool is registered with enforcer
        if tool_name not in self.enforcer.registered_tools:
            if self.strict_mode:
                raise UnauthorizedToolExecution(
                    tool_name,
                    f"Tool '{tool_name}' not registered with enforcer. Register with enforcer.register_tool()",
                )

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Track tool completion."""
        # Tool execution should have been recorded by the enforced tool
        pass

    def on_agent_finish(self, finish: "AgentFinish", **kwargs: Any) -> Any:
        """Verify agent's final response."""
        if not LANGCHAIN_AVAILABLE:
            return

        output = finish.return_values.get("output", "")
        if isinstance(output, str):
            verified_response, proofs, unverified = self.verifier.verify_response(
                output
            )

            # Add verification info to the finish
            finish.return_values["verification"] = {
                "verified_response": verified_response,
                "proofs": [p.to_dict() for p in proofs],
                "unverified_claims": [c.to_dict() for c in unverified],
                "fully_verified": len(unverified) == 0,
            }

            # In strict mode, modify output if unverified claims exist
            if self.strict_mode and unverified:
                finish.return_values["output"] = (
                    f"⚠️ Response contains {len(unverified)} unverified claims. "
                    f"Some information could not be cryptographically verified."
                )


class EnforcedAgentExecutor(AgentExecutor if LANGCHAIN_AVAILABLE else object):
    """AgentExecutor with built-in tool execution enforcement."""

    def __init__(
        self,
        agent: Union["BaseSingleActionAgent", "BaseMultiActionAgent"],
        tools: List[BaseTool],
        enforcer: ToolExecutionEnforcer,
        strict_mode: bool = False,
        **kwargs,
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")

        # Replace regular tools with enforced versions
        enforced_tools = []
        for tool in tools:
            if hasattr(tool, "name") and tool.name in enforcer.registered_tools:
                # Replace with enforced version
                enforced_tool = EnforcedLangChainTool(enforcer, tool.name)
                enforced_tools.append(enforced_tool)
            else:
                # Keep original tool but warn
                enforced_tools.append(tool)
                if strict_mode:
                    print(
                        f"⚠️ Warning: Tool '{getattr(tool, 'name', 'unknown')}' not registered with enforcer"
                    )

        # Add enforcement callback
        callbacks = kwargs.get("callbacks", [])
        callbacks.append(ToolEnforcementCallbackHandler(enforcer, strict_mode))
        kwargs["callbacks"] = callbacks

        super().__init__(agent=agent, tools=enforced_tools, **kwargs)

        self.enforcer = enforcer
        self.verifier = ResponseVerifier(enforcer)
        self.strict_mode = strict_mode

    def run(self, inputs: Union[str, Dict[str, Any]], **kwargs) -> Any:
        """Run with enforcement and verification."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")

        # Execute the agent
        result = super().run(inputs, **kwargs)

        # If result is a string, verify it
        if isinstance(result, str):
            verified_response, proofs, unverified = self.verifier.verify_response(
                result
            )

            if self.strict_mode and unverified:
                # In strict mode, return verification error
                return {
                    "response": f"⚠️ Cannot provide verified response. {len(unverified)} claims could not be verified.",
                    "original_response": result,
                    "unverified_claims": [c.to_dict() for c in unverified],
                    "verification_failed": True,
                }

            # Return enhanced result with verification info
            return {
                "response": verified_response,
                "proofs": [p.to_dict() for p in proofs],
                "unverified_claims": [c.to_dict() for c in unverified],
                "fully_verified": len(unverified) == 0,
                "original_response": result,
            }

        return result


def create_enforced_langchain_tools(enforcer: ToolExecutionEnforcer) -> List[BaseTool]:
    """Create LangChain tools for all registered enforcer tools."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    tools = []
    for tool_name in enforcer.registered_tools:
        enforced_tool = EnforcedLangChainTool(enforcer, tool_name)
        tools.append(enforced_tool)

    return tools


def create_enforced_agent_executor(
    agent: Union["BaseSingleActionAgent", "BaseMultiActionAgent"],
    enforcer: ToolExecutionEnforcer,
    strict_mode: bool = False,
    **kwargs,
) -> "EnforcedAgentExecutor":
    """Create an agent executor with automatic tool enforcement."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    # Create enforced tools from registered tools
    tools = create_enforced_langchain_tools(enforcer)

    return EnforcedAgentExecutor(
        agent=agent, tools=tools, enforcer=enforcer, strict_mode=strict_mode, **kwargs
    )


def register_langchain_tool_with_enforcer(
    tool: BaseTool,
    enforcer: ToolExecutionEnforcer,
    trusted_tool: Optional[BaseTrustedTool] = None,
) -> None:
    """Register a LangChain tool with the enforcer."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    if trusted_tool is None:
        # Create a wrapper trusted tool
        class LangChainTrustedTool(BaseTrustedTool):
            def __init__(self, langchain_tool: BaseTool):
                super().__init__(
                    tool_id=langchain_tool.name, description=langchain_tool.description
                )
                self.langchain_tool = langchain_tool

            def execute(self, input_data: Any) -> Any:
                return self.langchain_tool._run(input_data)

        trusted_tool = LangChainTrustedTool(tool)

    enforcer.register_tool(trusted_tool)


# Example usage patterns
def demo_enforcement_patterns():
    """Demonstrate different enforcement patterns."""
    if not LANGCHAIN_AVAILABLE:
        print("❌ LangChain not available")
        return

    print("🔧 Enforcement Patterns:")
    print("1. Manual tool registration with enforcer")
    print("2. Automatic agent wrapping with enforcement")
    print("3. Strict mode with verification rejection")
    print("4. Verification summary in responses")


# Export main classes
__all__ = [
    "EnforcedLangChainTool",
    "ToolEnforcementCallbackHandler",
    "EnforcedAgentExecutor",
    "create_enforced_langchain_tools",
    "create_enforced_agent_executor",
    "register_langchain_tool_with_enforcer",
    "LANGCHAIN_AVAILABLE",
]
