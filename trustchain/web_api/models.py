"""Pydantic models for TrustChain Web API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    """Request to call a tool."""
    
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    nonce: Optional[str] = Field(None, description="Optional nonce for replay protection")


class ToolCallResponse(BaseModel):
    """Response from tool call."""
    
    success: bool = Field(..., description="Whether the call succeeded")
    signed_response: Optional[Dict[str, Any]] = Field(None, description="Signed response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")


class VerifyRequest(BaseModel):
    """Request to verify a signed response."""
    
    signed_response: Dict[str, Any] = Field(..., description="Signed response to verify")


class VerifyResponse(BaseModel):
    """Response from verification."""
    
    valid: bool = Field(..., description="Whether the signature is valid")
    trust_level: Optional[str] = Field(None, description="Trust level of the signature")
    verification_time_ms: Optional[float] = Field(None, description="Verification time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if verification failed")


class ToolListResponse(BaseModel):
    """Response with list of available tools."""
    
    tools: List[Dict[str, Any]] = Field(..., description="List of available tools")
    total_count: int = Field(..., description="Total number of tools")


class StatsResponse(BaseModel):
    """Response with TrustChain statistics."""
    
    total_tools: int = Field(..., description="Total number of registered tools")
    total_calls: int = Field(..., description="Total number of tool calls")
    cache_size: int = Field(..., description="Number of cached responses")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    version: str = Field(..., description="TrustChain version")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="TrustChain version")
    timestamp: float = Field(..., description="Current timestamp") 