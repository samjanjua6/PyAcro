"""
Floating In-Canvas Quick Tools Pill
Houses annotation mode buttons (Select, Hand, Highlight, Pen, Note) in a floating pill overlay.
"""

from typing import Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QFrame,
    QButtonGroup, QMenu, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from pyacrobat.ui.styles import ThemeManager


class FloatingQuickTools(QWidget):
    """
    Floating pill action bar for annotation tools positioned over the canvas:
    [ ↖ Select ] [ ✋ Hand ] [ | ] [ 🖊 Highlight ▾ ] [ ✏ Pen ▾ ] [ 💬 Note ]
    """

    tool_changed = Signal(str)
    highlight_color_changed = Signal(tuple)
    draw_style_changed = Signal(tuple, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_tool = "select"
        self.current_highlight_color: Tuple[float, float, float] = (1.0, 0.88, 0.3)
        self.current_draw_color: Tuple[float, float, float] = (0.88, 0.15, 0.11)
        self.current_draw_width: float = 2.0

        self.setFixedHeight(38)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)

        self.pill_frame = QFrame(self)
        self.pill_frame.setObjectName("floatingPillFrame")
        pill_layout = QHBoxLayout(self.pill_frame)
        pill_layout.setContentsMargins(8, 3, 8, 3)
        pill_layout.setSpacing(4)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.pill_frame.setGraphicsEffect(shadow)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        # 1. Navigation Modes
        self.btn_select = QToolButton()
        self.btn_select.setText("↖ Select")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.tool_group.addButton(self.btn_select)
        self.btn_select.clicked.connect(lambda: self.set_tool("select"))
        pill_layout.addWidget(self.btn_select)

        self.btn_hand = QToolButton()
        self.btn_hand.setText("✋ Hand")
        self.btn_hand.setCheckable(True)
        self.tool_group.addButton(self.btn_hand)
        self.btn_hand.clicked.connect(lambda: self.set_tool("hand"))
        pill_layout.addWidget(self.btn_hand)

        pill_layout.addWidget(self._create_divider())

        # 2. Annotation Tools
        self.btn_highlight = QToolButton()
        self.btn_highlight.setText("🖊 Highlight ▾")
        self.btn_highlight.setCheckable(True)
        self.btn_highlight.setPopupMode(QToolButton.MenuButtonPopup)
        self.tool_group.addButton(self.btn_highlight)
        self.btn_highlight.clicked.connect(lambda: self.set_tool("highlight"))
        self._setup_highlight_menu()
        pill_layout.addWidget(self.btn_highlight)

        self.btn_draw = QToolButton()
        self.btn_draw.setText("✏ Pen ▾")
        self.btn_draw.setCheckable(True)
        self.btn_draw.setPopupMode(QToolButton.MenuButtonPopup)
        self.tool_group.addButton(self.btn_draw)
        self.btn_draw.clicked.connect(lambda: self.set_tool("draw"))
        self._setup_draw_menu()
        pill_layout.addWidget(self.btn_draw)

        self.btn_note = QToolButton()
        self.btn_note.setText("💬 Note")
        self.btn_note.setCheckable(True)
        self.tool_group.addButton(self.btn_note)
        self.btn_note.clicked.connect(lambda: self.set_tool("note"))
        pill_layout.addWidget(self.btn_note)

        main_layout.addWidget(self.pill_frame)
        self.update_theme()

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedSize(1, 16)
        line.setObjectName("floatingPillDivider")
        return line

    def _setup_highlight_menu(self):
        menu = QMenu(self)
        colors = [
            ("🟡 Yellow", (1.0, 0.88, 0.3)),
            ("🟢 Mint Green", (0.5, 0.9, 0.6)),
            ("🔵 Cyan", (0.4, 0.8, 1.0)),
            ("🌸 Pink", (1.0, 0.6, 0.8)),
        ]
        for name, rgb in colors:
            action = menu.addAction(name)
            action.triggered.connect(lambda checked=False, c=rgb: self._set_highlight_color(c))
        self.btn_highlight.setMenu(menu)

    def _setup_draw_menu(self):
        menu = QMenu(self)
        colors_menu = menu.addMenu("Colors")
        pen_colors = [
            ("🔴 Acrobat Red", (0.88, 0.15, 0.11)),
            ("🔵 Spectrum Blue", (0.08, 0.45, 0.9)),
            ("⚫ Black", (0.1, 0.1, 0.1)),
            ("🟢 Green", (0.15, 0.7, 0.3)),
        ]
        for name, rgb in pen_colors:
            act = colors_menu.addAction(name)
            act.triggered.connect(lambda checked=False, c=rgb: self._set_draw_color(c))

        width_menu = menu.addMenu("Stroke Width")
        widths = [("Thin (1px)", 1.0), ("Medium (2px)", 2.0), ("Thick (4px)", 4.0)]
        for name, w in widths:
            act = width_menu.addAction(name)
            act.triggered.connect(lambda checked=False, width=w: self._set_draw_width(width))

        self.btn_draw.setMenu(menu)

    def set_tool(self, tool_name: str, emit_signal: bool = True):
        self.active_tool = tool_name
        self.tool_group.blockSignals(True)
        if tool_name == "select":
            self.btn_select.setChecked(True)
        elif tool_name == "hand":
            self.btn_hand.setChecked(True)
        elif tool_name == "highlight":
            self.btn_highlight.setChecked(True)
        elif tool_name == "draw":
            self.btn_draw.setChecked(True)
        elif tool_name == "note":
            self.btn_note.setChecked(True)
        self.tool_group.blockSignals(False)
        if emit_signal:
            self.tool_changed.emit(tool_name)

    def _set_highlight_color(self, rgb: Tuple[float, float, float]):
        self.current_highlight_color = rgb
        self.highlight_color_changed.emit(rgb)
        self.set_tool("highlight", emit_signal=True)

    def _set_draw_color(self, rgb: Tuple[float, float, float]):
        self.current_draw_color = rgb
        self.draw_style_changed.emit(self.current_draw_color, self.current_draw_width)
        self.set_tool("draw")

    def _set_draw_width(self, width: float):
        self.current_draw_width = width
        self.draw_style_changed.emit(self.current_draw_color, self.current_draw_width)
        self.set_tool("draw")

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#252528" if is_dark else "#FFFFFF"
        border = "#3E3E42" if is_dark else "#D9D9D9"
        text_color = "#E0E0E0" if is_dark else "#242424"

        self.setStyleSheet(f"""
            #floatingPillFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            #floatingPillDivider {{
                background-color: {border};
                border: none;
            }}
            QToolButton {{
                background-color: transparent;
                color: {text_color};
                font-size: 12px;
                font-weight: 500;
                padding: 4px 8px;
                border: none;
                border-radius: 12px;
            }}
            QToolButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)'};
            }}
            QToolButton:checked {{
                background-color: {'#1473E6' if is_dark else '#0265DC'};
                color: #FFFFFF;
            }}
            QToolButton::menu-button {{
                border: none;
                background: transparent;
                width: 16px;
            }}
            QToolButton::menu-arrow {{
                image: none;
            }}
        """)
