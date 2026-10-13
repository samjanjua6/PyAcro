"""
All Tools Panel Component (Figma Acrobat Alignment)
Implements Figma node 3:12978:
- Fixed 232px width panel on the left of the document viewport
- Header: 'All tools' (18px SemiBold) + collapse button (panel-left-close.svg)
- Tool items (Edit, Export, Create, Organize, Fill & Sign, OCR, Combine, Comments, etc.)
- Upsell note card: 'Get more with Acrobat Pro' + 'Explore plans' button
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QScrollArea, QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QByteArray
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    """Loads SVG and replaces stroke color dynamically for crisp high-DPI painting."""
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


class AllToolsItemButton(QPushButton):
    """Single tool item row in the All Tools Panel (Icon + Label)."""

    def __init__(self, tool_id: str, label: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.label_text = label
        self.icon_name = icon_name
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        icon_color = "#C0C0C0" if is_dark else "#505050"
        text_color = "#E0E0E0" if is_dark else "#242424"
        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        pressed_bg = "rgba(255, 255, 255, 0.14)" if is_dark else "rgba(0, 0, 0, 0.10)"

        self.renderer = load_themed_svg(self.icon_name, icon_color)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 400;
                text-align: left;
                padding-left: 36px;
                padding-right: 10px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {'#FFFFFF' if is_dark else '#111111'};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)
        self.setText(self.label_text)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 18
            x = 8.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class AllToolsPanel(QWidget):
    """
    Left-hand 232px collapsible 'All tools' workstation drawer.
    Provides direct access to all Acrobat power tools and page operations.
    """

    collapse_requested = Signal()
    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(232)
        self.tool_buttons = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 18, 14, 14)
        main_layout.setSpacing(10)

        # 1. Header (Heading + Collapse button)
        header_container = QWidget()
        h_layout = QHBoxLayout(header_container)
        h_layout.setContentsMargins(0, 0, 0, 4)
        h_layout.setSpacing(8)

        self.lbl_heading = QLabel("All tools")
        self.lbl_heading.setFont(QFont("Inter", 14, QFont.DemiBold))
        h_layout.addWidget(self.lbl_heading)

        h_layout.addStretch()

        self.btn_collapse = QToolButton()
        self.btn_collapse.setFixedSize(28, 28)
        self.btn_collapse.setCursor(Qt.PointingHandCursor)
        self.btn_collapse.setToolTip("Collapse All Tools Panel")
        self.btn_collapse.clicked.connect(self.collapse_requested.emit)
        h_layout.addWidget(self.btn_collapse)

        main_layout.addWidget(header_container)

        # 2. Scrollable Tool List Container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setObjectName("allToolsScrollArea")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)

        # Tools matching Figma node 3:12982
        tools_def = [
            ("edit", "Edit a PDF", "pencil"),
            ("export", "Export a PDF", "file-output"),
            ("create", "Create a PDF", "file-plus-2"),
            ("organize", "Organize pages", "layers"),
            ("fill_sign", "Fill & Sign", "pen-line"),
            ("esign", "Request e-signatures", "signature"),
            ("ocr", "Scan & OCR", "scan-line"),
            ("combine", "Combine files", "files"),
            ("protect", "Protect a PDF", "shield-check"),
            ("prepare_form", "Prepare a form", "file-check"),
            ("comments", "Add comments", "message-square"),
            ("stamp", "Add a stamp", "stamp"),
        ]

        for tool_id, label, icon in tools_def:
            btn = AllToolsItemButton(tool_id, label, icon, content_widget)
            btn.clicked.connect(lambda checked=False, tid=tool_id: self.tool_selected.emit(tid))
            self.content_layout.addWidget(btn)
            self.tool_buttons.append(btn)

        # Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFixedHeight(1)
        self.divider.setObjectName("allToolsDivider")
        self.content_layout.addWidget(self.divider)

        # See all tools button
        self.btn_see_all = AllToolsItemButton("see_all", "See all tools", "circle-help", content_widget)
        self.btn_see_all.clicked.connect(lambda: self.tool_selected.emit("see_all"))
        self.content_layout.addWidget(self.btn_see_all)
        self.tool_buttons.append(self.btn_see_all)

        # Acrobat Pro Note Card
        self.pro_card = QFrame()
        self.pro_card.setObjectName("proUpsellCard")
        pc_layout = QVBoxLayout(self.pro_card)
        pc_layout.setContentsMargins(12, 12, 12, 12)
        pc_layout.setSpacing(6)

        self.lbl_pro_title = QLabel("Get more with Acrobat Pro")
        self.lbl_pro_title.setFont(QFont("Inter", 10, QFont.DemiBold))
        self.lbl_pro_title.setObjectName("proCardTitle")
        pc_layout.addWidget(self.lbl_pro_title)

        self.lbl_pro_body = QLabel("Edit, convert, and sign PDFs in one place.")
        self.lbl_pro_body.setFont(QFont("Inter", 9))
        self.lbl_pro_body.setWordWrap(True)
        self.lbl_pro_body.setObjectName("proCardBody")
        pc_layout.addWidget(self.lbl_pro_body)

        self.btn_explore_plans = QPushButton("Explore plans")
        self.btn_explore_plans.setFixedHeight(28)
        self.btn_explore_plans.setCursor(Qt.PointingHandCursor)
        self.btn_explore_plans.setObjectName("proCardButton")
        pc_layout.addWidget(self.btn_explore_plans)

        self.content_layout.addWidget(self.pro_card)
        self.content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#1E1E1E" if is_dark else "#FFFFFF"
        border_color = "#333333" if is_dark else "#D9D9D9"
        card_bg = "#252528" if is_dark else "#F8F8F8"
        text_color = "#F5F5F7" if is_dark else "#242424"
        subtle_text = "#9E9E9E" if is_dark else "#626262"
        btn_bg = "#303035" if is_dark else "#FFFFFF"
        btn_border = "#444444" if is_dark else "#D9D9D9"

        self.setStyleSheet(f"""
            AllToolsPanel {{
                background-color: {bg};
                border-right: 1px solid {border_color};
            }}
            #allToolsScrollArea, #allToolsScrollArea > QWidget {{
                background-color: transparent;
                border: none;
            }}
            #allToolsDivider {{
                background-color: {border_color};
                border: none;
            }}
            #proUpsellCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #proCardTitle {{
                color: {text_color};
            }}
            #proCardBody {{
                color: {subtle_text};
            }}
            #proCardButton {{
                background-color: {btn_bg};
                color: {text_color};
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid {btn_border};
                border-radius: 14px;
            }}
            #proCardButton:hover {{
                background-color: {'#3A3A40' if is_dark else '#F0F0F0'};
            }}
            QToolButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.10)' if is_dark else 'rgba(0, 0, 0, 0.06)'};
            }}
        """)

        self.lbl_heading.setStyleSheet(f"color: {text_color};")
        self.btn_collapse.setText("⟨")

        for btn in self.tool_buttons:
            btn.update_theme()
