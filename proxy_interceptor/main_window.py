import asyncio
import logging
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QSplitter,
    QLabel,
    QTabWidget,
    QApplication,
)
from PyQt6.QtGui import QPainter, QColor, QIcon

from .proxy_server import ProxyServer, ProxyConfig
from .request_list_widget import RequestListWidget
from .request_details_widget import RequestDetailsWidget
from .config_widget import ConfigWidget
from .cheatsheet_widget import CheatsheetWidget
from .styles import STYLESHEET

logger = logging.getLogger(__name__)


class StatusIndicator(QLabel):
    """A colored dot widget to show proxy server status."""

    def __init__(self):
        super().__init__()
        self.status = "stopped"  # stopped, running, error
        self.setFixedSize(16, 16)
        self.setToolTip("Proxy Server Status")

    def set_status(self, status: str):
        """Set the status and update the display."""
        self.status = status
        self.update()

        # Update tooltip
        if status == "running":
            self.setToolTip("Proxy Server: Running")
        elif status == "error":
            self.setToolTip("Proxy Server: Error")
        else:
            self.setToolTip("Proxy Server: Stopped")

    def paintEvent(self, event):
        """Paint the status indicator dot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Choose color based on status
        if self.status == "running":
            color = QColor(34, 197, 94)  # Green
        elif self.status == "error":
            color = QColor(239, 68, 68)  # Red
        else:
            color = QColor(156, 163, 175)  # Gray

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)


class InterceptBridge(QObject):
    """Signal bridge to safely emit intercepted requests to the UI thread."""

    request_intercepted = pyqtSignal(object)  # emits InterceptedRequest


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
        self.bridge = InterceptBridge()

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
                # Get configuration from the main window's config widget
                main_window = None
                for widget in QApplication.allWidgets():
                    if isinstance(widget, MainWindow):
                        main_window = widget
                        break

                if main_window and main_window.config_widget.has_valid_config():
                    # Use configuration from config widget
                    cfg_keys = main_window.config_widget.get_api_keys()
                    cfg_models = main_window.config_widget.get_api_models()
                    cfg_port = int(main_window.config_widget.get_port())
                    cfg_site_url = f"http://localhost:{cfg_port}"
                else:
                    # No valid configuration available
                    raise Exception(
                        "No valid configuration found. Please configure API keys and models in the Configuration tab."
                    )

                if self.proxy_server is None:
                    config = ProxyConfig(
                        openrouter_api_keys=cfg_keys,
                        openrouter_api_models=cfg_models,
                        port=cfg_port,
                        site_url=cfg_site_url,
                    )
                    self.proxy_server = ProxyServer(config, on_intercept=self._on_intercept)
                else:
                    # Update existing server config before (re)starting
                    self.proxy_server.config.openrouter_api_keys = cfg_keys
                    self.proxy_server.config.openrouter_api_models = cfg_models
                    self.proxy_server.config.port = cfg_port
                    self.proxy_server.config.site_url = cfg_site_url

            await self.proxy_server.start()
            self.proxy_started.emit()
        except Exception as e:
            logger.error(f"Failed to start proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))

    def _on_intercept(self, intercepted):
        """Called by ProxyServer thread when a request is intercepted."""
        # This callback runs in the proxy thread context; emit via signal to UI thread
        self.bridge.request_intercepted.emit(intercepted)

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
        self.setWindowTitle("OpenRouter Proxy Interceptor")
        self.setGeometry(100, 100, 1200, 800)

        # Apply modern stylesheet
        self.setStyleSheet(STYLESHEET)

        self.intercept_bridge = InterceptBridge()
        self.intercept_bridge.request_intercepted.connect(self._on_request_intercepted)

        # Create configuration widget
        self.config_widget = ConfigWidget()
        self.config_widget.config_changed.connect(self._on_config_changed)
        # React only on explicit save for server restarts
        self.config_widget.config_saved.connect(self._on_config_saved)
        
        # Create cheatsheet widget
        self.cheatsheet_widget = CheatsheetWidget()

        logger.info("Initializing MainWindow")
        self._setup_ui()
        self._auto_start_proxy()

    def _setup_ui(self):
        """Set up the user interface."""
        logger.debug("Setting up UI")

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create control buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        # Add status indicator
        self.status_indicator = StatusIndicator()
        control_layout.addWidget(self.status_indicator)

        self.toggle_proxy_btn = QPushButton("Start Proxy")
        self.toggle_proxy_btn.setObjectName("toggleProxyBtn")
        self.toggle_proxy_btn.clicked.connect(self._toggle_proxy)
        control_layout.addWidget(self.toggle_proxy_btn)

        self.clear_btn = QPushButton("Clear All Requests")
        self.clear_btn.clicked.connect(self._clear_requests)
        control_layout.addWidget(self.clear_btn)

        # Add proxy URL label and copy button
        self.proxy_url_label = QLabel(f"http://127.0.0.1:{self.config_widget.get_port()}")
        self.proxy_url_label.setStyleSheet("color: #888888; font-family: 'Monaco', 'Courier New', monospace;")
        self.proxy_url_label.setEnabled(False)  # Start greyed out
        control_layout.addWidget(self.proxy_url_label)
        
        # Add copy button with font glyph
        self.copy_url_btn = QPushButton("⧉")
        self.copy_url_btn.setToolTip("Copy proxy URL to clipboard")
        self.copy_url_btn.setFixedSize(25, 25)
        self.copy_url_btn.setStyleSheet("font-size: 14px; padding: 1px;")
        self.copy_url_btn.setEnabled(False)  # Start disabled
        self.copy_url_btn.clicked.connect(self._copy_proxy_url)
        control_layout.addWidget(self.copy_url_btn)

        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Main tab with request list and details
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        main_tab_layout.setContentsMargins(10, 10, 10, 10)

        # Create splitter for request list and details
        splitter = QSplitter()
        splitter.setHandleWidth(3)  # Make handle more visible
        splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")

        # Request list widget
        self.request_list_widget = RequestListWidget()
        self.request_list_widget.request_selected.connect(self._on_request_selected)
        splitter.addWidget(self.request_list_widget)

        # Request details widget
        self.request_details_widget = RequestDetailsWidget()
        splitter.addWidget(self.request_details_widget)

        # Set splitter proportions - expand request list more by default
        splitter.setStretchFactor(0, 1)  # Request list gets more space
        splitter.setStretchFactor(1, 2)  # Details gets less space
        
        # Set initial sizes to give more space to request list
        splitter.setSizes([150, 500])  # Request list: 400px, Details: 200px

        main_tab_layout.addWidget(splitter)

        # Add tabs
        self.tab_widget.addTab(main_tab, "Requests")
        self.tab_widget.addTab(self.config_widget, "Configuration")
        self.tab_widget.addTab(self.cheatsheet_widget, "Client Settings")

        main_layout.addWidget(self.tab_widget)

        logger.debug("UI setup complete")

    def _auto_start_proxy(self):
        """Auto-start the proxy server when the application starts."""
        logger.info("Auto-starting proxy server")
        self._toggle_proxy()

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
            # Connect live update signal
            self.async_runner.bridge.request_intercepted.connect(
                self._on_request_intercepted
            )
            # Queue the start request before starting the thread
            self.async_runner._start_requested = True
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
        self.status_indicator.set_status("running")
        self.proxy_url_label.setEnabled(True)
        self.proxy_url_label.setStyleSheet("color: #333333; font-family: 'Monaco', 'Courier New', monospace;")
        # Update displayed URL to current port
        self.proxy_url_label.setText(f"http://127.0.0.1:{self.config_widget.get_port()}")
        self.copy_url_btn.setEnabled(True)

    def _on_proxy_stopped(self):
        """Called when the proxy server has stopped."""
        logger.info("Proxy server stopped")
        self.toggle_proxy_btn.setText("Start Proxy")
        self.status_indicator.set_status("stopped")
        self.proxy_url_label.setEnabled(False)
        self.proxy_url_label.setStyleSheet("color: #888888; font-family: 'Monaco', 'Courier New', monospace;")
        self.copy_url_btn.setEnabled(False)

    def _on_proxy_error(self, error: str):
        """Called when a proxy error occurs."""
        logger.error(f"Proxy error: {error}")
        self.status_indicator.set_status("error")
        QMessageBox.critical(self, "Proxy Error", f"Proxy error: {error}")

    def _on_request_intercepted(self, intercepted):
        """Live-update the UI when a new request is intercepted."""
        logger.info("New intercepted request received; updating UI list")
        self.request_list_widget.add_request(intercepted)

    def _clear_requests(self):
        """Clear all requests."""
        logger.info("Clear button clicked")
        if self.async_runner:
            self.async_runner.clear_requests()
        self.request_list_widget.set_requests([])
        self.request_details_widget.clear()
    
    def _copy_proxy_url(self):
        """Copy the proxy URL to clipboard."""
        port = int(self.config_widget.get_port())
        proxy_url = f"http://127.0.0.1:{port}"
        clipboard = QApplication.clipboard()
        clipboard.setText(proxy_url)
        logger.info(f"Copied proxy URL to clipboard: {proxy_url}")
        
        # Show a brief visual feedback
        original_text = self.copy_url_btn.text()
        original_style = self.copy_url_btn.styleSheet()
        self.copy_url_btn.setText("✓")
        self.copy_url_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 2px; color: white; background-color: green; border-radius: 3px;")
        
        # Reset button after 500ms using QTimer
        def reset_button():
            self.copy_url_btn.setText(original_text)
            self.copy_url_btn.setStyleSheet(original_style)
        
        QTimer.singleShot(500, reset_button)

    def _on_request_selected(self, request):
        """Handle request selection."""
        self.request_details_widget.set_request(request)

    def _on_config_changed(self):
        """Handle configuration changes."""
        logger.debug("Configuration changed")
        # Update displayed URL label immediately (but do not restart server here)
        self.proxy_url_label.setText(f"http://127.0.0.1:{self.config_widget.get_port()}")

        if self.config_widget.has_valid_config():
            logger.info(
                f"Configuration updated (unsaved): {len(self.config_widget.get_api_keys())} keys, {len(self.config_widget.get_api_models())} models"
            )
        else:
            logger.warning("Configuration is incomplete - missing API keys or models")

    def _on_config_saved(self):
        """Handle configuration saved: restart server if needed and update cheatsheet."""
        try:
            # Update displayed URL label to saved port
            new_port = int(self.config_widget.get_port())
            self.proxy_url_label.setText(f"http://127.0.0.1:{new_port}")

            # Restart proxy only on save if port changed
            if self.async_runner and self.async_runner.proxy_server:
                try:
                    is_running = self.async_runner.proxy_server.is_running
                    current_port = int(self.async_runner.proxy_server.config.port)
                    if is_running and new_port != current_port:
                        logger.info(f"Config saved and port changed from {current_port} to {new_port}. Restarting proxy...")
                        self.async_runner.stop_proxy()
                        QTimer.singleShot(800, self.async_runner.start_proxy)
                except Exception:
                    logger.exception("Error while attempting to restart proxy after save")

            # Update Client Settings (Cheatsheet) text to new port and save
            try:
                if self.cheatsheet_widget:
                    self.cheatsheet_widget.update_port_and_save(new_port)
            except Exception:
                logger.exception("Failed to update cheatsheet after config save")
        except Exception:
            logger.exception("Error handling config_saved event")

    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Application closing")

        if self.async_runner and self.async_runner.isRunning():
            logger.info("Stopping AsyncRunner")
            self.async_runner.stop()

        event.accept()
