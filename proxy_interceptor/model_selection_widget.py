import logging

import httpx
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ReorderableListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)


class ModelSelectionWidget(QWidget):
    models_selected = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.free_models = []
        self.selected_models_ordered = []
        self.checkboxes = []
        self.previous_model_ids = set()  # Track model IDs from previous refresh
        self.new_model_ids = set()  # Track newly added models
        self._setup_ui()

    def _setup_ui(self):
        logger.debug("Setting up ModelSelectionWidget UI")

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)

        left_layout = QVBoxLayout()

        available_group = QGroupBox("Available Free OpenRouter Models")
        available_layout = QVBoxLayout(available_group)
        available_layout.setSpacing(8)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.models_layout.setSpacing(5)

        scroll_area.setWidget(self.models_container)
        available_layout.addWidget(scroll_area)

        self.refresh_btn = QPushButton("Refresh Model List")
        self.refresh_btn.clicked.connect(self._refresh_models)
        available_layout.addWidget(self.refresh_btn)

        left_layout.addWidget(available_group)
        main_layout.addLayout(left_layout)

        # Hide the right column since we're moving selected models to ModelTrackingWidget
        # Keep the selected_models_list for internal functionality but don't display it
        self.selected_models_list = ReorderableListWidget()
        self.selected_models_list.itemChanged.connect(self._on_selected_list_changed)
        self.selected_models_list.model().rowsMoved.connect(self._on_models_reordered)
        self.selected_models_list.hide()  # Hide the widget

        self._refresh_models()

        logger.debug("ModelSelectionWidget UI setup complete")

    def _refresh_models(self):
        logger.info("Refreshing OpenRouter model list")

        previously_selected_set = set(self.selected_models_ordered)

        # Store current model IDs as previous before refresh
        current_model_ids = {model["id"] for model in self.free_models}
        if current_model_ids:
            self.previous_model_ids = current_model_ids

        for checkbox in self.checkboxes:
            self.models_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.checkboxes = []

        try:
            response = httpx.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            if "data" not in data or not isinstance(data["data"], list):
                raise ValueError("Unexpected API response format")

            logger.info(f"Total models found: {len(data['data'])}")

            self.free_models = [
                model
                for model in data["data"]
                if "pricing" in model
                and float(model["pricing"].get("prompt", "0")) == 0
                and float(model["pricing"].get("completion", "0")) == 0
            ]

            logger.info(f"Free models found: {len(self.free_models)}")

            # Identify new models by comparing with previous model IDs
            new_model_ids_after_refresh = {model["id"] for model in self.free_models}
            self.new_model_ids = new_model_ids_after_refresh - self.previous_model_ids

            if self.new_model_ids:
                logger.info(
                    f"New models detected: {len(self.new_model_ids)} - {list(self.new_model_ids)}"
                )

            self.free_models.sort(
                key=lambda m: (
                    m["id"] not in previously_selected_set,
                    m.get("name", m["id"]).lower(),
                )
            )

            for model in self.free_models:
                model_id = model["id"]
                name = (
                    model["name"]
                    if "name" in model and model["name"] != model_id
                    else model_id
                )

                context_length_k = (
                    f"{model['context_length'] / 1000:.0f}K"
                    if "context_length" in model
                    else "Unknown"
                )

                is_new_model = model_id in self.new_model_ids
                display_text = f"{name} - Context Length: {context_length_k}"

                checkbox = QCheckBox(display_text)
                checkbox.model_id = model_id
                checkbox.setChecked(model_id in previously_selected_set)
                checkbox.stateChanged.connect(self._on_model_selection_changed)

                # Apply subtle left border for new models
                if is_new_model:
                    checkbox.setStyleSheet(
                        "QCheckBox { border-left: 2px solid #90caf9; }"
                    )

                self.models_layout.addWidget(checkbox)
                self.checkboxes.append(checkbox)

            self._update_selected_models_list()
            self.models_selected.emit(self.selected_models_ordered.copy())

        except Exception as e:
            logger.exception("Error fetching models")
            error_label = QLabel(f"Error loading models: {e!s}")
            error_label.setObjectName("errorLabel")
            self.models_layout.addWidget(error_label)
            self.checkboxes.append(error_label)

    def _on_model_selection_changed(self, state):
        checkbox = self.sender()
        model_id = checkbox.model_id

        if state == Qt.CheckState.Checked.value:
            if model_id not in self.selected_models_ordered:
                self.selected_models_ordered.append(model_id)
        else:
            if model_id in self.selected_models_ordered:
                self.selected_models_ordered.remove(model_id)

        logger.debug(
            f"Model selection changed. Selected models: {self.selected_models_ordered}"
        )

        self._refresh_checkboxes_order()
        self._update_selected_models_list()
        self.models_selected.emit(self.selected_models_ordered.copy())

    def _refresh_checkboxes_order(self):
        self.checkboxes.sort(
            key=lambda cb: (
                not cb.isChecked() if isinstance(cb, QCheckBox) else True,
                cb.text().lower() if isinstance(cb, QCheckBox) else "",
            )
        )

        for i, checkbox in enumerate(self.checkboxes):
            self.models_layout.removeWidget(checkbox)
            self.models_layout.insertWidget(i, checkbox)

    def _update_selected_models_list(self):
        self.selected_models_list.clear()

        for model_id in self.selected_models_ordered:
            model_info = None
            for model in self.free_models:
                if model["id"] == model_id:
                    model_info = model
                    break

            if model_info:
                name = (
                    model_info["name"]
                    if "name" in model_info and model_info["name"] != model_id
                    else model_id
                )
                context_length_k = (
                    f"{model_info['context_length'] / 1000:.0f}K"
                    if "context_length" in model_info
                    else "Unknown"
                )
                display_text = f"{name} - Context Length: {context_length_k}"
            else:
                display_text = model_id

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, model_id)
            self.selected_models_list.addItem(item)

    def _on_selected_list_changed(self):
        pass

    def _on_models_reordered(self, parent, start, end, destination, row):
        new_order = []
        for i in range(self.selected_models_list.count()):
            item = self.selected_models_list.item(i)
            model_id = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(model_id)

        self.selected_models_ordered = new_order
        logger.debug(f"Models reordered: {self.selected_models_ordered}")
        self.models_selected.emit(self.selected_models_ordered.copy())

    def get_selected_models(self) -> list[str]:
        return self.selected_models_ordered.copy()

    def set_selected_models(self, models: list[str]):
        self.selected_models_ordered = models.copy()
        selected_set = set(models)

        for checkbox in self.checkboxes:
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(checkbox.model_id in selected_set)

        self._update_selected_models_list()
        logger.debug(f"Set selected models: {self.selected_models_ordered}")
