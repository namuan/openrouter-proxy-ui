from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QListWidget, QListWidgetItem, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List
from .models import InterceptedRequest


class RequestListWidget(QWidget):
    """Widget displaying a list of intercepted requests."""
    
    request_selected = pyqtSignal(InterceptedRequest)
    
    def __init__(self):
        super().__init__()
        self.requests: List[InterceptedRequest] = []
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
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
        
    def set_requests(self, requests: List[InterceptedRequest]):
        """Update the list of requests."""
        self.requests = requests
        self._update_list()
        
    def _update_list(self):
        """Update the list widget with current requests."""
        self.request_list.clear()
        
        for request in self.requests:
            item = QListWidgetItem()
            item.setText(
                f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
                f"{request.request.method} {request.request.url}"
            )
            item.setData(Qt.ItemDataRole.UserRole, request)
            self.request_list.addItem(item)
            
    def _on_request_selected(self, item: QListWidgetItem):
        """Handle request selection."""
        request = item.data(Qt.ItemDataRole.UserRole)
        self.request_selected.emit(request)
