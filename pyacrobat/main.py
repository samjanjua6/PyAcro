"""
PyAcrobat Application Entrypoint
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pyacrobat.ui.main_window import MainWindow


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PyAcrobat")
    app.setOrganizationName("PyAcrobat Project")

    window = MainWindow()
    window.show()

    # If an argument is provided (e.g. sample PDF path), open it
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        window.open_document(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
