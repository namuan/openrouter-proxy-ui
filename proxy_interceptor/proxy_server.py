import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from .models import HttpRequest, HttpResponse, InterceptedRequest


@dataclass
class ProxyConfig:
    """Configuration for the proxy server."""
    host: str = "127.0.0.1"
    port: int = 8080
    target_base_url: str = "https://openrouter.ai/api/v1"
    log_requests: bool = True


class ProxyServer:
    """HTTP proxy server for intercepting and logging requests."""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.app = FastAPI(title="Proxy Interceptor")
        self.intercepted_requests: list[InterceptedRequest] = []
        self.is_running = False
        self.server_task: Optional[asyncio.Task] = None
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Handle all incoming requests and forward them."""
            try:
                # Build target URL
                target_url = f"{self.config.target_base_url}/{path}"
                
                # Read request body
                body = await request.body()
                body_str = body.decode() if body else ""
                
                # Create HttpRequest object
                http_request = HttpRequest(
                    timestamp=datetime.now(),
                    method=request.method,
                    url=str(request.url),
                    headers=dict(request.headers),
                    body=body_str
                )
                
                # Forward request to target
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers={k: v for k, v in request.headers.items() 
                                if k.lower() not in ["host", "content-length"]},
                        content=body if body else None,
                        params=request.query_params
                    )
                
                # Create HttpResponse object
                http_response = HttpResponse(
                    status_code=response.status_code,
                    status_text=response.reason_phrase,
                    headers=dict(response.headers),
                    body=response.text
                )
                
                # Create InterceptedRequest and store it
                intercepted = InterceptedRequest(
                    request=http_request,
                    response=http_response
                )
                
                if self.config.log_requests:
                    self.intercepted_requests.append(intercepted)
                
                # Return response to client
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            except Exception as e:
                logging.error(f"Proxy error: {e}")
                return Response(
                    content=json.dumps({"error": str(e)}),
                    status_code=500,
                    headers={"Content-Type": "application/json"}
                )
    
    async def start(self):
        """Start the proxy server."""
        if self.is_running:
            return
            
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        self.server_task = asyncio.create_task(server.serve())
        self.is_running = True
        
    async def stop(self):
        """Stop the proxy server."""
        if not self.is_running or not self.server_task:
            return
            
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass
        self.is_running = False
        self.server_task = None
        
    def get_requests(self) -> list[InterceptedRequest]:
        """Get all intercepted requests."""
        return self.intercepted_requests.copy()
        
    def clear_requests(self):
        """Clear all intercepted requests."""
        self.intercepted_requests.clear()
