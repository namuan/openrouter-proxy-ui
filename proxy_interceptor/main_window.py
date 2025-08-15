from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, 
                            QWidget, QHBoxLayout, QStatusBar, QPushButton)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from typing import List
import asyncio
import logging
from .models import InterceptedRequest
from .mock_data import generate_mock_data
from .request_list_widget import RequestListWidget
from .request_details_widget import RequestDetailsWidget
from .proxy_server import ProxyServer, ProxyConfig

logger = logging.getLogger(__name__)


class AsyncRunner(QThread):
    """Thread for running async operations."""
    
    proxy_started = pyqtSignal()
    proxy_stopped = pyqtSignal()
    proxy_error = pyqtSignal(str)
    loop_ready = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.proxy_server = None
        self.loop = None
        self._proxy_running = False
        logger.debug("AsyncRunner initialized")
        
    def run(self):
        """Run the async event loop."""
        try:
            logger.info("Starting async event loop thread")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            logger.info("Async event loop created and set")
            self.loop_ready.emit()
            self.loop.run_forever()
            logger.info("Async event loop stopped")
        except Exception as e:
            logger.error(f"Error in AsyncRunner: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
            
    def start_proxy(self):
        """Start the proxy server in the async thread."""
        logger.info("Attempting to start proxy server")
        if not self.proxy_server:
            config = ProxyConfig(host="127.0.0.1", port=8080)
            self.proxy_server = ProxyServer(config)
            logger.info(f"Created proxy server with config: {config}")
            
        if self.loop and self.loop.is_running():
            logger.debug("Loop is running, scheduling proxy start")
            asyncio.run_coroutine_threadsafe(self._start_proxy(), self.loop)
        else:
            logger.warning("Loop not ready, scheduling retry")
            QTimer.singleShot(100, self.start_proxy)
            
    async def _start_proxy(self):
        """Async method to start proxy."""
        try:
            logger.info("Starting proxy server coroutine")
            await self.proxy_server.start()
            self._proxy_running = True
            logger.info("Proxy server started successfully")
            self.proxy_started.emit()
        except Exception as e:
            logger.error(f"Error starting proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
            
    def stop_proxy(self):
        """Stop the proxy server."""
        logger.info("Attempting to stop proxy server")
        if self.proxy_server and self.loop and self.loop.is_running():
            logger.debug("Scheduling proxy stop")
            asyncio.run_coroutine_threadsafe(self._stop_proxy(), self.loop)
        else:
            logger.warning("Cannot stop proxy - loop not ready")
            
    async def _stop_proxy(self):
        """Async method to stop proxy."""
        try:
            logger.info("Stopping proxy server coroutine")
            await self.proxy_server.stop()
            self._proxy_running = False
            logger.info("Proxy server stopped successfully")
            self.proxy_stopped.emit()
        except Exception as e:
            logger.error(f"Error stopping proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
            
    def get_requests(self) -> list[InterceptedRequest]:
        """Get intercepted requests."""
        if self.proxy_server:
            requests = self.proxy_server.get_requests()
            logger.debug(f"Retrieved {len(requests)} intercepted requests")
            return requests
        logger.warning("No proxy server available to get requests")
        return []
        
    def clear_requests(self):
        """Clear intercepted requests."""
        if self.proxy_server:
            self.proxy_server.clear_requests()
            logger.info("Cleared intercepted requests")
        else:
            logger.warning("No proxy server available to clear requests")


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.requests: List[InterceptedRequest] = []
        self.async_runner = None
        logger.info("Initializing MainWindow")
        self._setup_ui()
        self._load_initial_data()
        logger.info("MainWindow initialization complete")
        
    def _setup_ui(self):
        """Set up the user interface."""
        logger.debug("Setting up UI")
        self.setWindowTitle("Proxy Interceptor")
        self.setGeometry(100, 100, 1200, 800)
        logger.debug(f"Window geometry set: {self.geometry()}")
        
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
        logger.debug("UI setup complete")
        
    def _load_initial_data(self):
        """Load initial mock data."""
        logger.info("Loading initial mock data")
        self.requests = generate_mock_data()
        self.request_list.set_requests(self.requests)
        logger.info(f"Loaded {len(self.requests)} mock requests")
        self.status_bar.showMessage(f"Loaded {len(self.requests)} requests")
        
    def _toggle_proxy(self):
        """Toggle the proxy server on/off."""
        logger.info("Toggle proxy button clicked")
        if not self.async_runner:
            logger.info("Creating new AsyncRunner")
            self.async_runner = AsyncRunner()
            self.async_runner.proxy_started.connect(self._on_proxy_started)
            self.async_runner.proxy_stopped.connect(self._on_proxy_stopped)
            self.async_runner.proxy_error.connect(self._on_proxy_error)
            self.async_runner.loop_ready.connect(self._on_loop_ready)
            self.async_runner.start()
            self.start_proxy_btn.setEnabled(False)  # Disable until loop is ready
            logger.debug("AsyncRunner started")
        elif self.start_proxy_btn.text() == "Start Proxy":
            logger.info("Starting proxy via AsyncRunner")
            self.async_runner.start_proxy()
        else:
            logger.info("Stopping proxy via AsyncRunner")
            self.async_runner.stop_proxy()
            
    def _on_loop_ready(self):
        """Handle when the event loop is ready."""
        logger.info("Async event loop is ready")
        self.start_proxy_btn.setEnabled(True)
        
    def _on_proxy_started(self):
        """Handle proxy started."""
        logger.info("Proxy server started successfully")
        self.start_proxy_btn.setText("Stop Proxy")
        self.status_bar.showMessage("Proxy server started on port 8080")
        
    def _on_proxy_stopped(self):
        """Handle proxy stopped."""
        logger.info("Proxy server stopped")
        self.start_proxy_btn.setText("Start Proxy")
        self.status_bar.showMessage("Proxy server stopped")
        
    def _on_proxy_error(self, error):
        """Handle proxy error."""
        logger.error(f"Proxy error: {error}")
        self.status_bar.showMessage(f"Proxy error: {error}")
        self.start_proxy_btn.setText("Start Proxy")
        
    def _refresh_requests(self):
        """Refresh the request list from proxy server."""
        logger.info("Refreshing request list")
        if self.async_runner:
            self.requests = self.async_runner.get_requests()
            self.request_list.set_requests(self.requests)
            logger.info(f"Refreshed {len(self.requests)} requests from proxy")
            self.status_bar.showMessage(f"Refreshed {len(self.requests)} requests")
        else:
            # Fallback to mock data
            logger.info("Using mock data for refresh")
            self.requests = generate_mock_data()
            self.request_list.set_requests(self.requests)
            self.status_bar.showMessage("Using mock data")
            
    def _clear_requests(self):
        """Clear all requests."""
        logger.info("Clearing all requests")
        if self.async_runner:
            self.async_runner.clear_requests()
            self.requests = self.async_runner.get_requests()
            logger.info("Cleared requests via proxy server")
        else:
            self.requests.clear()
            logger.info("Cleared local requests")
        self.request_list.set_requests(self.requests)
        self.status_bar.showMessage("Requests cleared")
        
    def _on_request_selected(self, request: InterceptedRequest):
        """Handle request selection."""
        logger.info(f"Request selected: {request.request.method} {request.request.url}")
        self.request_details.set_request(request)
        self.status_bar.showMessage(
            f"Selected: {request.request.method} {request.request.url}"
        )
        
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Application closing")
        if self.async_runner and self.async_runner.isRunning():
            if self.start_proxy_btn.text() == "Stop Proxy":
                logger.info("Stopping proxy server before exit")
                self.async_runner.stop_proxy()
            logger.info("Stopping AsyncRunner")
            self.async_runner.quit()
            self.async_runner.wait()
        logger.info("Application closed")
        event.accept()
