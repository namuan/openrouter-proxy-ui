import asyncio
import contextlib
import logging

from PyQt6.QtCore import QObject, Qt, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from proxy_interceptor import layout_config
from proxy_interceptor.cheatsheet_widget import CheatsheetWidget
from proxy_interceptor.config_widget import ConfigWidget
from proxy_interceptor.proxy_server import ProxyConfig, ProxyServer
from proxy_interceptor.request_details_widget import RequestDetailsWidget
from proxy_interceptor.request_list_widget import RequestListWidget
from proxy_interceptor.styles import STYLESHEET

logger = logging.getLogger(__name__)


class StatusIndicator(QLabel):
    def __init__(self):
        super().__init__()
        self.status = "stopped"
        self.setFixedSize(16, 16)
        self.setToolTip("Proxy Server Status")

    def set_status(self, status: str):
        self.status = status
        self.update()

        if status == "running":
            self.setToolTip("Proxy Server: Running")
        elif status == "error":
            self.setToolTip("Proxy Server: Error")
        else:
            self.setToolTip("Proxy Server: Stopped")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.status == "running":
            color = QColor(34, 197, 94)
        elif self.status == "error":
            color = QColor(239, 68, 68)
        else:
            color = QColor(156, 163, 175)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)


class InterceptBridge(QObject):
    request_intercepted = pyqtSignal(object)
    streaming_update = pyqtSignal(object)


class AsyncRunner(QThread):
    loop_ready = pyqtSignal(object)
    proxy_started = pyqtSignal()
    proxy_stopped = pyqtSignal()
    proxy_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.proxy_server: ProxyServer | None = None
        self._start_requested = False
        self._starting = False
        self._stopping = False
        self.bridge = InterceptBridge()

    def run(self):
        logger.info("Starting async event loop thread")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.loop.call_soon_threadsafe(lambda: self.loop_ready.emit(self.loop))

        try:
            self.loop.run_forever()
        finally:
            logger.info("Async event loop thread finished")
            self.loop.close()

    def start_proxy(self):
        if self._starting:
            logger.info("Start requested but already starting; ignoring")
            return
        if not self.loop or not self.loop.is_running():
            logger.warning("Cannot start proxy - loop not ready, queuing start request")
            self._start_requested = True
            return

        self._starting = True
        asyncio.run_coroutine_threadsafe(self._start_proxy(), self.loop)

    async def _start_proxy(self):
        try:
            main_window = None
            for widget in QApplication.allWidgets():
                if isinstance(widget, MainWindow):
                    main_window = widget
                    break

            if not (main_window and main_window.config_widget.has_valid_config()):
                raise Exception(
                    "No valid configuration found. Please configure API keys and models in the Configuration tab."
                )

            cfg_keys = main_window.config_widget.get_api_keys()
            cfg_models = main_window.config_widget.get_api_models()
            cfg_port = int(main_window.config_widget.get_port())
            try:
                from proxy_interceptor.config_widget import is_port_available

                if not is_port_available(cfg_port):
                    raise Exception(
                        f"Port {cfg_port} is not available. Please choose another port in Configuration and save."
                    )
            except Exception as ve:
                raise Exception(str(ve)) from ve
            cfg_site_url = f"http://localhost:{cfg_port}"

            if self.proxy_server is None:
                config = ProxyConfig(
                    openrouter_api_keys=cfg_keys,
                    openrouter_api_models=cfg_models,
                    port=cfg_port,
                    site_url=cfg_site_url,
                )
                self.proxy_server = ProxyServer(
                    config,
                    on_intercept=self._on_intercept,
                    on_streaming_update=self._on_streaming_update,
                )
            else:
                self.proxy_server.config.openrouter_api_keys = cfg_keys
                self.proxy_server.config.openrouter_api_models = cfg_models
                self.proxy_server.config.port = cfg_port
                self.proxy_server.config.site_url = cfg_site_url

            await self.proxy_server.start()
            self.proxy_started.emit()
        except Exception as e:
            logger.error(f"Failed to start proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
        finally:
            self._starting = False

    def _on_intercept(self, intercepted):
        self.bridge.request_intercepted.emit(intercepted)

    def _on_streaming_update(self, intercepted):
        self.bridge.streaming_update.emit(intercepted)

    def stop_proxy(self):
        if self._stopping:
            logger.info("Stop requested but already stopping; ignoring")
            return
        if not self.loop or not self.loop.is_running():
            logger.warning("Cannot stop proxy - loop not ready")
            return

        self._stopping = True
        asyncio.run_coroutine_threadsafe(self._stop_proxy(), self.loop)

    async def _stop_proxy(self):
        try:
            if self.proxy_server:
                await self.proxy_server.stop()
                self.proxy_stopped.emit()
        except Exception as e:
            logger.error(f"Failed to stop proxy: {e}", exc_info=True)
            self.proxy_error.emit(str(e))
        finally:
            self._stopping = False

    def get_requests(self) -> list:
        if self.proxy_server:
            return self.proxy_server.get_requests()
        return []

    def clear_requests(self):
        if self.proxy_server:
            self.proxy_server.clear_requests()

    def stop(self):
        if self.loop and self.loop.is_running():
            logger.info("Stopping AsyncRunner (ensure proxy stopped first)")
            try:
                if self.proxy_server and self.proxy_server.is_running:
                    fut = asyncio.run_coroutine_threadsafe(
                        self._stop_proxy(), self.loop
                    )
                    with contextlib.suppress(Exception):
                        fut.result(timeout=3.0)
            except Exception:
                logger.exception("Error while stopping proxy before loop shutdown")
            self.loop.call_soon_threadsafe(self.loop.stop)
        super().quit()
        super().wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.async_runner: AsyncRunner | None = None
        self.setWindowTitle("OpenRouter Proxy Interceptor")
        self.setGeometry(100, 100, 1200, 800)

        self.setStyleSheet(STYLESHEET)

        self.intercept_bridge = InterceptBridge()
        self.intercept_bridge.request_intercepted.connect(self._on_request_intercepted)
        self.intercept_bridge.streaming_update.connect(self._on_streaming_update)

        self.config_widget = ConfigWidget()
        self.config_widget.config_changed.connect(self._on_config_changed)
        self.config_widget.config_saved.connect(self._on_config_saved)

        self.cheatsheet_widget = CheatsheetWidget()

        logger.info("Initializing MainWindow")
        self._setup_ui()

        from collections import deque

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._on_status_timeout)
        self._status_queue = deque()
        self._status_showing = False

        try:
            if hasattr(self.config_widget, "status"):
                self.config_widget.status.connect(
                    lambda msg, level: self.show_status(msg, level)
                )
        except Exception:
            logger.exception("Failed to connect config_widget status signal")
        try:
            if hasattr(self.cheatsheet_widget, "status"):
                self.cheatsheet_widget.status.connect(
                    lambda msg, level: self.show_status(msg, level)
                )
        except Exception:
            logger.exception("Failed to connect cheatsheet_widget status signal")

        self._auto_start_proxy()

    def _setup_ui(self):
        logger.debug("Setting up UI")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(layout_config.MAIN_WINDOW_SPACING)
        main_layout.setContentsMargins(*layout_config.MAIN_WINDOW_MARGINS)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(layout_config.PANEL_SPACING)

        self.status_indicator = StatusIndicator()
        control_layout.addWidget(self.status_indicator)

        self.toggle_proxy_btn = QPushButton("Start Proxy")
        self.toggle_proxy_btn.setObjectName("toggleProxyBtn")
        self.toggle_proxy_btn.clicked.connect(self._toggle_proxy)
        control_layout.addWidget(self.toggle_proxy_btn)

        self.clear_btn = QPushButton("Clear All Requests")
        self.clear_btn.clicked.connect(self._clear_requests)
        control_layout.addWidget(self.clear_btn)

        self.auto_follow_btn = QPushButton("🔄 Auto-Follow: ON")
        self.auto_follow_btn.setObjectName("autoFollowBtn")
        self.auto_follow_btn.setToolTip("Toggle automatic following of new requests")
        self.auto_follow_btn.clicked.connect(self._toggle_auto_follow)
        control_layout.addWidget(self.auto_follow_btn)

        self.proxy_url_label = QLabel(
            f"http://127.0.0.1:{self.config_widget.get_port()}"
        )
        self.proxy_url_label.setObjectName("proxyUrlLabel")
        self.proxy_url_label.setEnabled(False)
        control_layout.addWidget(self.proxy_url_label)

        self.copy_url_btn = QPushButton("⧉")
        self.copy_url_btn.setObjectName("copyUrlBtn")
        self.copy_url_btn.setToolTip("Copy proxy URL to clipboard")
        self.copy_url_btn.setFixedSize(25, 25)
        self.copy_url_btn.setEnabled(False)
        self.copy_url_btn.clicked.connect(self._copy_proxy_url)
        control_layout.addWidget(self.copy_url_btn)

        control_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setVisible(False)
        control_layout.addWidget(self.status_label)

        main_layout.addLayout(control_layout)

        self.tab_widget = QTabWidget()

        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        main_tab_layout.setContentsMargins(*layout_config.TAB_WIDGET_PADDING)

        splitter = QSplitter()
        splitter.setHandleWidth(3)

        self.request_list_widget = RequestListWidget()
        self.request_list_widget.request_selected.connect(self._on_request_selected)
        self.request_list_widget.auto_follow_changed.connect(self._on_auto_follow_changed)
        
        # Load auto-follow preference from settings
        settings = QSettings()
        auto_follow_enabled = settings.value("auto_follow_enabled", True, type=bool)
        self.request_list_widget.set_auto_follow_enabled(auto_follow_enabled)
        
        splitter.addWidget(self.request_list_widget)

        self.request_details_widget = RequestDetailsWidget()
        splitter.addWidget(self.request_details_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        splitter.setSizes([150, 500])

        main_tab_layout.addWidget(splitter)

        self.tab_widget.addTab(main_tab, "Requests")
        self.tab_widget.addTab(self.config_widget, "Configuration")
        self.tab_widget.addTab(self.cheatsheet_widget, "Client Settings")

        main_layout.addWidget(self.tab_widget)

        logger.debug("UI setup complete")

    def show_status(self, message: str, level: str = "info", duration: int = 4000):
        if getattr(self, "_status_showing", False):
            try:
                self._status_queue.append((message, level, duration))
                return
            except Exception:
                logger.debug("Status queue not available, showing status immediately")

        self._display_status_now(message, level, duration)

    def _display_status_now(self, message: str, level: str, duration: int):
        try:
            self.status_label.setProperty("level", level)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
        except Exception:
            logger.debug(
                "Failed to repolish status_label after level change", exc_info=True
            )
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        self._status_showing = True
        with contextlib.suppress(Exception):
            self._status_timer.stop()
        self._status_timer.start(max(1000, duration))

    def _on_status_timeout(self):
        try:
            if self._status_queue and len(self._status_queue) > 0:
                next_msg, next_level, next_duration = self._status_queue.popleft()
                self._display_status_now(next_msg, next_level, next_duration)
            else:
                self.status_label.setVisible(False)
                self._status_showing = False
        except Exception:
            self.status_label.setVisible(False)
            self._status_showing = False

    def _auto_start_proxy(self):
        logger.info("Auto-starting proxy server")
        self._toggle_proxy()

    def _toggle_proxy(self):
        logger.info("Toggle proxy button clicked")

        if self.async_runner is None:
            logger.info("Creating new AsyncRunner")
            self.async_runner = AsyncRunner()
            self.async_runner.loop_ready.connect(self._on_loop_ready)
            self.async_runner.proxy_started.connect(self._on_proxy_started)
            self.async_runner.proxy_stopped.connect(self._on_proxy_stopped)
            self.async_runner.proxy_error.connect(self._on_proxy_error)
            self.async_runner.bridge.request_intercepted.connect(
                self._on_request_intercepted
            )
            self.async_runner.bridge.streaming_update.connect(self._on_streaming_update)
            self.async_runner._start_requested = True
            self.toggle_proxy_btn.setEnabled(False)
            self.toggle_proxy_btn.setText("Starting...")
            self.async_runner.start()
            return

        self.toggle_proxy_btn.setEnabled(False)

        if self.toggle_proxy_btn.text() == "Start Proxy":
            logger.info("Starting proxy via AsyncRunner")
            self.toggle_proxy_btn.setText("Starting...")
            self.status_indicator.set_status("stopped")
            self.async_runner.start_proxy()
        else:
            logger.info("Stopping proxy via AsyncRunner")
            self.toggle_proxy_btn.setText("Stopping...")
            self.async_runner.stop_proxy()

    def _on_loop_ready(self):
        logger.info("Async event loop is ready")
        if self.async_runner and self.async_runner._start_requested:
            logger.info("Starting proxy that was queued")
            self.async_runner._start_requested = False
            self.async_runner.start_proxy()
        if not (self.async_runner and self.async_runner._starting):
            self.toggle_proxy_btn.setEnabled(True)
            if self.toggle_proxy_btn.text() == "Starting...":
                self.toggle_proxy_btn.setText("Start Proxy")

    def _on_proxy_started(self):
        logger.info("Proxy server started successfully")
        self.toggle_proxy_btn.setText("Stop Proxy")
        self.toggle_proxy_btn.setEnabled(True)
        self.status_indicator.set_status("running")
        self.proxy_url_label.setEnabled(True)
        self.proxy_url_label.setText(
            f"http://127.0.0.1:{self.config_widget.get_port()}"
        )
        self.copy_url_btn.setEnabled(True)
        self.show_status("Proxy started and ready", level="success")

    def _on_proxy_stopped(self):
        logger.info("Proxy server stopped")
        self.toggle_proxy_btn.setText("Start Proxy")
        self.toggle_proxy_btn.setEnabled(True)
        self.status_indicator.set_status("stopped")
        self.proxy_url_label.setEnabled(False)
        self.copy_url_btn.setEnabled(False)
        self.show_status("Proxy stopped", level="info")

    def _on_proxy_error(self, error: str):
        logger.error(f"Proxy error: {error}")
        self.status_indicator.set_status("error")
        self.toggle_proxy_btn.setEnabled(True)
        if self.toggle_proxy_btn.text() in ("Starting...", "Stopping..."):
            self.toggle_proxy_btn.setText("Start Proxy")
        try:
            from proxy_interceptor.error_utils import to_user_message

            guidance_text = to_user_message(error)
        except Exception:
            guidance_text = (
                "Proxy error. Check if the port is in use or if configuration is valid. "
                "Try changing the port in the Configuration tab."
            )
        self.show_status(guidance_text, level="error")

    def _on_request_intercepted(self, intercepted):
        logger.info("New intercepted request received; updating UI list")
        self.request_list_widget.add_request(intercepted)

    def _on_streaming_update(self, intercepted):
        logger.debug("Streaming update received; updating UI")
        self.request_list_widget.update_streaming_request(intercepted)
        if (
            hasattr(self, "request_details_widget")
            and self.request_details_widget.current_request
            and self.request_details_widget.current_request.request.timestamp
            == intercepted.request.timestamp
        ):
            self.request_details_widget.update_streaming_content(intercepted)

    def _clear_requests(self):
        logger.info("Clear button clicked")
        if self.async_runner:
            self.async_runner.clear_requests()
        self.request_list_widget.set_requests([])
        self.request_details_widget.clear()
        self.show_status("Cleared all requests", level="success", duration=2500)

    def _copy_proxy_url(self):
        port = int(self.config_widget.get_port())
        proxy_url = f"http://127.0.0.1:{port}"
        clipboard = QApplication.clipboard()
        clipboard.setText(proxy_url)
        logger.info(f"Copied proxy URL to clipboard: {proxy_url}")

        self.copy_url_btn.setText("✓")
        try:
            self.copy_url_btn.setProperty("success", True)
            self.copy_url_btn.style().unpolish(self.copy_url_btn)
            self.copy_url_btn.style().polish(self.copy_url_btn)
        except Exception:
            logger.debug(
                "Failed to repolish copy_url_btn after success property", exc_info=True
            )

        def reset_button():
            self.copy_url_btn.setText("⧉")
            try:
                self.copy_url_btn.setProperty("success", False)
                self.copy_url_btn.style().unpolish(self.copy_url_btn)
                self.copy_url_btn.style().polish(self.copy_url_btn)
            except Exception:
                logger.debug(
                    "Failed to repolish copy_url_btn during reset", exc_info=True
                )

        QTimer.singleShot(500, reset_button)
        self.show_status(
            "Proxy URL copied to clipboard", level="success", duration=2000
        )

    def _on_request_selected(self, request):
        self.request_details_widget.set_request(request)
    
    def _toggle_auto_follow(self):
        """Toggle the auto-follow feature on/off."""
        current_state = self.request_list_widget.is_auto_follow_enabled()
        new_state = not current_state
        self.request_list_widget.set_auto_follow_enabled(new_state)
        logger.info(f"Auto-follow toggled to: {'ON' if new_state else 'OFF'}")
    
    def _on_auto_follow_changed(self, enabled: bool):
        """Update the UI when auto-follow state changes."""
        if enabled:
            self.auto_follow_btn.setText("🔄 Auto-Follow: ON")
            self.auto_follow_btn.setProperty("autoFollowEnabled", True)
        else:
            self.auto_follow_btn.setText("⏸️ Auto-Follow: OFF")
            self.auto_follow_btn.setProperty("autoFollowEnabled", False)
        
        # Save preference to settings
        settings = QSettings()
        settings.setValue("auto_follow_enabled", enabled)
        
        # Refresh button styling
        self.auto_follow_btn.style().unpolish(self.auto_follow_btn)
        self.auto_follow_btn.style().polish(self.auto_follow_btn)

    def _on_config_changed(self):
        logger.debug("Configuration changed")
        self.proxy_url_label.setText(
            f"http://127.0.0.1:{self.config_widget.get_port()}"
        )

        if self.config_widget.has_valid_config():
            logger.info(
                f"Configuration updated (unsaved): {len(self.config_widget.get_api_keys())} keys, {len(self.config_widget.get_api_models())} models"
            )
        else:
            logger.warning("Configuration is incomplete - missing API keys or models")

    def _on_config_saved(self):
        try:
            new_port = int(self.config_widget.get_port())
            self.proxy_url_label.setText(f"http://127.0.0.1:{new_port}")

            if self.async_runner and self.async_runner.proxy_server:
                try:
                    is_running = self.async_runner.proxy_server.is_running
                    current_port = int(self.async_runner.proxy_server.config.port)
                    if is_running and new_port != current_port:
                        logger.info(
                            f"Config saved and port changed from {current_port} to {new_port}. Restarting proxy..."
                        )
                        self.async_runner.stop_proxy()
                        QTimer.singleShot(800, self.async_runner.start_proxy)
                except Exception:
                    logger.exception(
                        "Error while attempting to restart proxy after save"
                    )

            try:
                if self.cheatsheet_widget:
                    old_port = None
                    try:
                        if self.async_runner and self.async_runner.proxy_server:
                            old_port = int(self.async_runner.proxy_server.config.port)
                    except Exception:
                        old_port = None
                    if old_port is None:
                        old_port = new_port
                    self.cheatsheet_widget.update_port_and_save(old_port, new_port)
            except Exception:
                logger.exception("Failed to update cheatsheet after config save")
        except Exception:
            logger.exception("Error handling config_saved event")

    def closeEvent(self, event):
        logger.info("Application closing")

        if self.async_runner and self.async_runner.isRunning():
            logger.info("Stopping AsyncRunner")
            self.async_runner.stop()

        event.accept()
