"""Entry point.

Named ``main.py`` on purpose: pyside6-android-deploy requires the app's
entry point to be named exactly this for the Android build.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("Thomas Vacation Finder")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
