"""FastAPI server for TrustChain Web API."""

import time
from typing import Dict, Any
import asyncio
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
    
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from trustchain.v2 import TrustChain, TrustChainConfig
from .models import (
    ToolCallRequest,
    ToolCallResponse, 
    VerifyRequest,
    VerifyResponse,
    ToolListResponse,
    StatsResponse,
    HealthResponse,
)


class TrustChainWebServer:
    """Web server for TrustChain API."""
    
    def __init__(self, trustchain: TrustChain = None, host: str = "0.0.0.0", port: int = 8000):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI not installed. Install with: pip install fastapi uvicorn")
        
        self.trustchain = trustchain or TrustChain(TrustChainConfig())
        self.host = host
        self.port = port
        self.start_time = time.time()
        self.websocket_connections: Dict[str, WebSocket] = {}
        
        # Create FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            print(f"🚀 TrustChain Web API starting on {self.host}:{self.port}")
            yield
            # Shutdown
            print("🛑 TrustChain Web API shutting down")
        
        self.app = FastAPI(
            title="TrustChain API",
            description="Cryptographically signed tool execution API",
            version="2.0.0",
            lifespan=lifespan
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict this
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                version="2.0.0",
                timestamp=time.time()
            )
        
        @self.app.post("/api/tools/call", response_model=ToolCallResponse)
        async def call_tool(request: ToolCallRequest):
            """Call a registered tool."""
            try:
                start_time = time.time()
                
                # Get the tool function from TrustChain
                if not hasattr(self.trustchain, '_tools') or request.tool_name not in self.trustchain._tools:
                    raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
                
                tool_func = self.trustchain._tools[request.tool_name]
                
                # Execute the tool
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(**request.parameters)
                else:
                    result = tool_func(**request.parameters)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Convert result to dict format for JSON response
                result_dict = {
                    "tool_id": request.tool_name,
                    "data": result.data if hasattr(result, 'data') else result,
                    "signature": result.signature if hasattr(result, 'signature') else "",
                    "signature_id": result.signature_id if hasattr(result, 'signature_id') else "",
                    "timestamp": result.timestamp if hasattr(result, 'timestamp') else time.time(),
                    "nonce": result.nonce if hasattr(result, 'nonce') else request.nonce,
                    "is_verified": result.is_verified if hasattr(result, 'is_verified') else True
                }
                
                # Notify WebSocket clients
                await self._notify_websocket_clients({
                    "type": "tool_call",
                    "tool_name": request.tool_name,
                    "success": True,
                    "execution_time_ms": execution_time
                })
                
                return ToolCallResponse(
                    success=True,
                    signed_response=result_dict,
                    execution_time_ms=execution_time
                )
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Notify WebSocket clients of error
                await self._notify_websocket_clients({
                    "type": "tool_call_error",
                    "tool_name": request.tool_name,
                    "error": str(e),
                    "execution_time_ms": execution_time
                })
                
                return ToolCallResponse(
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                )
        
        @self.app.post("/api/tools/verify", response_model=VerifyResponse)
        async def verify_response(request: VerifyRequest):
            """Verify a signed response."""
            try:
                start_time = time.time()
                
                # Create SignedResponse object from dict
                from trustchain.v2.signer import SignedResponse
                signed_response = SignedResponse(
                    tool_id=request.signed_response["tool_id"],
                    data=request.signed_response["data"],
                    signature=request.signed_response["signature"],
                    signature_id=request.signed_response.get("signature_id", ""),
                    timestamp=request.signed_response.get("timestamp", time.time()),
                    nonce=request.signed_response.get("nonce")
                )
                
                # Verify using TrustChain's signer
                is_valid = self.trustchain.signer.verify(signed_response)
                verification_time = (time.time() - start_time) * 1000
                
                return VerifyResponse(
                    valid=is_valid,
                    trust_level="high" if is_valid else "none",
                    verification_time_ms=verification_time
                )
                
            except Exception as e:
                verification_time = (time.time() - start_time) * 1000
                return VerifyResponse(
                    valid=False,
                    verification_time_ms=verification_time,
                    error=str(e)
                )
        
        @self.app.get("/api/tools", response_model=ToolListResponse)
        async def list_tools():
            """Get list of available tools."""
            tools = []
            
            if hasattr(self.trustchain, '_tools'):
                for tool_name, tool_func in self.trustchain._tools.items():
                    tools.append({
                        "name": tool_name,
                        "description": getattr(tool_func, '__doc__', f"Tool: {tool_name}"),
                        "is_async": asyncio.iscoroutinefunction(tool_func)
                    })
            
            return ToolListResponse(
                tools=tools,
                total_count=len(tools)
            )
        
        @self.app.get("/api/stats", response_model=StatsResponse)
        async def get_stats():
            """Get TrustChain statistics."""
            stats = self.trustchain.get_stats()
            
            return StatsResponse(
                total_tools=stats.get("total_tools", 0),
                total_calls=stats.get("total_calls", 0),
                cache_size=stats.get("cache_size", 0),
                uptime_seconds=time.time() - self.start_time,
                version="2.0.0"
            )
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            connection_id = f"ws_{id(websocket)}"
            self.websocket_connections[connection_id] = websocket
            
            try:
                # Send welcome message
                await websocket.send_json({
                    "type": "connected",
                    "message": "Connected to TrustChain WebSocket",
                    "connection_id": connection_id
                })
                
                # Keep connection alive and handle messages
                while True:
                    try:
                        data = await websocket.receive_json()
                        # Echo back for now (can add more functionality)
                        await websocket.send_json({
                            "type": "echo",
                            "data": data
                        })
                    except WebSocketDisconnect:
                        break
            except Exception as e:
                print(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.pop(connection_id, None)
    
    async def _notify_websocket_clients(self, message: Dict[str, Any]):
        """Notify all connected WebSocket clients."""
        if not self.websocket_connections:
            return
        
        disconnected = []
        for connection_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.websocket_connections.pop(connection_id, None)
    
    def run(self, **kwargs):
        """Run the server."""
        config = {
            "host": self.host,
            "port": self.port,
            "reload": False,
            "access_log": True,
            **kwargs
        }
        
        uvicorn.run(self.app, **config)


def start_server(
    trustchain: TrustChain = None,
    host: str = "0.0.0.0", 
    port: int = 8000,
    **kwargs
) -> None:
    """Start TrustChain web server."""
    if not HAS_FASTAPI:
        raise ImportError("FastAPI not installed. Install with: pip install 'trustchain[web]'")
    
    server = TrustChainWebServer(trustchain, host, port)
    server.run(**kwargs) 