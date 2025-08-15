from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class HttpRequest:
    """Represents an HTTP request."""
    timestamp: datetime
    method: str
    url: str
    headers: Dict[str, str]
    body: str


@dataclass
class HttpResponse:
    """Represents an HTTP response."""
    status_code: int
    status_text: str
    headers: Dict[str, str]
    body: str


@dataclass
class InterceptedRequest:
    """Represents a complete request/response pair."""
    request: HttpRequest
    response: HttpResponse
