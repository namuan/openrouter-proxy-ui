import json
import logging

import defusedxml.minidom
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QLabel,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import InterceptedRequest

logger = logging.getLogger(__name__)


class RequestDetailsWidget(QWidget):
    """Widget displaying details of a selected request/response."""

    def __init__(self):
        super().__init__()
        self.current_request = None
        logger.debug("RequestDetailsWidget initialized")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        logger.debug("Setting up RequestDetailsWidget UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Create horizontal splitter for side-by-side view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Request panel (left side)
        request_widget = QWidget()
        request_widget.setObjectName("requestPanel")
        request_layout = QVBoxLayout(request_widget)
        request_layout.setContentsMargins(15, 15, 15, 15)
        request_layout.setSpacing(8)

        # Request title
        request_title = QLabel("REQUEST")
        request_title.setObjectName("header")
        request_layout.addWidget(request_title)

        # Request status placeholder (for consistent spacing with response)
        request_status_placeholder = QLabel("")
        request_layout.addWidget(request_status_placeholder)

        # Request headers
        headers_label = QLabel("Headers:")
        headers_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        request_layout.addWidget(headers_label)
        self.request_headers = QTextEdit()
        self.request_headers.setMaximumHeight(150)
        request_layout.addWidget(self.request_headers)

        # Request body
        body_label = QLabel("Body:")
        body_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        request_layout.addWidget(body_label)
        self.request_body = QTextEdit()
        request_layout.addWidget(self.request_body)

        splitter.addWidget(request_widget)

        # Response panel (right side)
        response_widget = QWidget()
        response_widget.setObjectName("responsePanel")
        response_layout = QVBoxLayout(response_widget)
        response_layout.setContentsMargins(15, 15, 15, 15)
        response_layout.setSpacing(8)

        # Response title
        response_title = QLabel("RESPONSE")
        response_title.setObjectName("header")
        response_layout.addWidget(response_title)

        # Response status
        self.response_status = QLabel()
        self.response_status.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        response_layout.addWidget(self.response_status)

        # Response headers
        resp_headers_label = QLabel("Headers:")
        resp_headers_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        response_layout.addWidget(resp_headers_label)
        self.response_headers = QTextEdit()
        self.response_headers.setMaximumHeight(150)
        response_layout.addWidget(self.response_headers)

        # Response body with tabs for parsed and raw
        resp_body_label = QLabel("Body:")
        resp_body_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        response_layout.addWidget(resp_body_label)

        # Create tab widget for response body
        self.response_body_tabs = QTabWidget()

        # Parsed response tab
        self.response_body_parsed = QTextEdit()
        self.response_body_tabs.addTab(self.response_body_parsed, "Parsed")

        # Raw response tab
        self.response_body_raw = QTextEdit()
        self.response_body_tabs.addTab(self.response_body_raw, "Raw")

        response_layout.addWidget(self.response_body_tabs)

        # Keep reference to parsed body for backward compatibility
        self.response_body = self.response_body_parsed

        splitter.addWidget(response_widget)

        # Set equal proportions for both panels
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        logger.debug("RequestDetailsWidget UI setup complete")

    def _format_body_content(self, body: str, headers: dict) -> str:
        """Format body content based on content-type header."""
        if not body or not body.strip():
            return body

        # Get content type from headers (case-insensitive)
        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break

        try:
            # JSON formatting
            if "application/json" in content_type or "text/json" in content_type:
                parsed = json.loads(body)
                return json.dumps(parsed, indent=2, ensure_ascii=False)

            # XML formatting
            elif "application/xml" in content_type or "text/xml" in content_type:
                dom = defusedxml.minidom.parseString(body)
                return dom.toprettyxml(indent="  ")

            # HTML formatting (basic indentation)
            elif "text/html" in content_type:
                return self._format_html(body)

            # Plain text or unknown - return as is
            else:
                return body

        except Exception as e:
            logger.debug(f"Failed to format body content: {e}")
            return body  # Return original if formatting fails

    def _format_html(self, html: str) -> str:
        """Basic HTML formatting with indentation."""
        try:
            # Simple HTML formatting - add newlines after tags
            import re

            # Add newlines after closing tags
            formatted = re.sub(r"(</[^>]+>)", r"\1\n", html)
            # Add newlines after opening tags (but not self-closing)
            formatted = re.sub(r"(<[^/>]+[^/]>)", r"\1\n", formatted)
            # Clean up multiple newlines
            formatted = re.sub(r"\n\s*\n", "\n", formatted)
            return formatted.strip()
        except Exception:
            return html

    def set_request(self, request: InterceptedRequest | None):
        """Display details for the given request. If None, clear UI."""
        self.current_request = request

        if request is None:
            logger.debug("Clearing request details (None request)")
            self.request_headers.clear()
            self.request_body.clear()
            self.response_status.clear()
            self.response_headers.clear()
            self.response_body_parsed.clear()
            self.response_body_raw.clear()
            return

        logger.info(
            f"Setting request details for: {request.request.method} {request.request.url}"
        )

        # Update request details
        headers_text = "\n".join(
            f"{k}: {v}" for k, v in request.request.headers.items()
        )
        self.request_headers.setPlainText(headers_text)

        # Format request body based on content type
        formatted_request_body = self._format_body_content(
            request.request.body, request.request.headers
        )
        self.request_body.setPlainText(formatted_request_body)

        # Update response details
        self.response_status.setText(
            f"Status: {request.response.status_code} {request.response.status_text}"
        )

        headers_text = "\n".join(
            f"{k}: {v}" for k, v in request.response.headers.items()
        )
        self.response_headers.setPlainText(headers_text)

        # Format and display both parsed and raw response bodies
        formatted_response_body = self._format_body_content(
            request.response.body, request.response.headers
        )
        self.response_body_parsed.setPlainText(formatted_response_body)

        # Display raw response body (formatted for readability)
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
        """Clear all displayed request details."""
        self.set_request(None)
