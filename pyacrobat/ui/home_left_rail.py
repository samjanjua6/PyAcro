"""
Home Left Navigation Rail for PyAcrobat.
Matches the Adobe Acrobat / Figma design (node 3:12728).
Provides category navigation: Recent, Starred, Your computer, All agreements.
"""

import os
import re
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter, QCursor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager


def get_svg_icon_path(svg_name: str) -> Optional[str]:
    """Resolves SVG icon path across resources and assets bundles."""
    from pyacrobat.core.resources import get_icon_path, get_base_dir
    # 1. Try resources/icons via central locator
    path = get_icon_path(svg_name)
    if os.path.exists(path):
        return path
    # 2. Try assets/icons and local fallbacks
    base_dir = get_base_dir()
    for sub in [
        os.path.join(base_dir, "assets", "icons", svg_name),
        os.path.join(base_dir, "pyacrobat", "assets", "icons", svg_name),
        os.path.join(base_dir, "resources", "icons", svg_name),
        os.path.join(base_dir, "pyacrobat", "resources", "icons", svg_name),
    ]:
        if os.path.exists(sub):
            return sub
    return None


def load_themed_svg_icon(svg_name: str, color_hex: Optional[str] = None, size: int = 20) -> QIcon:
    """Loads an SVG icon from resources/assets and optionally applies a stroke tint color."""
    icon_path = get_svg_icon_path(svg_name)
    if not icon_path:
        return QIcon()
    try:
        with open(icon_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
        if color_hex:
            svg_text = re.sub(r'stroke="[^"]*"', f'stroke="{color_hex}"', svg_text)
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        pixmap = QPixmap(size * 2, size * 2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(2.0)
        return QIcon(pixmap)
    except Exception:
        return QIcon(icon_path)


def load_themed_svg_pixmap(svg_name: str, color_hex: Optional[str] = None, size: int = 23) -> QPixmap:
    """Loads an SVG icon from resources/assets and returns a High-DPI QPixmap."""
    icon_path = get_svg_icon_path(svg_name)
    if not icon_path:
        return QPixmap()
    try:
        with open(icon_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
        if color_hex:
            svg_text = re.sub(r'stroke="[^"]*"', f'stroke="{color_hex}"', svg_text)
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        pixmap = QPixmap(size * 2, size * 2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(2.0)
        return pixmap
    except Exception:
        return QPixmap(icon_path)


class HomeNavItem(QPushButton):
    """
    Custom navigation item button matching Figma node specs:
    - Fixed height: 42px
    - Border radius: 4px
    - Icon 20x20 + 13px text label
    - Active state: background #EAF3FF (light) / accent_subtle (dark), text #1473E6 (accent)
    - Inactive state: transparent background, text #242424 / theme text
    """

    def __init__(self, item_id: str, title: str, svg_name: str, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.title_text = title
        self.svg_name = svg_name
        self.is_active = False

        self.setFixedHeight(42)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setCheckable(True)
        self.setText(f"  {title}")
        self.setIconSize(QSize(20, 20))

    def set_active(self, active: bool):
        self.is_active = active
        self.setChecked(active)
        self.update_style()

    def update_style(self):
        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        if self.is_active:
            bg_color = "#EAF3FF" if not is_dark else t.accent_subtle
            text_color = t.accent
            icon_color = t.accent
            font_weight = "600"
        else:
            bg_color = "transparent"
            text_color = t.text
            icon_color = "#626262" if not is_dark else t.text_muted
            font_weight = "400"

        hover_bg = "#F0F0F0" if not is_dark else t.surface_raised

        self.setIcon(load_themed_svg_icon(self.svg_name, icon_color, size=20))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-size: 13px;
                font-weight: {font_weight};
                text-align: left;
                padding-left: 12px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover_bg if not self.is_active else bg_color};
            }}
        """)


class HomeLeftRail(QWidget):
    """
    Fixed 232px left navigation rail for the Home Dashboard.
    Emits navigation_changed(item_id) when an item is selected.
    """

    navigation_changed = Signal(str)  # 'recent', 'starred', 'computer', 'agreements'
    open_computer_requested = Signal()
    about_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeLeftRail")
        self.setFixedWidth(232)
        self.current_item_id = "recent"
        self.items: Dict[str, HomeNavItem] = {}

        self.init_ui()
        self.update_theme()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 28, 16, 20)
        self.main_layout.setSpacing(4)
        self.main_layout.setAlignment(Qt.AlignTop)

        # 1. Primary Section: Recent & Starred
        self.item_recent = HomeNavItem("recent", "Recent", "clock.svg", self)
        self.item_recent.clicked.connect(lambda: self.select_item("recent"))
        self.items["recent"] = self.item_recent
        self.main_layout.addWidget(self.item_recent)

        self.item_starred = HomeNavItem("starred", "Starred", "star.svg", self)
        self.item_starred.clicked.connect(lambda: self.select_item("starred"))
        self.items["starred"] = self.item_starred
        self.main_layout.addWidget(self.item_starred)

        self.main_layout.addSpacing(12)
        self.main_layout.addWidget(self._create_divider())
        self.main_layout.addSpacing(12)

        # 2. Section: FILES (Non-stub: Your computer)
        self.lbl_files = QLabel("FILES")
        self.lbl_files.setObjectName("homeRailSectionHeader")
        self.main_layout.addWidget(self.lbl_files)
        self.main_layout.addSpacing(4)

        self.item_computer = HomeNavItem("computer", "Your computer", "monitor.svg", self)
        self.item_computer.clicked.connect(self._on_computer_clicked)
        self.items["computer"] = self.item_computer
        self.main_layout.addWidget(self.item_computer)

        self.main_layout.addSpacing(12)
        self.main_layout.addWidget(self._create_divider())
        self.main_layout.addSpacing(12)

        # 3. Section: AGREEMENTS
        self.lbl_agreements = QLabel("AGREEMENTS")
        self.lbl_agreements.setObjectName("homeRailSectionHeader")
        self.main_layout.addWidget(self.lbl_agreements)
        self.main_layout.addSpacing(4)

        self.item_agreements = HomeNavItem("agreements", "All agreements", "signature.svg", self)
        self.item_agreements.clicked.connect(lambda: self.select_item("agreements"))
        self.items["agreements"] = self.item_agreements
        self.main_layout.addWidget(self.item_agreements)

        # Push items to top
        self.main_layout.addStretch(1)

        # 4. Bottom Footer: About & Developer
        self.main_layout.addWidget(self._create_divider())
        self.main_layout.addSpacing(6)
        self.btn_about = QPushButton("  About Spectra PDF")
        self.btn_about.setObjectName("homeRailAboutBtn")
        self.btn_about.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_about.setIcon(load_themed_svg_icon("info.svg", "#626262", size=18))
        self.btn_about.setFixedHeight(36)
        self.btn_about.clicked.connect(self.about_requested.emit)
        self.main_layout.addWidget(self.btn_about)

        # Default selection: 'recent'
        self.select_item("recent", emit_signal=False)

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setFixedHeight(1)
        line.setObjectName("homeRailDivider")
        return line

    def select_item(self, item_id: str, emit_signal: bool = True):
        self.current_item_id = item_id
        for k, btn in self.items.items():
            btn.set_active(k == item_id)
        if emit_signal:
            self.navigation_changed.emit(item_id)

    def _on_computer_clicked(self):
        self.select_item("computer")
        self.open_computer_requested.emit()

    def update_theme(self):
        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()
        rail_bg = "#F8F8F8" if not is_dark else t.surface
        border_color = "#D9D9D9" if not is_dark else t.border_subtle
        header_color = "#626262" if not is_dark else t.text_muted
        divider_color = "#D9D9D9" if not is_dark else t.border_subtle

        self.setStyleSheet(f"""
            #homeLeftRail {{
                background-color: {rail_bg};
                border-right: 1px solid {border_color};
            }}
            #homeRailSectionHeader {{
                font-size: 11px;
                font-weight: 600;
                color: {header_color};
                padding-left: 12px;
                background: transparent;
            }}
            #homeRailDivider {{
                color: {divider_color};
                background-color: {divider_color};
                border: none;
            }}
            #homeRailAboutBtn {{
                background-color: transparent;
                color: {t.text_muted};
                font-size: 12px;
                font-weight: 500;
                text-align: left;
                padding-left: 10px;
                border-radius: 4px;
                border: none;
            }}
            #homeRailAboutBtn:hover {{
                background-color: {"#F0F0F0" if not is_dark else t.surface_raised};
                color: {t.text};
            }}
        """)

        if hasattr(self, "btn_about"):
            self.btn_about.setIcon(load_themed_svg_icon("info.svg", header_color, size=18))

        for btn in self.items.values():
            btn.update_style()
