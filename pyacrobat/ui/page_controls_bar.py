"""
Page Controls Bar (Figma In-Viewport Controls)
Centered toolbar positioned above the PDF canvas inside the Document Viewport:
[ ◀ ] [ 1 ] / N [ ▶ ]  |  [ － ] [ 100% ▾ ] [ ＋ ]  |  [ ↔ Width ] [ ↕ Page ]
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QLabel, QLineEdit,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator

from pyacrobat.ui.styles import ThemeManager


class PageControlsBar(QWidget):
    """Compact viewport page navigation and zoom controls bar positioned above canvas."""

    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    zoom_level_changed = Signal(float)
    fit_width_requested = Signal()
    fit_page_requested = Signal()
    page_jump_requested = Signal(int)

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

        # 2. Zoom Controls
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

        # 3. Fit Controls
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
        self.setStyleSheet(f"""
            PageControlsBar {{
                background-color: {bg};
                border-bottom: 1px solid {border};
            }}
            #viewportCtrlDivider {{
                background-color: {'#3E3E42' if is_dark else '#D9D9D9'};
                border: none;
            }}
        """)

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
