"""
BookmarksPanel — Phase 6 Modern Acrobat Right Drawer Component
Bookmarks & Table of Contents side panel matching Figma Acrobat design (268px fixed width).

Layout:
  ┌─ Header ───────────────────────────────────────────┐
  │  Bookmarks                                 [✕]     │
  │  Table of Contents                                 │
  ├─ Outline Tree / Empty State ───────────────────────┤
  │   ▼ Chapter 1: Introduction            p. 1        │
  │     - 1.1 Overview                     p. 2        │
  │   ► Chapter 2: System Architecture     p. 5        │
  └────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
from typing import List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QTreeWidget, QTreeWidgetItem, QFrame, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon

from pyacrobat.ui.styles import ThemeManager


class BookmarksPanel(QWidget):
    """
    Right-docked Bookmarks & Table of Contents panel (268px fixed width).
    Matches Adobe Acrobat and Figma design standards.
    """

    page_selected = Signal(int)   # 1-indexed page number
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.resize(268, 800)
        self._current_page = 1
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 18, 14, 18)
        outer.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────
        header_col = QVBoxLayout()
        header_col.setSpacing(4)

        # Title row: "Bookmarks" + [✕]
        title_row = QHBoxLayout()
        self.lbl_title = QLabel("Bookmarks")
        self.lbl_title.setObjectName("bookmarksPanelTitle")
        title_row.addWidget(self.lbl_title)
        title_row.addStretch()

        btn_close = QToolButton()
        btn_close.setObjectName("bookmarksPanelCloseBtn")
        btn_close.setFixedSize(22, 22)
        btn_close.setText("✕")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close_requested.emit)
        title_row.addWidget(btn_close)
        header_col.addLayout(title_row)

        # Subtitle
        self.lbl_subtitle = QLabel("Table of Contents")
        self.lbl_subtitle.setObjectName("bookmarksSubtitle")
        header_col.addWidget(self.lbl_subtitle)

        outer.addLayout(header_col)

        # ── Divider ──────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("bookmarksDivider")
        outer.addWidget(divider)

        # ── Stack for Tree vs Empty State ────────────────────────────────
        self.stack = QStackedWidget()

        # Page 0: Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setIndentation(16)
        self.tree.setObjectName("bookmarksTreeWidget")
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.stack.addWidget(self.tree)

        # Page 1: Empty State
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(12, 40, 12, 20)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignCenter)

        self.lbl_empty_icon = QLabel("📑")
        self.lbl_empty_icon.setAlignment(Qt.AlignCenter)
        self.lbl_empty_icon.setStyleSheet("font-size: 32px;")
        empty_layout.addWidget(self.lbl_empty_icon)

        self.lbl_empty_title = QLabel("No Bookmarks Found")
        self.lbl_empty_title.setAlignment(Qt.AlignCenter)
        self.lbl_empty_title.setObjectName("bookmarksEmptyTitle")
        empty_layout.addWidget(self.lbl_empty_title)

        self.lbl_empty_desc = QLabel("This document does not contain an outline or bookmarks table.")
        self.lbl_empty_desc.setAlignment(Qt.AlignCenter)
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setObjectName("bookmarksEmptyDesc")
        empty_layout.addWidget(self.lbl_empty_desc)
        empty_layout.addStretch()

        self.stack.addWidget(self.empty_widget)
        outer.addWidget(self.stack)

        self.update_theme()

    def load_outline(self, toc: List[List[Any]]):
        """
        Populates tree from PyMuPDF toc: [[lvl, title, page_num], ...].
        """
        self.tree.clear()
        if not toc:
            self.lbl_subtitle.setText("0 items")
            self.stack.setCurrentIndex(1)  # Empty state
            return

        self.lbl_subtitle.setText(f"{len(toc)} bookmark{'s' if len(toc) != 1 else ''}")
        self.stack.setCurrentIndex(0)  # Tree view

        # Build hierarchical tree using stack
        # stack stores pairs of (level, parent_item_or_tree)
        stack = [(0, self.tree)]
        for entry in toc:
            lvl = entry[0]
            title = str(entry[1])
            page = int(entry[2]) if len(entry) > 2 and entry[2] is not None else 1

            # Adjust stack to find correct parent for this lvl
            while stack and stack[-1][0] >= lvl:
                stack.pop()

            parent = stack[-1][1] if stack else self.tree

            node = QTreeWidgetItem(parent, [title, f"p. {page}"])
            node.setData(0, Qt.UserRole, page)
            node.setToolTip(0, f"{title} (Page {page})")

            # Allow expanding children
            stack.append((lvl, node))

        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)

    def set_current_page(self, page_num: int):
        self._current_page = page_num
        # Find item matching page_num and select it if exact match
        def find_and_select(item: QTreeWidgetItem) -> bool:
            if item.data(0, Qt.UserRole) == page_num:
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if find_and_select(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if find_and_select(self.tree.topLevelItem(i)):
                break

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        page = item.data(0, Qt.UserRole)
        if page:
            self.page_selected.emit(page)

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#18181A" if is_dark else "#FFFFFF"
        border = "#333333" if is_dark else "#D9D9D9"
        title_color = "#F5F5F7" if is_dark else "#242424"
        subtitle_color = "#A0A0A0" if is_dark else "#626262"
        divider_color = "#2E2E32" if is_dark else "#E8E8E8"
        item_hover = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        sel_bg = "#1E293B" if is_dark else "#EAF3FF"
        sel_text = "#3B82F6" if is_dark else "#1473E6"
        close_hover = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"

        self.setStyleSheet(f"""
            BookmarksPanel {{
                background-color: {bg};
                border-left: 1px solid {border};
            }}
            QLabel#bookmarksPanelTitle {{
                font-size: 16px;
                font-weight: 600;
                color: {title_color};
            }}
            QLabel#bookmarksSubtitle {{
                font-size: 12px;
                font-weight: 500;
                color: {subtitle_color};
            }}
            QFrame#bookmarksDivider {{
                background-color: {divider_color};
                border: none;
                max-height: 1px;
                min-height: 1px;
            }}
            QToolButton#bookmarksPanelCloseBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {subtitle_color};
                font-size: 12px;
            }}
            QToolButton#bookmarksPanelCloseBtn:hover {{
                background-color: {close_hover};
                color: {title_color};
            }}
            QTreeWidget#bookmarksTreeWidget {{
                background-color: transparent;
                border: none;
                color: {title_color};
                font-size: 12px;
            }}
            QTreeWidget#bookmarksTreeWidget::item {{
                padding: 5px 4px;
                border-radius: 4px;
            }}
            QTreeWidget#bookmarksTreeWidget::item:hover {{
                background-color: {item_hover};
            }}
            QTreeWidget#bookmarksTreeWidget::item:selected {{
                background-color: {sel_bg};
                color: {sel_text};
                font-weight: 600;
            }}
            QLabel#bookmarksEmptyTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {title_color};
            }}
            QLabel#bookmarksEmptyDesc {{
                font-size: 12px;
                color: {subtitle_color};
            }}
        """)
