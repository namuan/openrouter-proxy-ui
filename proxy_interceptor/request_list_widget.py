from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                            QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import logging
from typing import List
from urllib.parse import urlparse
from .models import InterceptedRequest

logger = logging.getLogger(__name__)


class RequestListWidget(QWidget):
    """Widget displaying a list of intercepted requests."""
    
    request_selected = pyqtSignal(InterceptedRequest)
    
    def __init__(self):
        super().__init__()
        self.requests: List[InterceptedRequest] = []
        logger.debug("RequestListWidget initialized")
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
        logger.debug("Setting up RequestListWidget UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("Intercepted Requests")
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Request list
        self.request_list = QListWidget()
        self.request_list.itemClicked.connect(self._on_request_selected)
        layout.addWidget(self.request_list)
        logger.debug("RequestListWidget UI setup complete")
        
    def set_requests(self, requests: List[InterceptedRequest]):
        """Update the list of requests."""
        logger.info(f"Setting {len(requests)} requests in list widget")
        self.requests = requests
        self._update_list()
        
    def add_request(self, request: InterceptedRequest):
        """Append a single intercepted request to the list and UI."""
        self.requests.append(request)
        item = QListWidgetItem()
        # Extract path from URL
        parsed_url = urlparse(request.request.url)
        path = parsed_url.path if parsed_url.path else '/'
        
        # Extract model from request body if available
        model_name = "unknown"
        try:
            if request.request.body:
                body_data = json.loads(request.request.body)
                model_name = body_data.get("model", "unknown")
        except (json.JSONDecodeError, AttributeError):
            pass
        
        item.setText(
            f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
            f"{request.request.method} {path} - {model_name}"
        )
        item.setData(Qt.ItemDataRole.UserRole, request)
        self.request_list.addItem(item)
        logger.debug(
            f"Appended request to list: {request.request.method} {path} - {model_name}"
        )
        
    def _update_list(self):
        """Update the list widget with current requests."""
        logger.debug(f"Updating list widget with {len(self.requests)} requests")
        self.request_list.clear()
        
        for i, request in enumerate(self.requests):
            item = QListWidgetItem()
            # Extract path from URL
            parsed_url = urlparse(request.request.url)
            path = parsed_url.path if parsed_url.path else '/'
            
            # Extract model from request body if available
            model_name = "unknown"
            try:
                if request.request.body:
                    body_data = json.loads(request.request.body)
                    model_name = body_data.get("model", "unknown")
            except (json.JSONDecodeError, AttributeError):
                pass
            
            item.setText(
                f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
                f"{request.request.method} {path} - {model_name}"
            )
            item.setData(Qt.ItemDataRole.UserRole, request)
            self.request_list.addItem(item)
            logger.debug(f"Added request {i+1} to list: {request.request.method} {path} - {model_name}")
            
    def _on_request_selected(self, item: QListWidgetItem):
        """Handle request selection."""
        request = item.data(Qt.ItemDataRole.UserRole)
        # Extract path from URL for logging
        parsed_url = urlparse(request.request.url)
        path = parsed_url.path if parsed_url.path else '/'
        
        # Extract model from request body if available
        model_name = "unknown"
        try:
            if request.request.body:
                body_data = json.loads(request.request.body)
                model_name = body_data.get("model", "unknown")
        except (json.JSONDecodeError, AttributeError):
            pass
        
        logger.info(f"Request selected from list: {request.request.method} {path} - {model_name}")
        self.request_selected.emit(request)
