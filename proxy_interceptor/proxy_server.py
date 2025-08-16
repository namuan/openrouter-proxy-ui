import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .models import HttpRequest, HttpResponse, InterceptedRequest

logger = logging.getLogger(__name__)

# Environment variable loading helper
# Environment variable loading functions removed - configuration now comes from config widget only


@dataclass
class ProxyConfig:
    """Configuration for the proxy server."""

    host: str = "127.0.0.1"
    port: int = 8080
    target_base_url: str = "https://openrouter.ai/api/v1"
    log_requests: bool = True

    # OpenRouter-specific configuration
    openrouter_api_keys: list[str] = None
    openrouter_api_models: list[str] = None
    site_url: str = "http://localhost:8080"
    app_name: str = "OpenRouter Proxy Interceptor"

    def __post_init__(self):
        # Ensure we have lists/sets even if None provided
        if self.openrouter_api_keys is None:
            self.openrouter_api_keys = []
        if self.openrouter_api_models is None:
            self.openrouter_api_models = []
        # Align site_url with configured port if default was left
        try:
            if (
                not self.site_url
                or self.site_url.endswith(":8080")
                or self.site_url == "http://localhost:8080"
            ):
                self.site_url = f"http://localhost:{self.port}"
        except Exception:
            logger.debug("Failed to set site_url, using default")

        logger.info(
            f"ProxyConfig initialized with {len(self.openrouter_api_keys)} keys, {len(self.openrouter_api_models)} models"
        )


class ProxyServer:
    """HTTP proxy server for intercepting and logging requests."""

    def __init__(
        self,
        config: ProxyConfig,
        on_intercept: Callable[[InterceptedRequest], None] | None = None,
    ):
        self.config = config
        self.app = FastAPI(
            title="OpenRouter Proxy Interceptor",
            description="A proxy that intercepts OpenRouter requests with key rotation and retry logic.",
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
                raise HTTPException(
                    status_code=503, detail="No OpenRouter API keys configured"
                )
            idx = self._current_key_index
            self._current_key_index = (self._current_key_index + 1) % len(
                self.config.openrouter_api_keys
            )
            return idx

    async def _get_next_model_index(self) -> int:
        """Safely get the next model index for round-robin rotation."""
        async with self._model_lock:
            if not self.config.openrouter_api_models:
                raise HTTPException(
                    status_code=503, detail="No OpenRouter API models configured"
                )
            idx = self._current_model_index
            self._current_model_index = (self._current_model_index + 1) % len(
                self.config.openrouter_api_models
            )
            return idx

    # ruff: noqa: C901
    async def _stream_response_generator(
        self,
        api_response: httpx.Response,
        intercepted_request: InterceptedRequest = None,
    ):
        """Async generator to stream chunks from the OpenRouter response while capturing content."""
        captured_chunks = []
        extracted_content = []
        try:
            async for chunk in api_response.aiter_bytes():
                if intercepted_request:
                    captured_chunks.append(chunk)
                    # Parse SSE data to extract content
                    try:
                        chunk_text = chunk.decode("utf-8")
                        for line in chunk_text.split("\n"):
                            if line.startswith("data: ") and not line.startswith(
                                "data: [DONE]"
                            ):
                                json_data = line[6:]  # Remove 'data: ' prefix
                                if json_data.strip():
                                    data = json.loads(json_data)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            extracted_content.append(content)
                    except (
                        json.JSONDecodeError,
                        UnicodeDecodeError,
                        KeyError,
                        IndexError,
                    ):
                        # Skip malformed chunks
                        pass
                yield chunk
        except Exception:
            logger.exception("Error while streaming response")
        finally:
            # Update the intercepted request with both raw and extracted content
            if intercepted_request and captured_chunks:
                try:
                    full_content = b"".join(captured_chunks).decode("utf-8")
                    # Store both raw SSE data and extracted readable content
                    intercepted_request.response.raw_body = full_content
                    if extracted_content:
                        readable_content = "".join(extracted_content)
                        intercepted_request.response.body = readable_content
                        logger.debug(
                            f"Captured {len(full_content)} characters of raw SSE data and extracted {len(readable_content)} characters of readable content"
                        )
                    else:
                        intercepted_request.response.body = full_content
                        logger.debug(
                            f"Captured {len(full_content)} characters of raw streaming response (no extracted content)"
                        )
                except Exception:
                    logger.exception("Error capturing streaming content")
            await api_response.aclose()

    # ruff: noqa: C901
    def _setup_routes(self):
        """Set up FastAPI routes."""
        logger.debug("Setting up FastAPI routes")

        # ruff: noqa: C901
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: Request):
            """Handle OpenAI-compatible chat completion requests with key rotation and retry."""
            logger.info("Received chat completions request")

            try:
                request_data = await request.json()
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail="Invalid JSON body") from e

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
                    body=body_str,
                )

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.config.site_url,
                    "X-Title": self.config.app_name,
                }

                logger.info(
                    f"Attempting request with API key index {key_index}, model '{model_name}' (model index {model_index}) (Stream: {is_streaming})"
                )

                try:
                    target_url = f"{self.config.target_base_url}/chat/completions"

                    if is_streaming:
                        # Make streaming request
                        req = self._client.build_request(
                            "POST", target_url, json=request_data, headers=headers
                        )
                        api_response = await self._client.send(req, stream=True)

                        if api_response.status_code == 200:
                            logger.info(
                                f"Streaming success with API key index {key_index}, model '{model_name}' (index {model_index})"
                            )

                            # For streaming, we'll capture the response body as it streams
                            http_response = HttpResponse(
                                status_code=api_response.status_code,
                                status_text=api_response.reason_phrase,
                                headers=dict(api_response.headers),
                                body="[Streaming in progress...]",
                                raw_body="[Streaming in progress...]",
                            )

                            if self.config.log_requests:
                                intercepted = InterceptedRequest(
                                    request=http_request, response=http_response
                                )
                                self.intercepted_requests.append(intercepted)
                                if self.on_intercept:
                                    try:
                                        self.on_intercept(intercepted)
                                    except Exception:
                                        logger.exception(
                                            "Error in on_intercept callback for streaming response"
                                        )

                            return StreamingResponse(
                                self._stream_response_generator(
                                    api_response, intercepted
                                ),
                                media_type="text/event-stream",
                                headers={
                                    k: v
                                    for k, v in api_response.headers.items()
                                    if k.lower() in ["content-type", "content-encoding"]
                                },
                            )

                        elif api_response.status_code == 429:
                            error_detail = f"Rate limit exceeded for API key index {key_index}, model '{model_name}' (index {model_index})"
                            try:
                                error_body = await api_response.aread()
                                error_detail += f" Response: {error_body.decode()}"
                            except Exception:
                                logger.debug("Failed to read error response body")
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
                                raise HTTPException(
                                    status_code=last_error_status,
                                    detail=last_error_detail,
                                )
                    else:
                        # Make non-streaming request
                        api_response = await self._client.post(
                            target_url, json=request_data, headers=headers
                        )

                        if api_response.status_code == 200:
                            logger.info(
                                f"Non-streaming success with API key index {key_index}, model '{model_name}' (index {model_index})"
                            )

                            # Create response object for logging with both raw and parsed content
                            raw_text = api_response.text
                            try:
                                # Try to extract content from choices for better readability
                                parsed_json = api_response.json()

                                # Extract content from choices if available (similar to streaming)
                                extracted_content = ""
                                if (
                                    "choices" in parsed_json
                                    and len(parsed_json["choices"]) > 0
                                ):
                                    choice = parsed_json["choices"][0]
                                    if (
                                        "message" in choice
                                        and "content" in choice["message"]
                                    ):
                                        extracted_content = choice["message"]["content"]

                                # Use extracted content if available, otherwise format full JSON
                                if extracted_content:
                                    formatted_body = extracted_content
                                else:
                                    formatted_body = json.dumps(parsed_json, indent=2)
                            except (json.JSONDecodeError, ValueError):
                                # If not valid JSON, use raw text for both
                                formatted_body = raw_text

                            http_response = HttpResponse(
                                status_code=api_response.status_code,
                                status_text=api_response.reason_phrase,
                                headers=dict(api_response.headers),
                                body=formatted_body,
                                raw_body=raw_text,
                            )

                            if self.config.log_requests:
                                intercepted = InterceptedRequest(
                                    request=http_request, response=http_response
                                )
                                self.intercepted_requests.append(intercepted)
                                if self.on_intercept:
                                    try:
                                        self.on_intercept(intercepted)
                                    except Exception:
                                        logger.exception(
                                            "Error in on_intercept callback for non-streaming response"
                                        )

                            return JSONResponse(
                                content=api_response.json(),
                                status_code=api_response.status_code,
                            )

                        elif api_response.status_code == 429:
                            error_detail = f"Rate limit exceeded for API key index {key_index}, model '{model_name}' (index {model_index})"
                            with contextlib.suppress(Exception):
                                error_detail += f" Response: {api_response.text}"
                            logger.warning(error_detail)
                            last_error_status = 429
                            last_error_detail = error_detail
                        else:
                            error_detail = f"Error with API key index {key_index}, model '{model_name}' (index {model_index}): Status {api_response.status_code}, Response: {api_response.text}"
                            logger.error(error_detail)
                            last_error_status = api_response.status_code
                            last_error_detail = error_detail
                            if i == num_models - 1:
                                raise HTTPException(
                                    status_code=last_error_status,
                                    detail=last_error_detail,
                                )

                except httpx.RequestError as e:
                    error_detail = f"HTTPX Request Error with API key index {key_index}, model '{model_name}' (index {model_index}): {e.__class__.__name__} - {e}"
                    logger.exception(error_detail)
                    last_error_status = 503
                    last_error_detail = error_detail
                    if i == num_models - 1:
                        raise HTTPException(
                            status_code=last_error_status, detail=last_error_detail
                        ) from None

                except Exception as e:
                    error_detail = f"Unexpected error processing request with API key index {key_index}, model '{model_name}' (index {model_index}): {e.__class__.__name__} - {e}"
                    logger.exception(error_detail)
                    last_error_status = 500
                    last_error_detail = error_detail
                    if i == num_models - 1:
                        raise HTTPException(
                            status_code=last_error_status, detail=last_error_detail
                        ) from e

            # If we get here, all models failed - advance to next model for future requests
            async with self._model_lock:
                self._current_model_index = (self._current_model_index + 1) % len(
                    self.config.openrouter_api_models
                )
            logger.error(f"All {num_models} API models failed for the request")
            raise HTTPException(
                status_code=last_error_status, detail=last_error_detail
            ) from None

        @self.app.get("/v1/models")
        async def get_models():
            """Fetch the list of available models from OpenRouter."""
            if not self.config.openrouter_api_keys:
                raise HTTPException(
                    status_code=503, detail="No OpenRouter API keys configured"
                )

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
                return JSONResponse(
                    content=response.json(), status_code=response.status_code
                )

            except httpx.HTTPStatusError as e:
                error_detail = f"Error fetching models: Status {e.response.status_code}, Response: {e.response.text}"
                logger.exception(error_detail)
                raise HTTPException(
                    status_code=e.response.status_code, detail=error_detail
                ) from e
            except httpx.RequestError as e:
                error_detail = (
                    f"HTTPX Request Error fetching models: {e.__class__.__name__} - {e}"
                )
                logger.exception(error_detail)
                raise HTTPException(status_code=503, detail=error_detail) from e
            except Exception as e:
                error_detail = (
                    f"Unexpected error fetching models: {e.__class__.__name__} - {e}"
                )
                logger.exception(error_detail)
                raise HTTPException(status_code=500, detail=error_detail) from e

        @self.app.get("/")
        async def read_root():
            return {
                "message": "OpenRouter Proxy Interceptor is running. Use POST /v1/chat/completions and GET /v1/models."
            }

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
            access_log=False,
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
