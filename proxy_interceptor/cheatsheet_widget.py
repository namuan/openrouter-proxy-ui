from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
import json
import logging
from pathlib import Path
from .config_widget import get_config_dir

logger = logging.getLogger(__name__)


def get_cheatsheet_file_path() -> Path:
    """Get the full path to the cheatsheet file."""
    return get_config_dir() / "cheatsheet.json"


class CheatsheetWidget(QWidget):
    """Widget for managing client settings cheatsheet."""

    def __init__(self):
        super().__init__()
        self.default_text = """Aider

$ aider --openai-api-base http://localhost:8080/v1 --model openai/custom

RooCode

Settings → API Provider (OpenRouter) → API Key (Anything) → Custom Base URL (http://127.0.0.1:8080/v1) → Model (Any)"""
        
        self._setup_ui()
        self._load_cheatsheet()
        logger.debug("CheatsheetWidget initialized")

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
                "html_content": self.text_edit.toHtml()  # Save rich text formatting
            }

            cheatsheet_file = get_cheatsheet_file_path()
            with open(cheatsheet_file, "w", encoding="utf-8") as f:
                json.dump(cheatsheet_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self,
                "Cheatsheet Saved",
                f"Cheatsheet has been saved to:\n{cheatsheet_file}",
            )
            logger.info(f"Cheatsheet saved to {cheatsheet_file}")

        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save cheatsheet: {e}"
            )
            logger.error(f"Failed to save cheatsheet: {e}")

    def _load_cheatsheet(self):
        """Load cheatsheet content from file."""
        try:
            cheatsheet_file = get_cheatsheet_file_path()
            if not cheatsheet_file.exists():
                logger.debug("No cheatsheet file found, using default content")
                return

            with open(cheatsheet_file, "r", encoding="utf-8") as f:
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
            logger.error(f"Failed to load cheatsheet: {e}")
            # On error, use default content
            self.text_edit.setPlainText(self.default_text)

    def _reset_to_default(self):
        """Reset cheatsheet to default content."""
        reply = QMessageBox.question(
            self,
            "Reset Cheatsheet",
            "Are you sure you want to reset the cheatsheet to default content? This will lose any custom changes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.text_edit.setPlainText(self.default_text)
            logger.info("Cheatsheet reset to default content")

    def get_content(self) -> str:
        """Get the current cheatsheet content as plain text."""
        return self.text_edit.toPlainText()

    def get_html_content(self) -> str:
        """Get the current cheatsheet content as HTML."""
        return self.text_edit.toHtml()