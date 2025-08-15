from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QTabWidget, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging
from typing import Optional
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
        
        # Header
        self.header_label = QLabel("No request selected")
        header_font = QFont()
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        layout.addWidget(self.header_label)
        
        # Tab widget for request/response details
        self.tab_widget = QTabWidget()
        
        # Request tab
        request_widget = QWidget()
        request_layout = QVBoxLayout(request_widget)
        
        # Request headers
        request_layout.addWidget(QLabel("Headers:"))
        self.request_headers = QTextEdit()
        self.request_headers.setMaximumHeight(150)
        request_layout.addWidget(self.request_headers)
        
        # Request body
        request_layout.addWidget(QLabel("Body:"))
        self.request_body = QTextEdit()
        request_layout.addWidget(self.request_body)
        
        self.tab_widget.addTab(request_widget, "Request")
        
        # Response tab
        response_widget = QWidget()
        response_layout = QVBoxLayout(response_widget)
        
        # Response status
        self.response_status = QLabel()
        response_layout.addWidget(self.response_status)
        
        # Response headers
        response_layout.addWidget(QLabel("Headers:"))
        self.response_headers = QTextEdit()
        self.response_headers.setMaximumHeight(150)
        response_layout.addWidget(self.response_headers)
        
        # Response body
        response_layout.addWidget(QLabel("Body:"))
        self.response_body = QTextEdit()
        response_layout.addWidget(self.response_body)
        
        self.tab_widget.addTab(response_widget, "Response")
        
        layout.addWidget(self.tab_widget)
        logger.debug("RequestDetailsWidget UI setup complete")
        
    def set_request(self, request: Optional[InterceptedRequest]):
        """Display details for the given request. If None, clear UI."""
        self.current_request = request
        
        if request is None:
            logger.debug("Clearing request details (None request)")
            self.header_label.setText("No request selected")
            self.request_headers.clear()
            self.request_body.clear()
            self.response_status.clear()
            self.response_headers.clear()
            self.response_body.clear()
            return
        
        logger.info(f"Setting request details for: {request.request.method} {request.request.url}")
        
        # Update header
        self.header_label.setText(
            f"{request.request.method} {request.request.url}"
        )
        
        # Update request details
        headers_text = "\n".join(
            f"{k}: {v}" for k, v in request.request.headers.items()
        )
        self.request_headers.setPlainText(headers_text)
        self.request_body.setPlainText(request.request.body)
        
        # Update response details
        self.response_status.setText(
            f"Status: {request.response.status_code} {request.response.status_text}"
        )
        
        headers_text = "\n".join(
            f"{k}: {v}" for k, v in request.response.headers.items()
        )
        self.response_headers.setPlainText(headers_text)
        self.response_body.setPlainText(request.response.body)
        
        logger.debug("Request details updated successfully")
    
    def clear(self):
        """Clear all displayed request details."""
        self.set_request(None)
