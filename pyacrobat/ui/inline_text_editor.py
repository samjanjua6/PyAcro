"""
Inline Live Text Editor & Editing Tip Banner Components (Figma Acrobat Alignment)
Implements:
1. InlineTextEditor: Seamless in-place overlay editor mapped directly over PDF bounding boxes.
2. EditingTipBanner: Figma node 3:13359 toast banner:
   "Click any text to edit. Changes are saved automatically."
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QTextEdit, QFrame, QHBoxLayout, QLabel, QWidget
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray, QPointF
from PySide6.QtGui import QFont, QColor, QKeyEvent, QFocusEvent, QPainter
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


class InlineTextEditor(QTextEdit):
    """
    Seamless in-place text editor overlaid directly on top of the PDF page card.
    Matches typography and geometry of the targeted content block.
    """

    editing_committed = Signal(str)   # emits new_text
    editing_canceled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_committing = False
        self.orig_text = ""
        self.setObjectName("inlineTextEditor")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTabChangesFocus(True)
        self.update_theme()

    def start_editing(self, text: str, font_style: FontStyle, scale: float):
        """Initializes typography and content for editing."""
        self._is_committing = False
        self.orig_text = text
        self.setPlainText(text)

        # Calculate visual font size scaled by zoom
        scaled_size = max(8, int(round(font_style.font_size * scale)))
        qf = QFont(font_style.font_name, scaled_size)
        if font_style.is_bold:
            qf.setBold(True)
        if font_style.is_italic:
            qf.setItalic(True)
        self.setFont(qf)

        # Match text color
        r = int(font_style.color_rgb[0] * 255)
        g = int(font_style.color_rgb[1] * 255)
        b = int(font_style.color_rgb[2] * 255)
        text_color_hex = f"#{r:02X}{g:02X}{b:02X}"

        is_dark = ThemeManager.is_dark()
        bg_hex = "#252525" if is_dark else "#FFFFFF"

        self.setStyleSheet(f"""
            QTextEdit#inlineTextEditor {{
                background-color: {bg_hex};
                color: {text_color_hex};
                border: 1.5px solid #1473E6;
                border-radius: 2px;
                padding: 2px 4px;
            }}
        """)

        self.show()
        self.raise_()
        self.setFocus()
        self.selectAll()

    def commit(self):
        """Commits changes and signals completion."""
        if self._is_committing:
            return
        self._is_committing = True
        new_text = self.toPlainText()
        self.hide()
        self.editing_committed.emit(new_text)

    def cancel(self):
        """Cancels changes without modifying the document."""
        self._is_committing = True
        self.hide()
        self.editing_canceled.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.cancel()
            event.accept()
            return
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
            self.commit()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        if not self._is_committing and self.isVisible():
            self.commit()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#252525" if is_dark else "#FFFFFF"
        fg = "#FFFFFF" if is_dark else "#242424"
        self.setStyleSheet(f"""
            QTextEdit#inlineTextEditor {{
                background-color: {bg};
                color: {fg};
                border: 1.5px solid #1473E6;
                border-radius: 2px;
                padding: 2px 4px;
            }}
        """)


class EditingTipBanner(QFrame):
    """
    Bottom Tip Banner matching Figma #3:13359:
    Info icon + 'Click any text to edit. Changes are saved automatically.'
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.renderer: Optional[QSvgRenderer] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 12, 0)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignVCenter)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(16, 16)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel("Click any text to edit. Changes are saved automatically.", self)
        self.text_label.setFont(QFont("Inter", 10))
        layout.addWidget(self.text_label)

        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg_color = "rgba(35, 35, 35, 0.88)" if is_dark else "rgba(245, 245, 247, 0.92)"
        border_color = "#3A3A3A" if is_dark else "#D9D9D9"
        text_color = "#A0A0A0" if is_dark else "#626262"
        icon_color = "#A0A0A0" if is_dark else "#626262"

        self.renderer = load_themed_svg("info", icon_color)
        if not self.renderer:
            self.renderer = load_themed_svg("circle-help", icon_color)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {text_color};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 14
            x = 10.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()
