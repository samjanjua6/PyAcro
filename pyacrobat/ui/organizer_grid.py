"""
Organize Pages Interactive Workstation (Adobe Acrobat Figma Alignment #3:13380)
Features:
- Left 232px Organize Side Panel: Header, Select Pages dropdown, Range field, Selection Summary pill,
  Tool buttons (Insert, Extract, Replace, Split, Crop, Delete, Page labels), Bottom tip card.
- Center Pages Workspace (Canvas background #E8E8E8):
  - 60px Top Organize Toolbar with modern pill action buttons (Insert, Extract, Replace, Split),
    separators, quick rotation and delete icons, and "Close" pill button.
  - 50px View and selection sub-bar with selection count, "Clear selection" link, and Thumbnail zoom slider.
  - Interactive grid with cards featuring checkboxes (multi-select), drop shadows (0px 2px 7px rgba(0,0,0,0.14)),
    active blue highlight (#DCEAFF / #1473E6), page numbers, titles, and per-card quick action buttons (↺, ↻, 🗑).
  - Smooth fluid drag-and-drop animation with rock-solid card slot snapping.
  - Document footer: "{N} pages • {file_name}".
- Far-Right 48px Navigation Rail with 'pages' tab active.
"""

import os
import re
from typing import List, Any, Optional, Set
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QFrame, QMessageBox, QFileDialog, QScrollArea, QGraphicsDropShadowEffect,
    QComboBox, QLineEdit, QSlider, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QPoint, QRect, QRectF, QByteArray, QPropertyAnimation,
    QEasingCurve, QSize
)
from PySide6.QtGui import (
    QPixmap, QImage, QColor, QMouseEvent, QPainter, QPen, QFont, QCursor
)
from PySide6.QtSvg import QSvgRenderer

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.ui.right_nav_rail import RightNavRail

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")


def _load_themed_svg(icon_name: str, color_hex: str) -> Optional[QSvgRenderer]:
    """Loads an SVG icon from resources/icons and replaces stroke color dynamically."""
    path = os.path.join(ICONS_DIR, f"{icon_name}.svg")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'stroke="#[0-9a-fA-F]{6}"', f'stroke="{color_hex}"', content)
        content = content.replace('#626262', color_hex).replace('#242424', color_hex)
        return QSvgRenderer(QByteArray(content.encode("utf-8")))
    except Exception:
        return None


class OrganizeIconButton(QToolButton):
    """High-DPI vector icon button with custom sizing, padding and hover states."""

    def __init__(self, icon_name: str, tooltip: str, size: int = 32, icon_size: int = 18, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.btn_size = size
        self.icon_size = icon_size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        icon_color = "#D0D0D0" if is_dark else "#242424"
        hover_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.07)"
        self.renderer = _load_themed_svg(self.icon_name, icon_color)
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: {self.btn_size // 2}px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
            }}
            QToolButton:pressed {{
                background-color: {'rgba(255, 255, 255, 0.20)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            x = (self.width() - self.icon_size) / 2.0
            y = (self.height() - self.icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, self.icon_size, self.icon_size))
            painter.end()


class PillToolButton(QToolButton):
    """34px high pill button with border, icon, and label (Figma Organize Toolbar)."""

    def __init__(self, icon_name: Optional[str], text: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.label_text = text
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()
        text_color = tokens.text
        border_color = tokens.border
        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "#F5F5F7"
        pressed_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "#E8E8E8"

        padding_left = 34 if self.icon_name else 16
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {tokens.surface};
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding-left: {padding_left}px;
                padding-right: 16px;
                border: 1px solid {border_color};
                border-radius: 17px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {tokens.border_strong};
            }}
            QToolButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)
        self.setText(self.label_text)
        if self.icon_name:
            self.renderer = _load_themed_svg(self.icon_name, text_color)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.icon_name and self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 16
            x = 12.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


class SidePanelActionButton(QToolButton):
    """Vertical tool button inside Organize Panel (height 40px, left icon + text)."""

    def __init__(self, icon_name: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.label_text = label
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.renderer: Optional[QSvgRenderer] = None
        self.update_theme()

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()
        text_color = tokens.text
        hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        pressed_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.10)"

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {text_color};
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 400;
                padding-left: 38px;
                padding-right: 12px;
                border: none;
                border-radius: 4px;
                text-align: left;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
            }}
            QToolButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)
        self.setText(self.label_text)
        self.renderer = _load_themed_svg(self.icon_name, text_color)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.renderer and self.renderer.isValid():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            icon_size = 18
            x = 10.0
            y = (self.height() - icon_size) / 2.0
            self.renderer.render(painter, QRectF(x, y, icon_size, icon_size))
            painter.end()


# ==============================================================================
# Left Organize Panel (Figma #3:13433 - 232px width)
# ==============================================================================

class OrganizeSidePanel(QFrame):
    """
    Left-hand 232px tool drawer matching Figma Acrobat Organize pages layout:
    - Header & Close X button
    - Page selection combo & range input
    - Selection summary badge
    - Tool actions (Insert, Extract, Replace, Split, Crop, Delete, Page labels)
    - Helpful drag/select tips card
    """

    close_requested = Signal()
    selection_filter_changed = Signal(str)
    range_text_entered = Signal(str)

    insert_requested = Signal()
    extract_requested = Signal()
    replace_requested = Signal()
    split_requested = Signal()
    crop_requested = Signal()
    delete_requested = Signal()
    page_labels_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(232)
        self.setObjectName("organizeSidePanel")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)

        # 1. Title Row ("Organize pages" + close button)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Organize pages")
        self.title_label.setObjectName("organizePanelTitle")
        header_row.addWidget(self.title_label)
        header_row.addStretch()

        self.btn_close = OrganizeIconButton("close-x", "Close Organize Pages", size=26, icon_size=15)
        self.btn_close.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.btn_close)
        layout.addLayout(header_row)

        self.subtitle_label = QLabel("Reorder, rotate, or remove pages.")
        self.subtitle_label.setObjectName("organizePanelSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        layout.addSpacing(4)

        # 2. Select Pages Section
        self.lbl_select_pages = QLabel("Select pages")
        self.lbl_select_pages.setObjectName("organizeSectionLabel")
        layout.addWidget(self.lbl_select_pages)

        self.combo_selection = QComboBox()
        self.combo_selection.addItems(["Custom selection", "All pages", "Even pages", "Odd pages"])
        self.combo_selection.setFixedHeight(34)
        self.combo_selection.setObjectName("organizeCombo")
        self.combo_selection.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo_selection)

        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("e.g. 1-3, 5")
        self.range_input.setFixedHeight(34)
        self.range_input.setObjectName("organizeRangeInput")
        self.range_input.returnPressed.connect(self._on_range_entered)
        layout.addWidget(self.range_input)

        # 3. Selection Summary Banner
        self.summary_badge = QLabel("0 of 0 pages selected")
        self.summary_badge.setObjectName("organizeSummaryBadge")
        self.summary_badge.setAlignment(Qt.AlignCenter)
        self.summary_badge.setFixedHeight(34)
        layout.addWidget(self.summary_badge)

        layout.addWidget(self._create_divider())

        # 4. Action Buttons Stack
        self.btn_insert = SidePanelActionButton("file-plus-2", "Insert")
        self.btn_insert.clicked.connect(self.insert_requested.emit)
        layout.addWidget(self.btn_insert)

        self.btn_extract = SidePanelActionButton("file-output", "Extract")
        self.btn_extract.clicked.connect(self.extract_requested.emit)
        layout.addWidget(self.btn_extract)

        self.btn_replace = SidePanelActionButton("replace", "Replace")
        self.btn_replace.clicked.connect(self.replace_requested.emit)
        layout.addWidget(self.btn_replace)

        self.btn_split = SidePanelActionButton("scissors", "Split")
        self.btn_split.clicked.connect(self.split_requested.emit)
        layout.addWidget(self.btn_split)

        self.btn_crop = SidePanelActionButton("crop", "Crop")
        self.btn_crop.clicked.connect(self.crop_requested.emit)
        layout.addWidget(self.btn_crop)

        self.btn_delete = SidePanelActionButton("trash-2", "Delete")
        self.btn_delete.clicked.connect(self.delete_requested.emit)
        layout.addWidget(self.btn_delete)

        layout.addWidget(self._create_divider())

        self.btn_page_labels = SidePanelActionButton("settings-2", "Page labels")
        self.btn_page_labels.clicked.connect(self.page_labels_requested.emit)
        layout.addWidget(self.btn_page_labels)

        layout.addStretch()

        # 5. Bottom Tip Card
        self.tip_card = QFrame()
        self.tip_card.setObjectName("organizeTipCard")
        self.tip_card.setFixedHeight(82)
        tip_layout = QVBoxLayout(self.tip_card)
        tip_layout.setContentsMargins(12, 10, 12, 10)
        tip_layout.setSpacing(6)

        self.tip_icon = QLabel()
        self.tip_icon.setFixedSize(18, 18)
        tip_layout.addWidget(self.tip_icon)

        self.tip_text = QLabel("Drag thumbnails to reorder pages. Hold Ctrl to select multiple pages.")
        self.tip_text.setWordWrap(True)
        self.tip_text.setObjectName("organizeTipText")
        tip_layout.addWidget(self.tip_text)

        layout.addWidget(self.tip_card)

        self.update_theme()

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("organizeDivider")
        line.setFixedHeight(1)
        return line

    def _on_combo_changed(self, index: int):
        mapping = {0: "custom", 1: "all", 2: "even", 3: "odd"}
        self.selection_filter_changed.emit(mapping.get(index, "custom"))

    def _on_range_entered(self):
        text = self.range_input.text().strip()
        if text:
            self.range_text_entered.emit(text)

    def update_selection_summary(self, selected_count: int, total_count: int, range_str: str = ""):
        self.summary_badge.setText(f"{selected_count} of {total_count} pages selected")
        if range_str:
            self.range_input.blockSignals(True)
            self.range_input.setText(range_str)
            self.range_input.blockSignals(False)

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        self.setStyleSheet(f"""
            QFrame#organizeSidePanel {{
                background-color: {tokens.surface};
                border-right: 1px solid {tokens.border};
            }}
            QLabel#organizePanelTitle {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: 600;
                color: {tokens.text};
                background: transparent;
            }}
            QLabel#organizePanelSubtitle {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 12px;
                color: {tokens.text_muted};
                background: transparent;
            }}
            QLabel#organizeSectionLabel {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: {tokens.text};
                background: transparent;
            }}
            QComboBox#organizeCombo {{
                background-color: {tokens.surface};
                border: 1px solid {tokens.border};
                border-radius: 4px;
                padding: 0px 10px;
                font-size: 12px;
                color: {tokens.text};
            }}
            QComboBox#organizeCombo:hover {{
                border: 1px solid {tokens.border_strong};
            }}
            QLineEdit#organizeRangeInput {{
                background-color: {tokens.surface};
                border: 1px solid {tokens.border};
                border-radius: 4px;
                padding: 0px 10px;
                font-size: 12px;
                color: {tokens.text};
            }}
            QLineEdit#organizeRangeInput:focus {{
                border: 1px solid {tokens.accent};
            }}
            QLabel#organizeSummaryBadge {{
                background-color: {'#1E3A5F' if is_dark else '#EAF3FF'};
                color: {'#60A5FA' if is_dark else '#1473E6'};
                border-radius: 4px;
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 500;
            }}
            QFrame#organizeDivider {{
                background-color: {tokens.border};
                border: none;
            }}
            QFrame#organizeTipCard {{
                background-color: {'#242424' if is_dark else '#F8F8F8'};
                border-radius: 6px;
                border: 1px solid {tokens.border_subtle};
            }}
            QLabel#organizeTipText {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 11px;
                color: {tokens.text_muted};
                background: transparent;
            }}
        """)

        r = _load_themed_svg("move", tokens.text_muted)
        if r and r.isValid():
            pix = QPixmap(18, 18)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            r.render(painter, QRectF(0, 0, 18, 18))
            painter.end()
            self.tip_icon.setPixmap(pix)

        self.btn_close.update_theme()
        for btn in [self.btn_insert, self.btn_extract, self.btn_replace,
                    self.btn_split, self.btn_crop, self.btn_delete, self.btn_page_labels]:
            btn.update_theme()


# ==============================================================================
# Page Card Component with Checkbox, Title, and Per-Card Actions
# ==============================================================================

class CardCheckbox(QToolButton):
    """18x18px custom checkbox matching Figma Organize Pages selection box."""

    toggled_state = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self.is_checked = False
        self.check_renderer: Optional[QSvgRenderer] = None
        self._load_icon()
        self.clicked.connect(self._on_click)

    def _load_icon(self):
        self.check_renderer = _load_themed_svg("check", "#FFFFFF")

    def set_checked(self, checked: bool):
        self.is_checked = checked
        self.update()

    def _on_click(self):
        self.is_checked = not self.is_checked
        self.toggled_state.emit(self.is_checked)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(0.5, 0.5, 17, 17)
        if self.is_checked:
            painter.setBrush(QColor("#1473E6"))
            painter.setPen(QPen(QColor("#1473E6"), 1))
            painter.drawRoundedRect(rect, 3, 3)
            if self.check_renderer and self.check_renderer.isValid():
                self.check_renderer.render(painter, QRectF(2.5, 2.5, 12, 12))
        else:
            tokens = ThemeManager.get_tokens()
            painter.setBrush(QColor(tokens.surface))
            painter.setPen(QPen(QColor(tokens.border), 1))
            painter.drawRoundedRect(rect, 3, 3)

        painter.end()


class PageCardWidget(QFrame):
    """
    Figma-faithful individual Page Card (#3:13510 / #3:13531):
    - Strict, standardized geometry matching Figma slots
    - Upper-left selection checkbox (#3:13523)
    - High-DPI thumbnail sheet with drop shadow (0px 2px 7px rgba(0,0,0,0.14))
    - Active blue outline (#1473E6, 2px) and soft blue card wash (#DCEAFF)
    - Page number (Inter SemiBold 13px) + subtitle title (Inter Regular 11px)
    - Hover quick actions underneath: Rotate CCW, Rotate CW, Delete
    """

    card_clicked = Signal(object, object)
    double_clicked = Signal(object)
    rotate_requested = Signal(int, int)
    delete_requested = Signal(int)
    selection_toggled = Signal(int, bool)

    BASE_CARD_W = 164
    BASE_CARD_H = 276
    BASE_THUMB_W = 150
    BASE_THUMB_H = 195

    def __init__(self, page_index: int, thumbnail_pixmap: Any, title: str = "", parent=None):
        super().__init__(parent)
        self.original_page_index = page_index
        self.page_title = title
        self.is_selected = False
        self.scale_factor = 1.0

        self.setObjectName("organizerPageCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.init_ui(thumbnail_pixmap)

    def init_ui(self, pixmap_data: Any):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 8, 7, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # 1. Top row: Checkbox
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(2, 0, 2, 0)
        self.checkbox = CardCheckbox(self)
        self.checkbox.toggled_state.connect(self._on_checkbox_toggled)
        top_bar.addWidget(self.checkbox)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 2. Thumbnail Slot Container
        self.thumb_container = QFrame(self)
        self.thumb_container.setObjectName("thumbContainer")
        tc_layout = QVBoxLayout(self.thumb_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setAlignment(Qt.AlignCenter)

        self.thumb_label = QLabel(self.thumb_container)
        self.thumb_label.setAlignment(Qt.AlignCenter)

        self.original_pixmap: Optional[QPixmap] = None
        if pixmap_data:
            img = QImage(
                pixmap_data.samples, pixmap_data.width, pixmap_data.height,
                pixmap_data.stride, QImage.Format_RGB888
            )
            self.original_pixmap = QPixmap.fromImage(img)

        tc_layout.addWidget(self.thumb_label)

        # Figma Drop shadow
        self.shadow = QGraphicsDropShadowEffect(self.thumb_container)
        self.shadow.setBlurRadius(8)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(2)
        self.shadow.setColor(QColor(0, 0, 0, 36))
        self.thumb_container.setGraphicsEffect(self.shadow)

        layout.addWidget(self.thumb_container)

        # 3. Caption Container (Page number & subtitle)
        self.caption_container = QWidget(self)
        self.caption_container.setObjectName("captionContainer")
        cc_layout = QVBoxLayout(self.caption_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(2)
        cc_layout.setAlignment(Qt.AlignCenter)

        self.num_label = QLabel(f"{self.original_page_index + 1}", self.caption_container)
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setObjectName("pageNumberLabel")
        cc_layout.addWidget(self.num_label)

        self.subtitle_label = QLabel(self.page_title, self.caption_container)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setObjectName("pageSubtitleLabel")
        if not self.page_title:
            self.subtitle_label.hide()
        cc_layout.addWidget(self.subtitle_label)

        layout.addWidget(self.caption_container)

        # 4. Action buttons row (↺, ↻, 🗑)
        self.actions_container = QWidget(self)
        self.actions_container.setObjectName("actionsContainer")
        act_layout = QHBoxLayout(self.actions_container)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(14)
        act_layout.setAlignment(Qt.AlignCenter)

        self.btn_rot_ccw = OrganizeIconButton("rotate-ccw", "Rotate Left 90°", size=20, icon_size=13)
        self.btn_rot_ccw.clicked.connect(lambda: self.rotate_requested.emit(self.original_page_index, -90))
        act_layout.addWidget(self.btn_rot_ccw)

        self.btn_rot_cw = OrganizeIconButton("rotate-cw", "Rotate Right 90°", size=20, icon_size=13)
        self.btn_rot_cw.clicked.connect(lambda: self.rotate_requested.emit(self.original_page_index, 90))
        act_layout.addWidget(self.btn_rot_cw)

        self.btn_del = OrganizeIconButton("trash-2", "Delete Page", size=20, icon_size=13)
        self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self.original_page_index))
        act_layout.addWidget(self.btn_del)

        layout.addWidget(self.actions_container)

        self.update_dimensions()
        self.update_style()

    def set_scale(self, scale: float):
        self.scale_factor = scale
        self.update_dimensions()

    def update_dimensions(self):
        w = int(self.BASE_CARD_W * self.scale_factor)
        h = int(self.BASE_CARD_H * self.scale_factor)
        tw = int(self.BASE_THUMB_W * self.scale_factor)
        th = int(self.BASE_THUMB_H * self.scale_factor)

        self.setFixedSize(w, h)
        self.thumb_container.setFixedSize(tw, th)

        if self.original_pixmap:
            scaled = self.original_pixmap.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)
            self.thumb_label.setFixedSize(scaled.width(), scaled.height())
        else:
            self.thumb_label.setFixedSize(tw, th)

    def set_page_number(self, num: int):
        self.num_label.setText(f"{num}")

    def set_page_title(self, title: str):
        self.page_title = title
        self.subtitle_label.setText(title)
        self.subtitle_label.setVisible(bool(title))

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.checkbox.set_checked(selected)
        self.update_style()

    def _on_checkbox_toggled(self, checked: bool):
        self.is_selected = checked
        self.update_style()
        self.selection_toggled.emit(self.original_page_index, checked)

    def mousePressEvent(self, event: QMouseEvent):
        self.card_clicked.emit(self, event)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.double_clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def update_style(self):
        tokens = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        if self.is_selected:
            card_bg = "#1E2A3A" if is_dark else "#DCEAFF"
            thumb_border = f"2px solid {tokens.accent}"
            num_color = tokens.accent
        else:
            card_bg = "transparent"
            thumb_border = f"1px solid {tokens.border}"
            num_color = tokens.text

        self.setStyleSheet(f"""
            QFrame#organizerPageCard {{
                background-color: {card_bg};
                border-radius: 6px;
                border: none;
            }}
            QFrame#organizerPageCard QWidget {{
                background: transparent;
                border: none;
            }}
            QFrame#organizerPageCard QLabel {{
                background: transparent;
                border: none;
            }}
            QFrame#thumbContainer {{
                background-color: #FFFFFF;
                border: {thumb_border};
                border-radius: 2px;
            }}
            QLabel#pageNumberLabel {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: {num_color};
            }}
            QLabel#pageSubtitleLabel {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 11px;
                color: {tokens.text_muted};
            }}
        """)
        self.btn_rot_ccw.update_theme()
        self.btn_rot_cw.update_theme()
        self.btn_del.update_theme()


# ==============================================================================
# Interactive Page Canvas with Fluid Card Gliding & Multi-Selection
# ==============================================================================

class InteractivePageCanvas(QWidget):
    """
    Fluid canvas where page cards slide aside smoothly when dragged.
    Maintains exact card slot mathematics and robust drag-and-drop state.
    """

    order_rearranged = Signal(list)
    page_double_clicked = Signal(int)
    selection_changed = Signal()

    SPACING = 24
    MARGIN = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: List[PageCardWidget] = []
        self.animations: List[QPropertyAnimation] = []
        self.selected_indices: Set[int] = set()

        self.drag_card: Optional[PageCardWidget] = None
        self.drag_start_pos: QPoint = QPoint()
        self.drag_offset: QPoint = QPoint()
        self.is_dragging: bool = False
        self.scale_factor: float = 1.0

        self.setObjectName("organizerCanvasArea")
        self.setMouseTracking(True)

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        self.setStyleSheet(f"""
            QWidget#organizerCanvasArea {{
                background-color: {tokens.canvas_bg};
            }}
        """)
        for c in self.cards:
            c.update_style()

    def set_cards(self, thumbnails: List[Any], titles: Optional[List[str]] = None):
        for c in self.cards:
            c.setParent(None)
            c.deleteLater()
        self.cards.clear()
        self.animations.clear()
        self.selected_indices.clear()

        for idx, pix in enumerate(thumbnails):
            title = titles[idx] if titles and idx < len(titles) else ""
            card = PageCardWidget(page_index=idx, thumbnail_pixmap=pix, title=title, parent=self)
            card.set_scale(self.scale_factor)
            card.card_clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.selection_toggled.connect(self._on_card_checkbox_toggled)
            card.rotate_requested.connect(self._on_card_rotate_requested)
            card.delete_requested.connect(self._on_card_delete_requested)
            card.show()
            self.cards.append(card)

        if self.cards:
            self.selected_indices.add(0)
            self.cards[0].set_selected(True)

        self.relayout_cards(animate=False)
        self.selection_changed.emit()

    def set_scale(self, scale: float):
        self.scale_factor = scale
        for c in self.cards:
            c.set_scale(scale)
        self.relayout_cards(animate=False)

    @property
    def card_width(self) -> int:
        return int(PageCardWidget.BASE_CARD_W * self.scale_factor)

    @property
    def card_height(self) -> int:
        return int(PageCardWidget.BASE_CARD_H * self.scale_factor)

    def calculate_columns(self) -> int:
        available_w = max(self.card_width + 2 * self.MARGIN, self.width())
        cols = (available_w - 2 * self.MARGIN + self.SPACING) // (self.card_width + self.SPACING)
        return max(1, int(cols))

    def calculate_slot_pos(self, slot_idx: int) -> QPoint:
        cols = self.calculate_columns()
        col = slot_idx % cols
        row = slot_idx // cols
        x = self.MARGIN + col * (self.card_width + self.SPACING)
        y = self.MARGIN + row * (self.card_height + self.SPACING)
        return QPoint(int(x), int(y))

    def relayout_cards(self, animate: bool = True):
        cols = self.calculate_columns()
        total_rows = (len(self.cards) + cols - 1) // cols if self.cards else 1
        canvas_h = self.MARGIN * 2 + total_rows * (self.card_height + self.SPACING)
        self.setFixedHeight(max(400, int(canvas_h)))

        for a in self.animations:
            a.stop()
        self.animations.clear()

        for i, card in enumerate(self.cards):
            target_pos = self.calculate_slot_pos(i)
            if card == self.drag_card:
                continue

            if animate and card.isVisible() and card.pos() != target_pos:
                anim = QPropertyAnimation(card, b"pos", self)
                anim.setDuration(160)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.setEndValue(target_pos)
                anim.start()
                self.animations.append(anim)
            else:
                card.move(target_pos)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_cards(animate=False)

    # Selection Helpers
    def select_all(self):
        self.selected_indices = set(range(len(self.cards)))
        for c in self.cards:
            c.set_selected(True)
        self.selection_changed.emit()

    def select_even(self):
        self.selected_indices = {i for i in range(len(self.cards)) if (i + 1) % 2 == 0}
        for i, c in enumerate(self.cards):
            c.set_selected(i in self.selected_indices)
        self.selection_changed.emit()

    def select_odd(self):
        self.selected_indices = {i for i in range(len(self.cards)) if (i + 1) % 2 != 0}
        for i, c in enumerate(self.cards):
            c.set_selected(i in self.selected_indices)
        self.selection_changed.emit()

    def clear_selection(self):
        self.selected_indices.clear()
        for c in self.cards:
            c.set_selected(False)
        self.selection_changed.emit()

    def select_range_string(self, text: str):
        indices = set()
        parts = text.replace("–", "-").split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                tokens = part.split("-")
                if len(tokens) == 2 and tokens[0].isdigit() and tokens[1].isdigit():
                    start, end = int(tokens[0]), int(tokens[1])
                    for p in range(min(start, end), max(start, end) + 1):
                        if 1 <= p <= len(self.cards):
                            indices.add(p - 1)
            elif part.isdigit():
                p = int(part)
                if 1 <= p <= len(self.cards):
                    indices.add(p - 1)

        if indices:
            self.selected_indices = indices
            for i, c in enumerate(self.cards):
                c.set_selected(i in self.selected_indices)
            self.selection_changed.emit()

    def get_range_string(self) -> str:
        if not self.selected_indices:
            return ""
        sorted_pages = sorted(i + 1 for i in self.selected_indices)
        ranges = []
        start = end = sorted_pages[0]
        for p in sorted_pages[1:]:
            if p == end + 1:
                end = p
            else:
                ranges.append(f"{start}–{end}" if start != end else f"{start}")
                start = end = p
        ranges.append(f"{start}–{end}" if start != end else f"{start}")
        return ", ".join(ranges)

    def _on_card_clicked(self, card: PageCardWidget, event: QMouseEvent):
        idx = self.cards.index(card)
        if event.modifiers() & Qt.ControlModifier:
            if idx in self.selected_indices:
                self.selected_indices.remove(idx)
                card.set_selected(False)
            else:
                self.selected_indices.add(idx)
                card.set_selected(True)
        elif event.modifiers() & Qt.ShiftModifier and self.selected_indices:
            last = max(self.selected_indices)
            step = 1 if idx >= last else -1
            for i in range(last, idx + step, step):
                self.selected_indices.add(i)
                self.cards[i].set_selected(True)
        else:
            self.selected_indices = {idx}
            for c in self.cards:
                c.set_selected(c == card)

        self.selection_changed.emit()

    def _on_card_double_clicked(self, card: PageCardWidget):
        self.page_double_clicked.emit(card.original_page_index + 1)

    def _on_card_checkbox_toggled(self, page_index: int, is_selected: bool):
        for idx, c in enumerate(self.cards):
            if c.original_page_index == page_index:
                if is_selected:
                    self.selected_indices.add(idx)
                else:
                    self.selected_indices.discard(idx)
                break
        self.selection_changed.emit()

    def _on_card_rotate_requested(self, page_index: int, degrees: int):
        parent = self.parentWidget()
        while parent and not isinstance(parent, OrganizerGridWidget):
            parent = parent.parentWidget()
        if parent:
            parent.rotate_requested.emit([page_index], degrees)

    def _on_card_delete_requested(self, page_index: int):
        parent = self.parentWidget()
        while parent and not isinstance(parent, OrganizerGridWidget):
            parent = parent.parentWidget()
        if parent:
            parent._on_delete_specific([page_index])

    # Drag Reordering
    def _card_at_pos(self, pos: QPoint) -> Optional[PageCardWidget]:
        for card in self.cards:
            if card.geometry().contains(pos):
                return card
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            card = self._card_at_pos(pos)
            if card:
                self.drag_card = card
                self.drag_start_pos = pos
                self.drag_offset = pos - card.pos()
                self.is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_card and (event.buttons() & Qt.LeftButton):
            pos = event.position().toPoint()
            if not self.is_dragging:
                if (pos - self.drag_start_pos).manhattanLength() > 6:
                    self.is_dragging = True
                    self.drag_card.raise_()

            if self.is_dragging:
                self.drag_card.move(pos - self.drag_offset)
                curr_idx = self.cards.index(self.drag_card)

                for slot_idx in range(len(self.cards)):
                    if slot_idx == curr_idx:
                        continue
                    slot_center = self.calculate_slot_pos(slot_idx) + QPoint(
                        self.card_width // 2, self.card_height // 2
                    )
                    card_center = self.drag_card.pos() + QPoint(
                        self.card_width // 2, self.card_height // 2
                    )
                    if (card_center - slot_center).manhattanLength() < self.card_width // 2:
                        self.cards.remove(self.drag_card)
                        self.cards.insert(slot_idx, self.drag_card)
                        self.relayout_cards(animate=True)
                        break
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.drag_card:
            self.drag_card = None
            self.relayout_cards(animate=False)
            if self.is_dragging:
                new_order = [c.original_page_index for c in self.cards]
                new_sel = set()
                for i, c in enumerate(self.cards):
                    if c.is_selected:
                        new_sel.add(i)
                    c.original_page_index = i
                    c.set_page_number(i + 1)
                self.selected_indices = new_sel
                self.order_rearranged.emit(new_order)
                self.selection_changed.emit()
            self.is_dragging = False
        super().mouseReleaseEvent(event)


# ==============================================================================
# Master Organize Pages Workstation (3-Column Layout Matching Figma #3:13380)
# ==============================================================================

class OrganizerGridWidget(QWidget):
    """
    Visual workstation for managing document pages matching Figma #3:13380:
    - Left Column: 232px OrganizeSidePanel
    - Center Column: 60px Organize Toolbar + 50px Subbar + Canvas + Clean Footer
    - Right Column: 48px RightNavRail (Pages/Thumbnails active)
    """

    back_to_reading_requested = Signal()
    page_double_clicked = Signal(int)
    reorder_requested = Signal(list)
    rotate_requested = Signal(list, int)
    delete_requested = Signal(list)
    insert_blank_requested = Signal(int)
    duplicate_requested = Signal(list)
    merge_requested = Signal()
    extract_requested = Signal(list)
    replace_requested = Signal(list)
    split_requested = Signal(list)
    crop_requested = Signal(list)
    page_labels_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc_filename: str = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # Column 1: Left Organize Side Panel (232px)
        # ----------------------------------------------------------------------
        self.side_panel = OrganizeSidePanel(self)
        self.side_panel.close_requested.connect(self.back_to_reading_requested.emit)
        self.side_panel.selection_filter_changed.connect(self._on_selection_filter)
        self.side_panel.range_text_entered.connect(self._on_range_entered)

        self.side_panel.insert_requested.connect(self._on_insert_blank)
        self.side_panel.extract_requested.connect(self._on_extract)
        self.side_panel.replace_requested.connect(self._on_replace)
        self.side_panel.split_requested.connect(self._on_split)
        self.side_panel.crop_requested.connect(self._on_crop)
        self.side_panel.delete_requested.connect(self._on_delete)
        self.side_panel.page_labels_requested.connect(self.page_labels_requested.emit)
        main_layout.addWidget(self.side_panel)

        # ----------------------------------------------------------------------
        # Column 2: Center Pages Workspace (Organize Toolbar + Canvas + Footer)
        # ----------------------------------------------------------------------
        center_container = QWidget(self)
        center_container.setObjectName("centerWorkspace")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # 1. 60px Organize Top Toolbar
        self.toolbar_frame = QFrame(center_container)
        self.toolbar_frame.setObjectName("organizeTopToolbar")
        self.toolbar_frame.setFixedHeight(60)
        tb_layout = QHBoxLayout(self.toolbar_frame)
        tb_layout.setContentsMargins(28, 0, 28, 0)
        tb_layout.setSpacing(16)
        tb_layout.setAlignment(Qt.AlignVCenter)

        # Pill Action Buttons
        self.tb_insert = PillToolButton("file-plus-2", "Insert")
        self.tb_insert.clicked.connect(self._on_insert_blank)
        tb_layout.addWidget(self.tb_insert)

        self.tb_extract = PillToolButton("file-output", "Extract")
        self.tb_extract.clicked.connect(self._on_extract)
        tb_layout.addWidget(self.tb_extract)

        self.tb_replace = PillToolButton("replace", "Replace")
        self.tb_replace.clicked.connect(self._on_replace)
        tb_layout.addWidget(self.tb_replace)

        self.tb_split = PillToolButton("scissors", "Split")
        self.tb_split.clicked.connect(self._on_split)
        tb_layout.addWidget(self.tb_split)

        tb_layout.addWidget(self._create_v_separator())

        # Quick icon buttons (Rotate CCW, Rotate CW, Delete)
        self.tb_rot_ccw = OrganizeIconButton("rotate-ccw", "Rotate Left 90° (↺)", size=32, icon_size=18)
        self.tb_rot_ccw.clicked.connect(lambda: self._on_rotate(-90))
        tb_layout.addWidget(self.tb_rot_ccw)

        self.tb_rot_cw = OrganizeIconButton("rotate-cw", "Rotate Right 90° (↻)", size=32, icon_size=18)
        self.tb_rot_cw.clicked.connect(lambda: self._on_rotate(90))
        tb_layout.addWidget(self.tb_rot_cw)

        self.tb_delete = OrganizeIconButton("trash-2", "Delete Selected Pages", size=32, icon_size=18)
        self.tb_delete.clicked.connect(self._on_delete)
        tb_layout.addWidget(self.tb_delete)

        tb_layout.addStretch()

        # Close Pill Button
        self.tb_close = PillToolButton(None, "Close")
        self.tb_close.clicked.connect(self.back_to_reading_requested.emit)
        tb_layout.addWidget(self.tb_close)

        center_layout.addWidget(self.toolbar_frame)

        # 2. 52px View and Selection Sub-bar
        self.subbar_frame = QWidget(center_container)
        self.subbar_frame.setObjectName("organizeSubbar")
        self.subbar_frame.setFixedHeight(52)
        sb_layout = QHBoxLayout(self.subbar_frame)
        sb_layout.setContentsMargins(34, 0, 34, 0)
        sb_layout.setSpacing(16)
        sb_layout.setAlignment(Qt.AlignVCenter)

        # Left: Selection Summary & Clear Link
        self.lbl_view_selection = QLabel("0 pages selected")
        self.lbl_view_selection.setObjectName("organizeSelectionSummaryLabel")
        sb_layout.addWidget(self.lbl_view_selection)

        self.btn_clear_selection = QToolButton()
        self.btn_clear_selection.setText("Clear selection")
        self.btn_clear_selection.setObjectName("organizeClearSelectionLink")
        self.btn_clear_selection.setCursor(Qt.PointingHandCursor)
        self.btn_clear_selection.clicked.connect(self._on_clear_selection)
        sb_layout.addWidget(self.btn_clear_selection)

        sb_layout.addStretch()

        # Right: Thumbnail Size Controls
        self.btn_zoom_out = OrganizeIconButton("minus", "Smaller Thumbnails", size=24, icon_size=14)
        self.btn_zoom_out.clicked.connect(self._zoom_out_thumbnails)
        sb_layout.addWidget(self.btn_zoom_out)

        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(70, 150)
        self.slider_zoom.setValue(100)
        self.slider_zoom.setFixedWidth(90)
        self.slider_zoom.setObjectName("organizeZoomSlider")
        self.slider_zoom.valueChanged.connect(self._on_zoom_slider_changed)
        sb_layout.addWidget(self.slider_zoom)

        self.btn_zoom_in = OrganizeIconButton("plus", "Larger Thumbnails", size=24, icon_size=14)
        self.btn_zoom_in.clicked.connect(self._zoom_in_thumbnails)
        sb_layout.addWidget(self.btn_zoom_in)

        center_layout.addWidget(self.subbar_frame)

        # 3. Canvas Scroll Area
        self.scroll_area = QScrollArea(center_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("organizerCanvasArea")

        self.canvas = InteractivePageCanvas(self.scroll_area)
        self.canvas.order_rearranged.connect(self.reorder_requested.emit)
        self.canvas.page_double_clicked.connect(self.page_double_clicked.emit)
        self.canvas.selection_changed.connect(self._on_selection_changed)

        self.scroll_area.setWidget(self.canvas)
        center_layout.addWidget(self.scroll_area)

        # 4. Clean Canvas Bottom Footer (Anchored below canvas matching Figma #3:13736)
        self.footer_frame = QWidget(center_container)
        self.footer_frame.setObjectName("organizeFooterFrame")
        self.footer_frame.setFixedHeight(30)
        ff_layout = QHBoxLayout(self.footer_frame)
        ff_layout.setContentsMargins(0, 0, 0, 8)
        ff_layout.setAlignment(Qt.AlignCenter)

        self.footer_label = QLabel(self.footer_frame)
        self.footer_label.setObjectName("organizerFooterLabel")
        self.footer_label.setAlignment(Qt.AlignCenter)
        ff_layout.addWidget(self.footer_label)

        center_layout.addWidget(self.footer_frame)

        main_layout.addWidget(center_container)

        # ----------------------------------------------------------------------
        # Column 3: Far-Right Navigation Rail (48px fixed)
        # ----------------------------------------------------------------------
        self.right_nav_rail = RightNavRail(self)
        self.right_nav_rail.set_active_tab("pages")
        main_layout.addWidget(self.right_nav_rail)

        self.update_theme()

    def _create_v_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setObjectName("toolbarSeparator")
        sep.setFixedSize(1, 24)
        return sep

    def populate_grid(self, thumbnails: List[Any], file_name: str = "", bookmarks: Optional[List[Any]] = None):
        titles = None
        if bookmarks:
            titles = [""] * len(thumbnails)
            for item in bookmarks:
                if len(item) >= 3:
                    title, page_num = item[1], item[2]
                    if 1 <= page_num <= len(thumbnails) and not titles[page_num - 1]:
                        titles[page_num - 1] = str(title)

        self.doc_filename = file_name
        self.canvas.set_cards(thumbnails, titles)
        self._update_footer()
        self._on_selection_changed()

    def _update_footer(self):
        total = len(self.canvas.cards)
        if total > 0:
            name_part = f" • {self.doc_filename}" if self.doc_filename else ""
            self.footer_label.setText(f"{total} pages{name_part}")
            self.footer_frame.show()
        else:
            self.footer_frame.hide()

    def get_selected_indices(self) -> List[int]:
        return sorted(list(self.canvas.selected_indices))

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        self.toolbar_frame.setStyleSheet(f"""
            QFrame#organizeTopToolbar {{
                background-color: {tokens.surface};
                border-bottom: 1px solid {tokens.border};
            }}
            QFrame#toolbarSeparator {{
                background-color: {tokens.border};
                border: none;
            }}
        """)

        self.subbar_frame.setStyleSheet(f"""
            QWidget#organizeSubbar {{
                background-color: {tokens.canvas_bg};
            }}
            QLabel#organizeSelectionSummaryLabel {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: {tokens.text};
                background: transparent;
            }}
            QToolButton#organizeClearSelectionLink {{
                background: transparent;
                border: none;
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 12px;
                color: {tokens.accent};
                padding: 0px;
            }}
            QToolButton#organizeClearSelectionLink:hover {{
                text-decoration: underline;
                color: {tokens.accent_hover};
            }}
            QSlider#organizeZoomSlider::groove:horizontal {{
                height: 3px;
                background: {tokens.border};
                border-radius: 1px;
            }}
            QSlider#organizeZoomSlider::sub-page:horizontal {{
                height: 3px;
                background: {tokens.accent};
                border-radius: 1px;
            }}
            QSlider#organizeZoomSlider::handle:horizontal {{
                background: {tokens.accent};
                border: none;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }}
            QSlider#organizeZoomSlider::handle:horizontal:hover {{
                background: {tokens.accent_hover};
            }}
        """)

        self.scroll_area.setStyleSheet(f"""
            QScrollArea#organizerCanvasArea {{
                background-color: {tokens.canvas_bg};
                border: none;
            }}
        """)

        self.footer_frame.setStyleSheet(f"""
            QWidget#organizeFooterFrame {{
                background-color: {tokens.canvas_bg};
            }}
            QLabel#organizerFooterLabel {{
                font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
                font-size: 11px;
                color: {tokens.text_muted};
                background: transparent;
            }}
        """)

        self.side_panel.update_theme()
        self.canvas.update_theme()
        self.right_nav_rail.update_theme()

        self.tb_insert.update_theme()
        self.tb_extract.update_theme()
        self.tb_replace.update_theme()
        self.tb_split.update_theme()
        self.tb_close.update_theme()

        self.tb_rot_ccw.update_theme()
        self.tb_rot_cw.update_theme()
        self.tb_delete.update_theme()
        self.btn_zoom_out.update_theme()
        self.btn_zoom_in.update_theme()

    def _on_selection_changed(self):
        sel_count = len(self.canvas.selected_indices)
        total = len(self.canvas.cards)
        range_str = self.canvas.get_range_string()

        self.lbl_view_selection.setText(f"{sel_count} pages selected" if sel_count != 1 else "1 page selected")
        self.side_panel.update_selection_summary(sel_count, total, range_str)
        self._update_footer()

    def _on_clear_selection(self):
        self.canvas.clear_selection()

    def _on_selection_filter(self, filter_type: str):
        if filter_type == "all":
            self.canvas.select_all()
        elif filter_type == "even":
            self.canvas.select_even()
        elif filter_type == "odd":
            self.canvas.select_odd()

    def _on_range_entered(self, range_text: str):
        self.canvas.select_range_string(range_text)

    def _on_zoom_slider_changed(self, value: int):
        scale = value / 100.0
        self.canvas.set_scale(scale)

    def _zoom_in_thumbnails(self):
        val = min(self.slider_zoom.maximum(), self.slider_zoom.value() + 15)
        self.slider_zoom.setValue(val)

    def _zoom_out_thumbnails(self):
        val = max(self.slider_zoom.minimum(), self.slider_zoom.value() - 15)
        self.slider_zoom.setValue(val)

    # Operations
    def _on_rotate(self, degrees: int):
        sel = self.get_selected_indices()
        if sel:
            self.rotate_requested.emit(sel, degrees)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select one or more pages to rotate.")

    def _on_delete(self):
        sel = self.get_selected_indices()
        if not sel:
            QMessageBox.information(self, "No Page Selected", "Please select one or more pages to delete.")
            return

        self._on_delete_specific(sel)

    def _on_delete_specific(self, page_indices: List[int]):
        if len(self.canvas.cards) <= len(page_indices):
            QMessageBox.warning(self, "Cannot Delete", "A document must contain at least one page.")
            return

        pages_desc = ", ".join(str(p + 1) for p in page_indices)
        ret = QMessageBox.question(
            self,
            "Delete Pages",
            f"Are you sure you want to permanently delete page(s) {pages_desc}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.delete_requested.emit(page_indices)

    def _on_insert_blank(self):
        sel = self.get_selected_indices()
        insert_idx = sel[-1] + 1 if sel else len(self.canvas.cards)
        self.insert_blank_requested.emit(insert_idx)

    def _on_duplicate(self):
        sel = self.get_selected_indices()
        if sel:
            self.duplicate_requested.emit(sel)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select one or more pages to duplicate.")

    def _on_extract(self):
        sel = self.get_selected_indices()
        if sel:
            self.extract_requested.emit(sel)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select one or more pages to extract.")

    def _on_replace(self):
        sel = self.get_selected_indices()
        if sel:
            self.replace_requested.emit(sel)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select a page to replace.")

    def _on_split(self):
        sel = self.get_selected_indices()
        self.split_requested.emit(sel)

    def _on_crop(self):
        sel = self.get_selected_indices()
        self.crop_requested.emit(sel)
