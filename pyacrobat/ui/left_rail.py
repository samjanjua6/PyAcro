"""
Left Rail & Collapsible Drawer (Acrobat-style Navigation Strip)
Contains Thumbnails, Bookmarks/Outline, and Search panels.
"""

from typing import List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QStackedWidget,
    QLabel, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QPushButton, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage


class LeftRailWidget(QWidget):
    """Left vertical icon bar with expandable drawer panel."""

    page_selected = Signal(int)       # 1-based page number
    search_requested = Signal(str)    # Query string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_drawer_open = False
        self.active_tab_index = 0
        self.init_ui()
        self.close_drawer()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Left Icon Rail (Slim vertical strip)
        self.rail_bar = QFrame()
        self.rail_bar.setObjectName("leftRail")
        self.rail_bar.setFixedWidth(46)
        rail_layout = QVBoxLayout(self.rail_bar)
        rail_layout.setContentsMargins(2, 6, 2, 6)
        rail_layout.setSpacing(6)
        rail_layout.setAlignment(Qt.AlignTop)

        self.btn_pages = QToolButton()
        self.btn_pages.setText("📄")
        self.btn_pages.setToolTip("Page Thumbnails")
        self.btn_pages.setCheckable(True)
        self.btn_pages.setChecked(True)
        self.btn_pages.clicked.connect(lambda: self._toggle_drawer(0))
        rail_layout.addWidget(self.btn_pages)

        self.btn_outline = QToolButton()
        self.btn_outline.setText("📑")
        self.btn_outline.setToolTip("Table of Contents / Bookmarks")
        self.btn_outline.setCheckable(True)
        self.btn_outline.clicked.connect(lambda: self._toggle_drawer(1))
        rail_layout.addWidget(self.btn_outline)

        self.btn_search = QToolButton()
        self.btn_search.setText("🔍")
        self.btn_search.setToolTip("Search Document")
        self.btn_search.setCheckable(True)
        self.btn_search.clicked.connect(lambda: self._toggle_drawer(2))
        rail_layout.addWidget(self.btn_search)

        layout.addWidget(self.rail_bar)

        # 2. Drawer Panel (Stack of Thumbnails, Outline, Search)
        self.drawer_frame = QFrame()
        self.drawer_frame.setObjectName("sidebarDrawer")
        self.drawer_frame.setMinimumWidth(180)
        self.drawer_frame.setMaximumWidth(280)
        drawer_layout = QVBoxLayout(self.drawer_frame)
        drawer_layout.setContentsMargins(6, 8, 6, 6)

        # Header with title & close button
        header_layout = QHBoxLayout()
        self.header_title = QLabel("Page Thumbnails")
        self.header_title.setObjectName("drawerHeaderTitle")
        header_layout.addWidget(self.header_title)

        btn_close_drawer = QToolButton()
        btn_close_drawer.setText("✕")
        btn_close_drawer.setToolTip("Close Drawer")
        btn_close_drawer.clicked.connect(self.close_drawer)
        header_layout.addWidget(btn_close_drawer)
        drawer_layout.addLayout(header_layout)

        # Stacked pages
        self.stack = QStackedWidget()

        # Page 0: Thumbnails
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setIconSize(QSize(130, 170))
        self.thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        self.stack.addWidget(self.thumbnail_list)

        # Page 1: Outline Tree
        self.outline_tree = QTreeWidget()
        self.outline_tree.setHeaderHidden(True)
        self.outline_tree.itemClicked.connect(self._on_outline_clicked)
        self.stack.addWidget(self.outline_tree)

        # Page 2: Search Panel
        search_widget = QWidget()
        sw_layout = QVBoxLayout(search_widget)
        sw_layout.setContentsMargins(0, 4, 0, 0)
        
        search_bar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find in document...")
        self.search_input.returnPressed.connect(self._on_search)
        search_bar_layout.addWidget(self.search_input)

        btn_do_search = QPushButton("Find")
        btn_do_search.clicked.connect(self._on_search)
        search_bar_layout.addWidget(btn_do_search)
        sw_layout.addLayout(search_bar_layout)

        self.search_results_label = QLabel("Enter search term")
        self.search_results_label.setObjectName("subtleLabel")
        sw_layout.addWidget(self.search_results_label)

        self.search_results_list = QListWidget()
        self.search_results_list.itemClicked.connect(self._on_search_result_clicked)
        sw_layout.addWidget(self.search_results_list)

        self.stack.addWidget(search_widget)

        drawer_layout.addWidget(self.stack)
        layout.addWidget(self.drawer_frame)

    def _toggle_drawer(self, tab_index: int):
        if self.is_drawer_open and self.active_tab_index == tab_index:
            self.close_drawer()
        else:
            self.open_drawer(tab_index)

    def open_drawer(self, tab_index: int):
        self.setVisible(True)
        self.active_tab_index = tab_index
        self.stack.setCurrentIndex(tab_index)
        self.is_drawer_open = True
        self.drawer_frame.setVisible(True)

        titles = ["Page Thumbnails", "Bookmarks & Outline", "Find in Document"]
        self.header_title.setText(titles[tab_index])

        self.btn_pages.setChecked(tab_index == 0)
        self.btn_outline.setChecked(tab_index == 1)
        self.btn_search.setChecked(tab_index == 2)

    def close_drawer(self):
        self.is_drawer_open = False
        self.drawer_frame.setVisible(False)
        self.btn_pages.setChecked(False)
        self.btn_outline.setChecked(False)
        self.btn_search.setChecked(False)
        self.setVisible(False)

    def load_thumbnails(self, pixmaps: List[Any]):
        """Populates the thumbnail list from rendered PyMuPDF pixmaps."""
        self.thumbnail_list.clear()
        for idx, pix in enumerate(pixmaps):
            # Convert fitz.Pixmap to QImage/QPixmap
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            qpix = QPixmap.fromImage(img)
            item = QListWidgetItem(f"Page {idx + 1}")
            item.setIcon(QIcon(qpix))
            item.setData(Qt.UserRole, idx + 1)
            self.thumbnail_list.addItem(item)

    def load_outline(self, toc: List[List[Any]]):
        """Populates the outline tree from PyMuPDF toc list [lvl, title, page]."""
        self.outline_tree.clear()
        if not toc:
            item = QTreeWidgetItem(["(No outline in document)"])
            self.outline_tree.addTopLevelItem(item)
            return

        stack = [(0, self.outline_tree)]  # (level, parent)
        for entry in toc:
            lvl, title, page = entry[0], entry[1], entry[2]
            node = QTreeWidgetItem([title])
            node.setData(0, Qt.UserRole, page)

            while stack and stack[-1][0] >= lvl:
                stack.pop()

            parent = stack[-1][1]
            if isinstance(parent, QTreeWidget):
                parent.addTopLevelItem(node)
            else:
                parent.addChild(node)

            stack.append((lvl, node))

        self.outline_tree.expandAll()

    def _on_thumbnail_clicked(self, item: QListWidgetItem):
        page = item.data(Qt.UserRole)
        if page:
            self.page_selected.emit(page)

    def _on_outline_clicked(self, item: QTreeWidgetItem, column: int):
        page = item.data(0, Qt.UserRole)
        if page:
            self.page_selected.emit(page)

    def _on_search(self):
        text = self.search_input.text().strip()
        if text:
            self.search_requested.emit(text)

    def set_search_results(self, results: dict):
        self.search_results_list.clear()
        total_matches = sum(len(rects) for rects in results.values())
        self.search_results_label.setText(f"{total_matches} matches found")
        for page_idx, rects in results.items():
            for i, r in enumerate(rects):
                item = QListWidgetItem(f"Page {page_idx + 1} (match {i + 1})")
                item.setData(Qt.UserRole, page_idx + 1)
                self.search_results_list.addItem(item)

    def _on_search_result_clicked(self, item: QListWidgetItem):
        page = item.data(Qt.UserRole)
        if page:
            self.page_selected.emit(page)
