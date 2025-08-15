from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, 
                            QWidget, QHBoxLayout, QStatusBar, QPushButton)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import List
import asyncio
from .models import InterceptedRequest
from .mock_data import generate_mock_data
from .request_list_widget import RequestListWidget
from .request_details_widget import RequestDetailsWidget
from .proxy_server import ProxyServer, ProxyConfig


class ProxyWorker(QThread):
    """Worker thread for proxy operations."""
    
    requests_updated = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.proxy_server = None
        
    def run(self):
        """Run the proxy worker."""
        # This is a placeholder for async operations
        pass
        
    def start_proxy(self):
        """Start the proxy server."""
        if not self.proxy_server:
            config = ProxyConfig(host="127.0.0.1", port=8080)
            self.proxy_server = ProxyServer(config)
            
        # Start proxy in async context
        asyncio.create_task(self.proxy_server.start())
        
    def stop_proxy(self):
        """Stop the proxy server."""
        if self.proxy_server:
            asyncio.create_task(self.proxy_server.stop())


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.requests: List[InterceptedRequest] = []
        self.proxy_server = None
        self.proxy_running = False
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
        
        # Left panel with controls and request list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Proxy controls
        controls_layout = QHBoxLayout()
        
        self.start_proxy_btn = QPushButton("Start Proxy")
        self.start_proxy_btn.clicked.connect(self._toggle_proxy)
        controls_layout.addWidget(self.start_proxy_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_requests)
        controls_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_requests)
        controls_layout.addWidget(self.clear_btn)
        
        left_layout.addLayout(controls_layout)
        
        # Request list widget
        self.request_list = RequestListWidget()
        self.request_list.request_selected.connect(self._on_request_selected)
        left_layout.addWidget(self.request_list)
        
        splitter.addWidget(left_panel)
        
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
        
    def _toggle_proxy(self):
        """Toggle the proxy server on/off."""
        if not self.proxy_running:
            self._start_proxy()
        else:
            self._stop_proxy()
            
    def _start_proxy(self):
        """Start the proxy server."""
        try:
            import asyncio
            config = ProxyConfig(host="127.0.0.1", port=8080)
            self.proxy_server = ProxyServer(config)
            
            # Start in background
            asyncio.create_task(self.proxy_server.start())
            
            self.proxy_running = True
            self.start_proxy_btn.setText("Stop Proxy")
            self.status_bar.showMessage("Proxy server started on port 8080")
            
        except Exception as e:
            self.status_bar.showMessage(f"Failed to start proxy: {str(e)}")
            
    def _stop_proxy(self):
        """Stop the proxy server."""
        if self.proxy_server:
            import asyncio
            asyncio.create_task(self.proxy_server.stop())
            
        self.proxy_running = False
        self.start_proxy_btn.setText("Start Proxy")
        self.status_bar.showMessage("Proxy server stopped")
        
    def _refresh_requests(self):
        """Refresh the request list from proxy server."""
        if self.proxy_server:
            self.requests = self.proxy_server.get_requests()
            self.request_list.set_requests(self.requests)
            self.status_bar.showMessage(f"Refreshed {len(self.requests)} requests")
        else:
            # Fallback to mock data
            self.requests = generate_mock_data()
            self.request_list.set_requests(self.requests)
            self.status_bar.showMessage("Using mock data")
            
    def _clear_requests(self):
        """Clear all requests."""
        if self.proxy_server:
            self.proxy_server.clear_requests()
            self.requests = self.proxy_server.get_requests()
        else:
            self.requests.clear()
        self.request_list.set_requests(self.requests)
        self.status_bar.showMessage("Requests cleared")
        
    def _on_request_selected(self, request: InterceptedRequest):
        """Handle request selection."""
        self.request_details.set_request(request)
        self.status_bar.showMessage(
            f"Selected: {request.request.method} {request.request.url}"
        )
        
    def closeEvent(self, event):
        """Handle window close event."""
        if self.proxy_server and self.proxy_running:
            import asyncio
            asyncio.create_task(self.proxy_server.stop())
        event.accept()
