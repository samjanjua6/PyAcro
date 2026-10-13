"""
ThumbnailsPanel — Phase 6 Modern Acrobat Right Drawer Component
Page thumbnails side panel matching Figma Acrobat design (268px fixed width).

Layout:
  ┌─ Header ───────────────────────────────────────────┐
  │  Page Thumbnails                           [✕]     │
  │  4 pages                                           │
  ├─ Gallery (Vertical scroll) ────────────────────────┤
  │   ┌──────────────┐                                 │
  │   │  [Preview]   │                                 │
  │   └──────────────┘                                 │
  │       Page 1                                       │
  │                                                    │
  │   ┌──────────────┐ (Active: blue border #1473E6)   │
  │   │  [Preview]   │                                 │
  │   └──────────────┘                                 │
  │       Page 2                                       │
  └────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
from typing import List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QPainter

from pyacrobat.ui.styles import ThemeManager


class ThumbnailCard(QFrame):
    """
    Card representing a single page thumbnail.
    Renders drop-shadow, preview image, and page number label.
    """

    clicked = Signal(int)  # 1-indexed page number

    def __init__(self, page_num: int, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.page_num = page_num
        self.pixmap = pixmap
        self.is_active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._init_ui()
        self.update_theme()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Thumbnail Image Label
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setObjectName("thumbnailImgLabel")
        if not self.pixmap.isNull():
            # Scale proportionally to fit 170px width
            scaled = self.pixmap.scaledToWidth(170, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled)
        layout.addWidget(self.img_label)

        # Page Number Label
        self.lbl_page = QLabel(f"Page {self.page_num}")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setObjectName("thumbnailPageLabel")
        layout.addWidget(self.lbl_page)

    def set_active(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self.update_theme()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.page_num)
        super().mousePressEvent(event)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        if self.is_active:
            bg = "#1E293B" if is_dark else "#EAF3FF"
            border = "2px solid #1473E6"
            page_color = "#3B82F6" if is_dark else "#1473E6"
            font_weight = "bold"
        else:
            bg = "#252528" if is_dark else "#FFFFFF"
            border = "1px solid #383838" if is_dark else "1px solid #E0E0E0"
            page_color = "#A0A0A0" if is_dark else "#626262"
            font_weight = "500"

        hover_bg = "#2D2D32" if is_dark else "#F4F7FC"
        hover_border = "#505050" if is_dark else "#B0B0B0"

        self.setStyleSheet(f"""
            ThumbnailCard {{
                background-color: {bg};
                border: {border};
                border-radius: 8px;
            }}
            ThumbnailCard:hover {{
                background-color: {hover_bg if not self.is_active else bg};
                border: {hover_border if not self.is_active else border};
            }}
        """)

        img_border = "#444444" if is_dark else "#D0D0D0"
        self.img_label.setStyleSheet(f"""
            QLabel#thumbnailImgLabel {{
                background-color: {'#18181A' if is_dark else '#F0F0F0'};
                border: 1px solid {img_border};
                border-radius: 4px;
                padding: 2px;
            }}
        """)

        self.lbl_page.setStyleSheet(f"""
            QLabel#thumbnailPageLabel {{
                color: {page_color};
                font-size: 11px;
                font-weight: {font_weight};
                background: transparent;
                border: none;
            }}
        """)


class PageThumbnailsPanel(QWidget):
    """
    Right-docked Page Thumbnails side panel (268px fixed width).
    Matches Adobe Acrobat and Figma design standards.
    """

    page_selected = Signal(int)   # 1-indexed page number
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(268)
        self._cards: List[ThumbnailCard] = []
        self._current_page = 1
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Scroll Area ──────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setObjectName("thumbnailsPanelScroll")

        self._content = QWidget()
        self._content.setObjectName("thumbnailsPanelContent")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(14, 18, 14, 18)
        self._layout.setSpacing(12)
        self._layout.setAlignment(Qt.AlignTop)

        # ── Header ──────────────────────────────────────────────────────
        header_col = QVBoxLayout()
        header_col.setSpacing(4)

        # Title row: "Page Thumbnails" + [✕]
        title_row = QHBoxLayout()
        self.lbl_title = QLabel("Page Thumbnails")
        self.lbl_title.setObjectName("thumbnailsPanelTitle")
        title_row.addWidget(self.lbl_title)
        title_row.addStretch()

        btn_close = QToolButton()
        btn_close.setObjectName("thumbnailsPanelCloseBtn")
        btn_close.setFixedSize(22, 22)
        btn_close.setText("✕")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close_requested.emit)
        title_row.addWidget(btn_close)
        header_col.addLayout(title_row)

        # Page count label: "X pages"
        self.lbl_count = QLabel("0 pages")
        self.lbl_count.setObjectName("thumbnailsCount")
        header_col.addWidget(self.lbl_count)

        self._layout.addLayout(header_col)

        # ── Divider ──────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("thumbnailsDivider")
        self._layout.addWidget(divider)

        # ── Cards Container ──────────────────────────────────────────────
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)
        self._cards_layout.setSpacing(12)
        self._layout.addWidget(self._cards_container)

        self._layout.addStretch()

        self.scroll.setWidget(self._content)
        outer.addWidget(self.scroll)

        self.update_theme()

    def load_thumbnails(self, pixmaps: List[Any]):
        """
        Populates cards from rendered pixmaps (fitz.Pixmap or QPixmap).
        """
        # Clear existing cards
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        count = len(pixmaps)
        self.lbl_count.setText(f"{count} page{'s' if count != 1 else ''}")

        for idx, item in enumerate(pixmaps):
            page_num = idx + 1
            if isinstance(item, QPixmap):
                qpix = item
            elif hasattr(item, "samples"):
                # fitz.Pixmap
                img = QImage(item.samples, item.width, item.height, item.stride, QImage.Format_RGB888).copy()
                qpix = QPixmap.fromImage(img)
            else:
                qpix = QPixmap()

            card = ThumbnailCard(page_num, qpix, self._cards_container)
            card.clicked.connect(self._on_card_clicked)
            if page_num == self._current_page:
                card.set_active(True)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

    def set_current_page(self, page_num: int):
        """Highlights the active page card and scrolls to it if needed."""
        self._current_page = page_num
        for card in self._cards:
            is_active = (card.page_num == page_num)
            card.set_active(is_active)
            if is_active:
                self.scroll.ensureWidgetVisible(card, 0, 50)

    def _on_card_clicked(self, page_num: int):
        self.set_current_page(page_num)
        self.page_selected.emit(page_num)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#18181A" if is_dark else "#FFFFFF"
        border = "#333333" if is_dark else "#D9D9D9"
        title_color = "#F5F5F7" if is_dark else "#242424"
        count_color = "#A0A0A0" if is_dark else "#626262"
        divider_color = "#2E2E32" if is_dark else "#E8E8E8"
        close_hover = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"

        self.setStyleSheet(f"""
            PageThumbnailsPanel {{
                background-color: {bg};
                border-left: 1px solid {border};
            }}
            #thumbnailsPanelScroll, #thumbnailsPanelContent {{
                background-color: {bg};
                border: none;
            }}
            QLabel#thumbnailsPanelTitle {{
                font-size: 16px;
                font-weight: 600;
                color: {title_color};
            }}
            QLabel#thumbnailsCount {{
                font-size: 12px;
                font-weight: 500;
                color: {count_color};
            }}
            QFrame#thumbnailsDivider {{
                background-color: {divider_color};
                border: none;
                max-height: 1px;
                min-height: 1px;
            }}
            QToolButton#thumbnailsPanelCloseBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {count_color};
                font-size: 12px;
            }}
            QToolButton#thumbnailsPanelCloseBtn:hover {{
                background-color: {close_hover};
                color: {title_color};
            }}
        """)

        for card in self._cards:
            card.update_theme()
