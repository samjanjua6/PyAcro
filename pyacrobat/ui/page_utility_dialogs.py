"""
Secondary Page Utility Dialogs (Figma Acrobat Alignment)
Implements:
1. HeaderFooterDialog: 6-field header/footer configuration with dynamic tokens (<<Page>>, <<Total>>, <<Date>>, <<Title>>)
2. WatermarkDialog: Customizable opacity, rotation angle (0-90°), font size, color, and live preview
3. CropPagesDialog: Margin-based page cropbox configuration
4. LinkDialog: Hyperlink creation dialog
Supports full Adobe Spectrum Light & Dark theming.
"""

from typing import Optional, List, Tuple, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QColorDialog, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen

from pyacrobat.ui.styles import ThemeManager


class HeaderFooterDialog(QDialog):
    """
    Configures and applies running headers and footers across PDF pages.
    Supports dynamic replacement tokens: <<Page>>, <<Total>>, <<Date>>, <<Title>>.
    """

    def __init__(self, page_count: int = 1, current_page: int = 1, parent=None):
        super().__init__(parent)
        self.page_count = max(1, page_count)
        self.current_page = max(1, min(current_page, self.page_count))
        self.last_focused_input: Optional[QLineEdit] = None
        self.color_rgb: Tuple[float, float, float] = (0.4, 0.4, 0.4)

        self.setWindowTitle("Add Header & Footer")
        self.setFixedSize(540, 500)
        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title / Description
        self.title_lbl = QLabel("Header and Footer Settings", self)
        self.title_lbl.setFont(QFont("Inter", 12, QFont.Bold))
        layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(
            "Configure running headers and footers. Insert dynamic tokens using the helper buttons below.",
            self
        )
        self.desc_lbl.setFont(QFont("Inter", 9))
        self.desc_lbl.setWordWrap(True)
        layout.addWidget(self.desc_lbl)

        # Token helper buttons row
        token_row = QHBoxLayout()
        token_row.setSpacing(6)
        token_row.addWidget(QLabel("Insert token:", self))

        for token_label, token_val in [
            ("+ [Page]", "<<Page>>"),
            ("+ [Total Pages]", "<<Total>>"),
            ("+ [Date]", "<<Date>>"),
            ("+ [Title]", "<<Title>>")
        ]:
            btn = QPushButton(token_label, self)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch=False, t=token_val: self._insert_token(t))
            token_row.addWidget(btn)

        token_row.addStretch()
        layout.addLayout(token_row)

        # 2x3 Grid of Header and Footer inputs
        grid = QGridLayout()
        grid.setSpacing(10)

        # Headers
        self.lbl_hl = QLabel("Left Header:", self)
        self.input_hl = QLineEdit(self)
        self.input_hl.setPlaceholderText("Left header text")
        self.input_hl.focused = lambda: self._set_focused(self.input_hl)

        self.lbl_hc = QLabel("Center Header:", self)
        self.input_hc = QLineEdit(self)
        self.input_hc.setPlaceholderText("Center header text")

        self.lbl_hr = QLabel("Right Header:", self)
        self.input_hr = QLineEdit(self)
        self.input_hr.setPlaceholderText("Right header text")

        grid.addWidget(self.lbl_hl, 0, 0)
        grid.addWidget(self.input_hl, 1, 0)
        grid.addWidget(self.lbl_hc, 0, 1)
        grid.addWidget(self.input_hc, 1, 1)
        grid.addWidget(self.lbl_hr, 0, 2)
        grid.addWidget(self.input_hr, 1, 2)

        # Footers
        self.lbl_fl = QLabel("Left Footer:", self)
        self.input_fl = QLineEdit(self)
        self.input_fl.setPlaceholderText("Left footer text")

        self.lbl_fc = QLabel("Center Footer:", self)
        self.input_fc = QLineEdit(self)
        self.input_fc.setText("Page <<Page>> of <<Total>>")

        self.lbl_fr = QLabel("Right Footer:", self)
        self.input_fr = QLineEdit(self)
        self.input_fr.setPlaceholderText("Right footer text")

        grid.addWidget(self.lbl_fl, 2, 0)
        grid.addWidget(self.input_fl, 3, 0)
        grid.addWidget(self.lbl_fc, 2, 1)
        grid.addWidget(self.input_fc, 3, 1)
        grid.addWidget(self.lbl_fr, 2, 2)
        grid.addWidget(self.input_fr, 3, 2)

        layout.addLayout(grid)

        # Settings row: Font Size & Margin & Color
        settings_row = QHBoxLayout()
        settings_row.setSpacing(14)

        settings_row.addWidget(QLabel("Font size (pt):", self))
        self.spin_size = QDoubleSpinBox(self)
        self.spin_size.setRange(6.0, 36.0)
        self.spin_size.setValue(9.0)
        self.spin_size.setFixedWidth(65)
        settings_row.addWidget(self.spin_size)

        settings_row.addWidget(QLabel("Margin (pt):", self))
        self.spin_margin = QDoubleSpinBox(self)
        self.spin_margin.setRange(10.0, 100.0)
        self.spin_margin.setValue(36.0)
        self.spin_margin.setFixedWidth(65)
        settings_row.addWidget(self.spin_margin)

        self.btn_color = QPushButton("Color...", self)
        self.btn_color.setFixedHeight(28)
        self.btn_color.setCursor(Qt.PointingHandCursor)
        self.btn_color.clicked.connect(self._pick_color)
        settings_row.addWidget(self.btn_color)
        settings_row.addStretch()

        layout.addLayout(settings_row)

        # Page range row
        range_box = QHBoxLayout()
        range_box.setSpacing(12)
        range_box.addWidget(QLabel("Apply to:", self))

        self.rb_all = QRadioButton("All pages", self)
        self.rb_all.setChecked(True)
        self.rb_curr = QRadioButton(f"Current page ({self.current_page})", self)

        range_box.addWidget(self.rb_all)
        range_box.addWidget(self.rb_curr)
        range_box.addStretch()
        layout.addLayout(range_box)

        layout.addStretch()

        # Dialog Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(84, 32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Apply", self)
        self.btn_apply.setFixedSize(92, 32)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-weight: 600;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)

        # Track focus for token insertion
        for inp in (self.input_hl, self.input_hc, self.input_hr, self.input_fl, self.input_fc, self.input_fr):
            inp.cursorPositionChanged.connect(lambda old, new, i=inp: self._set_focused(i))

    def _set_focused(self, line_edit: QLineEdit):
        self.last_focused_input = line_edit

    def _insert_token(self, token: str):
        target = self.last_focused_input or self.input_fc
        target.insert(token)
        target.setFocus()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(int(self.color_rgb[0] * 255), int(self.color_rgb[1] * 255), int(self.color_rgb[2] * 255)), self)
        if c.isValid():
            self.color_rgb = (c.redF(), c.greenF(), c.blueF())

    def get_config(self) -> Dict[str, Any]:
        """Returns header/footer configuration dictionary."""
        page_indices = None if self.rb_all.isChecked() else [self.current_page - 1]
        return {
            "header_left": self.input_hl.text().strip(),
            "header_center": self.input_hc.text().strip(),
            "header_right": self.input_hr.text().strip(),
            "footer_left": self.input_fl.text().strip(),
            "footer_center": self.input_fc.text().strip(),
            "footer_right": self.input_fr.text().strip(),
            "font_size": self.spin_size.value(),
            "color_rgb": self.color_rgb,
            "margin": self.spin_margin.value(),
            "page_indices": page_indices
        }

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#222222" if is_dark else "#F8F8F8"
        fg = "#FFFFFF" if is_dark else "#242424"
        input_bg = "#2C2C2C" if is_dark else "#FFFFFF"
        border = "#3A3A3A" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: #1473E6;
            }}
            QPushButton {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {'#353535' if is_dark else '#EAEAEA'};
            }}
            QDoubleSpinBox {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px;
            }}
            QRadioButton {{
                color: {fg};
            }}
        """)


class WatermarkDialog(QDialog):
    """
    Configures and applies diagonal centered watermarks across PDF pages.
    Provides opacity, angle (0-90°), font size, and text color sliders.
    """

    def __init__(self, page_count: int = 1, current_page: int = 1, parent=None):
        super().__init__(parent)
        self.page_count = max(1, page_count)
        self.current_page = max(1, min(current_page, self.page_count))
        self.color_rgb: Tuple[float, float, float] = (0.5, 0.5, 0.5)

        self.setWindowTitle("Add Watermark")
        self.setFixedSize(500, 460)
        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.title_lbl = QLabel("Watermark Configuration", self)
        self.title_lbl.setFont(QFont("Inter", 12, QFont.Bold))
        layout.addWidget(self.title_lbl)

        # Watermark Text input
        layout.addWidget(QLabel("Watermark Text:", self))
        self.input_text = QLineEdit("CONFIDENTIAL", self)
        self.input_text.setFixedHeight(34)
        self.input_text.textChanged.connect(self._update_preview)
        layout.addWidget(self.input_text)

        # Controls Grid: Opacity, Angle, Size
        grid = QGridLayout()
        grid.setSpacing(12)

        # Opacity slider
        grid.addWidget(QLabel("Opacity (%):", self), 0, 0)
        self.slider_opacity = QSlider(Qt.Horizontal, self)
        self.slider_opacity.setRange(10, 100)
        self.slider_opacity.setValue(25)
        self.lbl_opacity_val = QLabel("25%", self)
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        self.slider_opacity.valueChanged.connect(self._update_preview)
        grid.addWidget(self.slider_opacity, 0, 1)
        grid.addWidget(self.lbl_opacity_val, 0, 2)

        # Rotation slider
        grid.addWidget(QLabel("Angle (°):", self), 1, 0)
        self.slider_angle = QSlider(Qt.Horizontal, self)
        self.slider_angle.setRange(0, 90)
        self.slider_angle.setValue(45)
        self.lbl_angle_val = QLabel("45°", self)
        self.slider_angle.valueChanged.connect(lambda v: self.lbl_angle_val.setText(f"{v}°"))
        self.slider_angle.valueChanged.connect(self._update_preview)
        grid.addWidget(self.slider_angle, 1, 1)
        grid.addWidget(self.lbl_angle_val, 1, 2)

        # Font size spinner
        grid.addWidget(QLabel("Font Size (pt):", self), 2, 0)
        self.spin_size = QSpinBox(self)
        self.spin_size.setRange(16, 120)
        self.spin_size.setValue(48)
        self.spin_size.valueChanged.connect(self._update_preview)
        grid.addWidget(self.spin_size, 2, 1)

        # Color picker button
        self.btn_color = QPushButton("Choose Color...", self)
        self.btn_color.clicked.connect(self._pick_color)
        grid.addWidget(self.btn_color, 2, 2)

        layout.addLayout(grid)

        # Target pages
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Pages:", self))
        self.rb_all = QRadioButton("All pages", self)
        self.rb_all.setChecked(True)
        self.rb_curr = QRadioButton(f"Current page ({self.current_page})", self)
        range_row.addWidget(self.rb_all)
        range_row.addWidget(self.rb_curr)
        range_row.addStretch()
        layout.addLayout(range_row)

        layout.addStretch()

        # Dialog Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(84, 32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Apply Watermark", self)
        self.btn_apply.setFixedSize(130, 32)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-weight: 600;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(int(self.color_rgb[0] * 255), int(self.color_rgb[1] * 255), int(self.color_rgb[2] * 255)), self)
        if c.isValid():
            self.color_rgb = (c.redF(), c.greenF(), c.blueF())
            self._update_preview()

    def _update_preview(self):
        self.update()

    def get_config(self) -> Dict[str, Any]:
        """Returns watermark configuration dictionary."""
        opacity = self.slider_opacity.value() / 100.0
        angle = float(self.slider_angle.value())
        font_size = float(self.spin_size.value())
        text = self.input_text.text().strip() or "CONFIDENTIAL"
        page_indices = None if self.rb_all.isChecked() else [self.current_page - 1]

        return {
            "text": text,
            "opacity": opacity,
            "angle": angle,
            "font_size": font_size,
            "color_rgb": self.color_rgb,
            "page_indices": page_indices
        }

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#222222" if is_dark else "#F8F8F8"
        fg = "#FFFFFF" if is_dark else "#242424"
        input_bg = "#2C2C2C" if is_dark else "#FFFFFF"
        border = "#3A3A3A" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QSpinBox {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px;
            }}
            QRadioButton {{
                color: {fg};
            }}
        """)


class CropPagesDialog(QDialog):
    """
    Configures and applies page cropbox margins (Top, Bottom, Left, Right in points/inches).
    """

    def __init__(self, page_width: float = 612.0, page_height: float = 792.0, current_page: int = 1, parent=None):
        super().__init__(parent)
        self.page_width = page_width
        self.page_height = page_height
        self.current_page = current_page

        self.setWindowTitle("Crop Pages")
        self.setFixedSize(400, 340)
        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.title_lbl = QLabel("Set Crop Margins (points)", self)
        self.title_lbl.setFont(QFont("Inter", 12, QFont.Bold))
        layout.addWidget(self.title_lbl)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Top
        grid.addWidget(QLabel("Top Margin:", self), 0, 0)
        self.spin_top = QDoubleSpinBox(self)
        self.spin_top.setRange(0, self.page_height / 3.0)
        self.spin_top.setValue(36.0)
        grid.addWidget(self.spin_top, 0, 1)

        # Bottom
        grid.addWidget(QLabel("Bottom Margin:", self), 1, 0)
        self.spin_bottom = QDoubleSpinBox(self)
        self.spin_bottom.setRange(0, self.page_height / 3.0)
        self.spin_bottom.setValue(36.0)
        grid.addWidget(self.spin_bottom, 1, 1)

        # Left
        grid.addWidget(QLabel("Left Margin:", self), 2, 0)
        self.spin_left = QDoubleSpinBox(self)
        self.spin_left.setRange(0, self.page_width / 3.0)
        self.spin_left.setValue(36.0)
        grid.addWidget(self.spin_left, 2, 1)

        # Right
        grid.addWidget(QLabel("Right Margin:", self), 3, 0)
        self.spin_right = QDoubleSpinBox(self)
        self.spin_right.setRange(0, self.page_width / 3.0)
        self.spin_right.setValue(36.0)
        grid.addWidget(self.spin_right, 3, 1)

        layout.addLayout(grid)

        # Page range
        range_row = QHBoxLayout()
        self.rb_curr = QRadioButton(f"Current page ({self.current_page})", self)
        self.rb_curr.setChecked(True)
        self.rb_all = QRadioButton("All pages", self)
        range_row.addWidget(self.rb_curr)
        range_row.addWidget(self.rb_all)
        layout.addLayout(range_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(84, 32)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Crop", self)
        self.btn_apply.setFixedSize(92, 32)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-weight: 600;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)

    def get_config(self) -> Dict[str, Any]:
        """Calculates cropped fitz.Rect from margin inputs."""
        left = self.spin_left.value()
        top = self.spin_top.value()
        right = self.page_width - self.spin_right.value()
        bottom = self.page_height - self.spin_bottom.value()

        return {
            "crop_rect_coords": (left, top, right, bottom),
            "apply_all": self.rb_all.isChecked()
        }

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#222222" if is_dark else "#F8F8F8"
        fg = "#FFFFFF" if is_dark else "#242424"
        input_bg = "#2C2C2C" if is_dark else "#FFFFFF"
        border = "#3A3A3A" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QDoubleSpinBox {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QRadioButton {{
                color: {fg};
            }}
        """)


class LinkDialog(QDialog):
    """
    Dialog to input and attach a destination web URL to a hyperlink area.
    """

    def __init__(self, initial_url: str = "https://", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Hyperlink")
        self.setFixedSize(440, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_lbl = QLabel("Enter Web URL Destination:", self)
        self.title_lbl.setFont(QFont("Inter", 11, QFont.Bold))
        layout.addWidget(self.title_lbl)

        self.input_url = QLineEdit(initial_url, self)
        self.input_url.setFixedHeight(34)
        layout.addWidget(self.input_url)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(84, 32)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Add Link", self)
        self.btn_apply.setFixedSize(92, 32)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-weight: 600;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)
        self.update_theme()

    def get_url(self) -> str:
        return self.input_url.text().strip()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#222222" if is_dark else "#F8F8F8"
        fg = "#FFFFFF" if is_dark else "#242424"
        input_bg = "#2C2C2C" if is_dark else "#FFFFFF"
        border = "#3A3A3A" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
        """)
