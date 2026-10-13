"""
Floating AI Assistant Action Button Component
Floating pill action button positioned at the bottom-right corner of the document viewport.
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def _load_white_sparkles_svg() -> Optional[QSvgRenderer]:
    path = os.path.join(ICONS_DIR, "sparkles.svg")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('#242424', '#FFFFFF').replace('#626262', '#FFFFFF')
        return QSvgRenderer(QByteArray(content.encode("utf-8")))
    except Exception:
        return None


class FloatingAIButton(QToolButton):
    """
    Floating action pill button for AI Assistant positioned in the viewport:
    [ ✨ AI Assistant ]
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("floatingAIButton")
        self.setText("  AI Assistant")
        self.setToolTip("Acrobat AI Assistant (Ctrl+I) — Ask questions, summarize, or extract insights")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(126)

        # Drop Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 70))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        self.renderer = _load_white_sparkles_svg()
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#2563EB" if is_dark else "#1473E6"
        hover_bg = "#3B82F6" if is_dark else "#0D66D0"

        self.setStyleSheet(f"""
            QToolButton#floatingAIButton {{
                background-color: {bg};
                color: #FFFFFF;
                border: 1px solid {'rgba(255, 255, 255, 0.20)' if is_dark else 'transparent'};
                border-radius: 18px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding-left: 28px;
                padding-right: 14px;
            }}
            QToolButton#floatingAIButton:hover {{
                background-color: {hover_bg};
            }}
            QToolButton#floatingAIButton:pressed {{
                background-color: {'#1D4ED8' if is_dark else '#0950A8'};
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
            x = 10
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()
