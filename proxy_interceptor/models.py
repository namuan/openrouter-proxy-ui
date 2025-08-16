from dataclasses import dataclass
from datetime import datetime


@dataclass
class HttpRequest:
    """Represents an HTTP request."""

    timestamp: datetime
    method: str
    url: str
    headers: dict[str, str]
    body: str


@dataclass
class HttpResponse:
    """Represents an HTTP response."""

    status_code: int
    status_text: str
    headers: dict[str, str]
    body: str  # Parsed/formatted response body (for display)
    raw_body: str = ""  # Raw response body (unprocessed)


@dataclass
class InterceptedRequest:
    """Represents a complete request/response pair."""

    request: HttpRequest
    response: HttpResponse
