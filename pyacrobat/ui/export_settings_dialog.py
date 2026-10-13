"""
Export Settings Dialog Component (Phase 3 Figma Acrobat Alignment)
Provides detailed, format-specific conversion configuration:
- Word (.docx): Layout mode (Flowing vs. Retain Layout), images, comments
- Excel (.xlsx): Sheet per page vs. single sheet, column autofit, non-table text
- PowerPoint (.pptx): Aspect ratio (match PDF vs. 16:9 vs. 4:3), high-res backdrop
- Images (PNG/JPEG/TIFF): Resolution DPI (72, 150, 300, 600), JPEG quality, color mode
- OCR & Recognition: Trigger sensitivity, force OCR, resolution
Full Adobe Spectrum Light & Dark theming.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTabWidget, QWidget, QRadioButton, QCheckBox,
    QComboBox, QSlider, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.core.export_engine import (
    FORMAT_DOCX, FORMAT_XLSX, FORMAT_PPTX, FORMAT_IMAGE,
    FORMAT_PNG, FORMAT_JPEG, FORMAT_TIFF
)


class ExportSettingsDialog(QDialog):
    """
    Format-specific configuration dialog opened from 'Export settings' link in ExportPdfPanel.
    """

    def __init__(
        self,
        initial_format_key: str = FORMAT_DOCX,
        initial_settings: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.initial_format_key = initial_format_key.lower()
        self.settings: Dict[str, Any] = initial_settings or {}

        self.setWindowTitle("Export Settings")
        self.setFixedSize(580, 480)
        self.setModal(True)

        self.init_ui()
        self.load_settings(self.settings)
        self._select_initial_tab()
        self.update_theme()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # 1. Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        self.lbl_title = QLabel("Conversion & Export Settings")
        self.lbl_title.setFont(QFont("Inter", 13, QFont.Bold))
        header_layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(
            "Configure layout preservation, formatting rules, resolution, and OCR for exported documents."
        )
        self.lbl_desc.setFont(QFont("Inter", 9))
        self.lbl_desc.setWordWrap(True)
        header_layout.addWidget(self.lbl_desc)

        root_layout.addLayout(header_layout)

        # 2. Tab Widget for format categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("exportSettingsTabs")

        self.tab_word = self._build_word_tab()
        self.tab_excel = self._build_excel_tab()
        self.tab_pptx = self._build_pptx_tab()
        self.tab_image = self._build_image_tab()
        self.tab_ocr = self._build_ocr_tab()

        self.tab_widget.addTab(self.tab_word, "Word (.docx)")
        self.tab_widget.addTab(self.tab_excel, "Excel (.xlsx)")
        self.tab_widget.addTab(self.tab_pptx, "PowerPoint (.pptx)")
        self.tab_widget.addTab(self.tab_image, "Image Formats")
        self.tab_widget.addTab(self.tab_ocr, "OCR Engine")

        root_layout.addWidget(self.tab_widget, 1)

        # 3. Action Buttons Ribbon (Cancel, OK)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(90, 32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Save Settings")
        self.btn_ok.setFixedSize(110, 32)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        root_layout.addLayout(btn_layout)

    # =========================================================================
    # Tab Builders
    # =========================================================================

    def _build_word_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_section = QLabel("Layout Engine")
        lbl_section.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_section)

        self.rad_word_layout = QRadioButton("Retain Page Layout (Recommended for forms, reports, flyers)")
        self.rad_word_layout.setChecked(True)
        layout.addWidget(self.rad_word_layout)

        self.rad_word_flowing = QRadioButton("Flowing Text Engine (Recommended for editing continuous text)")
        layout.addWidget(self.rad_word_flowing)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        lbl_content = QLabel("Content Options")
        lbl_content.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_content)

        self.chk_word_images = QCheckBox("Extract and embed graphics && photographs")
        self.chk_word_images.setChecked(True)
        layout.addWidget(self.chk_word_images)

        self.chk_word_comments = QCheckBox("Export PDF annotations as Word comments")
        self.chk_word_comments.setChecked(False)
        layout.addWidget(self.chk_word_comments)

        self.chk_word_headers = QCheckBox("Detect and format headings automatically")
        self.chk_word_headers.setChecked(True)
        layout.addWidget(self.chk_word_headers)

        layout.addStretch()
        return w

    def _build_excel_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_section = QLabel("Worksheet Organization")
        lbl_section.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_section)

        self.rad_excel_sheets = QRadioButton("Create a separate worksheet for each PDF page (Default)")
        self.rad_excel_sheets.setChecked(True)
        layout.addWidget(self.rad_excel_sheets)

        self.rad_excel_single = QRadioButton("Consolidate all extracted tables into a single sheet")
        layout.addWidget(self.rad_excel_single)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        lbl_content = QLabel("Table & Cell Formatting")
        lbl_content.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_content)

        self.chk_excel_autofit = QCheckBox("Auto-fit column widths to table content")
        self.chk_excel_autofit.setChecked(True)
        layout.addWidget(self.chk_excel_autofit)

        self.chk_excel_text = QCheckBox("Include page text outside of tables in Column A")
        self.chk_excel_text.setChecked(True)
        layout.addWidget(self.chk_excel_text)

        self.chk_excel_headers = QCheckBox("Format table headers with corporate accent fill")
        self.chk_excel_headers.setChecked(True)
        layout.addWidget(self.chk_excel_headers)

        layout.addStretch()
        return w

    def _build_pptx_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_section = QLabel("Slide Dimensions")
        lbl_section.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_section)

        self.rad_pptx_pdf_ratio = QRadioButton("Match original PDF aspect ratio (Default)")
        self.rad_pptx_pdf_ratio.setChecked(True)
        layout.addWidget(self.rad_pptx_pdf_ratio)

        self.rad_pptx_widescreen = QRadioButton("Widescreen 16:9")
        layout.addWidget(self.rad_pptx_widescreen)

        self.rad_pptx_standard = QRadioButton("Standard 4:3")
        layout.addWidget(self.rad_pptx_standard)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        lbl_content = QLabel("Visual Options")
        lbl_content.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_content)

        self.chk_pptx_backdrop = QCheckBox("High-resolution slide visual backdrop (150 DPI)")
        self.chk_pptx_backdrop.setChecked(True)
        layout.addWidget(self.chk_pptx_backdrop)

        layout.addStretch()
        return w

    def _build_image_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Image format
        grid.addWidget(QLabel("Default Format:"), 0, 0)
        self.combo_img_format = QComboBox()
        self.combo_img_format.addItems(["PNG (Lossless)", "JPEG (Compressed)", "TIFF (Multi-page Archive)"])
        grid.addWidget(self.combo_img_format, 0, 1)

        # Resolution DPI
        grid.addWidget(QLabel("Resolution (DPI):"), 1, 0)
        self.combo_img_dpi = QComboBox()
        self.combo_img_dpi.addItems([
            "72 DPI (Screen & Web)",
            "150 DPI (Standard Document - Recommended)",
            "300 DPI (High-Quality Print)",
            "600 DPI (Ultra-High Resolution)"
        ])
        self.combo_img_dpi.setCurrentIndex(1)
        grid.addWidget(self.combo_img_dpi, 1, 1)

        # Color mode
        grid.addWidget(QLabel("Color Space:"), 2, 0)
        self.combo_img_color = QComboBox()
        self.combo_img_color.addItems(["RGB (Full Color)", "Grayscale", "Monochrome (1-bit B&W)"])
        grid.addWidget(self.combo_img_color, 2, 1)

        layout.addLayout(grid)

        # JPEG Quality Slider
        layout.addWidget(QLabel("JPEG Quality / Compression:"))
        slider_row = QHBoxLayout()
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(50, 100)
        self.slider_quality.setValue(90)
        slider_row.addWidget(self.slider_quality)

        self.lbl_quality_val = QLabel("90%")
        self.lbl_quality_val.setFixedWidth(40)
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_quality_val.setText(f"{v}%"))
        slider_row.addWidget(self.lbl_quality_val)
        layout.addLayout(slider_row)

        layout.addStretch()
        return w

    def _build_ocr_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_section = QLabel("OCR Recognition Sensitivity")
        lbl_section.setFont(QFont("Inter", 10, QFont.DemiBold))
        layout.addWidget(lbl_section)

        self.rad_ocr_needed = QRadioButton("Recognize text only if page lacks selectable text (Default)")
        self.rad_ocr_needed.setChecked(True)
        layout.addWidget(self.rad_ocr_needed)

        self.rad_ocr_force = QRadioButton("Force OCR on all pages (Overwrites raw text layer)")
        layout.addWidget(self.rad_ocr_force)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        grid = QGridLayout()
        grid.addWidget(QLabel("OCR Rasterization DPI:"), 0, 0)
        self.combo_ocr_dpi = QComboBox()
        self.combo_ocr_dpi.addItems(["150 DPI (Fast)", "300 DPI (Accurate - Recommended)", "400 DPI (High Precision)"])
        self.combo_ocr_dpi.setCurrentIndex(1)
        grid.addWidget(self.combo_ocr_dpi, 0, 1)
        layout.addLayout(grid)

        layout.addStretch()
        return w

    # =========================================================================
    # Settings Management
    # =========================================================================

    def _select_initial_tab(self):
        """Switches to the tab corresponding to the format user is configuring."""
        mapping = {
            FORMAT_DOCX: 0,
            FORMAT_XLSX: 1,
            FORMAT_PPTX: 2,
            FORMAT_IMAGE: 3,
            FORMAT_PNG: 3,
            FORMAT_JPEG: 3,
            FORMAT_TIFF: 3,
        }
        idx = mapping.get(self.initial_format_key, 0)
        self.tab_widget.setCurrentIndex(idx)

    def load_settings(self, s: Dict[str, Any]):
        """Populates UI elements from stored dictionary."""
        # Word
        if s.get("word_flowing"):
            self.rad_word_flowing.setChecked(True)
        if "word_images" in s:
            self.chk_word_images.setChecked(bool(s["word_images"]))
        if "word_comments" in s:
            self.chk_word_comments.setChecked(bool(s["word_comments"]))

        # Excel
        if s.get("excel_single"):
            self.rad_excel_single.setChecked(True)
        if "excel_autofit" in s:
            self.chk_excel_autofit.setChecked(bool(s["excel_autofit"]))

        # PPTX
        if s.get("pptx_widescreen"):
            self.rad_pptx_widescreen.setChecked(True)

        # Image DPI
        dpi = s.get("dpi")
        if dpi == 72:
            self.combo_img_dpi.setCurrentIndex(0)
        elif dpi == 300:
            self.combo_img_dpi.setCurrentIndex(2)
        elif dpi == 600:
            self.combo_img_dpi.setCurrentIndex(3)

        if "quality" in s:
            self.slider_quality.setValue(int(s["quality"]))

        # OCR
        if s.get("ocr_force"):
            self.rad_ocr_force.setChecked(True)

    def get_settings(self) -> Dict[str, Any]:
        """Returns structured dictionary of configured settings."""
        dpi_values = [72.0, 150.0, 300.0, 600.0]
        selected_dpi = dpi_values[self.combo_img_dpi.currentIndex()]

        format_map = {0: "png", 1: "jpeg", 2: "tiff"}
        selected_img_fmt = format_map.get(self.combo_img_format.currentIndex(), "png")

        return {
            # Top-level direct properties
            "dpi": selected_dpi,
            "quality": self.slider_quality.value(),
            "image_format": selected_img_fmt,
            "ocr_force": self.rad_ocr_force.isChecked(),

            # Word group
            "word_flowing": self.rad_word_flowing.isChecked(),
            "word_images": self.chk_word_images.isChecked(),
            "word_comments": self.chk_word_comments.isChecked(),
            "word_headers": self.chk_word_headers.isChecked(),

            # Excel group
            "excel_single": self.rad_excel_single.isChecked(),
            "excel_autofit": self.chk_excel_autofit.isChecked(),
            "excel_text": self.chk_excel_text.isChecked(),
            "excel_headers": self.chk_excel_headers.isChecked(),

            # PPTX group
            "pptx_widescreen": self.rad_pptx_widescreen.isChecked(),
            "pptx_backdrop": self.chk_pptx_backdrop.isChecked(),

            # Image group
            "color_space": self.combo_img_color.currentText(),
        }

    # =========================================================================
    # Theme Support
    # =========================================================================

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_dialog = "#252528" if is_dark else "#FFFFFF"
        border_col = "#383838" if is_dark else "#D9D9D9"
        text_primary = "#FFFFFF" if is_dark else "#242424"
        text_muted = "#9E9E9E" if is_dark else "#626262"
        input_bg = "#1E1E1E" if is_dark else "#FFFFFF"
        input_border = "#444444" if is_dark else "#D9D9D9"
        tab_bg = "#1E1E22" if is_dark else "#F5F5F7"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_dialog};
                color: {text_primary};
            }}
            QLabel {{
                color: {text_primary};
            }}
            QTabWidget::pane {{
                border: 1px solid {border_col};
                background-color: {bg_dialog};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                color: {text_muted};
                border: 1px solid {border_col};
                border-bottom: none;
                padding: 6px 14px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 500;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {bg_dialog};
                color: {'#4BA3FF' if is_dark else '#1473E6'};
                font-weight: 600;
                border-bottom: 2px solid #1473E6;
            }}
            QRadioButton, QCheckBox {{
                color: {text_primary};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                spacing: 8px;
            }}
            QComboBox {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding-left: 8px;
                height: 28px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_dialog};
                color: {text_primary};
                selection-background-color: #1473E6;
                selection-color: #FFFFFF;
                border: 1px solid {input_border};
            }}
            QFrame[frameShape="4"] {{
                background-color: {border_col};
                border: none;
            }}
        """)

        self.lbl_title.setStyleSheet(f"color: {text_primary};")
        self.lbl_desc.setStyleSheet(f"color: {text_muted};")

        # Cancel button
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#303035' if is_dark else '#EAEAEA'};
                color: {text_primary};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 500;
                border: 1px solid {border_col};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {'#3A3A40' if is_dark else '#DFDFDF'};
            }}
        """)

        # OK button (Adobe Blue)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
            QPushButton:pressed {
                background-color: #095ABA;
            }
        """)
