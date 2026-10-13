"""
Export Progress and Success Dialogs for PyAcrobat (Phase 5).
Features:
- Adobe Spectrum-styled modal Progress Dialog with real-time percentage, status details, and cancel support.
- Post-Export Success Dialog with document card, file size info, 'Open File', 'Show in Folder', and 'Done' actions.
- Automatic theme adaptation (Light & Dark).
"""

import os
import subprocess
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager


def load_themed_svg(name: str, color_hex: str) -> Optional[QSvgRenderer]:
    icon_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "resources", "icons", f"{name}.svg"
    )
    if not os.path.exists(icon_path):
        return None
    try:
        with open(icon_path, "r", encoding="utf-8") as f:
            svg_data = f.read()
        svg_data = svg_data.replace('currentColor', color_hex)
        svg_data = svg_data.replace('stroke="#323232"', f'stroke="{color_hex}"')
        svg_data = svg_data.replace('stroke="black"', f'stroke="{color_hex}"')
        renderer = QSvgRenderer(svg_data.encode("utf-8"))
        return renderer if renderer.isValid() else None
    except Exception:
        return None


class ThemedSvgLabel(QLabel):
    """Clean label that paints a rendered SVG icon with crisp anti-aliasing."""

    def __init__(self, icon_name: str, color_hex: str, size: int = 24, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.color_hex = color_hex
        self.icon_size = size
        self.setFixedSize(size, size)
        self.renderer = load_themed_svg(icon_name, color_hex)

    def set_color(self, color_hex: str):
        self.color_hex = color_hex
        self.renderer = load_themed_svg(self.icon_name, color_hex)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height())
            self.renderer.render(painter, rect)
            painter.end()


class ExportProgressDialog(QDialog):
    """
    Modal Progress Dialog shown while document conversion is actively processing.
    Displays percentage, current page/sub-task status, and safe 'Cancel' action.
    """

    cancel_requested = Signal()

    def __init__(
        self,
        format_display: str,
        source_name: str,
        target_name: str,
        parent=None
    ):
        super().__init__(parent)
        self.format_display = format_display
        self.source_name = source_name
        self.target_name = target_name
        self.is_cancelling = False

        self.setWindowTitle(f"Converting to {format_display} — Adobe Acrobat")
        self.setFixedSize(450, 190)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Row: Icon + Title & Subtitle
        header_row = QWidget()
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(14)
        h_layout.setAlignment(Qt.AlignVCenter)

        self.icon_widget = ThemedSvgLabel("file-output", "#1473E6", size=28, parent=self)
        h_layout.addWidget(self.icon_widget)

        title_col = QWidget()
        t_layout = QVBoxLayout(title_col)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(3)

        self.lbl_title = QLabel(f"Exporting to {self.format_display}...")
        self.lbl_title.setFont(QFont("Inter", 12, QFont.Bold))
        t_layout.addWidget(self.lbl_title)

        self.lbl_files = QLabel(f"{self.source_name}  →  {self.target_name}")
        self.lbl_files.setFont(QFont("Inter", 9))
        t_layout.addWidget(self.lbl_files)

        h_layout.addWidget(title_col, 1)
        layout.addWidget(header_row)

        # Progress Bar & Percentage
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(5)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Status & Percentage Labels Row
        status_row = QWidget()
        sr_layout = QHBoxLayout(status_row)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setSpacing(8)

        self.lbl_status = QLabel("Initializing conversion engine...")
        self.lbl_status.setFont(QFont("Inter", 9))
        sr_layout.addWidget(self.lbl_status, 1)

        self.lbl_percent = QLabel("5%")
        self.lbl_percent.setFont(QFont("Inter", 9, QFont.DemiBold))
        sr_layout.addWidget(self.lbl_percent)

        layout.addWidget(status_row)

        layout.addStretch()

        # Action Buttons Row
        btn_row = QWidget()
        b_layout = QHBoxLayout(btn_row)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(10)
        b_layout.setAlignment(Qt.AlignRight)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(90, 32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        b_layout.addWidget(self.btn_cancel)

        layout.addWidget(btn_row)

    def set_progress(self, current: int, total: int, status_text: str):
        """Updates progress bar value, percentage, and current step description."""
        total = max(1, total)
        current = max(0, min(current, total))
        pct = int((current / total) * 100)
        pct = max(5, pct)  # Keep minimal visual cue

        self.progress_bar.setValue(pct)
        self.lbl_percent.setText(f"{pct}%")
        if status_text:
            self.lbl_status.setText(status_text)

    def _on_cancel_clicked(self):
        if not self.is_cancelling:
            self.is_cancelling = True
            self.lbl_status.setText("Cancelling export operation...")
            self.btn_cancel.setEnabled(False)
            self.cancel_requested.emit()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_col = "#252528" if is_dark else "#FFFFFF"
        text_primary = "#FFFFFF" if is_dark else "#242424"
        text_muted = "#9E9E9E" if is_dark else "#626262"
        bar_bg = "#3A3A3E" if is_dark else "#E5E5E5"
        accent_blue = "#2680EB" if is_dark else "#1473E6"
        btn_bg = "#323236" if is_dark else "#F0F0F0"
        btn_border = "#4A4A4F" if is_dark else "#D0D0D0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
            }}
            QProgressBar {{
                background-color: {bar_bg};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_blue};
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_primary};
                border: 1px solid {btn_border};
                border-radius: 4px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {'#3E3E43' if is_dark else '#E5E5E5'};
            }}
            QPushButton:disabled {{
                color: {text_muted};
                opacity: 0.6;
            }}
        """)

        self.lbl_title.setStyleSheet(f"color: {text_primary};")
        self.lbl_files.setStyleSheet(f"color: {text_muted};")
        self.lbl_status.setStyleSheet(f"color: {text_muted};")
        self.lbl_percent.setStyleSheet(f"color: {accent_blue};")
        self.icon_widget.set_color(accent_blue)


class ExportSuccessDialog(QDialog):
    """
    Modal Dialog presented upon successful export completion.
    Provides destination file metadata, 'Open File', 'Show in Folder', and 'Done' actions.
    """

    def __init__(self, target_file_path: str, format_display: str, parent=None):
        super().__init__(parent)
        self.target_file_path = os.path.normpath(target_file_path)
        self.format_display = format_display

        self.setWindowTitle("Export Complete — Adobe Acrobat")
        self.setFixedSize(480, 240)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        # Header Row: Success Icon + Title
        header_row = QWidget()
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(14)
        h_layout.setAlignment(Qt.AlignVCenter)

        self.icon_success = ThemedSvgLabel("file-check", "#12805C", size=30, parent=self)
        h_layout.addWidget(self.icon_success)

        title_col = QWidget()
        t_layout = QVBoxLayout(title_col)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(3)

        self.lbl_title = QLabel("Export Complete")
        self.lbl_title.setFont(QFont("Inter", 13, QFont.Bold))
        t_layout.addWidget(self.lbl_title)

        self.lbl_sub = QLabel(f"Your document was converted to {self.format_display} successfully.")
        self.lbl_sub.setFont(QFont("Inter", 9))
        t_layout.addWidget(self.lbl_sub)

        h_layout.addWidget(title_col, 1)
        layout.addWidget(header_row)

        # Target File Information Card
        self.file_card = QFrame()
        self.file_card.setObjectName("successFileCard")
        fc_layout = QHBoxLayout(self.file_card)
        fc_layout.setContentsMargins(14, 10, 14, 10)
        fc_layout.setSpacing(12)
        fc_layout.setAlignment(Qt.AlignVCenter)

        self.icon_doc = ThemedSvgLabel("file-text", "#1473E6", size=24, parent=self)
        fc_layout.addWidget(self.icon_doc)

        details_col = QWidget()
        d_layout = QVBoxLayout(details_col)
        d_layout.setContentsMargins(0, 0, 0, 0)
        d_layout.setSpacing(2)

        file_name = os.path.basename(self.target_file_path)
        self.lbl_filename = QLabel(file_name)
        self.lbl_filename.setFont(QFont("Inter", 10, QFont.DemiBold))
        d_layout.addWidget(self.lbl_filename)

        # Size and directory
        size_str = ""
        if os.path.exists(self.target_file_path):
            try:
                b = os.path.getsize(self.target_file_path)
                if b >= 1024 * 1024:
                    size_str = f"{b / (1024 * 1024):.1f} MB"
                elif b >= 1024:
                    size_str = f"{b / 1024:.0f} KB"
                else:
                    size_str = f"{b} B"
            except Exception:
                pass

        parent_dir = os.path.dirname(self.target_file_path)
        meta_str = f"{size_str} • {parent_dir}" if size_str else parent_dir
        self.lbl_filepath = QLabel(meta_str)
        self.lbl_filepath.setFont(QFont("Inter", 8))
        self.lbl_filepath.setToolTip(self.target_file_path)
        d_layout.addWidget(self.lbl_filepath)

        fc_layout.addWidget(details_col, 1)
        layout.addWidget(self.file_card)

        layout.addStretch()

        # Action Buttons Row: [Show in Folder] [Open File] [Done]
        btn_row = QWidget()
        b_layout = QHBoxLayout(btn_row)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(10)
        b_layout.setAlignment(Qt.AlignRight)

        self.btn_folder = QPushButton("Show in Folder")
        self.btn_folder.setFixedHeight(34)
        self.btn_folder.setCursor(Qt.PointingHandCursor)
        self.btn_folder.clicked.connect(self._on_show_in_folder)
        b_layout.addWidget(self.btn_folder)

        self.btn_open = QPushButton("Open File")
        self.btn_open.setFixedHeight(34)
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._on_open_file)
        b_layout.addWidget(self.btn_open)

        self.btn_done = QPushButton("Done")
        self.btn_done.setFixedHeight(34)
        self.btn_done.setCursor(Qt.PointingHandCursor)
        self.btn_done.clicked.connect(self.accept)
        b_layout.addWidget(self.btn_done)

        layout.addWidget(btn_row)

    def _on_open_file(self):
        try:
            os.startfile(self.target_file_path)
        except Exception as e:
            print(f"Error opening exported file: {e}")
        self.accept()

    def _on_show_in_folder(self):
        try:
            subprocess.Popen(f'explorer /select,"{os.path.normpath(self.target_file_path)}"')
        except Exception as e:
            print(f"Error opening folder: {e}")
        self.accept()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_col = "#252528" if is_dark else "#FFFFFF"
        card_bg = "#1E1E22" if is_dark else "#F8F8F8"
        border_col = "#383838" if is_dark else "#E0E0E0"
        text_primary = "#FFFFFF" if is_dark else "#242424"
        text_muted = "#9E9E9E" if is_dark else "#626262"
        accent_blue = "#2680EB" if is_dark else "#1473E6"
        btn_secondary_bg = "#323236" if is_dark else "#F0F0F0"
        btn_secondary_border = "#4A4A4F" if is_dark else "#D0D0D0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
            }}
            #successFileCard {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: {btn_secondary_bg};
                color: {text_primary};
                border: 1px solid {btn_secondary_border};
                border-radius: 4px;
                padding: 0px 14px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {'#3E3E43' if is_dark else '#E5E5E5'};
            }}
        """)

        # Highlight primary 'Open File' button
        self.btn_open.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_blue};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 0px 16px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {'#1D6FD8' if is_dark else '#0D66D0'};
            }}
            QPushButton:pressed {{
                background-color: {'#145BB8' if is_dark else '#095ABA'};
            }}
        """)

        self.lbl_title.setStyleSheet(f"color: {text_primary};")
        self.lbl_sub.setStyleSheet(f"color: {text_muted};")
        self.lbl_filename.setStyleSheet(f"color: {text_primary}; background: transparent;")
        self.lbl_filepath.setStyleSheet(f"color: {text_muted}; background: transparent;")
        self.icon_success.set_color("#22A06B" if is_dark else "#12805C")
        self.icon_doc.set_color(accent_blue)
