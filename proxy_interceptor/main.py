import contextlib
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import ClassVar

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow


class SanitizingFormatter(logging.Formatter):
    SENSITIVE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"(?i)(Authorization)\s*:\s*Bearer\s+([A-Za-z0-9._-]+)"),
        re.compile(r"(?i)(\"Authorization\")\s*:\s*\"Bearer\s+([^\"]+)\""),
        re.compile(r"(?i)(api[_\- ]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"),
        re.compile(
            r"(?i)(X-Api-Key|X-OpenAI-Api-Key|OpenRouter-Api-Key)\s*:\s*([A-Za-z0-9._-]+)"
        ),
        re.compile(r"(?i)(Cookie)\s*:\s*([^;\n]+)"),
        re.compile(r"(?i)(Set-Cookie)\s*:\s*([^;\n]+)"),
        re.compile(r"(sk-[A-Za-z0-9]{8,})"),
        re.compile(r"(or-[A-Za-z0-9]{8,})"),
    ]

    def sanitize(self, text: str) -> str:
        redacted = text
        for pat in self.SENSITIVE_PATTERNS:
            with contextlib.suppress(Exception):
                # Best-effort sanitization; never fail logging
                redacted = pat.sub(
                    lambda m: f"{m.group(1)}: ****"
                    if m.lastindex and len(m.groups()) >= 2
                    else "****",
                    redacted,
                )
        return redacted

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.getMessage()
        # Temporarily set the sanitized message into the record for formatting
        record.message = self.sanitize(original_msg)
        formatted = super().format(record)
        # Also sanitize the final formatted string (covers extras like pathname)
        return self.sanitize(formatted)


def setup_logging():
    root = logging.getLogger()
    if root.handlers:
        # Already configured elsewhere (embedded), avoid duplicate handlers
        return

    level = logging.DEBUG
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = SanitizingFormatter(fmt)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        "proxy_interceptor.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    # Tweak noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.INFO)


setup_logging()

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Proxy Interceptor application")

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("Proxy Interceptor")
        logger.info("Qt application initialized")

        window = MainWindow()
        window.show()
        logger.info("Main window shown")

        return app.exec()

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    sys.exit(main())
