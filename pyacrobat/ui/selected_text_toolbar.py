"""
Floating Selected Text Toolbar Component (Figma Acrobat Alignment)
Implements Figma node 3:13348:
- Fixed 322px width, 38px height, 6px border radius
- Elevation drop-shadow: 0px 3px 12px rgba(0, 0, 0, 0.13)
- Left: Font family dropdown/label ('Inter' + chevron-down)
- Separator: 1px x 20px (#D9D9D9)
- Center-left: Font size dropdown ('11' + chevron-down)
- Actions: Bold, Italic, Underline toggle icon buttons
- Text color swatch rectangle (16x16px) with QColorDialog trigger
- More options ellipsis button (...)
- Clamped positioning logic to float directly above selected text blocks.
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QFrame,
    QGraphicsDropShadowEffect, QComboBox, QColorDialog, QMenu
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.core.pdf_editor import FontStyle


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
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


class QuickFormatButton(QToolButton):
    """26x26px icon button within the floating text toolbar."""

    def __init__(self, icon_name: str, checkable: bool = True, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(26, 26)
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

        hover_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.06)"
        self.renderer = load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 3px;
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
            icon_size = 15
            x = (self.width() - icon_size) / 2.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class ColorSwatchButton(QToolButton):
    """16x16px clickable color swatch square matching Figma #3:13357."""

    color_changed = Signal(QColor)

    def __init__(self, initial_color: QColor = QColor("#203C42"), parent=None):
        super().__init__(parent)
        self.current_color = initial_color
        self.setFixedSize(16, 16)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self.update_theme()

    def set_color(self, color: QColor):
        self.current_color = color
        self.update()

    def _pick_color(self):
        chosen = QColorDialog.getColor(self.current_color, self, "Text Color")
        if chosen.isValid():
            self.current_color = chosen
            self.color_changed.emit(chosen)
            self.update()

    def update_theme(self):
        self.setStyleSheet("QToolButton { background: transparent; border: none; }")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(QRectF(0, 0, 16, 16), self.current_color)
        painter.setPen(QPen(QColor(0, 0, 0, 50), 1))
        painter.drawRoundedRect(QRectF(0.5, 0.5, 15, 15), 2.0, 2.0)
        painter.end()


class SelectedTextToolbar(QWidget):
    """
    322px Floating Quick Formatting Toolbar.
    Hovers above or near the active text block.
    """

    font_style_changed = Signal(object)  # FontStyle instance
    more_options_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(322, 38)
        self.current_font_style = FontStyle()
        self._block_signals = False

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        # Drop shadow matching Figma: 0px 3px 12px rgba(0, 0, 0, 0.13)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 33))  # 0.13 * 255 ≈ 33
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignVCenter)

        # 1. Font Family Dropdown
        self.combo_font = QComboBox(self)
        self.combo_font.setFixedSize(92, 28)
        self.combo_font.addItems(["Inter", "Helvetica", "Arial", "Times", "Courier", "Georgia"])
        self.combo_font.currentTextChanged.connect(self._on_controls_changed)
        layout.addWidget(self.combo_font)

        # 2. Separator line
        self.sep = QFrame(self)
        self.sep.setFrameShape(QFrame.VLine)
        self.sep.setFixedSize(1, 20)
        layout.addWidget(self.sep)

        # 3. Font Size Dropdown
        self.combo_size = QComboBox(self)
        self.combo_size.setFixedSize(54, 28)
        self.combo_size.setEditable(True)
        self.combo_size.addItems(["9", "10", "11", "12", "14", "18", "24", "36"])
        self.combo_size.setCurrentText("11")
        self.combo_size.currentTextChanged.connect(self._on_controls_changed)
        layout.addWidget(self.combo_size)

        # 4. Bold, Italic, Underline
        self.btn_bold = QuickFormatButton("bold", checkable=True, parent=self)
        self.btn_bold.clicked.connect(self._on_controls_changed)
        layout.addWidget(self.btn_bold)

        self.btn_italic = QuickFormatButton("italic", checkable=True, parent=self)
        self.btn_italic.clicked.connect(self._on_controls_changed)
        layout.addWidget(self.btn_italic)

        self.btn_underline = QuickFormatButton("underline", checkable=True, parent=self)
        self.btn_underline.clicked.connect(self._on_controls_changed)
        layout.addWidget(self.btn_underline)

        # 5. Color Swatch
        self.btn_color = ColorSwatchButton(initial_color=QColor("#203C42"), parent=self)
        self.btn_color.color_changed.connect(self._on_color_changed)
        layout.addWidget(self.btn_color)

        # 6. More Options (...)
        self.btn_more = QuickFormatButton("ellipsis", checkable=False, parent=self)
        self.btn_more.clicked.connect(self.more_options_requested.emit)
        layout.addWidget(self.btn_more)

    def _on_controls_changed(self):
        if self._block_signals:
            return

        font_name = self.combo_font.currentText()
        try:
            font_size = float(self.combo_size.currentText())
        except ValueError:
            font_size = 11.0

        is_bold = self.btn_bold.isChecked()
        is_italic = self.btn_italic.isChecked()
        is_underline = self.btn_underline.isChecked()

        qc = self.btn_color.current_color
        color_rgb = (qc.redF(), qc.greenF(), qc.blueF())

        self.current_font_style.font_name = font_name
        self.current_font_style.font_size = font_size
        self.current_font_style.is_bold = is_bold
        self.current_font_style.is_italic = is_italic
        self.current_font_style.is_underline = is_underline
        self.current_font_style.color_rgb = color_rgb

        self.font_style_changed.emit(self.current_font_style)

    def _on_color_changed(self, color: QColor):
        if self._block_signals:
            return
        self.current_font_style.color_rgb = (color.redF(), color.greenF(), color.blueF())
        self.font_style_changed.emit(self.current_font_style)

    def set_font_style(self, style: FontStyle):
        """Synchronizes floating pill with active FontStyle."""
        self._block_signals = True
        try:
            self.current_font_style = style

            idx = self.combo_font.findText(style.font_name)
            if idx >= 0:
                self.combo_font.setCurrentIndex(idx)

            self.combo_size.setCurrentText(str(int(style.font_size) if style.font_size.is_integer() else style.font_size))

            self.btn_bold.setChecked(style.is_bold)
            self.btn_italic.setChecked(style.is_italic)
            self.btn_underline.setChecked(style.is_underline)

            qc = QColor(
                int(style.color_rgb[0] * 255),
                int(style.color_rgb[1] * 255),
                int(style.color_rgb[2] * 255)
            )
            self.btn_color.set_color(qc)

            self.btn_bold.update_theme()
            self.btn_italic.update_theme()
            self.btn_underline.update_theme()
        finally:
            self._block_signals = False

    def position_over_screen_rect(self, block_screen_rect: QRectF, container_rect: QRectF):
        """
        Calculates optimal floating position directly above the block.
        If near top edge, flips to position directly below the block.
        Clamps horizontally within the container.
        """
        toolbar_w = self.width()
        toolbar_h = self.height()

        # Center horizontally over the block
        x = block_screen_rect.center().x() - (toolbar_w / 2.0)
        # Clamp within container width margins
        margin_x = 16.0
        x = max(margin_x, min(container_rect.width() - toolbar_w - margin_x, x))

        # Position above block (-46px = 38px toolbar height + 8px gap)
        y = block_screen_rect.top() - toolbar_h - 8.0
        if y < 8.0:
            # Not enough room above -> place 8px below block
            y = block_screen_rect.bottom() + 8.0

        self.move(int(round(x)), int(round(y)))
        self.raise_()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_color = "#252525" if is_dark else "#FFFFFF"
        border_color = "#3A3A3A" if is_dark else "#E0E0E0"
        sep_color = "#3A3A3A" if is_dark else "#D9D9D9"
        text_color = "#FFFFFF" if is_dark else "#242424"
        combo_bg = "#2D2D2D" if is_dark else "#F8F8F8"

        self.setStyleSheet(f"""
            SelectedTextToolbar {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QComboBox {{
                background-color: {combo_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding-left: 6px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border-color: #1473E6;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_bg};
                color: {text_color};
                selection-background-color: #1473E6;
                selection-color: #FFFFFF;
                border: 1px solid {border_color};
            }}
        """)

        self.sep.setStyleSheet(f"background-color: {sep_color};")
        self.btn_bold.update_theme()
        self.btn_italic.update_theme()
        self.btn_underline.update_theme()
        self.btn_more.update_theme()
        self.btn_color.update_theme()
        self.update()
