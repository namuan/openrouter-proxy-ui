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


@dataclass
class InterceptedRequest:
    request: HttpRequest
    response: HttpResponse
