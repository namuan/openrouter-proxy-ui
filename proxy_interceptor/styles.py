"""Modern stylesheet for the Proxy Interceptor application."""

STYLESHEET = """
/* Main window styling */
QMainWindow {
    background-color: #f0f2f5;
}

/* Status indicator styling */
StatusIndicator {
    background-color: transparent;
}

/* Buttons */
QPushButton {
    background-color: #4285f4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #3367d6;
}

QPushButton:pressed {
    background-color: #2a56c6;
}

QPushButton#toggleProxyBtn {
    background-color: #0f9d58;
    min-width: 120px;
    font-weight: 600;
}

QPushButton#toggleProxyBtn:hover {
    background-color: #0d8a4d;
}

QPushButton#stopProxyBtn {
    background-color: #ea4335;
}

QPushButton#stopProxyBtn:hover {
    background-color: #d33b2e;
}

QPushButton:disabled {
    background-color: #dadce0;
    color: #9aa0a6;
}

/* Tab widget */
QTabWidget::pane {
    border: none;
    background-color: white;
    border-radius: 8px;
    padding: 10px;
}

QTabBar::tab {
    background-color: transparent;
    padding: 10px 20px;
    margin: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    color: #5f6368;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
}

QTabBar::tab:hover:!selected {
    background-color: #f1f3f4;
    border-radius: 4px;
}

/* Group boxes */
QGroupBox {
    font-weight: 600;
    border: none;
    border-radius: 8px;
    margin-top: 1ex;
    padding-top: 10px;
    background-color: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #202124;
}

/* Text edits */
QTextEdit {
    border: none;
    border-radius: 4px;
    padding: 8px;
    background-color: #f8f9fa;
    selection-background-color: #4285f4;
    selection-color: white;
}

QTextEdit:focus {
    background-color: white;
    border: 1px solid #4285f4;
    border-radius: 4px;
}

/* List widgets */
QListWidget {
    border: none;
    background-color: white;
    alternate-background-color: #f8f9fa;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f3f4;
}

QListWidget::item:selected {
    background-color: #4285f4;
    color: white;
}

QListWidget::item:hover:!selected {
    background-color: #f1f3f4;
}

/* Labels */
QLabel {
    color: #202124;
}

QLabel#header {
    font-size: 16px;
    font-weight: 600;
    color: #202124;
    margin-bottom: 10px;
}

/* Scroll bars */
QScrollBar:vertical {
    border: none;
    background-color: #f1f3f4;
    width: 12px;
    border-radius: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #c2c4c6;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9aa0a6;
}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
    height: 0px;
}

/* Splitter */
QSplitter::handle {
    background-color: transparent;
}

QSplitter::handle:hover {
    background-color: transparent;
}

/* Request/Response panels */
QWidget#requestPanel, QWidget#responsePanel {
    background-color: white;
    border-radius: 8px;
    padding: 10px;
}
"""
