import asyncio
import logging
import sys
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QHBoxLayout, QMessageBox, QSplitter)

from .proxy_server import ProxyServer, ProxyConfig
from .request_list_widget import RequestListWidget
from .request_details_widget import RequestDetailsWidget
from .mock_data import generate_mock_data

logger = logging.getLogger(__name__)


class AsyncRunner(QThread):
    """Thread for running async operations."""
    
    loop_ready = pyqtSignal(object)  # Emits the event loop when ready
    proxy_started = pyqtSignal()
    proxy_stopped = pyqtSignal()
    proxy_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.proxy_server: Optional[ProxyServer] = None
        self._start_requested = False
        
    def run(self):
        """Run the async event loop in this thread."""
        logger.info("Starting async event loop thread")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Schedule a call to emit the loop reference
        self.loop.call_soon_threadsafe(lambda: self.loop_ready.emit(self.loop))
        
        try:
            self.loop.run_forever()
        finally:
            logger.info("Async event loop thread finished")
            self.loop.close()
    
    def start_proxy(self):
        """Start the proxy server."""
        if not self.loop or not self.loop.is_running():
            logger.warning("Cannot start proxy - loop not ready, queuing start request")
            self._start_requested = True
            return
            
        asyncio.run_coroutine_threadsafe(self._start_proxy(), self.loop)
    
    async def _start_proxy(self):
        """Async implementation to start the proxy server."""
        try:
            if self.proxy_server is None:
                config = ProxyConfig()
                self.proxy_server = ProxyServer(config)
            
            await self.proxy_server.start()
            self.proxy_started.emit()
        except Exception as e:
            logger.error(f"Failed to start proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
    
    def stop_proxy(self):
        """Stop the proxy server."""
        if not self.loop or not self.loop.is_running():
            logger.warning("Cannot stop proxy - loop not ready")
            return
            
        asyncio.run_coroutine_threadsafe(self._stop_proxy(), self.loop)
    
    async def _stop_proxy(self):
        """Async implementation to stop the proxy server."""
        try:
            if self.proxy_server:
                await self.proxy_server.stop()
                self.proxy_stopped.emit()
        except Exception as e:
            logger.error(f"Failed to stop proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
    
    def get_requests(self) -> list:
        """Get intercepted requests from the proxy server."""
        if self.proxy_server:
            return self.proxy_server.get_requests()
        return []
    
    def clear_requests(self):
        """Clear intercepted requests."""
        if self.proxy_server:
            self.proxy_server.clear_requests()
    
    def stop(self):
        """Stop the thread by stopping its event loop."""
        if self.loop and self.loop.is_running():
            logger.info("Stopping AsyncRunner")
            self.loop.call_soon_threadsafe(self.loop.stop)
        super().quit()
        super().wait()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.async_runner: Optional[AsyncRunner] = None
        self.setWindowTitle("Proxy Interceptor")
        self.setGeometry(100, 100, 1200, 800)
        
        logger.info("Initializing MainWindow")
        self._setup_ui()
        self._load_initial_data()
        
    def _setup_ui(self):
        """Set up the user interface."""
        logger.debug("Setting up UI")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create control buttons
        control_layout = QHBoxLayout()
        
        self.toggle_proxy_btn = QPushButton("Start Proxy")
        self.toggle_proxy_btn.clicked.connect(self._toggle_proxy)
        control_layout.addWidget(self.toggle_proxy_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_requests)
        control_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_requests)
        control_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(control_layout)
        
        # Create splitter for request list and details
        splitter = QSplitter()
        
        # Request list widget
        self.request_list_widget = RequestListWidget()
        self.request_list_widget.request_selected.connect(self._on_request_selected)
        splitter.addWidget(self.request_list_widget)
        
        # Request details widget
        self.request_details_widget = RequestDetailsWidget()
        splitter.addWidget(self.request_details_widget)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        logger.debug("UI setup complete")
    
    def _load_initial_data(self):
        """Load initial mock data."""
        logger.info("Loading initial mock data")
        mock_requests = generate_mock_data()
        self.request_list_widget.set_requests(mock_requests)
        logger.info(f"Loaded {len(mock_requests)} mock requests")
    
    def _toggle_proxy(self):
        """Toggle the proxy server on/off."""
        logger.info("Toggle proxy button clicked")
        
        if self.async_runner is None:
            logger.info("Creating new AsyncRunner")
            self.async_runner = AsyncRunner()
            self.async_runner.loop_ready.connect(self._on_loop_ready)
            self.async_runner.proxy_started.connect(self._on_proxy_started)
            self.async_runner.proxy_stopped.connect(self._on_proxy_stopped)
            self.async_runner.proxy_error.connect(self._on_proxy_error)
            self.async_runner.start()
            return
            
        if self.toggle_proxy_btn.text() == "Start Proxy":
            logger.info("Starting proxy via AsyncRunner")
            self.async_runner.start_proxy()
        else:
            logger.info("Stopping proxy via AsyncRunner")
            self.async_runner.stop_proxy()
    
    def _on_loop_ready(self):
        """Called when the async event loop is ready."""
        logger.info("Async event loop is ready")
        # If start was requested before loop was ready, start it now
        if self.async_runner and self.async_runner._start_requested:
            logger.info("Starting proxy that was queued")
            self.async_runner._start_requested = False
            self.async_runner.start_proxy()
    
    def _on_proxy_started(self):
        """Called when the proxy server has started."""
        logger.info("Proxy server started successfully")
        self.toggle_proxy_btn.setText("Stop Proxy")
    
    def _on_proxy_stopped(self):
        """Called when the proxy server has stopped."""
        logger.info("Proxy server stopped")
        self.toggle_proxy_btn.setText("Start Proxy")
    
    def _on_proxy_error(self, error: str):
        """Called when a proxy error occurs."""
        logger.error(f"Proxy error: {error}")
        QMessageBox.critical(self, "Proxy Error", f"Proxy error: {error}")
    
    def _refresh_requests(self):
        """Refresh the request list."""
        logger.info("Refresh button clicked")
        if self.async_runner:
            requests = self.async_runner.get_requests()
            self.request_list_widget.set_requests(requests)
    
    def _clear_requests(self):
        """Clear all requests."""
        logger.info("Clear button clicked")
        if self.async_runner:
            self.async_runner.clear_requests()
        self.request_list_widget.set_requests([])
        self.request_details_widget.clear()
    
    def _on_request_selected(self, request):
        """Handle request selection."""
        self.request_details_widget.set_request(request)
    
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Application closing")
        
        if self.async_runner and self.async_runner.isRunning():
            logger.info("Stopping AsyncRunner")
            self.async_runner.stop()
        
        event.accept()
