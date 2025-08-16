import contextlib
import json
import logging
import os
import platform
import socket
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from proxy_interceptor.model_selection_widget import ModelSelectionWidget

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    system = platform.system()

    if system == "Windows":
        config_dir = (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / "OpenRouterProxy"
        )
    elif system == "Darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "OpenRouterProxy"
    else:
        config_dir = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            / "openrouter-proxy"
        )

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    return get_config_dir() / "proxy_config.json"


class AppConfig(BaseModel):
    api_keys: list[str] = Field(default_factory=list)
    api_models: list[str] = Field(default_factory=list)
    auth_tokens: set[str] = Field(default_factory=set)
    port: int = 8080

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v: list[str]):
        if not v:
            raise ValueError("At least one API key is required")
        invalid = [k for k in v if not (k and k.startswith("sk-or-"))]
        if invalid:
            raise ValueError("Invalid API key format detected")
        return v

    @field_validator("api_models")
    @classmethod
    def validate_models(cls, v: list[str]):
        if not v:
            raise ValueError("At least one API model is required")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int):
        if not (1 <= int(v) <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return int(v)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, int(port)))
        return True
    except OSError:
        return False


class ConfigWidget(QWidget):
    config_changed = pyqtSignal()
    config_saved = pyqtSignal()
    status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.api_keys = []
        self.api_models = []
        self.port = 8080
        self._saved_port: int | None = None
        self._setup_ui()

    def _setup_ui(self):
        logger.debug("Setting up ConfigWidget UI")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)

        api_keys_group = QGroupBox("OpenRouter API Keys (One per line)")
        api_keys_layout = QVBoxLayout(api_keys_group)
        api_keys_layout.setSpacing(8)

        self.api_keys_text = QTextEdit()
        self.api_keys_text.setPlaceholderText("sk-or-v1-...\nsk-or-v1-...")
        self.api_keys_text.setMaximumHeight(100)
        self.api_keys_text.textChanged.connect(self._on_config_changed)
        api_keys_layout.addWidget(self.api_keys_text)

        layout.addWidget(api_keys_group)

        self.model_selection_widget = ModelSelectionWidget()
        self.model_selection_widget.models_selected.connect(self._on_models_selected)
        layout.addWidget(self.model_selection_widget)

        port_group = QGroupBox("Proxy Server Port")
        port_layout = QHBoxLayout(port_group)
        port_layout.setSpacing(8)

        port_label = QLabel("Port:")
        self.port_input = QLineEdit()
        self.port_input.setValidator(QIntValidator(1, 65535))
        self.port_input.setText(str(self.port))
        self.port_input.textChanged.connect(self._on_config_changed)
        self.port_input.setMaximumWidth(100)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()

        layout.addWidget(port_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

        self._load_config()

        logger.debug("ConfigWidget UI setup complete")

    def _on_config_changed(self):
        self._parse_config()
        self.config_changed.emit()

    def _on_models_selected(self, models):
        self.api_models = models
        self.config_changed.emit()

    def _parse_config(self):
        api_keys_text = self.api_keys_text.toPlainText().strip()
        input_keys = [key.strip() for key in api_keys_text.split("\n") if key.strip()]

        parsed_keys = []
        for i, input_key in enumerate(input_keys):
            if "*" in input_key and i < len(self.api_keys):
                original_key = self.api_keys[i]
                if input_key == self._mask_api_key(original_key):
                    parsed_keys.append(original_key)
                else:
                    parsed_keys.append(input_key)
            else:
                parsed_keys.append(input_key)

        self.api_keys = parsed_keys

        port_text = self.port_input.text()
        if port_text:
            self.port = int(port_text)
        else:
            self.port = 8080

    def _save_config(self):
        try:
            # Parse latest values from UI
            self._parse_config()

            # Validate with AppConfig model
            try:
                cfg = AppConfig(
                    api_keys=self.api_keys,
                    api_models=self.api_models,
                    auth_tokens=set(self.auth_tokens),
                    port=int(self.port),
                )
            except ValidationError as ve:
                self.status.emit(
                    "Invalid configuration: " + str(ve.errors()[0]["msg"]), "error"
                )
                logger.warning(f"Config validation failed: {ve}")
                return
            except ValueError as ve:
                self.status.emit(f"Invalid configuration: {ve}", "error")
                logger.warning(f"Config validation failed: {ve}")
                return

            # Port availability check - only if port has changed
            if (
                self._saved_port is None or cfg.port != self._saved_port
            ) and not is_port_available(cfg.port):
                self.status.emit(
                    f"Port {cfg.port} is not available. Choose another port.", "error"
                )
                logger.error(f"Port {cfg.port} unavailable during save")
                return

            config_data = cfg.model_dump(mode="json")
            # Pydantic serializes set to list in JSON mode

            config_file = get_config_file_path()
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            # Update saved port after successful save
            self._saved_port = cfg.port

            self.status.emit(f"Configuration saved to: {config_file}", "success")
            logger.info(f"Configuration saved to {config_file}")

            try:
                self.config_saved.emit()
            except Exception:
                logger.exception("Failed to emit config_saved signal")

        except Exception as e:
            self.status.emit(f"Failed to save configuration: {e}", "error")
            logger.exception("Failed to save configuration")

    def _load_config(self):
        try:
            config_file = get_config_file_path()
            with open(config_file) as f:
                loaded = json.load(f)

            # Validate loaded config; if invalid, fall back to defaults but keep UI usable
            try:
                cfg = AppConfig(**loaded)
                self.api_keys = cfg.api_keys
                self.api_models = cfg.api_models
                self.auth_tokens = set(cfg.auth_tokens)
                self.port = int(cfg.port)
                self._saved_port = self.port  # Track the saved port value
            except Exception as ve:
                logger.warning(f"Invalid config file, using safe defaults: {ve}")
                self.api_keys = loaded.get("api_keys", [])
                saved_models = loaded.get("api_models", [])
                if not saved_models:
                    self.api_models = [
                        "qwen/qwen3-coder:free",
                        "openai/gpt-oss-20b:free",
                    ]
                else:
                    self.api_models = saved_models
                self.auth_tokens = set(loaded.get("auth_tokens", []))
                self.port = int(loaded.get("port", 8080))
                self._saved_port = self.port  # Track the saved port value

            self._update_ui()
            logger.info(f"Configuration loaded from {config_file}")
            logger.debug(
                f"Loaded {len(self.api_keys)} API keys, {len(self.api_models)} models, {len(self.auth_tokens)} auth tokens"
            )
            logger.debug(f"API models: {self.api_models}")
            logger.debug(f"Valid config check: {self.has_valid_config()}")

        except FileNotFoundError:
            self.api_keys = []
            self.api_models = ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
            self.auth_tokens = set()
            self._update_ui()
            logger.info("No configuration file found, using defaults")
            logger.debug(
                f"Default config - {len(self.api_keys)} API keys, {len(self.api_models)} models"
            )
            logger.debug(f"Valid config check: {self.has_valid_config()}")

        except Exception:
            logger.exception("Failed to load configuration")
            self.api_keys = []
            self.api_models = ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
            self.auth_tokens = set()
            self._update_ui()

    def _mask_api_key(self, api_key: str) -> str:
        if len(api_key) <= 20:
            return api_key
        return api_key[:20] + "*" * (len(api_key) - 20)

    def _update_ui(self):
        self.api_keys_text.textChanged.disconnect()
        with contextlib.suppress(Exception):
            self.port_input.textChanged.disconnect()

        masked_keys = [self._mask_api_key(key) for key in self.api_keys]
        self.api_keys_text.setPlainText("\n".join(masked_keys))

        self.model_selection_widget.set_selected_models(self.api_models)

        try:
            self.port_input.setText(str(int(self.port)))
        finally:
            self.api_keys_text.textChanged.connect(self._on_config_changed)
            self.port_input.textChanged.connect(self._on_config_changed)

    def get_api_keys(self) -> list[str]:
        return self.api_keys.copy()

    def get_api_models(self) -> list[str]:
        return self.api_models.copy()

    def get_port(self) -> int:
        return int(self.port)

    def has_valid_config(self) -> bool:
        return len(self.api_keys) > 0 and len(self.api_models) > 0
