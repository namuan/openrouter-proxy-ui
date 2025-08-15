import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from .main_window import MainWindow


def main():
    """Main entry point for the application."""
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Proxy Interceptor")
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
