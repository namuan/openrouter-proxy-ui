import json
import logging

import defusedxml.minidom
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from proxy_interceptor.models import InterceptedRequest

logger = logging.getLogger(__name__)


class RequestDetailsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_request = None
        logger.debug("RequestDetailsWidget initialized")
        self._setup_ui()

    def _redact_header(self, key: str, value: str) -> str:
        try:
            k = key.lower()
            if k == "authorization":
                # Mask bearer tokens
                if isinstance(value, str) and value.lower().startswith("bearer "):
                    token = value[7:]
                    if len(token) > 8:
                        return (
                            "Bearer " + token[:4] + "*" * (len(token) - 8) + token[-4:]
                        )
                    return "Bearer ****"
                return "****"
            if k in ("cookie", "set-cookie", "x-api-key"):  # common secret carriers
                return "****"
        except Exception as e:
            logger.debug(f"Error redacting header: {e}")
        return value

    def _setup_ui(self):
        logger.debug("Setting up RequestDetailsWidget UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        request_widget = QWidget()
        request_widget.setObjectName("requestPanel")
        request_layout = QVBoxLayout(request_widget)
        request_layout.setContentsMargins(15, 15, 15, 15)
        request_layout.setSpacing(8)

        request_title = QLabel("REQUEST")
        request_title.setObjectName("header")
        request_layout.addWidget(request_title)

        headers_label = QLabel("Headers:")
        request_layout.addWidget(headers_label)
        self.request_headers = QTextEdit()
        self.request_headers.setMaximumHeight(150)
        request_layout.addWidget(self.request_headers)

        body_label = QLabel("Body:")
        request_layout.addWidget(body_label)
        self.request_body = QTextEdit()
        request_layout.addWidget(self.request_body)

        splitter.addWidget(request_widget)

        response_widget = QWidget()
        response_widget.setObjectName("responsePanel")
        response_layout = QVBoxLayout(response_widget)
        response_layout.setContentsMargins(15, 15, 8, 8)
        response_layout.setSpacing(8)

        self.response_title = QLabel("RESPONSE")
        self.response_title.setObjectName("header")
        response_layout.addWidget(self.response_title)

        resp_headers_label = QLabel("Headers:")
        response_layout.addWidget(resp_headers_label)
        self.response_headers = QTextEdit()
        self.response_headers.setMaximumHeight(150)
        response_layout.addWidget(self.response_headers)

        resp_body_label = QLabel("Body:")
        response_layout.addWidget(resp_body_label)

        self.response_body_tabs = QTabWidget()

        self.response_body_parsed = QTextEdit()
        self.response_body_tabs.addTab(self.response_body_parsed, "Parsed")

        self.response_body_raw = QTextEdit()
        self.response_body_tabs.addTab(self.response_body_raw, "Raw")

        response_layout.addWidget(self.response_body_tabs)

        self.response_body = self.response_body_parsed

        splitter.addWidget(response_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        logger.debug("RequestDetailsWidget UI setup complete")

    def _format_body_content(self, body: str, headers: dict) -> str:
        if not body or not body.strip():
            return body

        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break

        try:
            if "application/json" in content_type or "text/json" in content_type:
                parsed = json.loads(body)
                return json.dumps(parsed, indent=2, ensure_ascii=False)

            elif "application/xml" in content_type or "text/xml" in content_type:
                dom = defusedxml.minidom.parseString(body)
                return dom.toprettyxml(indent="  ")

            elif "text/html" in content_type:
                return self._format_html(body)

            else:
                return body

        except Exception as e:
            logger.debug(f"Failed to format body content: {e}")
            return body

    def _format_html(self, html: str) -> str:
        try:
            import re

            formatted = re.sub(r"(</[^>]+>)", r"\1\n", html)
            formatted = re.sub(r"(<[^/>]+[^/]>)", r"\1\n", formatted)
            formatted = re.sub(r"\n\s*\n", "\n", formatted)
            return formatted.strip()
        except Exception:
            return html

    def set_request(self, request: InterceptedRequest | None):
        self.current_request = request

        if request is None:
            logger.debug("Clearing request details (None request)")
            self.request_headers.clear()
            self.response_title.setText("RESPONSE")
            self.request_body.clear()
            self.response_headers.clear()
            self.response_body_parsed.clear()
            self.response_body_raw.clear()
            return

        logger.info(
            f"Setting request details for: {request.request.method} {request.request.url}"
        )

        headers_text = "\n".join(
            f"{k}: {self._redact_header(k, v)}"
            for k, v in request.request.headers.items()
        )
        self.request_headers.setPlainText(headers_text)

        formatted_request_body = self._format_body_content(
            request.request.body, request.request.headers
        )
        self.request_body.setPlainText(formatted_request_body)

        # Build response title with latency/tokens if available
        meta = []
        try:
            if request.response.latency_ms is not None:
                meta.append(f"{request.response.latency_ms:.0f}ms")
            if request.response.total_tokens is not None:
                meta.append(f"tok:{request.response.total_tokens}")
        except Exception as e:
            logger.debug(f"Error extracting meta info: {e}")
        meta_suffix = f"  ({', '.join(meta)})" if meta else ""
        self.response_title.setText(
            f"RESPONSE: ({request.response.status_code} {request.response.status_text}){meta_suffix}"
        )

        headers_text = "\n".join(
            f"{k}: {self._redact_header(k, v)}"
            for k, v in request.response.headers.items()
        )
        self.response_headers.setPlainText(headers_text)

        formatted_response_body = self._format_body_content(
            request.response.body, request.response.headers
        )
        self.response_body_parsed.setPlainText(formatted_response_body)

        raw_response_body = (
            request.response.raw_body
            if hasattr(request.response, "raw_body") and request.response.raw_body
            else request.response.body
        )
        formatted_raw_body = self._format_body_content(
            raw_response_body, request.response.headers
        )
        self.response_body_raw.setPlainText(formatted_raw_body)

        logger.debug("Request details updated successfully")

    def clear(self):
        self.set_request(None)
