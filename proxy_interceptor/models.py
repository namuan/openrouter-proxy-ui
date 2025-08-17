from dataclasses import dataclass
from datetime import datetime


@dataclass
class HttpRequest:
    timestamp: datetime
    method: str
    url: str
    headers: dict[str, str]
    body: str


@dataclass
class HttpResponse:
    status_code: int
    status_text: str
    headers: dict[str, str]
    body: str
    raw_body: str = ""
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    is_streaming: bool = False
    streaming_content: str = ""
    streaming_complete: bool = False


@dataclass
class InterceptedRequest:
    request: HttpRequest
    response: HttpResponse
