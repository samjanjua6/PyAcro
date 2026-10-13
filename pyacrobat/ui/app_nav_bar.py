"""
Application Navigation Bar (Acrobat-styled Branded Top Strip)
Figma Reference: Node #3:12938 ("Application navigation")
48px fixed height strip containing:
- Adobe Acrobat Brand (Red 30x32 mark + "Adobe Acrobat" SemiBold 16px)
- Divider line
- Home tab (House icon + "Home", active 3px red underline)
- Document tab chips (File icon + Title + Close [x], active 3px red underline)
- Add new PDF [+] button
- Expanding spacer
- Utility icon buttons (Search, Notification, Help)
- Profile avatar circle ("AM", 28x28px, #E8EFED)
"""

import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QFrame,
    QSizePolicy, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRectF, QByteArray
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPaintEvent,
    QMouseEvent, QPainterPath
)
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
        content = content.replace('#626262', color_hex).replace('#242424', color_hex)
        return QSvgRenderer(QByteArray(content.encode("utf-8")))
    except Exception:
        return None


class AcrobatMarkWidget(QWidget):
    """
    Acrobat 30x32px red icon badge with stylized white Acrobat loop symbol.
    Figma spec: width: 30, height: 32, fills: #EB1000, borderRadius: 3px.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 32)
        svg_path = os.path.join(ICONS_DIR, "adobe_acrobat.svg")
        self.renderer = QSvgRenderer(svg_path) if os.path.exists(svg_path) else None

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self.renderer and self.renderer.isValid():
            self.renderer.render(painter, QRectF(0, 1, 30, 30))
        else:
            # Fallback red rounded rectangle badge
            rect = QRectF(0, 0, self.width(), self.height())
            painter.setBrush(QBrush(QColor("#EB1000")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 3, 3)

            pen = QPen(QColor("#FFFFFF"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            path = QPainterPath()
            path.moveTo(6.5, 25.0)
            path.cubicTo(10.0, 24.0, 13.0, 16.0, 15.0, 7.5)
            path.cubicTo(17.0, 16.0, 20.0, 24.0, 23.5, 25.0)

            cross_path = QPainterPath()
            cross_path.moveTo(9.5, 20.5)
            cross_path.cubicTo(12.5, 19.0, 17.5, 19.0, 20.5, 20.5)

            painter.drawPath(path)
            painter.drawPath(cross_path)

        painter.end()


class HomeTabButton(QFrame):
    """
    Home tab button with house icon and active red bottom indicator.
    Figma spec: Node #3:12944.
    """
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_active = True
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("appNavHomeTab")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel("Home")
        self.text_label.setFont(QFont("Inter", 11, QFont.Medium))
        layout.addWidget(self.text_label)

        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if self.is_active:
            painter = QPainter(self)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#EB1000")))
            painter.drawRect(0, self.height() - 3, self.width(), 3)
            painter.end()

    def update_style(self):
        is_dark = ThemeManager.is_dark()
        fg_color = "#F5F5F7" if is_dark else "#242424"
        dim_color = "#A0A0A0" if is_dark else "#626262"
        color = fg_color if self.is_active else dim_color

        self.text_label.setStyleSheet(f"color: {color}; background: transparent;")

        # Draw crisp house icon
        pix = self._draw_house_icon(QColor(color))
        self.icon_label.setPixmap(pix)

    def _draw_house_icon(self, color: QColor):
        from PySide6.QtGui import QPixmap
        pix = QPixmap(18, 18)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)

        # Roof
        roof = QPainterPath()
        roof.moveTo(2.5, 9.0)
        roof.lineTo(9.0, 3.0)
        roof.lineTo(15.5, 9.0)
        p.drawPath(roof)

        # Body
        body = QPainterPath()
        body.moveTo(4.5, 8.5)
        body.lineTo(4.5, 15.0)
        body.lineTo(13.5, 15.0)
        body.lineTo(13.5, 8.5)
        p.drawPath(body)

        # Door
        p.drawLine(7.5, 15.0, 7.5, 11.5)
        p.drawLine(10.5, 15.0, 10.5, 11.5)
        p.drawLine(7.5, 11.5, 10.5, 11.5)

        p.end()
        return pix


class DocumentTabChip(QFrame):
    """
    Document tab chip with file icon, truncated title, dirty indicator (*),
    close button (x), and active bottom red underline indicator (#EB1000).
    Figma spec: Node #3:12947 (width: ~242px, height: 48px).
    """
    clicked = Signal()
    close_requested = Signal()

    def __init__(self, title: str, file_path: str = "", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._raw_title = title
        self.is_active = False
        self.is_dirty = False

        self.setFixedHeight(48)
        self.setMinimumWidth(130)
        self.setMaximumWidth(240)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("appNavDocTab")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignVCenter)

        # File icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        layout.addWidget(self.icon_label)

        # Filename label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Inter", 10, QFont.Normal))
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.title_label)

        # Close button [x]
        self.btn_close = QToolButton()
        self.btn_close.setFixedSize(16, 16)
        self.btn_close.setText("✕")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Close Tab (Ctrl W)")
        self.btn_close.clicked.connect(self.close_requested.emit)
        layout.addWidget(self.btn_close)

        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()
        self.update()

    def set_dirty(self, is_dirty: bool):
        self.is_dirty = is_dirty
        display = f"{self._raw_title} *" if is_dirty else self._raw_title
        self.title_label.setText(display)

    def set_title(self, title: str):
        self._raw_title = title
        display = f"{title} *" if self.is_dirty else title
        self.title_label.setText(display)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if self.is_active:
            painter = QPainter(self)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#EB1000")))
            painter.drawRect(0, self.height() - 3, self.width(), 3)
            painter.end()

    def update_style(self):
        is_dark = ThemeManager.is_dark()
        fg_color = "#F5F5F7" if is_dark else "#242424"
        dim_color = "#A0A0A0" if is_dark else "#626262"
        bg_active = "#222222" if is_dark else "#FFFFFF"
        close_hover = "#444444" if is_dark else "#E5E5E5"

        text_color = fg_color if self.is_active else dim_color
        bg_color = bg_active if self.is_active else "transparent"

        self.setStyleSheet(f"""
            #appNavDocTab {{
                background-color: {bg_color};
                border: none;
            }}
            #appNavDocTab:hover {{
                background-color: {"#2A2A2A" if is_dark else "#F5F5F7"};
            }}
        """)

        self.title_label.setStyleSheet(f"""
            color: {text_color};
            background: transparent;
            font-weight: {"600" if self.is_active else "400"};
        """)

        self.btn_close.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {dim_color};
                border: none;
                border-radius: 8px;
                font-size: 10px;
                padding: 0px;
            }}
            QToolButton:hover {{
                background: {close_hover};
                color: {fg_color};
            }}
        """)

        # Draw document file icon
        pix = self._draw_file_icon(QColor(text_color))
        self.icon_label.setPixmap(pix)

    def _draw_file_icon(self, color: QColor):
        from PySide6.QtGui import QPixmap
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(color, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)

        # File outline with folded top-right corner
        path = QPainterPath()
        path.moveTo(3.0, 1.5)
        path.lineTo(9.5, 1.5)
        path.lineTo(13.0, 5.0)
        path.lineTo(13.0, 14.5)
        path.lineTo(3.0, 14.5)
        path.closeSubpath()
        p.drawPath(path)

        # Corner fold
        p.drawLine(9.5, 1.5, 9.5, 5.0)
        p.drawLine(9.5, 5.0, 13.0, 5.0)

        # Text lines
        p.drawLine(5.5, 8.0, 10.5, 8.0)
        p.drawLine(5.5, 11.0, 9.5, 11.0)

        p.end()
        return pix


class ProfileAvatarWidget(QFrame):
    """
    Circular profile avatar badge with initials.
    Figma spec: Node #3:12955 (width: 28, height: 28, fills: #E8EFED, text: 'AM').
    """

    def __init__(self, initials="AM", parent=None):
        super().__init__(parent)
        self.initials = initials
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Account Profile")

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background circle
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setBrush(QBrush(QColor("#E8EFED")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)

        # Initials text
        painter.setPen(QPen(QColor("#203C42")))
        font = QFont("Inter", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.initials)
        painter.end()


class NavIconButton(QToolButton):
    """Clean vector-drawn utility icon button for Navigation Bar."""

    def __init__(self, icon_type: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setToolTip(tooltip)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("appNavIconBtn")

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = ThemeManager.is_dark()
        col = QColor("#F5F5F7" if is_dark else "#242424") if self.underMouse() else QColor("#A0A0A0" if is_dark else "#626262")

        pen = QPen(col, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.icon_type == "search":
            painter.drawEllipse(QRectF(7.0, 7.0, 9.0, 9.0))
            painter.drawLine(13.5, 13.5, 19.5, 19.5)
        elif self.icon_type == "bell":
            path = QPainterPath()
            path.moveTo(8.5, 17.5)
            path.lineTo(19.5, 17.5)
            path.lineTo(18.0, 11.0)
            path.cubicTo(18.0, 7.5, 10.0, 7.5, 10.0, 11.0)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(12.5, 19.5, 15.5, 19.5)
        elif self.icon_type == "help":
            painter.drawEllipse(QRectF(5.5, 5.5, 17.0, 17.0))
            font = QFont("Inter", 9, QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(5.5, 5.5, 17.0, 17.0), Qt.AlignCenter, "?")
        elif self.icon_type == "theme":
            svg_name = "sun" if is_dark else "moon"
            renderer = load_themed_svg_renderer(svg_name, col.name())
            if renderer and renderer.isValid():
                renderer.render(painter, QRectF(6.0, 6.0, 16.0, 16.0))
            else:
                if is_dark:
                    painter.drawEllipse(QRectF(9.5, 9.5, 9.0, 9.0))
                    painter.drawLine(14.0, 5.5, 14.0, 7.5)
                    painter.drawLine(14.0, 20.5, 14.0, 22.5)
                    painter.drawLine(5.5, 14.0, 7.5, 14.0)
                    painter.drawLine(20.5, 14.0, 22.5, 14.0)
                else:
                    path = QPainterPath()
                    path.moveTo(17.5, 8.0)
                    path.cubicTo(13.0, 8.0, 9.5, 11.5, 9.5, 16.0)
                    path.cubicTo(9.5, 18.5, 10.5, 20.0, 11.5, 20.5)
                    path.cubicTo(8.5, 19.5, 7.0, 16.5, 7.0, 13.5)
                    path.cubicTo(7.0, 9.0, 10.5, 5.5, 15.0, 5.5)
                    path.closeSubpath()
                    painter.setBrush(QBrush(col))
                    painter.drawPath(path)

        painter.end()


class AppNavBar(QWidget):
    """
    Main Application Navigation Bar (Figma spec: 48px height row).
    Houses:
    - Acrobat mark & brand name
    - Separator
    - Home tab button
    - Scrollable document tabs strip
    - Add tab [+] button
    - Spacer
    - Utility icons: Search, Bell, Help
    - Profile avatar
    """

    home_clicked = Signal()
    tab_selected = Signal(int)             # 0-based index
    tab_close_requested = Signal(int)      # 0-based index
    new_document_requested = Signal()
    search_clicked = Signal()
    theme_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chips: List[DocumentTabChip] = []
        self.active_tab_index: int = -1
        self.is_home_active: bool = True

        self.setFixedHeight(48)
        self.setObjectName("appNavigationBar")
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 0, 18, 0)
        main_layout.setSpacing(18)
        main_layout.setAlignment(Qt.AlignVCenter)

        # 1. Brand Section (Acrobat Mark + 'Adobe Acrobat')
        self.brand_container = QWidget()
        b_layout = QHBoxLayout(self.brand_container)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(9)
        b_layout.setAlignment(Qt.AlignVCenter)

        self.mark = AcrobatMarkWidget()
        b_layout.addWidget(self.mark)

        self.brand_label = QLabel("Adobe Acrobat")
        self.brand_label.setFont(QFont("Inter", 12, QFont.DemiBold))
        b_layout.addWidget(self.brand_label)

        main_layout.addWidget(self.brand_container)

        # 2. Vertical Divider
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.VLine)
        self.sep.setFixedSize(1, 23)
        self.sep.setObjectName("appNavDivider")
        main_layout.addWidget(self.sep)

        # 3. Home Tab
        self.btn_home = HomeTabButton()
        self.btn_home.clicked.connect(self._on_home_clicked)
        main_layout.addWidget(self.btn_home)

        # 4. Document Tabs Container
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(4)
        self.tabs_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(self.tabs_container)

        # 5. Add Document Button [+]
        self.btn_add_doc = QToolButton()
        self.btn_add_doc.setText("＋")
        self.btn_add_doc.setToolTip("Open Document (Ctrl O)")
        self.btn_add_doc.setFixedSize(28, 28)
        self.btn_add_doc.setCursor(Qt.PointingHandCursor)
        self.btn_add_doc.setObjectName("appNavAddBtn")
        self.btn_add_doc.clicked.connect(self.new_document_requested.emit)
        main_layout.addWidget(self.btn_add_doc)

        # 6. Expanding Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(spacer)

        # 7. Right Utility Icons
        self.btn_search = NavIconButton("search", "Search Document")
        self.btn_search.clicked.connect(self.search_clicked.emit)
        main_layout.addWidget(self.btn_search)

        self.btn_bell = NavIconButton("bell", "Notifications")
        main_layout.addWidget(self.btn_bell)

        self.btn_help = NavIconButton("help", "Help & Support")
        main_layout.addWidget(self.btn_help)

        self.btn_theme = NavIconButton("theme", "Toggle Light / Dark Theme")
        self.btn_theme.clicked.connect(self.theme_toggle_requested.emit)
        main_layout.addWidget(self.btn_theme)

        # 8. Profile Avatar
        self.avatar = ProfileAvatarWidget("AM")
        main_layout.addWidget(self.avatar)

        self.update_theme()

    def _on_home_clicked(self):
        self.set_home_active()
        self.home_clicked.emit()

    def set_home_active(self):
        """Activates Home tab and marks all document tabs inactive."""
        self.is_home_active = True
        self.btn_home.set_active(True)
        self.active_tab_index = -1
        for chip in self.chips:
            chip.set_active(False)

    def set_active_document_tab(self, index: int):
        """Activates document tab at index and marks Home tab inactive."""
        if 0 <= index < len(self.chips):
            self.is_home_active = False
            self.btn_home.set_active(False)
            self.active_tab_index = index
            for i, chip in enumerate(self.chips):
                chip.set_active(i == index)
        elif len(self.chips) == 0:
            self.set_home_active()

    def add_document_tab(self, title: str, file_path: str = "") -> int:
        """Adds a document tab chip to the strip and returns its index."""
        chip = DocumentTabChip(title, file_path, parent=self.tabs_container)
        idx = len(self.chips)
        chip.clicked.connect(lambda i=idx: self._on_chip_clicked(chip))
        chip.close_requested.connect(lambda i=idx: self._on_chip_close(chip))

        self.tabs_layout.addWidget(chip)
        self.chips.append(chip)
        self.set_active_document_tab(idx)
        return idx

    def _on_chip_clicked(self, chip: DocumentTabChip):
        try:
            idx = self.chips.index(chip)
            self.set_active_document_tab(idx)
            self.tab_selected.emit(idx)
        except ValueError:
            pass

    def _on_chip_close(self, chip: DocumentTabChip):
        try:
            idx = self.chips.index(chip)
            self.tab_close_requested.emit(idx)
        except ValueError:
            pass

    def remove_document_tab(self, index: int):
        """Removes document tab chip at index."""
        if 0 <= index < len(self.chips):
            chip = self.chips.pop(index)
            self.tabs_layout.removeWidget(chip)
            chip.setParent(None)
            chip.deleteLater()

            # Re-index remaining chips
            if len(self.chips) == 0:
                self.set_home_active()
            else:
                new_idx = min(index, len(self.chips) - 1)
                self.set_active_document_tab(new_idx)

    def set_tab_dirty(self, index: int, is_dirty: bool):
        if 0 <= index < len(self.chips):
            self.chips[index].set_dirty(is_dirty)

    def set_tab_title(self, index: int, title: str):
        if 0 <= index < len(self.chips):
            self.chips[index].set_title(title)

    def tab_count(self) -> int:
        return len(self.chips)

    def update_theme(self):
        """Updates styling based on current theme tokens."""
        is_dark = ThemeManager.is_dark()
        bg_bar = "#1E1E1E" if is_dark else "#FFFFFF"
        border_col = "#333333" if is_dark else "#D9D9D9"
        text_col = "#F5F5F7" if is_dark else "#242424"
        dim_col = "#A0A0A0" if is_dark else "#626262"
        btn_hover = "#2A2A2A" if is_dark else "#F0F0F0"

        self.setStyleSheet(f"""
            #appNavigationBar {{
                background-color: {bg_bar};
                border-bottom: 1px solid {border_col};
            }}
            #appNavDivider {{
                color: {border_col};
                background-color: {border_col};
            }}
            #appNavAddBtn {{
                background: transparent;
                color: {dim_col};
                border: 1px solid {border_col};
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}
            #appNavAddBtn:hover {{
                background: {btn_hover};
                color: {text_col};
            }}
            #appNavIconBtn {{
                background: transparent;
                color: {dim_col};
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }}
            #appNavIconBtn:hover {{
                background: {btn_hover};
                color: {text_col};
            }}
        """)

        self.brand_label.setStyleSheet(f"color: {text_col}; background: transparent;")

        self.btn_home.update_style()
        for chip in self.chips:
            chip.update_style()

        if hasattr(self, "btn_theme"):
            self.btn_theme.setToolTip("Switch to Light Theme" if is_dark else "Switch to Dark Theme")
            self.btn_theme.update()
        if hasattr(self, "btn_search"):
            self.btn_search.update()
        if hasattr(self, "btn_bell"):
            self.btn_bell.update()
        if hasattr(self, "btn_help"):
            self.btn_help.update()
