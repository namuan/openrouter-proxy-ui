import json
import logging
import os
import platform
from pathlib import Path
from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QSpinBox,
    QLineEdit,
)

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get the platform-appropriate configuration directory."""
    system = platform.system()

    if system == "Windows":
        # Windows: %APPDATA%\OpenRouterProxy
        config_dir = (
                Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                / "OpenRouterProxy"
        )
    elif system == "Darwin":
        # macOS: ~/Library/Application Support/OpenRouterProxy
        config_dir = Path.home() / "Library" / "Application Support" / "OpenRouterProxy"
    else:
        # Linux/Unix: ~/.config/openrouter-proxy
        config_dir = (
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
                / "openrouter-proxy"
        )

    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    """Get the full path to the configuration file."""
    return get_config_dir() / "proxy_config.json"


class ConfigWidget(QWidget):
    """Widget for configuring API keys and models."""

    config_changed = pyqtSignal()  # Emitted when configuration changes
    config_saved = pyqtSignal()  # Emitted when configuration is saved

    def __init__(self):
        super().__init__()
        self.api_keys = []
        self.api_models = []
        self.port = 8080
        self._setup_ui()

    def _setup_ui(self):
        """Set up the configuration UI."""
        logger.debug("Setting up ConfigWidget UI")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # API Keys section
        api_keys_group = QGroupBox("OpenRouter API Keys (One per line)")
        api_keys_layout = QVBoxLayout(api_keys_group)
        api_keys_layout.setSpacing(8)

        self.api_keys_text = QTextEdit()
        self.api_keys_text.setPlaceholderText("sk-or-v1-...\nsk-or-v1-...")
        self.api_keys_text.setMaximumHeight(100)
        self.api_keys_text.textChanged.connect(self._on_config_changed)
        api_keys_layout.addWidget(self.api_keys_text)

        layout.addWidget(api_keys_group)

        # API Models section
        api_models_group = QGroupBox("OpenRouter API Models (One per line)")
        api_models_layout = QVBoxLayout(api_models_group)
        api_models_layout.setSpacing(8)

        self.api_models_text = QTextEdit()
        self.api_models_text.setPlaceholderText(
            "qwen/qwen3-coder:free\nopenai/gpt-oss-20b:free\nanthropic/claude-3-haiku:beta"
        )
        self.api_models_text.setMaximumHeight(100)
        self.api_models_text.textChanged.connect(self._on_config_changed)
        api_models_layout.addWidget(self.api_models_text)

        layout.addWidget(api_models_group)

        # Port section
        port_group = QGroupBox("Proxy Server Port")
        port_layout = QHBoxLayout(port_group)
        port_layout.setSpacing(8)

        port_label = QLabel("Port:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.port)
        self.port_spin.valueChanged.connect(self._on_config_changed)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_spin)

        layout.addWidget(port_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

        # Load existing configuration
        self._load_config()

        logger.debug("ConfigWidget UI setup complete")

    def _on_config_changed(self):
        """Handle configuration changes."""
        self._parse_config()
        self.config_changed.emit()

    def _parse_config(self):
        """Parse configuration from UI elements."""
        # Parse API keys - handle masked keys
        api_keys_text = self.api_keys_text.toPlainText().strip()
        input_keys = [key.strip() for key in api_keys_text.split("\n") if key.strip()]

        # Process each input key
        parsed_keys = []
        for i, input_key in enumerate(input_keys):
            # If the input key contains asterisks, check if it matches a masked version of an existing key
            if "*" in input_key and i < len(self.api_keys):
                original_key = self.api_keys[i]
                if input_key == self._mask_api_key(original_key):
                    # User didn't change this key, keep the original
                    parsed_keys.append(original_key)
                else:
                    # User modified the masked key, treat as new key
                    parsed_keys.append(input_key)
            else:
                # New key or key without masking
                parsed_keys.append(input_key)

        self.api_keys = parsed_keys

        # Parse API models
        api_models_text = self.api_models_text.toPlainText().strip()
        self.api_models = [
            model.strip() for model in api_models_text.split("\n") if model.strip()
        ]

        # Parse port
        self.port = int(self.port_spin.value())

    def _save_config(self):
        """Save configuration to file."""
        try:
            config_data = {
                "api_keys": self.api_keys,
                "api_models": self.api_models,
                "auth_tokens": list(self.auth_tokens),
                "port": int(self.port),
            }

            config_file = get_config_file_path()
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Configuration has been saved to:\n{config_file}",
            )
            logger.info(f"Configuration saved to {config_file}")

            # Emit saved signal so the app can react (e.g., restart server)
            try:
                self.config_saved.emit()
            except Exception:
                logger.exception("Failed to emit config_saved signal")

        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save configuration: {e}"
            )
            logger.error(f"Failed to save configuration: {e}")

    def _load_config(self):
        """Load configuration from file."""
        try:
            config_file = get_config_file_path()
            with open(config_file, "r") as f:
                config_data = json.load(f)

            self.api_keys = config_data.get("api_keys", [])
            # Ensure we have default models if none are saved
            saved_models = config_data.get("api_models", [])
            logger.debug(
                f"Raw saved_models from config: {saved_models}, type: {type(saved_models)}"
            )
            if not saved_models:  # If empty list or None
                logger.debug("Using default models because saved_models is empty")
                self.api_models = ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
            else:
                logger.debug("Using saved models from config")
                self.api_models = saved_models
            self.auth_tokens = set(config_data.get("auth_tokens", []))
            self.port = int(config_data.get("port", 8080))

            self._update_ui()
            logger.info(f"Configuration loaded from {config_file}")
            logger.debug(
                f"Loaded {len(self.api_keys)} API keys, {len(self.api_models)} models, {len(self.auth_tokens)} auth tokens"
            )
            logger.debug(f"API models: {self.api_models}")
            logger.debug(f"Valid config check: {self.has_valid_config()}")

        except FileNotFoundError:
            # Use default configuration
            self.api_keys = []
            self.api_models = ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
            self.auth_tokens = set()
            self._update_ui()
            logger.info("No configuration file found, using defaults")
            logger.debug(
                f"Default config - {len(self.api_keys)} API keys, {len(self.api_models)} models"
            )
            logger.debug(f"Valid config check: {self.has_valid_config()}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Use default configuration
            self.api_keys = []
            self.api_models = ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
            self.auth_tokens = set()
            self._update_ui()

    # Environment variable loading method removed - configuration now comes from config widget only

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key showing only first 20 characters."""
        if len(api_key) <= 20:
            return api_key
        return api_key[:20] + "*" * (len(api_key) - 20)

    def _update_ui(self):
        """Update UI elements with current configuration."""
        # Temporarily disconnect signals to prevent _parse_config from being called
        self.api_keys_text.textChanged.disconnect()
        self.api_models_text.textChanged.disconnect()
        try:
            self.port_spin.blockSignals(True)
        except Exception:
            pass

        # Update the UI with current configuration - mask API keys for security
        masked_keys = [self._mask_api_key(key) for key in self.api_keys]
        self.api_keys_text.setPlainText("\n".join(masked_keys))
        self.api_models_text.setPlainText("\n".join(self.api_models))
        try:
            self.port_spin.setValue(int(self.port))
        finally:
            try:
                self.port_spin.blockSignals(False)
            except Exception:
                pass

        # Reconnect the signals
        self.api_keys_text.textChanged.connect(self._on_config_changed)
        self.api_models_text.textChanged.connect(self._on_config_changed)

    def get_api_keys(self) -> List[str]:
        """Get the configured API keys."""
        return self.api_keys.copy()

    def get_api_models(self) -> List[str]:
        """Get the configured API models."""
        return self.api_models.copy()

    def get_port(self) -> int:
        """Get the configured server port."""
        return int(self.port)

    def has_valid_config(self) -> bool:
        """Check if the configuration is valid."""
        return len(self.api_keys) > 0 and len(self.api_models) > 0
