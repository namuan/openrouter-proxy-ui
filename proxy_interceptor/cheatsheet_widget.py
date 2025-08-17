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

from proxy_interceptor.config_widget import get_config_dir, get_config_file_path
from proxy_interceptor.layout_config import (
    BUTTON_SPACING,
    PANEL_MARGINS,
    PANEL_SPACING,
)

logger = logging.getLogger(__name__)


def get_cheatsheet_file_path() -> Path:
    return get_config_dir() / "cheatsheet.json"


class CheatsheetWidget(QWidget):
    status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
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
        layout = QVBoxLayout(self)
        layout.setSpacing(PANEL_SPACING)
        layout.setContentsMargins(*PANEL_MARGINS)

        title_label = QLabel("Client Settings Cheatsheet")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        desc_label = QLabel(
            "Edit the cheatsheet below with client configuration examples. "
            "Rich text formatting is supported."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlainText(self.default_text)
        layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(BUTTON_SPACING)

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
        try:
            content = self.text_edit.toPlainText()
            cheatsheet_data = {
                "content": content,
                "html_content": self.text_edit.toHtml(),
            }

            cheatsheet_file = get_cheatsheet_file_path()
            with open(cheatsheet_file, "w", encoding="utf-8") as f:
                json.dump(cheatsheet_data, f, indent=2, ensure_ascii=False)

            self.status.emit(f"Cheatsheet saved to: {cheatsheet_file}", "success")
            logger.info(f"Cheatsheet saved to {cheatsheet_file}")

        except Exception as e:
            self.status.emit(f"Failed to save cheatsheet: {e}", "error")
            logger.exception("Failed to save cheatsheet")

    def _load_cheatsheet(self):
        try:
            cheatsheet_file = get_cheatsheet_file_path()
            if not cheatsheet_file.exists():
                logger.debug("No cheatsheet file found, using default content")
                return

            with open(cheatsheet_file, encoding="utf-8") as f:
                cheatsheet_data = json.load(f)

            html_content = cheatsheet_data.get("html_content")
            if html_content:
                self.text_edit.setHtml(html_content)
            else:
                content = cheatsheet_data.get("content", self.default_text)
                self.text_edit.setPlainText(content)

            logger.info(f"Cheatsheet loaded from {cheatsheet_file}")

        except Exception:
            logger.exception("Failed to load cheatsheet")
            self.text_edit.setPlainText(self.default_text)

    def _reset_to_default(self):
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
        return self.text_edit.toPlainText()

    def get_html_content(self) -> str:
        return self.text_edit.toHtml()

    def update_port_and_save(self, old_port: int, new_port: int):
        try:
            current_plain = self.text_edit.toPlainText()
            current_html = self.text_edit.toHtml()

            default_old = self._generate_default_text(old_port)
            is_default_like = (
                current_plain.strip()
                == getattr(self, "default_text", default_old).strip()
                or current_plain.strip() == default_old.strip()
            )

            if is_default_like:
                self.default_text = self._generate_default_text(new_port)
                self.text_edit.setPlainText(self.default_text)
            else:
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

            self._save_cheatsheet()
        except Exception:
            logger.exception("Failed to update cheatsheet content for new port")
