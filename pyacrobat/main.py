"""
PyAcrobat Application Entrypoint
"""

import sys
import os

# Ensure package root is on sys.path for direct script execution and PyInstaller bundling
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pyacrobat.ui.main_window import MainWindow
from pyacrobat.ui.styles import get_app_icon


def apply_windows_taskbar_icon(hwnd: int):
    """Binds high-resolution Spectra icon directly to Windows HWND via Win32 API."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from pyacrobat.core.resources import get_icon_path
        ico_path = get_icon_path("spectra_icon.ico")
        if not os.path.exists(ico_path):
            return

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010

        user32 = ctypes.windll.user32
        h_big = user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_small = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
    except Exception:
        pass


def main():
    # On Windows, assign explicit AppUserModelID ONLY when running as non-frozen script.
    # When running as a compiled standalone executable (SpectraPDF.exe), setting an explicit
    # unregistered AppUserModelID causes Windows Taskbar to disassociate from the EXE's embedded
    # icon and show a generic fallback blank window icon!
    if sys.platform == "win32" and not getattr(sys, "frozen", False):
        try:
            import ctypes
            myappid = "spectra.pdf.workstation.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Spectra PDF")
    app.setOrganizationName("Spectra")
    app.setWindowIcon(get_app_icon())

    window = MainWindow()
    window.show()

    # Explicitly set native Win32 window and taskbar icons
    if sys.platform == "win32":
        apply_windows_taskbar_icon(int(window.winId()))

    # If an argument is provided (e.g. sample PDF path), open it
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        window.open_document(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
