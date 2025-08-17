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

/* Copy button base and success feedback */
QPushButton#copyUrlBtn {
    font-size: 14px;
    padding: 1px;
}
QPushButton#copyUrlBtn[success="true"] {
    font-size: 16px;
    font-weight: bold;
    padding: 2px;
    color: white;
    background-color: green;
    border-radius: 3px;
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

/* Auto-follow button styling */
QPushButton#autoFollowBtn {
    background-color: #0f9d58;
    min-width: 140px;
    font-weight: 600;
}

QPushButton#autoFollowBtn:hover {
    background-color: #0d8a4d;
}

QPushButton#autoFollowBtn[autoFollowEnabled="false"] {
    background-color: #ea4335;
}

QPushButton#autoFollowBtn[autoFollowEnabled="false"]:hover {
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
    border-radius: 2px;
    padding: 1px;
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

/* Input fields: shared base + focus for QLineEdit, QTextEdit, QPlainTextEdit */
QLineEdit, QTextEdit, QPlainTextEdit {
    border: none;
    border-radius: 4px;
    padding: 8px;
    background-color: #f8f9fa;
    selection-background-color: #4285f4;
    selection-color: white;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
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
}

/* Monospace proxy URL label with state colors */
QLabel#proxyUrlLabel {
    font-family: 'Monaco', 'Courier New', monospace;
}
QLabel#proxyUrlLabel:enabled { color: #333333; }
QLabel#proxyUrlLabel:disabled { color: #888888; }

/* Status label base and dynamic color by level property */
QLabel#statusLabel {
    padding: 0px;
    font-size: 12px;
    color: #6B7280; /* default (info) */
}
QLabel#statusLabel[level="error"] { color: #EF4444; }
QLabel#statusLabel[level="success"] { color: #10B981; }

/* Error label variant */
QLabel#errorLabel { color: red; }

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

/* Splitter handle visibility */
QSplitter::handle {
    background-color: #cccccc; /* visible by default */
}

QSplitter::handle:hover {
    background-color: #bfbfbf;
}

/* Request/Response panels */
QWidget#requestPanel, QWidget#responsePanel {
    background-color: white;
    border-radius: 8px;
    padding: 10px;
}
"""
