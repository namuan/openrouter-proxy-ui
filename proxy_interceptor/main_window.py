from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, 
                            QWidget, QHBoxLayout, QStatusBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import List
from .models import InterceptedRequest
from .mock_data import generate_mock_data
from .request_list_widget import RequestListWidget
from .request_details_widget import RequestDetailsWidget


class ProxyWorker(QThread):
    """Worker thread for proxy operations."""
    
    requests_updated = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        """Run the proxy worker."""
        # In a real implementation, this would start the proxy server
        # For now, we'll just emit mock data
        mock_data = generate_mock_data()
        self.requests_updated.emit(mock_data)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.requests: List[InterceptedRequest] = []
        self.worker = None
        self._setup_ui()
        self._load_initial_data()
        
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Proxy Interceptor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Request list widget
        self.request_list = RequestListWidget()
        self.request_list.request_selected.connect(self._on_request_selected)
        splitter.addWidget(self.request_list)
        
        # Request details widget
        self.request_details = RequestDetailsWidget()
        splitter.addWidget(self.request_details)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def _load_initial_data(self):
        """Load initial mock data."""
        self.requests = generate_mock_data()
        self.request_list.set_requests(self.requests)
        self.status_bar.showMessage(f"Loaded {len(self.requests)} requests")
        
    def _on_request_selected(self, request: InterceptedRequest):
        """Handle request selection."""
        self.request_details.set_request(request)
        self.status_bar.showMessage(
            f"Selected: {request.request.method} {request.request.url}"
        )
        
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
        event.accept()
