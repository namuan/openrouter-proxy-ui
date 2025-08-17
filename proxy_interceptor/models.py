from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ModelProcessStatus(Enum):
    """Status of a model process invocation."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


@dataclass
class ModelInvocation:
    """Tracks a single model invocation with detailed status information."""

    model_name: str
    model_version: str | None = None
    status: ModelProcessStatus = ModelProcessStatus.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str | None = None
    api_key_index: int | None = None
    model_index: int | None = None
    retry_count: int = 0
    latency_ms: float | None = None
    tokens_used: int | None = None

    def is_successful(self) -> bool:
        """Check if the model invocation was successful."""
        return self.status == ModelProcessStatus.SUCCESS

    def is_failed(self) -> bool:
        """Check if the model invocation failed."""
        return self.status in [
            ModelProcessStatus.FAILED,
            ModelProcessStatus.TIMEOUT,
            ModelProcessStatus.RATE_LIMITED,
        ]


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
    model_invocations: list[ModelInvocation] = field(default_factory=list)
    primary_model: str | None = None
    fallback_models_used: list[str] = field(default_factory=list)

    def get_successful_model(self) -> str | None:
        """Get the model that successfully handled this request."""
        for invocation in self.model_invocations:
            if invocation.is_successful():
                return invocation.model_name
        return None

    def get_failed_models(self) -> list[str]:
        """Get list of models that failed for this request."""
        return [inv.model_name for inv in self.model_invocations if inv.is_failed()]

    def has_model_failures(self) -> bool:
        """Check if any models failed during this request."""
        return any(inv.is_failed() for inv in self.model_invocations)
