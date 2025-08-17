import json
import logging
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from proxy_interceptor.models import InterceptedRequest

logger = logging.getLogger(__name__)


class RequestListWidget(QWidget):
    request_selected = pyqtSignal(InterceptedRequest)
    auto_follow_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.requests: list[InterceptedRequest] = []
        self._auto_follow_enabled = True  # Auto-follow is enabled by default
        self._user_manually_selected = False  # Track if user manually selected a request
        logger.debug("RequestListWidget initialized")
        self._setup_ui()
        self._pending: list[InterceptedRequest] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_pending)

    def _setup_ui(self):
        logger.debug("Setting up RequestListWidget UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QLabel("Intercepted Requests")
        header.setObjectName("header")
        layout.addWidget(header)

        self.request_list = QListWidget()
        self.request_list.setAlternatingRowColors(True)
        self.request_list.itemClicked.connect(self._on_request_clicked)
        self.request_list.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self.request_list)
        logger.debug("RequestListWidget UI setup complete")

    def set_requests(self, requests: list[InterceptedRequest]):
        logger.info(f"Setting {len(requests)} requests in list widget")
        self.requests = requests
        self._update_list()

    def add_request(self, request: InterceptedRequest):
        self.requests.append(request)
        self._pending.append(request)
        try:
            if self._flush_timer.isActive():
                self._flush_timer.stop()
            self._flush_timer.start(100)
        except Exception:
            self._flush_pending()
        
        # Auto-select the new request if auto-follow is enabled
        if self._auto_follow_enabled:
            self._auto_select_latest_request()

    def _update_list(self):
        logger.debug(f"Updating list widget with {len(self.requests)} requests")
        self.request_list.clear()

        for i, request in enumerate(self.requests):
            item = QListWidgetItem()
            parsed_url = urlparse(request.request.url)
            path = parsed_url.path if parsed_url.path else "/"

            model_name = "unknown"
            try:
                if request.request.body:
                    body_data = json.loads(request.request.body)
                    model_name = body_data.get("model", "unknown")
            except (json.JSONDecodeError, AttributeError):
                pass

            suffix = ""
            try:
                lat = request.response.latency_ms
                tok = request.response.total_tokens
                parts = []
                if lat is not None:
                    parts.append(f"{lat:.0f}ms")
                if tok is not None:
                    parts.append(f"tok:{tok}")
                if parts:
                    suffix = "  (" + ", ".join(parts) + ")"
            except Exception as e:
                logger.debug(f"Error creating suffix: {e}")

            item.setText(
                f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
                f"{request.request.method} {path} - {model_name}{suffix}"
            )
            item.setData(Qt.ItemDataRole.UserRole, request)
            self.request_list.addItem(item)
            logger.debug(
                f"Added request {i + 1} to list: {request.request.method} {path} - {model_name}{suffix}"
            )

    def _create_list_item(self, request: InterceptedRequest) -> QListWidgetItem:
        item = QListWidgetItem()
        parsed_url = urlparse(request.request.url)
        path = parsed_url.path if parsed_url.path else "/"

        model_name = "unknown"
        try:
            if request.request.body:
                body_data = json.loads(request.request.body)
                model_name = body_data.get("model", "unknown")
        except (json.JSONDecodeError, AttributeError):
            pass

        suffix = ""
        try:
            lat = request.response.latency_ms
            tok = request.response.total_tokens
            parts = []
            if lat is not None:
                parts.append(f"{lat:.0f}ms")
            if tok is not None:
                parts.append(f"tok:{tok}")
            if parts:
                suffix = "  (" + ", ".join(parts) + ")"
        except Exception as e:
            logger.debug(f"Error creating suffix: {e}")

        item.setText(
            f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
            f"{request.request.method} {path} - {model_name}{suffix}"
        )
        item.setData(Qt.ItemDataRole.UserRole, request)
        return item

    # ruff: noqa: C901
    def update_streaming_request(self, updated_request: InterceptedRequest):
        for i, existing_request in enumerate(self.requests):
            if existing_request.request.timestamp == updated_request.request.timestamp:
                self.requests[i] = updated_request

                item = self.request_list.item(i)
                if item:
                    parsed_url = urlparse(updated_request.request.url)
                    path = parsed_url.path if parsed_url.path else "/"

                    model_name = "unknown"
                    try:
                        if updated_request.request.body:
                            body_data = json.loads(updated_request.request.body)
                            model_name = body_data.get("model", "unknown")
                    except (json.JSONDecodeError, AttributeError):
                        pass

                    suffix = ""
                    try:
                        parts = []
                        if (
                            updated_request.response.is_streaming
                            and not updated_request.response.streaming_complete
                        ):
                            content_len = len(
                                updated_request.response.streaming_content
                            )
                            parts.append(f"streaming: {content_len} chars")
                        elif updated_request.response.streaming_complete:
                            lat = updated_request.response.latency_ms
                            tok = updated_request.response.total_tokens
                            if lat is not None:
                                parts.append(f"{lat:.0f}ms")
                            if tok is not None:
                                parts.append(f"tok:{tok}")
                        if parts:
                            suffix = "  (" + ", ".join(parts) + ")"
                    except Exception as e:
                        logger.debug(f"Error creating streaming suffix: {e}")

                    item.setText(
                        f"[{updated_request.request.timestamp.strftime('%H:%M:%S')}] "
                        f"{updated_request.request.method} {path} - {model_name}{suffix}"
                    )
                    item.setData(Qt.ItemDataRole.UserRole, updated_request)
                break

    def _flush_pending(self):
        if not self._pending:
            return
        import time

        start = time.perf_counter()
        pending = self._pending
        self._pending = []
        for request in pending:
            try:
                item = self._create_list_item(request)
                self.request_list.addItem(item)
            except Exception:
                logger.exception("Failed to append pending request to list")
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if elapsed_ms > 50:
            logger.info(
                f"Batched UI update: appended {len(pending)} items in {elapsed_ms:.1f} ms"
            )
        
        # Auto-select the latest request if auto-follow is enabled
        if self._auto_follow_enabled and pending:
            self._auto_select_latest_request()

    def _on_request_clicked(self, item: QListWidgetItem):
        """Handle manual clicks on request items."""
        if item and self._auto_follow_enabled:
            # User manually clicked, disable auto-follow
            self._user_manually_selected = True
            self.set_auto_follow_enabled(False)
            logger.info("Auto-follow disabled due to manual click")
    
    def _on_current_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle when the current item changes (both manual and automatic)."""
        if current:
            request = current.data(Qt.ItemDataRole.UserRole)
            if request:
                parsed_url = urlparse(request.request.url)
                path = parsed_url.path if parsed_url.path else "/"

                model_name = "unknown"
                try:
                    if request.request.body:
                        body_data = json.loads(request.request.body)
                        model_name = body_data.get("model", "unknown")
                except (json.JSONDecodeError, AttributeError):
                    pass

                logger.info(
                    f"Request selected from list: {request.request.method} {path} - {model_name}"
                )
                self.request_selected.emit(request)
    
    def set_auto_follow_enabled(self, enabled: bool):
        """Enable or disable auto-follow for new requests."""
        if self._auto_follow_enabled != enabled:
            self._auto_follow_enabled = enabled
            self.auto_follow_changed.emit(enabled)
            logger.info(f"Auto-follow {'enabled' if enabled else 'disabled'}")
            
            # Reset manual selection flag when re-enabling auto-follow
            if enabled:
                self._user_manually_selected = False
    
    def is_auto_follow_enabled(self) -> bool:
        """Check if auto-follow is currently enabled."""
        return self._auto_follow_enabled
    
    def _auto_select_latest_request(self):
        """Automatically select the latest request in the list."""
        if self.request_list.count() > 0:
            # Get the last item (most recent request)
            last_item = self.request_list.item(self.request_list.count() - 1)
            if last_item:
                # Mark this as an automatic selection to avoid disabling auto-follow
                self._user_manually_selected = False
                
                # Select the item in the list
                self.request_list.setCurrentItem(last_item)
                
                # Directly emit the selection signal and update details
                request = last_item.data(Qt.ItemDataRole.UserRole)
                if request:
                    logger.debug(f"Auto-selected latest request: {request.request.method} {request.request.url}")
                    self.request_selected.emit(request)
