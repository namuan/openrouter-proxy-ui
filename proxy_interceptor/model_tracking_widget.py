import logging
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from proxy_interceptor.layout_config import (
    INNER_SPACING,
    PANEL_MARGINS,
    PANEL_SPACING,
)
from proxy_interceptor.models import (
    InterceptedRequest,
    ModelProcessStatus,
)

logger = logging.getLogger(__name__)


class ModelStatusIndicator(QLabel):
    """Visual indicator for model status with color coding."""

    def __init__(self, status: ModelProcessStatus, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.setStyleSheet("border-radius: 6px;")
        self.update_status(status)

    def update_status(self, status: ModelProcessStatus):
        """Update the visual indicator based on status."""
        color_map = {
            ModelProcessStatus.SUCCESS: "#4CAF50",  # Green
            ModelProcessStatus.FAILED: "#F44336",  # Red
            ModelProcessStatus.RATE_LIMITED: "#FF9800",  # Orange
            ModelProcessStatus.TIMEOUT: "#FF5722",  # Deep Orange
            ModelProcessStatus.IN_PROGRESS: "#2196F3",  # Blue
            ModelProcessStatus.UNKNOWN: "#9E9E9E",  # Grey
        }

        color = color_map.get(status, "#9E9E9E")
        self.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        self.setToolTip(f"Status: {status.value.title()}")


class ModelTrackingWidget(QWidget):
    """Widget for tracking and displaying model usage, status, and history."""

    model_selected = pyqtSignal(str)  # Emitted when a model is selected for details
    models_reordered = pyqtSignal(list)  # Emitted when models are reordered
    model_removed = pyqtSignal(
        str
    )  # Emitted when a model is automatically removed due to failures

    def __init__(self, parent=None):
        super().__init__(parent)
        self.intercepted_requests: list[InterceptedRequest] = []
        self.current_model: str | None = None
        self.model_stats: dict[str, dict] = {}  # Model name -> stats dict
        self.selected_models: list[str] = []  # List of selected models

        self._setup_ui()
        self._setup_refresh_timer()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*PANEL_MARGINS)
        layout.setSpacing(PANEL_SPACING)

        # Create a horizontal layout for the two sections side by side
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setSpacing(PANEL_SPACING)

        # Selected Models Section with Active Model Display
        selected_models_group = QGroupBox()
        selected_models_layout = QVBoxLayout(selected_models_group)
        selected_models_layout.setSpacing(INNER_SPACING)

        # Header with title and active model display
        header_layout = QHBoxLayout()
        header_layout.setSpacing(INNER_SPACING)

        title_label = QLabel("Selected Models (Drag to Reorder)")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        # Active model display inline with title
        active_label = QLabel("Active:")
        self.current_model_indicator = ModelStatusIndicator(ModelProcessStatus.UNKNOWN)
        self.current_model_label = QLabel("No model active")
        self.current_model_label.setStyleSheet("font-weight: bold; color: #2196F3;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(active_label)
        header_layout.addWidget(self.current_model_indicator)
        header_layout.addWidget(self.current_model_label)

        # Add Remove button to delete selected model
        self.remove_model_btn = QPushButton("Remove Selected")
        self.remove_model_btn.setToolTip(
            "Remove the highlighted model from the selection"
        )
        self.remove_model_btn.clicked.connect(self._on_remove_selected_model)
        header_layout.addWidget(self.remove_model_btn)

        selected_models_layout.addLayout(header_layout)

        self.selected_models_list = QListWidget()
        self.selected_models_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.selected_models_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.selected_models_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        # Remove height restriction to allow expansion into the freed space

        # Connect signal to handle reordering
        self.selected_models_list.model().rowsMoved.connect(self._on_models_reordered)

        selected_models_layout.addWidget(self.selected_models_list)

        # Add selected models group to horizontal layout with stretch
        horizontal_layout.addWidget(selected_models_group, 1)

        # Model Statistics Section
        stats_group = QGroupBox("Model Statistics")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(INNER_SPACING)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels([
            "Model",
            "Success Rate",
            "Total Requests",
            "Avg Latency (ms)",
            "Last Used",
        ])

        # Configure stats table
        stats_header = self.stats_table.horizontalHeader()
        stats_header.setStretchLastSection(True)
        for i in range(4):
            stats_header.setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )

        self.stats_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSortingEnabled(True)

        stats_layout.addWidget(self.stats_table)

        # Add stats group to horizontal layout with stretch
        horizontal_layout.addWidget(stats_group, 1)

        # Add the horizontal layout to the main layout
        layout.addLayout(horizontal_layout, 1)

    def _setup_refresh_timer(self):
        """Set up timer for periodic UI updates."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_display)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds

    def update_requests(self, requests: list[InterceptedRequest]):
        """Update the widget with new intercepted requests."""
        self.intercepted_requests = requests
        self._update_model_stats()
        self._refresh_display()

    def set_current_model(self, model_name: str | None):
        """Set the currently active model."""
        self.current_model = model_name
        self._update_current_model_display()

    def set_selected_models(self, models: list[str]):
        """Set the list of selected models."""
        self.selected_models = models.copy()
        self._update_selected_models_display()

    def _update_selected_models_display(self):
        """Update the selected models list display."""
        self.selected_models_list.clear()

        for i, model_name in enumerate(self.selected_models):
            item = QListWidgetItem(f"{i + 1}. {model_name}")
            item.setData(Qt.ItemDataRole.UserRole, model_name)
            self.selected_models_list.addItem(item)

    def _on_models_reordered(self, parent, start, end, destination, row):
        """Handle when models are reordered via drag and drop."""
        try:
            # Get the new order from the list widget
            new_order = []
            for i in range(self.selected_models_list.count()):
                item = self.selected_models_list.item(i)
                if item:
                    model_name = item.data(Qt.ItemDataRole.UserRole)
                    if model_name:
                        new_order.append(model_name)

            # Update our internal list
            self.selected_models = new_order

            # Emit signal to notify parent widget
            self.models_reordered.emit(new_order)

            logger.info(f"Models reordered: {new_order}")

        except Exception:
            logger.exception("Error handling model reordering")

    def _on_remove_selected_model(self):
        """Remove the currently selected model from the list via UI action."""
        try:
            current_item = self.selected_models_list.currentItem()
            if not current_item:
                logger.info("Remove requested but no model is selected")
                return

            model_name = current_item.data(Qt.ItemDataRole.UserRole)
            if not model_name:
                logger.warning(
                    "Selected list item does not have a model name payload; aborting removal"
                )
                return

            # Remove from internal list if present
            if model_name in self.selected_models:
                self.selected_models.remove(model_name)
                logger.info(f"Removed model from selection via UI: {model_name}")
            else:
                logger.info(
                    f"Model {model_name} not found in internal selected list; still emitting removal"
                )

            # Update UI list
            row = self.selected_models_list.row(current_item)
            self.selected_models_list.takeItem(row)

            # Notify parent (ConfigWidget) to propagate changes and persist
            self.model_removed.emit(model_name)
        except Exception:
            logger.exception("Error while removing selected model")

    def _update_model_stats(self):
        """Calculate statistics for each model based on intercepted requests."""
        self.model_stats.clear()

        for request in self.intercepted_requests:
            for invocation in request.model_invocations:
                model_name = invocation.model_name

                if model_name not in self.model_stats:
                    self.model_stats[model_name] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "total_latency": 0.0,
                        "last_used": None,
                        "invocations": [],
                    }

                stats = self.model_stats[model_name]
                stats["total_requests"] += 1
                stats["invocations"].append(invocation)

                if invocation.is_successful():
                    stats["successful_requests"] += 1
                elif invocation.is_failed():
                    stats["failed_requests"] += 1

                if invocation.latency_ms:
                    stats["total_latency"] += invocation.latency_ms

                if not stats["last_used"] or invocation.timestamp > stats["last_used"]:
                    stats["last_used"] = invocation.timestamp

    def _update_current_model_display(self):
        """Update the current model display section."""
        if self.current_model:
            self.current_model_label.setText(f"Model: {self.current_model}")

            # Determine status based on recent usage
            recent_status = self._get_recent_model_status(self.current_model)
            self.current_model_indicator.update_status(recent_status)
        else:
            self.current_model_label.setText("No model active")
            self.current_model_indicator.update_status(ModelProcessStatus.UNKNOWN)

    def _get_recent_model_status(self, model_name: str) -> ModelProcessStatus:
        """Get the most recent status for a model."""
        recent_invocations = []
        cutoff_time = datetime.now() - timedelta(minutes=5)  # Last 5 minutes

        for request in self.intercepted_requests:
            for invocation in request.model_invocations:
                if (
                    invocation.model_name == model_name
                    and invocation.timestamp > cutoff_time
                ):
                    recent_invocations.append(invocation)

        if not recent_invocations:
            return ModelProcessStatus.UNKNOWN

        # Return the most recent status
        recent_invocations.sort(key=lambda x: x.timestamp, reverse=True)
        return recent_invocations[0].status

    def _refresh_display(self):
        """Refresh all display components."""
        # Note: Don't refresh selected models display here to preserve drag-and-drop reordering
        self._update_current_model_display()
        self._populate_stats_table()
        self._check_and_remove_failed_models()

    def _check_and_remove_failed_models(self):
        """Check for models with more than 5 failures and remove them from selected models."""
        models_to_remove = []

        for model_name in self.selected_models:
            if model_name in self.model_stats:
                stats = self.model_stats[model_name]
                if stats["failed_requests"] > 5:
                    models_to_remove.append(model_name)
                    logger.warning(
                        f"Removing model '{model_name}' due to {stats['failed_requests']} failures"
                    )

        # Remove failed models from selected list
        for model_name in models_to_remove:
            if model_name in self.selected_models:
                self.selected_models.remove(model_name)
                self.model_removed.emit(model_name)

        # Update display if any models were removed
        if models_to_remove:
            self._update_selected_models_display()

    def _populate_stats_table(self):
        """Populate the statistics table."""
        self.stats_table.setRowCount(len(self.model_stats))

        for row, (model_name, stats) in enumerate(self.model_stats.items()):
            # Model name
            self.stats_table.setItem(row, 0, QTableWidgetItem(model_name))

            # Success rate
            if stats["total_requests"] > 0:
                success_rate = (
                    stats["successful_requests"] / stats["total_requests"]
                ) * 100
                success_rate_str = f"{success_rate:.1f}%"

                success_item = QTableWidgetItem(success_rate_str)
                if success_rate >= 90:
                    success_item.setBackground(QColor(200, 255, 200))  # Light green
                elif success_rate >= 70:
                    success_item.setBackground(QColor(255, 255, 200))  # Light yellow
                else:
                    success_item.setBackground(QColor(255, 200, 200))  # Light red

                self.stats_table.setItem(row, 1, success_item)
            else:
                self.stats_table.setItem(row, 1, QTableWidgetItem("N/A"))

            # Total requests
            self.stats_table.setItem(
                row, 2, QTableWidgetItem(str(stats["total_requests"]))
            )

            # Average latency
            if stats["successful_requests"] > 0 and stats["total_latency"] > 0:
                avg_latency = stats["total_latency"] / stats["successful_requests"]
                avg_latency_str = f"{avg_latency:.1f}"
            else:
                avg_latency_str = "N/A"
            self.stats_table.setItem(row, 3, QTableWidgetItem(avg_latency_str))

            # Last used
            if stats["last_used"]:
                last_used_str = stats["last_used"].strftime("%H:%M:%S")
            else:
                last_used_str = "Never"
            self.stats_table.setItem(row, 4, QTableWidgetItem(last_used_str))

    def clear_history(self):
        """Clear all tracking history."""
        self.intercepted_requests.clear()
        self.model_stats.clear()
        self._refresh_display()
