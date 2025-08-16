import errno
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


PORT_IN_USE_PATTERNS = [
    re.compile(r"in use", re.IGNORECASE),
    re.compile(r"address already in use", re.IGNORECASE),
]


def is_port_in_use_error(msg: str) -> bool:
    return any(p.search(msg or "") for p in PORT_IN_USE_PATTERNS)


def to_user_message(err: Any) -> str:
    """
    Convert various exception objects or error strings into a friendly, actionable
    message suitable for display in the GUI. The technical details remain in logs.
    """
    try:
        if err is None:
            return "An unknown error occurred. Check logs for details."
        if isinstance(err, Exception):
            msg = str(err)
            name = err.__class__.__name__
        else:
            msg = str(err)
            name = "Error"

        # Common guidance buckets
        # 1) Port in use / bind errors
        if is_port_in_use_error(msg) or getattr(err, "errno", None) in (
            errno.EADDRINUSE,
        ):
            return (
                "Port appears to be in use. Another process may be listening on the selected port. "
                "Try a different port in the Configuration tab and start again."
            )

        # 2) Missing configuration
        if (
            "No valid configuration" in msg
            or "No OpenRouter API keys" in msg
            or "models configured" in msg
        ):
            return (
                "Configuration incomplete. Please add at least one API key and one model in the Configuration tab, "
                "then save and start the proxy."
            )

        # 3) Permission or access issues
        if any(
            k in msg.lower()
            for k in ["permission", "forbidden", "unauthorized", "auth"]
        ):
            return (
                "Authentication or permission error. Verify your API key, ensure it has access to the selected model, "
                "and try again."
            )

        # 4) Network / connectivity
        if any(
            k in msg.lower()
            for k in ["timeout", "connection", "network", "dns", "refused"]
        ):
            return "Network issue detected. Check your internet connection and DNS settings, then retry."

        # 5) Generic fallback
        return f"{name}: {msg}"
    except Exception:
        logger.exception("Failed to convert error to user message")
        return "An error occurred. Check proxy_interceptor.log for details."
