"""
Right Navigation Rail Component (Figma Acrobat Alignment)
Implements Figma node 3:13133:
- Fixed 48px width navigation rail situated on the far right of the workspace
- Houses 4 tool icon buttons:
  1. Comments (message-square.svg)
  2. Bookmarks / TOC (bookmark.svg)
  3. Pages / Thumbnails (files.svg)
  4. Attachments (paperclip.svg)
"""

import os
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray
from PySide6.QtGui import QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager


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


class NavRailButton(QToolButton):
    """34x34px high-DPI vector navigation button for the right rail."""

    def __init__(self, tab_id: str, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.icon_name = icon_name
        self.is_active = False
        self.setFixedSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_theme()
        self.update()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_active:
            icon_color = "#3B82F6" if is_dark else "#1473E6"
            bg = "#1E293B" if is_dark else "#EAF3FF"
            border = "1px solid #1473E6"
        else:
            icon_color = "#B0B0B0" if is_dark else "#626262"
            bg = "transparent"
            border = "1px solid transparent"

        hover_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.06)"
        self.renderer = load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg};
                border: {border};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg if not self.is_active else bg};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 18
            x = (self.width() - icon_size) / 2.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class RightNavRail(QWidget):
    """
    Far-right 48px slim icon rail.
    Coordinates panel visibility in the adjacent right drawer.
    """

    tab_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(48)
        self.buttons = {}
        self.active_tab: Optional[str] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 18, 7, 18)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        rail_defs = [
            ("comments", "message-square", "Comments & Annotations"),
            ("bookmarks", "bookmark", "Table of Contents / Bookmarks"),
            ("pages", "files", "Page Thumbnails"),
            ("attachments", "paperclip", "Attachments & File Details"),
        ]

        for tab_id, icon, tip in rail_defs:
            btn = NavRailButton(tab_id, icon, tip, self)
            btn.clicked.connect(lambda checked=False, tid=tab_id: self._on_btn_clicked(tid))
            layout.addWidget(btn)
            self.buttons[tab_id] = btn

        layout.addStretch()
        self.update_theme()

    def _on_btn_clicked(self, tab_id: str):
        # Toggle behavior: if already active, toggle off (or keep active)
        if self.active_tab == tab_id:
            self.set_active_tab(None)
            self.tab_selected.emit("close")
        else:
            self.set_active_tab(tab_id)
            self.tab_selected.emit(tab_id)

    def set_active_tab(self, tab_id: Optional[str]):
        if tab_id == "close":
            tab_id = None
        self.active_tab = tab_id
        for tid, btn in self.buttons.items():
            btn.set_active(tid == tab_id)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#18181A" if is_dark else "#F8F8F8"
        border = "#333333" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            RightNavRail {{
                background-color: {bg};
                border-left: 1px solid {border};
            }}
        """)

        for btn in self.buttons.values():
            btn.update_theme()
