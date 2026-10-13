"""
Document Toolbar Component (Figma Acrobat Alignment)
Implements Figma node 3:12957:
- Fixed 56px height, bottom border #D9D9D9 (light) / #333333 (dark)
- Left: Workspace tab strip ("All tools" [SemiBold, red 3px underline], "Edit", "Convert", "E-Sign")
- Right: Search, Save, Print vector icon buttons + Separator + Share (blue pill) + AI Assistant (white/dark pill)
"""

import os
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QLabel, QFrame,
    QPushButton, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def load_themed_svg_renderer(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    """Loads an SVG icon from resources/icons and replaces stroke color dynamically."""
    svg_path = os.path.join(ICONS_DIR, f"{icon_name}.svg")
    if not os.path.exists(svg_path):
        return None
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Replace default stroke color
        content = content.replace('#626262', color_hex).replace('#242424', color_hex)
        return QSvgRenderer(QByteArray(content.encode("utf-8")))
    except Exception:
        return None


class WorkspaceTabButton(QToolButton):
    """
    Individual workspace tab button (e.g. 'All tools', 'Edit', 'Convert', 'E-Sign').
    Figma spec:
    - 56px vertical fill
    - Inter 13px (SemiBold 600 when active, Regular 400 when inactive)
    - Active: 3px solid #EB1000 bottom stroke
    - Inactive: transparent bottom stroke
    """

    def __init__(self, tab_id: str, label: str, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.label_text = label
        self.is_active = False

        self.setFixedHeight(56)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_Hover, True)
        self.update_theme()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_theme()
        self.update()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_active:
            text_color = "#FFFFFF" if is_dark else "#242424"
            font_weight = "600"
        else:
            text_color = "#9E9E9E" if is_dark else "#5A5A5A"
            font_weight = "400"

        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: {font_weight};
                padding: 0px 14px;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
                color: {'#FFFFFF' if is_dark else '#1E1E1E'};
            }}
        """)
        self.setText(self.label_text)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_active:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            indicator_height = 3
            # Active red indicator #EB1000 at bottom
            painter.fillRect(
                0, self.height() - indicator_height,
                self.width(), indicator_height,
                QColor("#EB1000")
            )
            painter.end()


class WorkspaceTabStrip(QWidget):
    """
    Houses the 4 workspace tabs matching Figma:
    'All tools' | 'Edit' | 'Convert' | 'E-Sign'
    """

    tab_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_tab_id = "all_tools"
        self.tabs = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        tab_defs = [
            ("all_tools", "All tools"),
            ("edit", "Edit"),
            ("convert", "Convert"),
            ("esign", "E-Sign"),
        ]

        for tab_id, label in tab_defs:
            btn = WorkspaceTabButton(tab_id, label, self)
            btn.clicked.connect(lambda checked=False, tid=tab_id: self.select_tab(tid))
            layout.addWidget(btn)
            self.tabs[tab_id] = btn

        self.select_tab("all_tools", emit_signal=False)

    def select_tab(self, tab_id: str, emit_signal: bool = True):
        if tab_id not in self.tabs:
            return
        self.active_tab_id = tab_id
        for tid, btn in self.tabs.items():
            btn.set_active(tid == tab_id)
        if emit_signal:
            self.tab_changed.emit(tab_id)

    def update_theme(self):
        for btn in self.tabs.values():
            btn.update_theme()


class ToolbarIconButton(QToolButton):
    """
    High-DPI vector icon button for toolbar utilities (Search, Save, Print).
    Renders SVG icon centered at 18x18 inside a 32x32 button with rounded hover state.
    """

    def __init__(self, icon_name: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAttribute(Qt.WA_Hover, True)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        color_hex = "#D0D0D0" if is_dark else "#626262"
        self.renderer = load_themed_svg_renderer(self.icon_name, color_hex)
        hover_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.06)"
        pressed_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.12)"
        
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
            }}
            QToolButton:pressed {{
                background-color: {pressed_bg};
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


class ToolbarSeparator(QFrame):
    """1px wide by 22px high vertical divider (#D9D9D9 light / #3E3E42 dark)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFixedSize(1, 22)
        self.update_theme()

    def update_theme(self):
        color = "#3E3E42" if ThemeManager.is_dark() else "#D9D9D9"
        self.setStyleSheet(f"background-color: {color}; border: none;")


class SharePillButton(QPushButton):
    """
    Figma Share button:
    - Height: 34px, border-radius: 17px (pill)
    - Fill: #1473E6 (Adobe Blue)
    - Icon: 16x16 vector share-2.svg in white
    - Text: 'Share', Inter SemiBold 13px, white
    - Padding: 0px 14px, gap: 8px
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Share Document")
        self.renderer: Optional[QSvgRenderer] = None
        self._load_icon()
        self.update_theme()

    def _load_icon(self):
        self.renderer = load_themed_svg_renderer("share-2", "#FFFFFF")

    def update_theme(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: #1473E6;
                color: #FFFFFF;
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding-left: 36px;
                padding-right: 16px;
                border: none;
                border-radius: 17px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #0D66D0;
            }
            QPushButton:pressed {
                background-color: #095ABA;
            }
        """)
        self.setText("Share")
        self.adjustSize()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 16
            # Position icon to the left of the text
            x = 14.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class AIAssistantPillButton(QPushButton):
    """
    Figma AI Assistant button:
    - Height: 34px, border-radius: 17px (pill)
    - Light: bg #FFFFFF, border 1px #D9D9D9, text #242424
    - Dark: bg #252528, border 1px #444444, text #F5F5F7
    - Icon: 16x16 vector sparkles.svg
    - Text: 'AI Assistant', Inter SemiBold 13px
    - Padding: 0px 14px, gap: 8px
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Open Acrobat AI Document Assistant (Ctrl+I)")
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if is_dark:
            bg = "#252528"
            border = "#444444"
            text_color = "#F5F5F7"
            hover_bg = "#303035"
            pressed_bg = "#3A3A40"
            icon_color = "#F5F5F7"
        else:
            bg = "#FFFFFF"
            border = "#D9D9D9"
            text_color = "#242424"
            hover_bg = "#F5F5F7"
            pressed_bg = "#ECECEF"
            icon_color = "#242424"

        self.renderer = load_themed_svg_renderer("sparkles", icon_color)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding-left: 36px;
                padding-right: 16px;
                border: 1px solid {border};
                border-radius: 17px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)
        self.setText("AI Assistant")
        self.adjustSize()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 16
            x = 14.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class DocumentToolbar(QWidget):
    """
    Figma Document Toolbar (56px full-width row):
    - Layout: Left workspace tabs -> Flex spacer -> Search -> Save -> Print -> | -> Share -> AI Assistant
    - Maintains all backward-compatible signals and state hooks from QuickToolsBar.
    """

    # New Figma Workspace & Document Toolbar Signals
    workspace_tab_changed = Signal(str)
    search_requested = Signal()
    save_requested = Signal()
    print_requested = Signal()
    share_requested = Signal()
    ai_assistant_requested = Signal()

    # Preserved QuickToolsBar Signals for 100% Backward Compatibility
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    zoom_level_changed = Signal(float)
    fit_width_requested = Signal()
    fit_page_requested = Signal()
    page_jump_requested = Signal(int)

    tool_changed = Signal(str)
    theme_toggle_requested = Signal()
    ai_toggle_requested = Signal()
    highlight_color_changed = Signal(tuple)
    draw_style_changed = Signal(tuple, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_pages = 1
        self.current_page = 1
        self.active_tool = "select"

        self.current_highlight_color: Tuple[float, float, float] = (1.0, 0.88, 0.3)
        self.current_draw_color: Tuple[float, float, float] = (0.88, 0.15, 0.11)
        self.current_draw_width: float = 2.0

        self.setFixedHeight(56)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(22, 0, 22, 0)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignVCenter)

        # 1. Left: Workspace Tabs Strip ("All tools" | "Edit" | "Convert" | "E-Sign")
        self.workspace_tabs = WorkspaceTabStrip(self)
        self.workspace_tabs.tab_changed.connect(self._on_workspace_tab_changed)
        main_layout.addWidget(self.workspace_tabs)

        # 2. Flexible Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(spacer)

        # 3. Right: Utility Icon Buttons (Search, Save, Print)
        self.btn_search = ToolbarIconButton("search", "Search document (Ctrl+F)")
        self.btn_search.clicked.connect(self.search_requested.emit)
        main_layout.addWidget(self.btn_search)

        self.btn_save = ToolbarIconButton("save", "Save annotations (Ctrl+S)")
        self.btn_save.clicked.connect(self.save_requested.emit)
        main_layout.addWidget(self.btn_save)

        self.btn_print = ToolbarIconButton("printer", "Print / Export document (Ctrl+P)")
        self.btn_print.clicked.connect(self.print_requested.emit)
        main_layout.addWidget(self.btn_print)

        # 4. Vertical Separator
        self.separator = ToolbarSeparator()
        main_layout.addWidget(self.separator)

        # 5. Share Button (Blue Pill)
        self.btn_share = SharePillButton(self)
        self.btn_share.clicked.connect(self.share_requested.emit)
        main_layout.addWidget(self.btn_share)

        # 6. AI Assistant Button (Pill)
        self.btn_ai_assistant = AIAssistantPillButton(self)
        self.btn_ai_assistant.clicked.connect(self._on_ai_clicked)
        main_layout.addWidget(self.btn_ai_assistant)

        # Aliases for compatibility
        self.btn_ai = self.btn_ai_assistant

        self.update_theme()

    def _on_workspace_tab_changed(self, tab_id: str):
        self.workspace_tab_changed.emit(tab_id)

    def _on_ai_clicked(self):
        self.ai_assistant_requested.emit()
        self.ai_toggle_requested.emit()

    def select_workspace_tab(self, tab_id: str):
        """Programmatically select workspace tab."""
        self.workspace_tabs.select_tab(tab_id)

    def update_theme(self):
        """Updates toolbar background, bottom border, and child styles for active theme."""
        is_dark = ThemeManager.is_dark()
        bg = "#1E1E1E" if is_dark else "#FFFFFF"
        border_color = "#333333" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            DocumentToolbar {{
                background-color: {bg};
                border-bottom: 1px solid {border_color};
            }}
        """)

        self.workspace_tabs.update_theme()
        self.btn_search.update_theme()
        self.btn_save.update_theme()
        self.btn_print.update_theme()
        self.separator.update_theme()
        self.btn_share.update_theme()
        self.btn_ai_assistant.update_theme()

    # =========================================================================
    # Compatibility Methods for DocumentTab / Zoom / Page navigation
    # =========================================================================

    def update_page_info(self, current: int, total: int):
        self.current_page = current
        self.total_pages = max(1, total)

    def update_zoom_display(self, scale: float):
        pass

    def set_tool(self, tool_name: str):
        self.active_tool = tool_name
        self.tool_changed.emit(tool_name)
