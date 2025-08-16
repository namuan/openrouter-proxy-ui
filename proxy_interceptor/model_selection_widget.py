import logging

import httpx
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ModelSelectionWidget(QWidget):
    """Widget for selecting OpenRouter models with checkboxes."""

    models_selected = pyqtSignal(list)  # Emitted when models are selected

    def __init__(self):
        super().__init__()
        self.free_models = []
        self.selected_models = set()
        self.checkboxes = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the model selection UI."""
        logger.debug("Setting up ModelSelectionWidget UI")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Create a group box for the model list
        models_group = QGroupBox("Available Free OpenRouter Models")
        models_layout = QVBoxLayout(models_group)
        models_layout.setSpacing(8)

        # Create scroll area for models
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for checkboxes
        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.models_layout.setSpacing(5)

        scroll_area.setWidget(self.models_container)
        models_layout.addWidget(scroll_area)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Model List")
        self.refresh_btn.clicked.connect(self._refresh_models)
        models_layout.addWidget(self.refresh_btn)

        layout.addWidget(models_group)
        layout.addStretch()

        # Load initial model list
        self._refresh_models()

        logger.debug("ModelSelectionWidget UI setup complete")

    def _refresh_models(self):
        """Fetch and display the list of free models from OpenRouter."""
        logger.info("Refreshing OpenRouter model list")

        # Store currently selected models to preserve selection after refresh
        previously_selected = self.selected_models.copy()

        # Clear existing checkboxes
        for checkbox in self.checkboxes:
            self.models_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.checkboxes = []

        try:
            # Fetch models from OpenRouter API
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

            # Filter for free models
            # Free models typically have pricing.prompt = "0" and pricing.completion = "0"
            self.free_models = [
                model
                for model in data["data"]
                if "pricing" in model
                and float(model["pricing"].get("prompt", "0")) == 0
                and float(model["pricing"].get("completion", "0")) == 0
            ]

            logger.info(f"Free models found: {len(self.free_models)}")

            # Create checkboxes for each free model
            for model in self.free_models:
                model_id = model["id"]
                name = (
                    model["name"]
                    if "name" in model and model["name"] != model_id
                    else model_id
                )

                # Format context length
                context_length_k = (
                    f"{model['context_length'] / 1000:.0f}K"
                    if "context_length" in model
                    else "Unknown"
                )

                # Create checkbox with model info
                checkbox = QCheckBox(f"{name} - Context Length: {context_length_k}")
                checkbox.model_id = model_id
                checkbox.setChecked(model_id in previously_selected)
                checkbox.stateChanged.connect(self._on_model_selection_changed)

                self.models_layout.addWidget(checkbox)
                self.checkboxes.append(checkbox)

                # Add to selected models if it was previously selected
                if model_id in previously_selected:
                    self.selected_models.add(model_id)

            # Emit the updated selection
            self.models_selected.emit(list(self.selected_models))

        except Exception as e:
            logger.exception("Error fetching models")
            # Show error in UI
            error_label = QLabel(f"Error loading models: {e!s}")
            error_label.setStyleSheet("color: red;")
            self.models_layout.addWidget(error_label)
            self.checkboxes.append(error_label)

    def _on_model_selection_changed(self, state):
        """Handle model selection changes."""
        checkbox = self.sender()
        model_id = checkbox.model_id

        if state == Qt.CheckState.Checked.value:
            self.selected_models.add(model_id)
        else:
            self.selected_models.discard(model_id)

        logger.debug(
            f"Model selection changed. Selected models: {self.selected_models}"
        )
        self.models_selected.emit(list(self.selected_models))

    def get_selected_models(self) -> list[str]:
        """Get the list of currently selected models."""
        return list(self.selected_models)

    def set_selected_models(self, models: list[str]):
        """Set the selected models."""
        self.selected_models = set(models)

        # Update checkboxes
        for checkbox in self.checkboxes:
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(checkbox.model_id in self.selected_models)

        logger.debug(f"Set selected models: {self.selected_models}")
