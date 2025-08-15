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

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Configuration for the proxy server."""
    host: str = "127.0.0.1"
    port: int = 8080
    target_base_url: str = "https://openrouter.ai/api/v1"
    log_requests: bool = True
    
    def __post_init__(self):
        logger.info(f"ProxyConfig initialized: {self}")


class ProxyServer:
    """HTTP proxy server for intercepting and logging requests."""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.app = FastAPI(title="Proxy Interceptor")
        self.intercepted_requests: list[InterceptedRequest] = []
        self.is_running = False
        self.server_task: Optional[asyncio.Task] = None
        
        logger.info("Initializing ProxyServer")
        self._setup_routes()
        logger.info("ProxyServer routes configured")
        
    def _setup_routes(self):
        """Set up FastAPI routes."""
        logger.debug("Setting up FastAPI routes")
        
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Handle all incoming requests and forward them."""
            logger.info(f"Received request: {request.method} {request.url}")
            
            try:
                # Build target URL
                target_url = f"{self.config.target_base_url}/{path}"
                logger.debug(f"Target URL: {target_url}")
                
                # Read request body
                body = await request.body()
                body_str = body.decode() if body else ""
                logger.debug(f"Request body length: {len(body_str)}")
                
                # Create HttpRequest object
                http_request = HttpRequest(
                    timestamp=datetime.now(),
                    method=request.method,
                    url=str(request.url),
                    headers=dict(request.headers),
                    body=body_str
                )
                logger.debug(f"Created HttpRequest: {http_request.method} {http_request.url}")
                
                # Forward request to target
                logger.info(f"Forwarding request to: {target_url}")
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers={k: v for k, v in request.headers.items() 
                                if k.lower() not in ["host", "content-length"]},
                        content=body if body else None,
                        params=request.query_params
                    )
                
                logger.info(f"Received response: {response.status_code} {response.reason_phrase}")
                
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
                    logger.info(f"Logged intercepted request: {len(self.intercepted_requests)} total")
                
                # Return response to client
                logger.debug("Returning response to client")
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            except Exception as e:
                logger.error(f"Proxy error: {e}", exc_info=True)
                return Response(
                    content=json.dumps({"error": str(e)}),
                    status_code=500,
                    headers={"Content-Type": "application/json"}
                )
    
    async def start(self):
        """Start the proxy server."""
        if self.is_running:
            logger.warning("Proxy server already running")
            return
            
        logger.info(f"Starting proxy server on {self.config.host}:{self.config.port}")
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
        logger.info("Proxy server started successfully")
        
    async def stop(self):
        """Stop the proxy server."""
        if not self.is_running or not self.server_task:
            logger.warning("Proxy server not running")
            return
            
        logger.info("Stopping proxy server")
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            logger.info("Proxy server task cancelled")
            pass
        self.is_running = False
        self.server_task = None
        logger.info("Proxy server stopped")
        
    def get_requests(self) -> list[InterceptedRequest]:
        """Get all intercepted requests."""
        logger.debug(f"Retrieved {len(self.intercepted_requests)} intercepted requests")
        return self.intercepted_requests.copy()
        
    def clear_requests(self):
        """Clear all intercepted requests."""
        count = len(self.intercepted_requests)
        self.intercepted_requests.clear()
        logger.info(f"Cleared {count} intercepted requests")
