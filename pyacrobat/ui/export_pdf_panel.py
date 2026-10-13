"""
Export PDF Left Tool Drawer Component (Figma Acrobat Alignment)
Implements Figma node 3:13809:
- Fixed 308px width panel on the left of the document viewport
- Header: 'Export a PDF' (18px SemiBold) + Close button (X) + Subtitle 'Convert your PDF to an editable file.'
- Source file card with document metadata (filename, page count, file size)
- 'Convert to' format selection cards:
  * Microsoft Word (.docx)
  * Microsoft Excel (.xlsx)
  * Microsoft PowerPoint (.pptx)
  * Image (JPEG, PNG, TIFF)
- 'More formats' collapsible section (RTF, Plain Text, HTML, XML)
- Document language dropdown (English, Spanish, French, German, etc.)
- Checkbox: 'Recognize text if needed' (OCR trigger)
- Output File name input + Browse file dialog button
- 'Export settings' link button
- Primary pill CTA button: 'Convert to [FORMAT]' (prompts user to save file)
- Reassurance notice: 'Your original PDF will stay unchanged.'
- Full Light & Dark Adobe Spectrum theming.
"""

import os
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QScrollArea, QFrame, QPushButton, QComboBox, QCheckBox,
    QLineEdit, QFileDialog, QSizePolicy, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.core.export_engine import (
    FORMAT_DOCX, FORMAT_XLSX, FORMAT_PPTX, FORMAT_IMAGE,
    FORMAT_PNG, FORMAT_JPEG, FORMAT_TIFF, FORMAT_RTF,
    FORMAT_TXT, FORMAT_HTML, FORMAT_XML,
    suggest_output_path, get_format_extension, get_format_file_filter, get_format_display_name
)


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    """Loads SVG and replaces stroke/fill color dynamically for crisp high-DPI rendering."""
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


def renderer_to_icon(renderer: Optional[QSvgRenderer], size: int = 16):
    """Converts a QSvgRenderer to a crisp High-DPI QIcon."""
    from PySide6.QtGui import QPixmap, QIcon
    if renderer and renderer.isValid():
        pix = QPixmap(size * 2, size * 2)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return QIcon(pix)
    return QIcon()


class FormatCardWidget(QFrame):
    """
    Figma Export format card (48px height, rounded 4px) with custom radio indicator.
    Supports active highlight (#EAF3FF / #102A45), border accent, and theme transitions.
    """

    clicked = Signal(str)

    def __init__(
        self,
        format_id: str,
        title: str,
        subtitle: str,
        icon_name: str,
        parent=None
    ):
        super().__init__(parent)
        self.format_id = format_id
        self.title_text = title
        self.subtitle_text = subtitle
        self.icon_name = icon_name
        self.is_selected = False
        self.renderer: Optional[QSvgRenderer] = None

        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 14, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignVCenter)

        # 1. Left Icon Container
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_label)

        # 2. Text Details
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("background: transparent;")
        text_layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(self.subtitle_text)
        self.lbl_subtitle.setStyleSheet("background: transparent;")
        text_layout.addWidget(self.lbl_subtitle)

        layout.addLayout(text_layout)
        layout.addStretch()

        # 3. Radio Indicator Container (painted in paintEvent)
        self.radio_spacer = QWidget()
        self.radio_spacer.setFixedSize(16, 16)
        self.radio_spacer.setStyleSheet("background: transparent;")
        layout.addWidget(self.radio_spacer)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_theme()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.format_id)
        super().mousePressEvent(event)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_selected:
            bg_color = "#102A45" if is_dark else "#EAF3FF"
            border_color = "#2680EB" if is_dark else "#1473E6"
            title_color = "#FFFFFF" if is_dark else "#1473E6"
            icon_color = "#4BA3FF" if is_dark else "#1473E6"
        else:
            bg_color = "#1E1E1E" if is_dark else "#FFFFFF"
            border_color = "#383838" if is_dark else "#D9D9D9"
            title_color = "#EDEDED" if is_dark else "#242424"
            icon_color = "#A0A0A0" if is_dark else "#626262"

        sub_color = "#9E9E9E" if is_dark else "#626262"
        hover_bg = "#26262B" if is_dark else "#F5F5F7"

        self.setStyleSheet(f"""
            FormatCardWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            FormatCardWidget:hover {{
                background-color: {bg_color if self.is_selected else hover_bg};
            }}
        """)

        self.lbl_title.setStyleSheet(f"""
            color: {title_color};
            font-family: 'Inter', -apple-system, sans-serif;
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)

        self.lbl_subtitle.setStyleSheet(f"""
            color: {sub_color};
            font-family: 'Inter', -apple-system, sans-serif;
            font-size: 10px;
            font-weight: 400;
            background: transparent;
        """)

        self.renderer = load_themed_svg(self.icon_name, icon_color)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Render icon in icon_label rect
        if self.renderer and self.renderer.isValid():
            icon_rect = QRectF(12, (self.height() - 20) / 2.0, 20, 20)
            self.renderer.render(painter, icon_rect)

        # 2. Render custom radio button on right
        radio_size = 15.0
        rx = self.width() - 14.0 - radio_size
        ry = (self.height() - radio_size) / 2.0
        radio_rect = QRectF(rx, ry, radio_size, radio_size)

        is_dark = ThemeManager.is_dark()
        if self.is_selected:
            accent_blue = QColor("#2680EB" if is_dark else "#1473E6")
            painter.setPen(QPen(accent_blue, 4.0))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(radio_rect)
        else:
            border_col = QColor("#5A5A5A" if is_dark else "#858585")
            bg_col = QColor("#1E1E1E" if is_dark else "#FFFFFF")
            painter.setPen(QPen(border_col, 1.2))
            painter.setBrush(bg_col)
            painter.drawEllipse(radio_rect)

        painter.end()


class SecondaryFormatButton(QPushButton):
    """Row button for secondary format selection under 'More formats'."""

    format_selected = Signal(str)

    def __init__(self, format_id: str, label: str, ext_label: str, parent=None):
        super().__init__(parent)
        self.format_id = format_id
        self.label_text = label
        self.ext_label = ext_label
        self.is_active = False

        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clicked.connect(lambda: self.format_selected.emit(self.format_id))
        self.update_theme()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_active:
            bg = "#102A45" if is_dark else "#EAF3FF"
            color = "#4BA3FF" if is_dark else "#1473E6"
            weight = "600"
        else:
            bg = "transparent"
            color = "#E0E0E0" if is_dark else "#242424"
            weight = "400"

        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: {weight};
                text-align: left;
                padding-left: 12px;
                padding-right: 12px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {bg if self.is_active else hover_bg};
            }}
        """)
        self.setText(f"{self.label_text}  ({self.ext_label})")


class ExportPdfPanel(QWidget):
    """
    Export a PDF Drawer Panel (308px fixed width).
    Implements Figma node 3:13809 with full light/dark Spectrum styling,
    format cards, collapsible formats, language selector, OCR toggle, and save prompt.
    """

    close_requested = Signal()
    export_requested = Signal(str, str, dict)  # (target_path, format_key, options_dict)
    format_changed = Signal(str)
    settings_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(308)

        self.current_format_key: str = FORMAT_DOCX
        self.source_file_path: str = ""
        self.page_count: int = 1
        self.file_size_bytes: int = 0
        self.target_output_path: str = ""

        self.format_cards: Dict[str, FormatCardWidget] = {}
        self.secondary_buttons: Dict[str, SecondaryFormatButton] = {}
        self.is_more_formats_expanded: bool = False
        self.custom_settings: Dict[str, Any] = {}

        self.init_ui()
        self.update_theme()

    @property
    def selected_format(self) -> str:
        return self.current_format_key

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll area for clean overflow handling on smaller viewports
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("exportPanelContent")
        self.content_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(18, 18, 18, 18)
        self.content_layout.setSpacing(12)

        # 1. Header: 'Export a PDF' + Close Button ('X')
        self._init_header()

        # 2. Source File Information Card
        self._init_source_file_card()

        # 3. 'Convert to' Format Selection Section
        self._init_format_selection()

        # 4. 'More formats' Collapsible Container
        self._init_more_formats()

        # 5. Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFixedHeight(1)
        self.content_layout.addWidget(self.divider)

        # 6. Document Language Field
        self._init_language_selector()

        # 7. Recognize Text Checkbox (OCR)
        self._init_ocr_option()

        # 8. Output File Name Field + Browse Button
        self._init_filename_field()

        # 9. Export Settings Action Link
        self._init_settings_link()

        # 10. Flexible Spacer
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area, 1)

        # 11. Primary CTA Pill Button & Footnote pinned at bottom
        self._init_cta_footer(root_layout)

        # Select initial format now that all widgets are initialized
        self.select_format(FORMAT_DOCX, emit_signal=False)

    # =========================================================================
    # UI Sub-builders
    # =========================================================================

    def _init_header(self):
        header_row = QWidget()
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        self.lbl_title = QLabel("Export a PDF")
        self.lbl_title.setFont(QFont("Inter", 14, QFont.Bold))
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()

        self.btn_close = QToolButton()
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Close Export Panel (Esc)")
        self.btn_close.clicked.connect(self.close_requested.emit)
        h_layout.addWidget(self.btn_close)

        self.content_layout.addWidget(header_row)

        self.lbl_subtitle = QLabel("Convert your PDF to an editable file.")
        self.lbl_subtitle.setFont(QFont("Inter", 9))
        self.lbl_subtitle.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_subtitle)

    def _init_source_file_card(self):
        self.source_card = QFrame()
        self.source_card.setFixedHeight(46)
        card_layout = QHBoxLayout(self.source_card)
        card_layout.setContentsMargins(10, 0, 10, 0)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignVCenter)

        self.icon_source_file = QLabel()
        self.icon_source_file.setFixedSize(21, 21)
        card_layout.addWidget(self.icon_source_file)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)
        info_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_source_filename = QLabel("document.pdf")
        self.lbl_source_filename.setFont(QFont("Inter", 9, QFont.DemiBold))
        info_layout.addWidget(self.lbl_source_filename)

        self.lbl_source_meta = QLabel("1 page • 0 KB")
        self.lbl_source_meta.setFont(QFont("Inter", 8))
        info_layout.addWidget(self.lbl_source_meta)

        card_layout.addLayout(info_layout)
        card_layout.addStretch()

        self.content_layout.addWidget(self.source_card)

    def _init_format_selection(self):
        self.lbl_convert_to = QLabel("Convert to")
        self.lbl_convert_to.setFont(QFont("Inter", 10, QFont.DemiBold))
        self.content_layout.addWidget(self.lbl_convert_to)

        format_defs = [
            (FORMAT_DOCX, "Microsoft Word", "Word document (.docx)", "file-type-2"),
            (FORMAT_XLSX, "Microsoft Excel", "Excel workbook (.xlsx)", "sheet"),
            (FORMAT_PPTX, "Microsoft PowerPoint", "Presentation (.pptx)", "presentation"),
            (FORMAT_IMAGE, "Image", "JPEG, PNG, or TIFF", "image"),
        ]

        self.formats_container = QWidget()
        fc_layout = QVBoxLayout(self.formats_container)
        fc_layout.setContentsMargins(0, 0, 0, 0)
        fc_layout.setSpacing(8)

        for fid, title, sub, icon in format_defs:
            card = FormatCardWidget(fid, title, sub, icon, self)
            card.clicked.connect(self._on_format_card_clicked)
            fc_layout.addWidget(card)
            self.format_cards[fid] = card

        self.content_layout.addWidget(self.formats_container)

    def _init_more_formats(self):
        # Toggle Header
        self.btn_more_toggle = QPushButton()
        self.btn_more_toggle.setFixedHeight(26)
        self.btn_more_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_more_toggle.clicked.connect(self._toggle_more_formats)
        self.content_layout.addWidget(self.btn_more_toggle)

        # Collapsible Container
        self.more_container = QWidget()
        mc_layout = QVBoxLayout(self.more_container)
        mc_layout.setContentsMargins(0, 2, 0, 4)
        mc_layout.setSpacing(4)

        secondary_defs = [
            (FORMAT_RTF, "Rich Text Format", ".rtf"),
            (FORMAT_TXT, "Plain Text", ".txt"),
            (FORMAT_HTML, "HTML Web Page", ".html"),
            (FORMAT_XML, "XML Document", ".xml"),
        ]

        for fid, label, ext in secondary_defs:
            btn = SecondaryFormatButton(fid, label, ext, self)
            btn.format_selected.connect(self._on_format_card_clicked)
            mc_layout.addWidget(btn)
            self.secondary_buttons[fid] = btn

        self.more_container.setVisible(False)
        self.content_layout.addWidget(self.more_container)

    def _init_language_selector(self):
        self.lbl_language = QLabel("Document language")
        self.lbl_language.setFont(QFont("Inter", 9, QFont.DemiBold))
        self.content_layout.addWidget(self.lbl_language)

        self.combo_language = QComboBox()
        self.combo_language.setFixedHeight(34)
        self.combo_language.addItems([
            "English (U.S.)",
            "Spanish",
            "French",
            "German",
            "Italian",
            "Japanese",
            "Chinese (Simplified)"
        ])
        self.combo_language.setCurrentIndex(0)
        self.content_layout.addWidget(self.combo_language)

    def _init_ocr_option(self):
        self.chk_ocr = QCheckBox("Recognize text if needed")
        self.chk_ocr.setFont(QFont("Inter", 9))
        self.chk_ocr.setChecked(True)
        self.chk_ocr.setCursor(Qt.PointingHandCursor)
        self.content_layout.addWidget(self.chk_ocr)

    def _init_filename_field(self):
        self.lbl_filename = QLabel("File name")
        self.lbl_filename.setFont(QFont("Inter", 9, QFont.DemiBold))
        self.content_layout.addWidget(self.lbl_filename)

        fn_row = QWidget()
        fn_layout = QHBoxLayout(fn_row)
        fn_layout.setContentsMargins(0, 0, 0, 0)
        fn_layout.setSpacing(6)

        self.txt_filename = QLineEdit()
        self.txt_filename.setFixedHeight(34)
        self.txt_filename.setFont(QFont("Inter", 9))
        self.txt_filename.setPlaceholderText("Output filename...")
        self.txt_filename.textChanged.connect(self._on_filename_text_changed)
        fn_layout.addWidget(self.txt_filename, 1)

        self.btn_browse = QToolButton()
        self.btn_browse.setFixedSize(34, 34)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setToolTip("Browse export destination...")
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        fn_layout.addWidget(self.btn_browse)

        self.content_layout.addWidget(fn_row)

    def _init_settings_link(self):
        settings_row = QWidget()
        s_layout = QHBoxLayout(settings_row)
        s_layout.setContentsMargins(0, 2, 0, 2)
        s_layout.setSpacing(6)
        s_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.icon_settings = QLabel()
        self.icon_settings.setFixedSize(16, 16)
        s_layout.addWidget(self.icon_settings)

        self.btn_settings = QPushButton("Export settings")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        s_layout.addWidget(self.btn_settings)

        s_layout.addStretch()
        self.content_layout.addWidget(settings_row)

    def _init_cta_footer(self, root_layout: QVBoxLayout):
        self.footer_widget = QWidget()
        self.footer_widget.setObjectName("exportFooterWidget")
        self.footer_widget.setAttribute(Qt.WA_StyledBackground, True)
        footer_layout = QVBoxLayout(self.footer_widget)
        footer_layout.setContentsMargins(18, 10, 18, 16)
        footer_layout.setSpacing(6)

        self.btn_convert_cta = QPushButton("Convert to DOCX")
        self.btn_convert_cta.setFixedHeight(38)
        self.btn_convert_cta.setCursor(Qt.PointingHandCursor)
        self.btn_convert_cta.clicked.connect(self._on_convert_cta_clicked)
        footer_layout.addWidget(self.btn_convert_cta)

        self.lbl_footer_note = QLabel("Your original PDF will stay unchanged.")
        self.lbl_footer_note.setAlignment(Qt.AlignCenter)
        self.lbl_footer_note.setFont(QFont("Inter", 8))
        footer_layout.addWidget(self.lbl_footer_note)

        root_layout.addWidget(self.footer_widget, 0)

    # =========================================================================
    # State & Logic Management
    # =========================================================================

    def set_document_info(self, file_path: str, page_count: int, file_size_bytes: int = 0):
        """Populates source document details and derives output filename."""
        self.source_file_path = file_path
        self.page_count = max(1, page_count)

        if not file_size_bytes and file_path and os.path.exists(file_path):
            try:
                self.file_size_bytes = os.path.getsize(file_path)
            except Exception:
                self.file_size_bytes = 0
        else:
            self.file_size_bytes = file_size_bytes

        # Format file size nicely
        if self.file_size_bytes >= 1024 * 1024:
            size_str = f"{self.file_size_bytes / (1024 * 1024):.1f} MB"
        elif self.file_size_bytes >= 1024:
            size_str = f"{self.file_size_bytes / 1024:.0f} KB"
        else:
            size_str = f"{self.file_size_bytes} B"

        filename = os.path.basename(file_path) if file_path else "Untitled.pdf"
        self.lbl_source_filename.setText(filename)
        pages_label = f"{self.page_count} page" if self.page_count == 1 else f"{self.page_count} pages"
        self.lbl_source_meta.setText(f"{pages_label} • {size_str}")

        # Derive recommended output path
        self._sync_suggested_output_filename()

    def _sync_suggested_output_filename(self):
        """Updates the suggested file path and line edit matching the active format."""
        suggested = suggest_output_path(self.source_file_path, self.current_format_key)
        self.target_output_path = suggested
        self.txt_filename.setText(os.path.basename(suggested))

    def _on_filename_text_changed(self, text: str):
        """Synchronizes target_output_path if user manually changes text."""
        base_dir = os.path.dirname(self.target_output_path) or os.getcwd()
        self.target_output_path = os.path.join(base_dir, text.strip())

    def _on_format_card_clicked(self, format_id: str):
        self.select_format(format_id, emit_signal=True)

    def select_format(self, format_id: str, emit_signal: bool = True):
        """Selects the format card or secondary item and updates button labels."""
        self.current_format_key = format_id.lower()

        # Update primary cards
        for fid, card in self.format_cards.items():
            card.set_selected(fid == self.current_format_key)

        # Update secondary buttons
        for fid, btn in self.secondary_buttons.items():
            btn.set_active(fid == self.current_format_key)

        # Update CTA button label
        if hasattr(self, "btn_convert_cta"):
            ext = get_format_extension(self.current_format_key).upper()
            if self.current_format_key == FORMAT_IMAGE:
                self.btn_convert_cta.setText("Convert to Images")
            else:
                self.btn_convert_cta.setText(f"Convert to {ext}")

        # Update filename extension
        if hasattr(self, "txt_filename"):
            current_text = self.txt_filename.text().strip()
            if current_text:
                stem = os.path.splitext(current_text)[0]
                new_ext = get_format_extension(self.current_format_key)
                self.txt_filename.setText(f"{stem}.{new_ext}")
            else:
                self._sync_suggested_output_filename()

        if emit_signal:
            self.format_changed.emit(self.current_format_key)

    def _toggle_more_formats(self):
        self.is_more_formats_expanded = not self.is_more_formats_expanded
        self.more_container.setVisible(self.is_more_formats_expanded)
        self._update_more_toggle_style()

    def _on_browse_clicked(self):
        """Prompts user to pick target destination using QFileDialog."""
        filter_str = get_format_file_filter(self.current_format_key)
        suggested = self.target_output_path or suggest_output_path(self.source_file_path, self.current_format_key)

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export as {get_format_display_name(self.current_format_key)}",
            suggested,
            filter_str
        )

        if dest_path:
            self.target_output_path = dest_path
            self.txt_filename.setText(os.path.basename(dest_path))

    def _on_convert_cta_clicked(self):
        """
        Primary CTA Handler:
        Prompts user to choose destination via QFileDialog (as required),
        then emits export_requested signal.
        """
        filter_str = get_format_file_filter(self.current_format_key)
        suggested = self.target_output_path or suggest_output_path(self.source_file_path, self.current_format_key)

        # Prompt user to confirm / save file
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {get_format_display_name(self.current_format_key)} As",
            suggested,
            filter_str
        )

        if not dest_path:
            return  # User cancelled dialog

        self.target_output_path = dest_path
        self.txt_filename.setText(os.path.basename(dest_path))

        # Build options dictionary merging custom_settings
        options = {
            "ocr": self.chk_ocr.isChecked(),
            "language": self._get_ocr_language_code(),
            "dpi": self.custom_settings.get("dpi", 150.0),
            "image_format": self.custom_settings.get("image_format", "png" if self.current_format_key == FORMAT_IMAGE else self.current_format_key),
            **self.custom_settings
        }

        self.export_requested.emit(dest_path, self.current_format_key, options)

    def _on_settings_clicked(self):
        """Opens format-specific ExportSettingsDialog."""
        from pyacrobat.ui.export_settings_dialog import ExportSettingsDialog
        from PySide6.QtWidgets import QDialog
        dlg = ExportSettingsDialog(
            initial_format_key=self.current_format_key,
            initial_settings=self.custom_settings,
            parent=self.window()
        )
        if dlg.exec() == QDialog.Accepted:
            self.custom_settings = dlg.get_settings()
        self.settings_requested.emit(self.current_format_key)

    def _get_ocr_language_code(self) -> str:
        lang_text = self.combo_language.currentText()
        mapping = {
            "English (U.S.)": "eng",
            "Spanish": "spa",
            "French": "fra",
            "German": "deu",
            "Italian": "ita",
            "Japanese": "jpn",
            "Chinese (Simplified)": "chi_sim"
        }
        return mapping.get(lang_text, "eng")

    # =========================================================================
    # Adobe Spectrum Theming
    # =========================================================================

    def update_theme(self):
        """Updates styling and icons for active theme (Dark / Light)."""
        is_dark = ThemeManager.is_dark()

        bg_panel = "#252528" if is_dark else "#FFFFFF"
        border_panel = "#383838" if is_dark else "#D9D9D9"
        card_bg = "#1E1E22" if is_dark else "#F8F8F8"
        text_primary = "#FFFFFF" if is_dark else "#242424"
        text_muted = "#9E9E9E" if is_dark else "#626262"
        input_bg = "#1E1E1E" if is_dark else "#FFFFFF"
        input_border = "#444444" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            ExportPdfPanel, #exportPanelContent {{
                background-color: {bg_panel};
            }}
            ExportPdfPanel {{
                border-right: 1px solid {border_panel};
            }}
            #exportPanelScrollArea, #exportPanelScrollArea > QWidget > QWidget {{
                background-color: {bg_panel};
                border: none;
            }}
            #exportFooterWidget {{
                background-color: {bg_panel};
                border-top: 1px solid {border_panel};
            }}
        """)

        # Headers & labels
        self.lbl_title.setStyleSheet(f"color: {text_primary};")
        self.lbl_subtitle.setStyleSheet(f"color: {text_muted};")
        self.lbl_convert_to.setStyleSheet(f"color: {text_primary};")
        self.lbl_language.setStyleSheet(f"color: {text_primary};")
        self.lbl_filename.setStyleSheet(f"color: {text_primary};")
        self.lbl_footer_note.setStyleSheet(f"color: {text_muted};")

        # Source file card
        self.source_card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border-radius: 4px;
                border: 1px solid {border_panel};
            }}
        """)
        self.lbl_source_filename.setStyleSheet(f"color: {text_primary}; background: transparent;")
        self.lbl_source_meta.setStyleSheet(f"color: {text_muted}; background: transparent;")

        # Close button ('X')
        close_icon = load_themed_svg("close-x", "#D0D0D0" if is_dark else "#626262")
        self.btn_close.setIcon(renderer_to_icon(close_icon, 16))
        self.btn_close.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.12)' if is_dark else 'rgba(0, 0, 0, 0.08)'};
            }}
        """)

        # Source file icon
        source_icon = load_themed_svg("file-text", "#4BA3FF" if is_dark else "#1473E6")
        self._set_label_svg(self.icon_source_file, source_icon, 20, 20)

        # Settings icon & link
        settings_icon = load_themed_svg("settings-2", "#4BA3FF" if is_dark else "#1473E6")
        self._set_label_svg(self.icon_settings, settings_icon, 16, 16)
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {'#4BA3FF' if is_dark else '#1473E6'};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 500;
                border: none;
                text-align: left;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {'#75B8FF' if is_dark else '#0D66D0'};
                text-decoration: underline;
            }}
        """)

        # Divider
        self.divider.setStyleSheet(f"background-color: {border_panel}; border: none;")

        # Language dropdown
        self.combo_language.setStyleSheet(f"""
            QComboBox {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding-left: 10px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_panel};
                color: {text_primary};
                selection-background-color: {'#1473E6'};
                selection-color: #FFFFFF;
                border: 1px solid {input_border};
            }}
        """)

        # Checkbox OCR
        self.chk_ocr.setStyleSheet(f"""
            QCheckBox {{
                color: {text_primary};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                border: 1px solid {input_border};
                border-radius: 3px;
                background-color: {input_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: #1473E6;
                border-color: #1473E6;
                image: none;
            }}
        """)

        # Filename input and Browse button
        self.txt_filename.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 0px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid #1473E6;
            }}
        """)

        folder_icon = load_themed_svg("folder", "#A0A0A0" if is_dark else "#626262")
        self.btn_browse.setIcon(renderer_to_icon(folder_icon, 18))
        self.btn_browse.setStyleSheet(f"""
            QToolButton {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {'#303035' if is_dark else '#EAEAEA'};
            }}
        """)

        # Primary CTA button
        self.btn_convert_cta.setStyleSheet(f"""
            QPushButton {{
                background-color: #1473E6;
                color: #FFFFFF;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: #0D66D0;
            }}
            QPushButton:pressed {{
                background-color: #095ABA;
            }}
        """)

        self._update_more_toggle_style()

        # Update child cards
        for card in self.format_cards.values():
            card.update_theme()
        for btn in self.secondary_buttons.values():
            btn.update_theme()

    def _update_more_toggle_style(self):
        is_dark = ThemeManager.is_dark()
        chevron = "▲" if self.is_more_formats_expanded else "▼"
        color = "#4BA3FF" if is_dark else "#1473E6"
        self.btn_more_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 500;
                border: none;
                text-align: left;
                padding-left: 2px;
            }}
            QPushButton:hover {{
                color: {'#75B8FF' if is_dark else '#0D66D0'};
            }}
        """)
        self.btn_more_toggle.setText(f"More formats  {chevron}")

    def _set_label_svg(self, label: QLabel, renderer: Optional[QSvgRenderer], w: int, h: int):
        if renderer and renderer.isValid():
            from PySide6.QtGui import QPixmap
            pix = QPixmap(w * 2, h * 2)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            renderer.render(painter)
            painter.end()
            label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            label.clear()
