"""
PyAcrobat Application Entrypoint
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pyacrobat.ui.main_window import MainWindow
from pyacrobat.ui.styles import get_app_icon


def main():
    # On Windows, assign explicit AppUserModelID so Windows taskbar groups and shows the custom icon
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "adobe.pyacrobat.workstation.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Adobe Acrobat")
    app.setOrganizationName("Adobe")
    app.setWindowIcon(get_app_icon())

    window = MainWindow()
    window.show()

    # If an argument is provided (e.g. sample PDF path), open it
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        window.open_document(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
