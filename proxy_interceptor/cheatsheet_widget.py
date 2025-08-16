import json
import logging
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config_widget import get_config_dir, get_config_file_path

logger = logging.getLogger(__name__)


def get_cheatsheet_file_path() -> Path:
    """Get the full path to the cheatsheet file."""
    return get_config_dir() / "cheatsheet.json"


class CheatsheetWidget(QWidget):
    """Widget for managing client settings cheatsheet."""

    status = pyqtSignal(str, str)  # message, level ('info'|'success'|'error')

    def __init__(self):
        super().__init__()
        # Load port from config (default to 8080)
        port = 8080
        try:
            cfg_file = get_config_file_path()
            if cfg_file.exists():
                with open(cfg_file) as f:
                    cfg = json.load(f)
                    port = int(cfg.get("port", 8080))
        except Exception:
            logger.exception("Failed to read port from config; using default 8080")

        self.default_text = self._generate_default_text(port)

        self._setup_ui()
        self._load_cheatsheet()
        logger.debug("CheatsheetWidget initialized")

    def _generate_default_text(self, port: int) -> str:
        return (
            f"Aider\n\n"
            f"$ aider --openai-api-base http://localhost:{port}/v1 --model openai/custom\n\n"
            f"RooCode\n\n"
            f"Settings → API Provider (OpenRouter) → API Key (Anything) → Custom Base URL (http://127.0.0.1:{port}/v1) → Model (Any)"
        )

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Client Settings Cheatsheet")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Edit the cheatsheet below with client configuration examples. "
            "Rich text formatting is supported."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Rich text editor
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlainText(self.default_text)

        # Set a monospace font for better code display
        font = QFont("Monaco", 11)  # Monaco is available on macOS
        if not font.exactMatch():
            font = QFont("Courier New", 11)  # Fallback
        self.text_edit.setFont(font)

        layout.addWidget(self.text_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("Save Cheatsheet")
        self.save_btn.clicked.connect(self._save_cheatsheet)
        button_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        logger.debug("CheatsheetWidget UI setup complete")

    def _save_cheatsheet(self):
        """Save cheatsheet content to file."""
        try:
            content = self.text_edit.toPlainText()
            cheatsheet_data = {
                "content": content,
                "html_content": self.text_edit.toHtml(),  # Save rich text formatting
            }

            cheatsheet_file = get_cheatsheet_file_path()
            with open(cheatsheet_file, "w", encoding="utf-8") as f:
                json.dump(cheatsheet_data, f, indent=2, ensure_ascii=False)

            # Notify via status signal instead of dialog
            self.status.emit(f"Cheatsheet saved to: {cheatsheet_file}", "success")
            logger.info(f"Cheatsheet saved to {cheatsheet_file}")

        except Exception as e:
            # Notify error via status signal instead of dialog
            self.status.emit(f"Failed to save cheatsheet: {e}", "error")
            logger.exception(f"Failed to save cheatsheet: {e}")

    def _load_cheatsheet(self):
        """Load cheatsheet content from file."""
        try:
            cheatsheet_file = get_cheatsheet_file_path()
            if not cheatsheet_file.exists():
                logger.debug("No cheatsheet file found, using default content")
                return

            with open(cheatsheet_file, encoding="utf-8") as f:
                cheatsheet_data = json.load(f)

            # Try to load HTML content first (rich text), fallback to plain text
            html_content = cheatsheet_data.get("html_content")
            if html_content:
                self.text_edit.setHtml(html_content)
            else:
                content = cheatsheet_data.get("content", self.default_text)
                self.text_edit.setPlainText(content)

            logger.info(f"Cheatsheet loaded from {cheatsheet_file}")

        except Exception as e:
            logger.exception(f"Failed to load cheatsheet: {e}")
            # On error, use default content
            self.text_edit.setPlainText(self.default_text)

    def _reset_to_default(self):
        """Reset cheatsheet to default content."""
        reply = QMessageBox.question(
            self,
            "Reset Cheatsheet",
            "Are you sure you want to reset the cheatsheet to default content? This will lose any custom changes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.text_edit.setPlainText(self.default_text)
            self.status.emit("Cheatsheet reset to default content", "info")
            logger.info("Cheatsheet reset to default content")

    def get_content(self) -> str:
        """Get the current cheatsheet content as plain text."""
        return self.text_edit.toPlainText()

    def get_html_content(self) -> str:
        """Get the current cheatsheet content as HTML."""
        return self.text_edit.toHtml()

    def update_port_and_save(self, old_port: int, new_port: int):
        """Update cheatsheet for port change without losing custom content.
        - If content equals the default template (for the old port), regenerate with new port.
        - Otherwise, attempt in-place replacement of the port in common URLs (localhost/127.0.0.1), preserving user edits.
        Always saves the cheatsheet after update.
        """
        try:
            # Current contents
            current_plain = self.text_edit.toPlainText()
            current_html = self.text_edit.toHtml()

            # Detect if current content is still the default (for either stored default_text or default generated with old_port)
            default_old = self._generate_default_text(old_port)
            is_default_like = (
                current_plain.strip()
                == getattr(self, "default_text", default_old).strip()
                or current_plain.strip() == default_old.strip()
            )

            if is_default_like:
                # Simply regenerate the default template for the new port
                self.default_text = self._generate_default_text(new_port)
                self.text_edit.setPlainText(self.default_text)
            else:
                # Preserve user content: replace occurrences of old_port with new_port in typical proxy URLs
                # Operate on HTML to preserve formatting
                import re

                def replace_ports(s: str) -> str:
                    patterns = [
                        rf"(http://localhost:){old_port}(\b)",
                        rf"(http://127\.0\.0\.1:){old_port}(\b)",
                    ]
                    for pat in patterns:
                        s = re.sub(pat, rf"\g<1>{new_port}\2", s)
                    return s

                updated_html = replace_ports(current_html)
                self.text_edit.setHtml(updated_html)

            # Save updated cheatsheet
            self._save_cheatsheet()
        except Exception:
            logger.exception("Failed to update cheatsheet content for new port")
