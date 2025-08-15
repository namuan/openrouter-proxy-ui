import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from .models import HttpRequest, HttpResponse, InterceptedRequest

logger = logging.getLogger(__name__)

# Environment variable loading helper
def _load_api_keys() -> List[str]:
    """Load OpenRouter API keys from environment variable."""
    keys_str = os.environ.get("OPENROUTER_API_KEY", "")
    if not keys_str:
        logger.warning("OPENROUTER_API_KEY environment variable not set. Proxy will fail requests without keys.")
        return []
    keys = [key.strip() for key in keys_str.split(',')]
    logger.info(f"Loaded {len(keys)} OpenRouter API keys")
    return keys

def _load_auth_tokens() -> Set[str]:
    """Load allowed authentication tokens from environment variable."""
    tokens_str = os.environ.get("ALLOWED_AUTH_TOKENS", "")
    if not tokens_str:
        logger.info("ALLOWED_AUTH_TOKENS not set. Authentication disabled.")
        return set()
    tokens = {token.strip() for token in tokens_str.split(',')}
    logger.info(f"Loaded {len(tokens)} allowed authentication tokens. Authentication enabled.")
    return tokens

def _load_api_models() -> List[str]:
    """Load OpenRouter API models from environment variable."""
    models_str = os.environ.get("OPENROUTER_API_MODELS", "qwen/qwen3-coder:free,openai/gpt-oss-20b:free")
    if not models_str:
        logger.warning("OPENROUTER_API_MODELS environment variable not set. Will use original model from requests.")
        return []
    models = [model.strip() for model in models_str.split(',')]
    logger.info(f"Loaded {len(models)} OpenRouter API models: {models}")
    return models

@dataclass
class ProxyConfig:
    """Configuration for the proxy server."""
    host: str = "127.0.0.1"
    port: int = 8080
    target_base_url: str = "https://openrouter.ai/api/v1"
    log_requests: bool = True
    
    # OpenRouter-specific configuration
    openrouter_api_keys: List[str] = None
    allowed_auth_tokens: Set[str] = None
    openrouter_api_models: List[str] = None
    site_url: str = "http://localhost:8080"
    app_name: str = "OpenRouter Proxy Interceptor"
    
    def __post_init__(self):
        if self.openrouter_api_keys is None:
            self.openrouter_api_keys = _load_api_keys()
        if self.allowed_auth_tokens is None:
            self.allowed_auth_tokens = _load_auth_tokens()
        if self.openrouter_api_models is None:
            self.openrouter_api_models = _load_api_models()
        logger.info(f"ProxyConfig initialized: {self}")


class ProxyServer:
    """HTTP proxy server for intercepting and logging requests."""
    
    def __init__(self, config: ProxyConfig, on_intercept: Optional[Callable[[InterceptedRequest], None]] = None):
        self.config = config
        self.app = FastAPI(
            title="OpenRouter Proxy Interceptor",
            description="A proxy that intercepts OpenRouter requests with key rotation and retry logic."
        )
        self.intercepted_requests: list[InterceptedRequest] = []
        self.is_running = False
        self.server = None
        self.server_task = None
        self.on_intercept = on_intercept
        
        # Key rotation state
        self._current_key_index = 0
        self._key_lock = asyncio.Lock()
        
        # Model rotation state
        self._current_model_index = 0
        self._model_lock = asyncio.Lock()
        
        # HTTP client for forwarding requests
        self._client = None
        
        logger.info("Initializing ProxyServer")
        self._setup_routes()
        logger.info("ProxyServer routes configured")
        
    async def _get_next_key_index(self) -> int:
        """Safely get the next key index for round-robin rotation."""
        async with self._key_lock:
            if not self.config.openrouter_api_keys:
                raise HTTPException(status_code=503, detail="No OpenRouter API keys configured")
            idx = self._current_key_index
            self._current_key_index = (self._current_key_index + 1) % len(self.config.openrouter_api_keys)
            return idx
    
    async def _get_next_model_index(self) -> int:
        """Safely get the next model index for round-robin rotation."""
        async with self._model_lock:
            if not self.config.openrouter_api_models:
                raise HTTPException(status_code=503, detail="No OpenRouter API models configured")
            idx = self._current_model_index
            self._current_model_index = (self._current_model_index + 1) % len(self.config.openrouter_api_models)
            return idx
    
    async def _verify_token(self, authorization: Optional[str] = Header(None)):
        """Dependency to verify the provided Bearer token."""
        if not self.config.allowed_auth_tokens:
            return  # No auth required
            
        if authorization is None:
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if token not in self.config.allowed_auth_tokens:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid authentication token",
                )
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _stream_response_generator(self, api_response: httpx.Response, intercepted_request: InterceptedRequest = None):
        """Async generator to stream chunks from the OpenRouter response while capturing content."""
        captured_chunks = []
        extracted_content = []
        try:
            async for chunk in api_response.aiter_bytes():
                if intercepted_request:
                    captured_chunks.append(chunk)
                    # Parse SSE data to extract content
                    try:
                        chunk_text = chunk.decode('utf-8')
                        for line in chunk_text.split('\n'):
                            if line.startswith('data: ') and not line.startswith('data: [DONE]'):
                                json_data = line[6:]  # Remove 'data: ' prefix
                                if json_data.strip():
                                    data = json.loads(json_data)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            extracted_content.append(content)
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, IndexError):
                        # Skip malformed chunks
                        pass
                yield chunk
        except Exception as e:
            logger.error(f"Error while streaming response: {e}")
        finally:
            # Update the intercepted request with both raw and extracted content
            if intercepted_request and captured_chunks:
                try:
                    full_content = b''.join(captured_chunks).decode('utf-8')
                    # Store extracted readable content instead of raw SSE data
                    if extracted_content:
                        readable_content = ''.join(extracted_content)
                        intercepted_request.response.body = readable_content
                        logger.debug(f"Captured and extracted {len(readable_content)} characters of readable content")
                    else:
                        intercepted_request.response.body = full_content
                        logger.debug(f"Captured {len(full_content)} characters of raw streaming response")
                except Exception as e:
                    logger.error(f"Error capturing streaming content: {e}")
            await api_response.aclose()
        
    def _setup_routes(self):
        """Set up FastAPI routes."""
        logger.debug("Setting up FastAPI routes")
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: Request, _=Depends(self._verify_token)):
            """Handle OpenAI-compatible chat completion requests with key rotation and retry."""
            logger.info("Received chat completions request")
            
            try:
                request_data = await request.json()
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON body")
            
            # Store original model for reference
            original_model = request_data.get("model", "")
            
            is_streaming = request_data.get("stream", False)
            
            # Get next API key using round-robin rotation
            key_index = await self._get_next_key_index()
            api_key = self.config.openrouter_api_keys[key_index]
            
            # Start with current model (don't advance until there's an error)
            current_model_index = self._current_model_index
            last_error_status = 500
            last_error_detail = "All API models failed."
            num_models = len(self.config.openrouter_api_models)
            
            for i in range(num_models):
                model_index = (current_model_index + i) % num_models
                model_name = self.config.openrouter_api_models[model_index]
                
                # Update request data with current model
                request_data["model"] = model_name
                
                # Get request body as string for logging (with updated model)
                body_str = json.dumps(request_data)
                
                # Create HttpRequest for logging
                http_request = HttpRequest(
                    timestamp=datetime.now(),
                    method=request.method,
                    url=str(request.url),
                    headers=dict(request.headers),
                    body=body_str
                )
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.config.site_url,
                    "X-Title": self.config.app_name,
                }
                
                logger.info(f"Attempting request with API key index {key_index}, model '{model_name}' (model index {model_index}) (Stream: {is_streaming})")
                
                try:
                    target_url = f"{self.config.target_base_url}/chat/completions"
                    
                    if is_streaming:
                        # Make streaming request
                        req = self._client.build_request(
                            "POST", target_url, json=request_data, headers=headers
                        )
                        api_response = await self._client.send(req, stream=True)
                        
                        if api_response.status_code == 200:
                            logger.info(f"Streaming success with API key index {key_index}, model '{model_name}' (index {model_index})")
                            
                            # For streaming, we'll capture the response body as it streams
                            http_response = HttpResponse(
                                status_code=api_response.status_code,
                                status_text=api_response.reason_phrase,
                                headers=dict(api_response.headers),
                                body="[Streaming in progress...]"
                            )
                            
                            if self.config.log_requests:
                                intercepted = InterceptedRequest(
                                    request=http_request,
                                    response=http_response
                                )
                                self.intercepted_requests.append(intercepted)
                                if self.on_intercept:
                                    try:
                                        self.on_intercept(intercepted)
                                    except Exception:
                                        logger.exception("Error in on_intercept callback for streaming response")
                            
                            return StreamingResponse(
                                self._stream_response_generator(api_response, intercepted),
                                media_type="text/event-stream",
                                headers={k: v for k, v in api_response.headers.items() 
                                        if k.lower() in ['content-type', 'content-encoding']}
                            )
                            
                        elif api_response.status_code == 429:
                            error_detail = f"Rate limit exceeded for API key index {key_index}, model '{model_name}' (index {model_index})"
                            try:
                                error_body = await api_response.aread()
                                error_detail += f" Response: {error_body.decode()}"
                            except Exception: 
                                pass
                            await api_response.aclose()
                            logger.warning(error_detail)
                            last_error_status = 429
                            last_error_detail = error_detail
                        else:
                            error_body = await api_response.aread()
                            error_detail = f"Error with API key index {key_index}, model '{model_name}' (index {model_index}): Status {api_response.status_code}, Response: {error_body.decode()}"
                            await api_response.aclose()
                            logger.error(error_detail)
                            last_error_status = api_response.status_code
                            last_error_detail = error_detail
                            if i == num_models - 1:
                                raise HTTPException(status_code=last_error_status, detail=last_error_detail)
                    else:
                        # Make non-streaming request
                        api_response = await self._client.post(
                            target_url, json=request_data, headers=headers
                        )
                        
                        if api_response.status_code == 200:
                            logger.info(f"Non-streaming success with API key index {key_index}, model '{model_name}' (index {model_index})")
                            
                            # Create response object for logging
                            http_response = HttpResponse(
                                status_code=api_response.status_code,
                                status_text=api_response.reason_phrase,
                                headers=dict(api_response.headers),
                                body=api_response.text
                            )
                            
                            if self.config.log_requests:
                                intercepted = InterceptedRequest(
                                    request=http_request,
                                    response=http_response
                                )
                                self.intercepted_requests.append(intercepted)
                                if self.on_intercept:
                                    try:
                                        self.on_intercept(intercepted)
                                    except Exception:
                                        logger.exception("Error in on_intercept callback for non-streaming response")
                            
                            return JSONResponse(content=api_response.json(), status_code=api_response.status_code)
                            
                        elif api_response.status_code == 429:
                            error_detail = f"Rate limit exceeded for API key index {key_index}, model '{model_name}' (index {model_index})"
                            try:
                                error_detail += f" Response: {api_response.text}"
                            except Exception: 
                                pass
                            logger.warning(error_detail)
                            last_error_status = 429
                            last_error_detail = error_detail
                        else:
                            error_detail = f"Error with API key index {key_index}, model '{model_name}' (index {model_index}): Status {api_response.status_code}, Response: {api_response.text}"
                            logger.error(error_detail)
                            last_error_status = api_response.status_code
                            last_error_detail = error_detail
                            if i == num_models - 1:
                                raise HTTPException(status_code=last_error_status, detail=last_error_detail)
                
                except httpx.RequestError as e:
                    error_detail = f"HTTPX Request Error with API key index {key_index}, model '{model_name}' (index {model_index}): {e.__class__.__name__} - {e}"
                    logger.error(error_detail)
                    last_error_status = 503
                    last_error_detail = error_detail
                    if i == num_models - 1:
                        raise HTTPException(status_code=last_error_status, detail=last_error_detail)
                
                except Exception as e:
                    error_detail = f"Unexpected error processing request with API key index {key_index}, model '{model_name}' (index {model_index}): {e.__class__.__name__} - {e}"
                    logger.exception(error_detail)
                    last_error_status = 500
                    last_error_detail = error_detail
                    if i == num_models - 1:
                        raise HTTPException(status_code=last_error_status, detail=last_error_detail)
            
            # If we get here, all models failed - advance to next model for future requests
            async with self._model_lock:
                self._current_model_index = (self._current_model_index + 1) % len(self.config.openrouter_api_models)
            logger.error(f"All {num_models} API models failed for the request")
            raise HTTPException(status_code=last_error_status, detail=last_error_detail)
        
        @self.app.get("/v1/models")
        async def get_models(_=Depends(self._verify_token)):
            """Fetch the list of available models from OpenRouter."""
            if not self.config.openrouter_api_keys:
                raise HTTPException(status_code=503, detail="No OpenRouter API keys configured")
                
            api_key = self.config.openrouter_api_keys[0]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": self.config.site_url,
                "X-Title": self.config.app_name,
            }
            
            logger.info("Fetching models list from OpenRouter...")
            try:
                target_url = f"{self.config.target_base_url}/models"
                response = await self._client.get(target_url, headers=headers)
                response.raise_for_status()
                
                logger.info("Successfully fetched models list")
                return JSONResponse(content=response.json(), status_code=response.status_code)
            
            except httpx.HTTPStatusError as e:
                error_detail = f"Error fetching models: Status {e.response.status_code}, Response: {e.response.text}"
                logger.error(error_detail)
                raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            except httpx.RequestError as e:
                error_detail = f"HTTPX Request Error fetching models: {e.__class__.__name__} - {e}"
                logger.error(error_detail)
                raise HTTPException(status_code=503, detail=error_detail)
            except Exception as e:
                error_detail = f"Unexpected error fetching models: {e.__class__.__name__} - {e}"
                logger.exception(error_detail)
                raise HTTPException(status_code=500, detail=error_detail)
        
        @self.app.get("/")
        async def read_root():
            return {"message": "OpenRouter Proxy Interceptor is running. Use POST /v1/chat/completions and GET /v1/models."}
        
        # Legacy catch-all route removed    
    async def start(self):
        """Start the proxy server."""
        if self.is_running:
            logger.warning("Proxy server already running")
            return
            
        logger.info(f"Starting proxy server on {self.config.host}:{self.config.port}")
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(timeout=600.0)
        
        # Configure uvicorn with proper shutdown handling
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            access_log=False
        )
        
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        self.is_running = True
        logger.info("Proxy server started successfully")
        
    async def stop(self):
        """Stop the proxy server."""
        if not self.is_running or not self.server:
            logger.warning("Proxy server not running")
            return
            
        logger.info("Stopping proxy server")
        
        # Close HTTP client
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self.server:
            self.server.should_exit = True
            
            if self.server_task and not self.server_task.done():
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    logger.debug("Server task was cancelled")
        
        self.is_running = False
        self.server = None
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
