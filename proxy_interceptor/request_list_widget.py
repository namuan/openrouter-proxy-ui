import json
import logging
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, pyqtSignal
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
        self.requests.append(request)
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

            item.setText(
                f"[{request.request.timestamp.strftime('%H:%M:%S')}] "
                f"{request.request.method} {path} - {model_name}"
            )
            item.setData(Qt.ItemDataRole.UserRole, request)
            self.request_list.addItem(item)
            logger.debug(
                f"Added request {i + 1} to list: {request.request.method} {path} - {model_name}"
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
