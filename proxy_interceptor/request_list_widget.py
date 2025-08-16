import json
import logging
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .models import InterceptedRequest

logger = logging.getLogger(__name__)


class RequestListWidget(QWidget):
    request_selected = pyqtSignal(InterceptedRequest)

    def __init__(self):
        super().__init__()
        self.requests: list[InterceptedRequest] = []
        logger.debug("RequestListWidget initialized")
        self._setup_ui()
        # Batching for UI updates to avoid signal storms
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
        self.request_list.itemClicked.connect(self._on_request_selected)
        layout.addWidget(self.request_list)
        logger.debug("RequestListWidget UI setup complete")

    def set_requests(self, requests: list[InterceptedRequest]):
        logger.info(f"Setting {len(requests)} requests in list widget")
        self.requests = requests
        self._update_list()

    def add_request(self, request: InterceptedRequest):
        # Append to in-memory store
        self.requests.append(request)
        # Stage for batched UI addition
        self._pending.append(request)
        # Start or extend the flush timer (coalesce bursts)
        try:
            if self._flush_timer.isActive():
                self._flush_timer.stop()
            self._flush_timer.start(100)  # flush within 100ms window
        except Exception:
            # On failure, fall back to immediate add
            self._flush_pending()

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

    def _flush_pending(self):
        if not self._pending:
            return
        # Simple profiling of batch size and duration
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

    def _on_request_selected(self, item: QListWidgetItem):
        request = item.data(Qt.ItemDataRole.UserRole)
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
