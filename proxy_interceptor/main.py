import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("proxy_interceptor.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Proxy Interceptor application")

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("Proxy Interceptor")
        logger.info("Qt application initialized")

        window = MainWindow()
        window.show()
        logger.info("Main window shown")

        return app.exec()

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    sys.exit(main())
