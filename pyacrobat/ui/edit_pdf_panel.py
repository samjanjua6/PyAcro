"""
Edit PDF Left Tool Drawer Component (Figma Acrobat Alignment)
Implements Figma node 3:13204:
- Fixed 284px width panel on the left of the document viewport
- Header: 'Edit a PDF' (18px SemiBold) + Close button (X) + Subtitle 'Select text or an image to edit it.'
- Add content tools: Text (toggle), Image, Link
- Section: 'FORMAT TEXT'
  * Font family selector (Inter / system fonts)
  * Font style ('Regular', 'Bold', 'Italic') & Font size ('11' etc.)
  * Character formatting: Bold, Italic, Underline, Strikethrough, Text color picker
  * Paragraph alignment: Left, Center, Right, Justify, Bullet list, Numbered list
  * Spacing: Line spacing, Character spacing
  * Checkbox: 'Show bounding boxes' (checked by default)
- Section: 'OTHER OPTIONS'
  * Header & footer (panel-top.svg)
  * Watermark (droplets.svg)
  * Crop pages (crop.svg)
- Supports full Light & Dark Adobe Spectrum theming.
"""

import os
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QScrollArea, QFrame, QPushButton, QComboBox, QCheckBox,
    QSizePolicy, QColorDialog, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.core.pdf_editor import FontStyle


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    """Loads SVG and replaces stroke color dynamically for crisp high-DPI rendering."""
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


class EditToolButton(QPushButton):
    """
    Figma-styled action row button (42px height) used for:
    Text, Image, Link, Header & Footer, Watermark, Crop pages.
    """

    def __init__(self, tool_id: str, label: str, icon_name: str, checkable: bool = False, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.label_text = label
        self.icon_name = icon_name
        self.is_active = False
        self.renderer: Optional[QSvgRenderer] = None

        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(checkable)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.update_theme()

    def set_active(self, active: bool):
        self.is_active = active
        self.setChecked(active)
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_active or self.isChecked():
            bg_color = "#102A45" if is_dark else "#EAF3FF"
            text_color = "#4BA3FF" if is_dark else "#1473E6"
            icon_color = "#4BA3FF" if is_dark else "#1473E6"
            font_weight = "600"
        else:
            bg_color = "transparent"
            text_color = "#E0E0E0" if is_dark else "#242424"
            icon_color = "#B0B0B0" if is_dark else "#626262"
            font_weight = "400"

        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"

        self.renderer = load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: {font_weight};
                text-align: left;
                padding-left: 42px;
                padding-right: 12px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg if not (self.is_active or self.isChecked()) else bg_color};
            }}
        """)
        self.setText(self.label_text)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 20
            x = 12.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class FormatIconButton(QToolButton):
    """
    30x30px square formatting icon button (Bold, Italic, Align, etc.).
    Figma spec: border-radius 4px, hover background, active accent.
    """

    def __init__(self, icon_name: str, checkable: bool = True, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(checkable)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.isChecked():
            bg_color = "#102A45" if is_dark else "#EAF3FF"
            icon_color = "#4BA3FF" if is_dark else "#1473E6"
        else:
            bg_color = "transparent"
            icon_color = "#CCCCCC" if is_dark else "#505050"

        hover_bg = "rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.06)"

        self.renderer = load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_color};
                border: 1px solid {'#3A3A3A' if is_dark else '#D9D9D9'};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg if not self.isChecked() else bg_color};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 16
            x = (self.width() - icon_size) / 2.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class TextColorPickerButton(QToolButton):
    """
    Color picker tool button: Shows letter 'A' with color swatch bar underneath (18x3px).
    Clicking it opens QColorDialog.
    """

    color_changed = Signal(QColor)

    def __init__(self, initial_color: QColor = QColor("#203C42"), parent=None):
        super().__init__(parent)
        self.current_color = initial_color
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._choose_color)
        self.update_theme()

    def set_color(self, color: QColor):
        self.current_color = color
        self.update()

    def _choose_color(self):
        chosen = QColorDialog.getColor(self.current_color, self, "Select Text Color")
        if chosen.isValid():
            self.current_color = chosen
            self.update()
            self.color_changed.emit(chosen)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        border_color = "#3A3A3A" if is_dark else "#D9D9D9"
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {'rgba(255,255,255,0.08)' if is_dark else 'rgba(0,0,0,0.05)'};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = ThemeManager.is_dark()
        text_color = QColor("#FFFFFF") if is_dark else QColor("#242424")

        # Draw 'A'
        painter.setPen(text_color)
        font = QFont("Inter", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 2, self.width(), 16), Qt.AlignCenter, "A")

        # Draw Color Swatch bar underneath
        swatch_w, swatch_h = 18, 3
        swatch_x = (self.width() - swatch_w) / 2
        swatch_y = self.height() - swatch_h - 4
        painter.fillRect(QRectF(swatch_x, swatch_y, swatch_w, swatch_h), self.current_color)

        painter.end()


class EditPdfPanel(QWidget):
    """
    284px Collapsible Left 'Edit a PDF' Workstation Panel.
    Fully synchronized with document text and canvas selection state.
    """

    close_requested = Signal()
    tool_selected = Signal(str)                  # 'text', 'image', 'link'
    font_style_changed = Signal(object)          # FontStyle instance
    bounding_boxes_toggled = Signal(bool)

    # Action signals
    header_footer_requested = Signal()
    watermark_requested = Signal()
    crop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(284)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.current_font_style = FontStyle()
        self.show_bounding_boxes = True
        self._block_signals = False

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for comfortable layout on any window height
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 22, 20, 24)
        self.content_layout.setSpacing(14)

        # 1. Header: Title + Close Button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Edit a PDF", self.content_widget)
        self.title_label.setFont(QFont("Inter", 13, QFont.DemiBold))

        self.btn_close = FormatIconButton("close-x", checkable=False, parent=self.content_widget)
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.clicked.connect(self.close_requested.emit)

        header_row.addWidget(self.title_label)
        header_row.addStretch()
        header_row.addWidget(self.btn_close)
        self.content_layout.addLayout(header_row)

        # Subtitle
        self.subtitle_label = QLabel("Select text or an image to edit it.", self.content_widget)
        self.subtitle_label.setFont(QFont("Inter", 9))
        self.subtitle_label.setWordWrap(True)
        self.content_layout.addWidget(self.subtitle_label)

        # 2. Add Content Tools Strip
        self.add_tools_layout = QVBoxLayout()
        self.add_tools_layout.setContentsMargins(0, 4, 0, 4)
        self.add_tools_layout.setSpacing(2)

        self.btn_tool_text = EditToolButton("text", "Text", "text-cursor-input", checkable=True, parent=self.content_widget)
        self.btn_tool_text.clicked.connect(lambda: self._on_tool_clicked("text"))

        self.btn_tool_image = EditToolButton("image", "Image", "image-plus", checkable=False, parent=self.content_widget)
        self.btn_tool_image.clicked.connect(lambda: self._on_tool_clicked("image"))

        self.btn_tool_link = EditToolButton("link", "Link", "link", checkable=False, parent=self.content_widget)
        self.btn_tool_link.clicked.connect(lambda: self._on_tool_clicked("link"))

        self.add_tools_layout.addWidget(self.btn_tool_text)
        self.add_tools_layout.addWidget(self.btn_tool_image)
        self.add_tools_layout.addWidget(self.btn_tool_link)
        self.content_layout.addLayout(self.add_tools_layout)

        # Divider
        self.divider1 = self._create_divider()
        self.content_layout.addWidget(self.divider1)

        # 3. FORMAT TEXT Section Heading
        self.format_title = QLabel("FORMAT TEXT", self.content_widget)
        self.format_title.setFont(QFont("Inter", 9, QFont.Bold))
        self.content_layout.addWidget(self.format_title)

        # Font Family Dropdown
        self.combo_font_family = QComboBox(self.content_widget)
        self.combo_font_family.setFixedHeight(34)
        self.combo_font_family.addItems([
            "Inter", "Helvetica", "Arial", "Times New Roman", "Courier New", "Georgia", "Segoe UI"
        ])
        self.combo_font_family.currentTextChanged.connect(self._on_format_changed)
        self.content_layout.addWidget(self.combo_font_family)

        # Font Style & Font Size Row
        style_size_row = QHBoxLayout()
        style_size_row.setSpacing(10)

        self.combo_font_style = QComboBox(self.content_widget)
        self.combo_font_style.setFixedHeight(34)
        self.combo_font_style.addItems(["Regular", "Bold", "Italic", "Bold Italic"])
        self.combo_font_style.currentTextChanged.connect(self._on_font_style_dropdown_changed)

        self.combo_font_size = QComboBox(self.content_widget)
        self.combo_font_size.setFixedHeight(34)
        self.combo_font_size.setFixedWidth(75)
        self.combo_font_size.setEditable(True)
        self.combo_font_size.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "32", "36", "48", "72"])
        self.combo_font_size.setCurrentText("11")
        self.combo_font_size.currentTextChanged.connect(self._on_format_changed)

        style_size_row.addWidget(self.combo_font_style, stretch=1)
        style_size_row.addWidget(self.combo_font_size, stretch=0)
        self.content_layout.addLayout(style_size_row)

        # Character Formatting Row (B, I, U, S, Color)
        char_row = QHBoxLayout()
        char_row.setSpacing(6)
        char_row.setAlignment(Qt.AlignLeft)

        self.btn_bold = FormatIconButton("bold", checkable=True, parent=self.content_widget)
        self.btn_bold.clicked.connect(self._on_format_changed)

        self.btn_italic = FormatIconButton("italic", checkable=True, parent=self.content_widget)
        self.btn_italic.clicked.connect(self._on_format_changed)

        self.btn_underline = FormatIconButton("underline", checkable=True, parent=self.content_widget)
        self.btn_underline.clicked.connect(self._on_format_changed)

        self.btn_strike = FormatIconButton("strikethrough", checkable=True, parent=self.content_widget)
        self.btn_strike.clicked.connect(self._on_format_changed)

        self.btn_color = TextColorPickerButton(initial_color=QColor("#203C42"), parent=self.content_widget)
        self.btn_color.color_changed.connect(self._on_color_selected)

        char_row.addWidget(self.btn_bold)
        char_row.addWidget(self.btn_italic)
        char_row.addWidget(self.btn_underline)
        char_row.addWidget(self.btn_strike)
        char_row.addWidget(self.btn_color)
        self.content_layout.addLayout(char_row)

        # Paragraph Alignment Row (Left, Center, Right, Justify, Bullet, Numbered)
        align_row = QHBoxLayout()
        align_row.setSpacing(6)
        align_row.setAlignment(Qt.AlignLeft)

        self.align_group = QButtonGroup(self)
        self.align_group.setExclusive(True)

        self.btn_align_left = FormatIconButton("align-left", checkable=True, parent=self.content_widget)
        self.btn_align_center = FormatIconButton("align-center", checkable=True, parent=self.content_widget)
        self.btn_align_right = FormatIconButton("align-right", checkable=True, parent=self.content_widget)
        self.btn_align_justify = FormatIconButton("align-justify", checkable=True, parent=self.content_widget)

        self.align_group.addButton(self.btn_align_left, 0)
        self.align_group.addButton(self.btn_align_center, 1)
        self.align_group.addButton(self.btn_align_right, 2)
        self.align_group.addButton(self.btn_align_justify, 3)

        self.btn_align_left.setChecked(True)
        self.align_group.idClicked.connect(self._on_align_group_clicked)

        self.btn_bullet = FormatIconButton("list", checkable=True, parent=self.content_widget)
        self.btn_numbered = FormatIconButton("list-ordered", checkable=True, parent=self.content_widget)

        align_row.addWidget(self.btn_align_left)
        align_row.addWidget(self.btn_align_center)
        align_row.addWidget(self.btn_align_right)
        align_row.addWidget(self.btn_align_justify)
        align_row.addWidget(self.btn_bullet)
        align_row.addWidget(self.btn_numbered)
        self.content_layout.addLayout(align_row)

        # Spacing Row (Line Spacing, Character Spacing)
        spacing_row = QHBoxLayout()
        spacing_row.setSpacing(10)

        # Line spacing
        ls_col = QVBoxLayout()
        ls_col.setSpacing(4)
        self.lbl_ls = QLabel("Line spacing", self.content_widget)
        self.lbl_ls.setFont(QFont("Inter", 8, QFont.DemiBold))
        self.combo_line_spacing = QComboBox(self.content_widget)
        self.combo_line_spacing.setFixedHeight(34)
        self.combo_line_spacing.addItems(["1.0", "1.15", "1.2", "1.55", "2.0"])
        self.combo_line_spacing.setCurrentText("1.55")
        self.combo_line_spacing.currentTextChanged.connect(self._on_format_changed)
        ls_col.addWidget(self.lbl_ls)
        ls_col.addWidget(self.combo_line_spacing)

        # Character spacing
        cs_col = QVBoxLayout()
        cs_col.setSpacing(4)
        self.lbl_cs = QLabel("Character spacing", self.content_widget)
        self.lbl_cs.setFont(QFont("Inter", 8, QFont.DemiBold))
        self.combo_char_spacing = QComboBox(self.content_widget)
        self.combo_char_spacing.setFixedHeight(34)
        self.combo_char_spacing.addItems(["-1", "0", "1", "2", "3"])
        self.combo_char_spacing.setCurrentText("0")
        self.combo_char_spacing.currentTextChanged.connect(self._on_format_changed)
        cs_col.addWidget(self.lbl_cs)
        cs_col.addWidget(self.combo_char_spacing)

        spacing_row.addLayout(ls_col, stretch=1)
        spacing_row.addLayout(cs_col, stretch=1)
        self.content_layout.addLayout(spacing_row)

        # Checkbox Option: 'Show bounding boxes'
        self.chk_bounding_boxes = QCheckBox("Show bounding boxes", self.content_widget)
        self.chk_bounding_boxes.setFont(QFont("Inter", 9))
        self.chk_bounding_boxes.setChecked(True)
        self.chk_bounding_boxes.setCursor(Qt.PointingHandCursor)
        self.chk_bounding_boxes.toggled.connect(self._on_bounding_boxes_toggled)
        self.content_layout.addWidget(self.chk_bounding_boxes)

        # Divider
        self.divider2 = self._create_divider()
        self.content_layout.addWidget(self.divider2)

        # 4. OTHER OPTIONS Section
        self.other_title = QLabel("OTHER OPTIONS", self.content_widget)
        self.other_title.setFont(QFont("Inter", 9, QFont.Bold))
        self.content_layout.addWidget(self.other_title)

        self.btn_header_footer = EditToolButton("hf", "Header && footer", "panel-top", parent=self.content_widget)
        self.btn_header_footer.clicked.connect(self.header_footer_requested.emit)

        self.btn_watermark = EditToolButton("watermark", "Watermark", "droplets", parent=self.content_widget)
        self.btn_watermark.clicked.connect(self.watermark_requested.emit)

        self.btn_crop = EditToolButton("crop", "Crop pages", "crop", parent=self.content_widget)
        self.btn_crop.clicked.connect(self.crop_requested.emit)

        self.content_layout.addWidget(self.btn_header_footer)
        self.content_layout.addWidget(self.btn_watermark)
        self.content_layout.addWidget(self.btn_crop)

        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

    def _create_divider(self) -> QFrame:
        div = QFrame(self.content_widget)
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        return div

    def _on_tool_clicked(self, tool_id: str):
        if tool_id == "text":
            is_active = self.btn_tool_text.isChecked()
            self.btn_tool_text.set_active(is_active)
            self.tool_selected.emit("text" if is_active else "select")
        else:
            self.tool_selected.emit(tool_id)

    def _on_align_group_clicked(self, btn_id: int):
        self._on_format_changed()

    def _on_color_selected(self, qcolor: QColor):
        self._on_format_changed()

    def _on_font_style_dropdown_changed(self, text: str):
        if self._block_signals:
            return
        self._block_signals = True
        try:
            is_bold = "Bold" in text
            is_italic = "Italic" in text
            self.btn_bold.setChecked(is_bold)
            self.btn_italic.setChecked(is_italic)
            self.btn_bold.update_theme()
            self.btn_italic.update_theme()
        finally:
            self._block_signals = False
        self._on_format_changed()

    def _on_bounding_boxes_toggled(self, checked: bool):
        self.show_bounding_boxes = checked
        self.bounding_boxes_toggled.emit(checked)

    def _on_format_changed(self):
        if self._block_signals:
            return

        font_name = self.combo_font_family.currentText()
        try:
            font_size = float(self.combo_font_size.currentText())
        except ValueError:
            font_size = 11.0

        is_bold = self.btn_bold.isChecked()
        is_italic = self.btn_italic.isChecked()
        is_underline = self.btn_underline.isChecked()
        is_strike = self.btn_strike.isChecked()

        qc = self.btn_color.current_color
        color_rgb = (qc.redF(), qc.greenF(), qc.blueF())

        alignment = self.align_group.checkedId()
        if alignment < 0:
            alignment = 0

        try:
            line_spacing = float(self.combo_line_spacing.currentText())
        except ValueError:
            line_spacing = 1.2

        try:
            char_spacing = float(self.combo_char_spacing.currentText())
        except ValueError:
            char_spacing = 0.0

        self.current_font_style = FontStyle(
            font_name=font_name,
            font_size=font_size,
            color_rgb=color_rgb,
            is_bold=is_bold,
            is_italic=is_italic,
            is_underline=is_underline,
            is_strike=is_strike,
            line_spacing=line_spacing,
            char_spacing=char_spacing,
            alignment=alignment
        )
        self.font_style_changed.emit(self.current_font_style)

    def set_font_style(self, style: FontStyle):
        """Synchronizes UI controls with an active selected block's FontStyle."""
        self._block_signals = True
        try:
            self.current_font_style = style
            idx = self.combo_font_family.findText(style.font_name)
            if idx >= 0:
                self.combo_font_family.setCurrentIndex(idx)

            self.combo_font_size.setCurrentText(str(int(style.font_size) if style.font_size.is_integer() else style.font_size))

            self.btn_bold.setChecked(style.is_bold)
            self.btn_italic.setChecked(style.is_italic)
            self.btn_underline.setChecked(style.is_underline)
            self.btn_strike.setChecked(style.is_strike)

            # Style dropdown text sync
            if style.is_bold and style.is_italic:
                self.combo_font_style.setCurrentText("Bold Italic")
            elif style.is_bold:
                self.combo_font_style.setCurrentText("Bold")
            elif style.is_italic:
                self.combo_font_style.setCurrentText("Italic")
            else:
                self.combo_font_style.setCurrentText("Regular")

            # Color
            qc = QColor(
                int(style.color_rgb[0] * 255),
                int(style.color_rgb[1] * 255),
                int(style.color_rgb[2] * 255)
            )
            self.btn_color.set_color(qc)

            # Alignment
            btn = self.align_group.button(style.alignment)
            if btn:
                btn.setChecked(True)

            self.btn_bold.update_theme()
            self.btn_italic.update_theme()
            self.btn_underline.update_theme()
            self.btn_strike.update_theme()
            self.btn_align_left.update_theme()
            self.btn_align_center.update_theme()
            self.btn_align_right.update_theme()
            self.btn_align_justify.update_theme()
        finally:
            self._block_signals = False

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_panel = "#242424" if is_dark else "#FFFFFF"
        border_right = "#333333" if is_dark else "#D9D9D9"
        text_primary = "#FFFFFF" if is_dark else "#242424"
        text_secondary = "#9E9E9E" if is_dark else "#626262"
        divider_color = "#333333" if is_dark else "#D9D9D9"
        combo_bg = "#2D2D2D" if is_dark else "#FFFFFF"
        combo_border = "#3A3A3A" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            QWidget#editPdfPanelContent {{
                background-color: {bg_panel};
            }}
            QScrollArea {{
                background-color: {bg_panel};
                border: none;
                border-right: 1px solid {border_right};
            }}
            QComboBox {{
                background-color: {combo_bg};
                color: {text_primary};
                border: 1px solid {combo_border};
                border-radius: 4px;
                padding-left: 10px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: #1473E6;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_bg};
                color: {text_primary};
                selection-background-color: #1473E6;
                selection-color: #FFFFFF;
                border: 1px solid {combo_border};
            }}
            QCheckBox {{
                color: {text_primary};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                border-radius: 3px;
                border: 1px solid {combo_border};
                background-color: {combo_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: #1473E6;
                border-color: #1473E6;
                image: url({os.path.join(ICONS_DIR, 'check.svg').replace(os.sep, '/')});
            }}
        """)

        self.content_widget.setObjectName("editPdfPanelContent")
        self.title_label.setStyleSheet(f"color: {text_primary};")
        self.subtitle_label.setStyleSheet(f"color: {text_secondary};")
        self.format_title.setStyleSheet(f"color: {text_primary};")
        self.other_title.setStyleSheet(f"color: {text_primary};")
        self.lbl_ls.setStyleSheet(f"color: {text_primary};")
        self.lbl_cs.setStyleSheet(f"color: {text_primary};")

        self.divider1.setStyleSheet(f"background-color: {divider_color};")
        self.divider2.setStyleSheet(f"background-color: {divider_color};")

        # Update close button
        self.btn_close.update_theme()

        # Update sub-widgets
        for btn in (
            self.btn_tool_text, self.btn_tool_image, self.btn_tool_link,
            self.btn_header_footer, self.btn_watermark, self.btn_crop
        ):
            btn.update_theme()

        for btn in (
            self.btn_bold, self.btn_italic, self.btn_underline, self.btn_strike,
            self.btn_align_left, self.btn_align_center, self.btn_align_right,
            self.btn_align_justify, self.btn_bullet, self.btn_numbered
        ):
            btn.update_theme()

        self.btn_color.update_theme()
        self.update()
