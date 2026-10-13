"""
Page Controls Bar (Figma In-Viewport Controls with Page Tools & TTS)
Centered toolbar positioned above the PDF canvas inside the Document Viewport:
[ ◀ ] [ 1 ] / N [ ▶ ]  |  [ ↺ ] [ ↻ ] [ 🗑 ] [ 📑 ]  |  [ － ] [ 100% ▾ ] [ ＋ ]  |  [ ↔ Width ] [ ↕ Page ]  |  [ 🔊 Read Aloud ]
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QLabel, QLineEdit,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray
from PySide6.QtGui import QIntValidator, QPainter
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def _load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    path = os.path.join(ICONS_DIR, f"{icon_name}.svg")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('#626262', color_hex).replace('#242424', color_hex)
        return QSvgRenderer(QByteArray(content.encode("utf-8")))
    except Exception:
        return None


class ViewportIconButton(QToolButton):
    """High-DPI 26x26 vector button for viewport controls."""

    def __init__(self, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(26, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        icon_color = "#D0D0D0" if is_dark else "#444444"
        hover_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
        self.renderer = _load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {'#404040' if is_dark else '#D0D0D0'};
            }}
            QToolButton:pressed {{
                background-color: {'#1E293B' if is_dark else '#EAF3FF'};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            size = 14
            x = (self.width() - size) / 2.0
            y = (self.height() - size) / 2.0
            self.renderer.render(painter, QRectF(x, y, size, size))
            painter.end()


class PageControlsBar(QWidget):
    """Viewport toolbar housing Page Navigation, Page Tools, Zoom, Fit, and TTS."""

    # Navigation & Zoom Signals
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    zoom_level_changed = Signal(float)
    fit_width_requested = Signal()
    fit_page_requested = Signal()
    page_jump_requested = Signal(int)

    # Page Tools Signals
    rotate_cw_requested = Signal()
    rotate_ccw_requested = Signal()
    delete_page_requested = Signal()
    organize_pages_requested = Signal()

    # TTS Signal
    tts_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_pages = 1
        self.current_page = 1
        self.setFixedHeight(38)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 2, 12, 2)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignCenter)

        # 1. Page Navigation
        self.btn_prev_page = QToolButton()
        self.btn_prev_page.setText("◀")
        self.btn_prev_page.setToolTip("Previous Page (PgUp)")
        self.btn_prev_page.setFixedSize(26, 26)
        self.btn_prev_page.setCursor(Qt.PointingHandCursor)
        self.btn_prev_page.clicked.connect(self._on_prev_page)
        main_layout.addWidget(self.btn_prev_page)

        self.page_input = QLineEdit("1")
        self.page_input.setFixedSize(36, 24)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_validator = QIntValidator(1, 9999, self)
        self.page_input.setValidator(self.page_validator)
        self.page_input.returnPressed.connect(self._on_page_input_submitted)
        main_layout.addWidget(self.page_input)

        self.total_page_label = QLabel("/ 1")
        self.total_page_label.setObjectName("subtleLabel")
        main_layout.addWidget(self.total_page_label)

        self.btn_next_page = QToolButton()
        self.btn_next_page.setText("▶")
        self.btn_next_page.setToolTip("Next Page (PgDn)")
        self.btn_next_page.setFixedSize(26, 26)
        self.btn_next_page.setCursor(Qt.PointingHandCursor)
        self.btn_next_page.clicked.connect(self._on_next_page)
        main_layout.addWidget(self.btn_next_page)

        main_layout.addWidget(self._create_divider())

        # 2. Page Tools (Relocated to toolbar)
        self.btn_rotate_ccw = ViewportIconButton("rotate-ccw", "Rotate Page Counter-Clockwise (Ctrl+Shift+R)", self)
        self.btn_rotate_ccw.clicked.connect(self.rotate_ccw_requested.emit)
        main_layout.addWidget(self.btn_rotate_ccw)

        self.btn_rotate_cw = ViewportIconButton("rotate-cw", "Rotate Page Clockwise (Ctrl+R)", self)
        self.btn_rotate_cw.clicked.connect(self.rotate_cw_requested.emit)
        main_layout.addWidget(self.btn_rotate_cw)

        self.btn_delete_page = ViewportIconButton("trash", "Delete Current Page", self)
        self.btn_delete_page.clicked.connect(self.delete_page_requested.emit)
        main_layout.addWidget(self.btn_delete_page)

        self.btn_organize = ViewportIconButton("layers", "Organize Pages Workstation", self)
        self.btn_organize.clicked.connect(self.organize_pages_requested.emit)
        main_layout.addWidget(self.btn_organize)

        main_layout.addWidget(self._create_divider())

        # 3. Zoom Controls
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("－")
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl -)")
        self.btn_zoom_out.setFixedSize(26, 26)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(self.zoom_out_requested.emit)
        main_layout.addWidget(self.btn_zoom_out)

        self.zoom_combo = QComboBox()
        self.zoom_combo.setFixedWidth(72)
        self.zoom_combo.setFixedHeight(24)
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "300%"])
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_combo_changed)
        main_layout.addWidget(self.zoom_combo)

        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("＋")
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl +)")
        self.btn_zoom_in.setFixedSize(26, 26)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self.zoom_in_requested.emit)
        main_layout.addWidget(self.btn_zoom_in)

        main_layout.addWidget(self._create_divider())

        # 4. Fit Controls
        self.btn_fit_width = QToolButton()
        self.btn_fit_width.setText("↔ Width")
        self.btn_fit_width.setToolTip("Fit to Page Width")
        self.btn_fit_width.setFixedHeight(26)
        self.btn_fit_width.setCursor(Qt.PointingHandCursor)
        self.btn_fit_width.clicked.connect(self.fit_width_requested.emit)
        main_layout.addWidget(self.btn_fit_width)

        self.btn_fit_page = QToolButton()
        self.btn_fit_page.setText("↕ Page")
        self.btn_fit_page.setToolTip("Fit Entire Page in View")
        self.btn_fit_page.setFixedHeight(26)
        self.btn_fit_page.setCursor(Qt.PointingHandCursor)
        self.btn_fit_page.clicked.connect(self.fit_page_requested.emit)
        main_layout.addWidget(self.btn_fit_page)

        main_layout.addWidget(self._create_divider())

        # 5. Neural Read Aloud (TTS) Action Trigger
        self.btn_tts = QToolButton()
        self.btn_tts.setText("🔊 Read Aloud")
        self.btn_tts.setToolTip("Neural Read Aloud (TTS) — Click to open speech player (Ctrl+Shift+Y)")
        self.btn_tts.setFixedHeight(26)
        self.btn_tts.setCursor(Qt.PointingHandCursor)
        self.btn_tts.setObjectName("btnTTSBar")
        self.btn_tts.clicked.connect(self.tts_toggle_requested.emit)
        main_layout.addWidget(self.btn_tts)

        self.update_theme()

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedSize(1, 16)
        line.setObjectName("viewportCtrlDivider")
        return line

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#181818" if is_dark else "#F5F5F7"
        border = "#2E2E32" if is_dark else "#E0E0E0"
        btn_hover = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
        text_color = "#F0F0F0" if is_dark else "#242424"

        self.setStyleSheet(f"""
            PageControlsBar {{
                background-color: {bg};
                border-bottom: 1px solid {border};
            }}
            #viewportCtrlDivider {{
                background-color: {'#3E3E42' if is_dark else '#D9D9D9'};
                border: none;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: {text_color};
                padding: 2px 6px;
                font-size: 11px;
            }}
            QToolButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {'#404040' if is_dark else '#D0D0D0'};
            }}
            QToolButton#btnTTSBar {{
                font-weight: 500;
                color: {'#60A5FA' if is_dark else '#1473E6'};
            }}
            QToolButton#btnTTSBar:hover {{
                background-color: {'#1E293B' if is_dark else '#EAF3FF'};
                border: 1px solid {'#2563EB' if is_dark else '#1473E6'};
            }}
        """)

        # Update vector icon buttons
        if hasattr(self, "btn_rotate_ccw"):
            self.btn_rotate_ccw.update_theme()
        if hasattr(self, "btn_rotate_cw"):
            self.btn_rotate_cw.update_theme()
        if hasattr(self, "btn_delete_page"):
            self.btn_delete_page.update_theme()
        if hasattr(self, "btn_organize"):
            self.btn_organize.update_theme()

    def update_page_info(self, current: int, total: int):
        self.current_page = current
        self.total_pages = max(1, total)
        self.page_validator.setTop(self.total_pages)
        self.page_input.setText(str(current))
        self.total_page_label.setText(f"/ {self.total_pages}")
        self.btn_prev_page.setEnabled(current > 1)
        self.btn_next_page.setEnabled(current < self.total_pages)

    def update_zoom_display(self, scale: float):
        percent = int(round(scale * 100))
        text = f"{percent}%"
        self.zoom_combo.blockSignals(True)
        idx = self.zoom_combo.findText(text)
        if idx >= 0:
            self.zoom_combo.setCurrentIndex(idx)
        else:
            self.zoom_combo.setEditText(text)
        self.zoom_combo.blockSignals(False)

    def _on_prev_page(self):
        if self.current_page > 1:
            self.page_jump_requested.emit(self.current_page - 1)

    def _on_next_page(self):
        if self.current_page < self.total_pages:
            self.page_jump_requested.emit(self.current_page + 1)

    def _on_page_input_submitted(self):
        try:
            val = int(self.page_input.text())
            val = max(1, min(self.total_pages, val))
            self.page_jump_requested.emit(val)
        except ValueError:
            self.page_input.setText(str(self.current_page))

    def _on_zoom_combo_changed(self, text: str):
        clean = text.replace("%", "").strip()
        try:
            val = float(clean) / 100.0
            self.zoom_level_changed.emit(val)
        except ValueError:
            pass
