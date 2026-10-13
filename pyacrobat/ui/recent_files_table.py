"""
Recent Files Table & Workspace for PyAcrobat.
Matches Adobe Acrobat / Figma design (nodes 3:12791, 3:12802, 3:12882).
Presents the Recent Documents table with Two-Line File Identity, Location Subtitles, and Context Menus.
"""

import os
import subprocess
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QToolButton, QAbstractItemView, QPushButton,
    QStyledItemDelegate, QStyle, QMenu, QApplication, QLineEdit,
    QStackedWidget, QGridLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import QIcon, QCursor, QFont, QPainter, QFontMetrics, QColor, QPen, QPixmap

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.ui.home_left_rail import load_themed_svg_icon, load_themed_svg_pixmap
from pyacrobat.core.recent_files import RecentFilesManager, normalize_path
from pyacrobat.ui.file_details_panel import FileDetailsPanel, get_cached_pdf_thumbnail


# Placeholder recent documents matching Figma node 3:12809 - 3:12880
PLACEHOLDER_RECENT_FILES = [
    {
        "name": "Northstar_Proposal.pdf",
        "date": "Today, 10:42 AM",
        "size": "2.4 MB",
        "pages": 8,
        "path": "Documents / Riverside Workplace / Northstar_Proposal.pdf",
        "subtitle": "Your computer",
        "starred": True,
    },
    {
        "name": "Riverside_Floor_Plan.pdf",
        "date": "Today, 9:18 AM",
        "size": "5.8 MB",
        "pages": 12,
        "path": "Documents / Blueprints / Riverside_Floor_Plan.pdf",
        "subtitle": "Your computer",
        "starred": False,
    },
    {
        "name": "Design_Review_Notes.pdf",
        "date": "Yesterday, 4:35 PM",
        "size": "846 KB",
        "pages": 4,
        "path": "Downloads / Design_Review_Notes.pdf",
        "subtitle": "Shared by Jamie Lee",
        "starred": False,
    },
    {
        "name": "Brand_Guidelines.pdf",
        "date": "Oct 7, 2026",
        "size": "3.1 MB",
        "pages": 24,
        "path": "Assets / Marketing / Brand_Guidelines.pdf",
        "subtitle": "Your computer",
        "starred": False,
    },
]


class TwoLineFileNameDelegate(QStyledItemDelegate):
    """
    Renders Column 1 matching Figma node 3:12813:
    - 20x20 vector file icon
    - Line 1: Filename (12px Semi Bold)
    - Line 2: Subtitle / Location ("Your computer" or location, 10px Regular muted)
    - High-DPI crisp rendering and selection contrast
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_pixmap = load_themed_svg_pixmap("file-text.svg", "#EB1000", size=20)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect
        is_selected = bool(option.state & QStyle.State_Selected)

        # Draw default selection panel if selected
        if is_selected:
            t = ThemeManager.get_tokens()
            is_dark = ThemeManager.is_dark()
            sel_bg = QColor("#EAF3FF" if not is_dark else t.accent_subtle)
            painter.fillRect(rect, sel_bg)

        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        # 1. Draw File Icon (20x20 centered vertically)
        icon_x = rect.left() + 10
        icon_y = rect.top() + (rect.height() - 20) // 2
        if not self.icon_pixmap.isNull():
            painter.drawPixmap(icon_x, icon_y, self.icon_pixmap)

        # 2. Extract Data
        rec = index.data(Qt.UserRole) or {}
        name = rec.get("name") or index.data(Qt.DisplayRole) or ""
        subtitle = rec.get("subtitle") or "Your computer"

        # 3. Text Bounds (starts 10px after 20px icon)
        text_x = icon_x + 20 + 10
        text_width = max(10, rect.right() - text_x - 10)

        # Line 1: Filename (12px Semi Bold)
        font_title = QFont()
        font_title.setPointSize(10)
        font_title.setBold(True)
        painter.setFont(font_title)

        title_color = QColor(t.accent if is_selected else t.text)
        painter.setPen(title_color)

        fm_title = QFontMetrics(font_title)
        elided_title = fm_title.elidedText(name, Qt.ElideRight, text_width)
        title_rect = QRect(text_x, rect.top() + 9, text_width, 18)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        # Line 2: Location Subtitle ("Your computer", 10px regular)
        font_sub = QFont()
        font_sub.setPointSize(9)
        font_sub.setBold(False)
        painter.setFont(font_sub)

        sub_color = QColor(t.text_dim if is_selected else t.text_muted)
        painter.setPen(sub_color)

        fm_sub = QFontMetrics(font_sub)
        elided_sub = fm_sub.elidedText(subtitle, Qt.ElideRight, text_width)
        sub_rect = QRect(text_x, rect.top() + 29, text_width, 16)
        painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_sub)

        # Bottom row border
        subtle_border = QColor("#EAEAEA" if not is_dark else t.border_subtle)
        painter.setPen(subtle_border)
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(220, 54)


def create_placeholder_page_pixmap(is_dark: bool = False) -> QPixmap:
    """Generates a high-DPI stylized document sheet thumbnail for files without raster preview."""
    w, h = 78, 98
    pm = QPixmap(w * 2, h * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)

    bg_color = QColor("#303030" if is_dark else "#FFFFFF")
    border_color = QColor("#444444" if is_dark else "#D5D5D8")
    line_color = QColor("#505050" if is_dark else "#E6E6E8")

    painter.setBrush(bg_color)
    painter.setPen(QPen(border_color, 1))
    painter.drawRoundedRect(0, 0, w, h, 3, 3)

    # Red PDF icon
    icon_pm = load_themed_svg_pixmap("file-text.svg", "#EB1000", size=24)
    if not icon_pm.isNull():
        painter.drawPixmap((w - 24) // 2, 20, icon_pm)

    # Stylized faux text lines
    painter.setPen(QPen(line_color, 2))
    painter.drawLine(16, 56, 62, 56)
    painter.drawLine(16, 64, 62, 64)
    painter.drawLine(16, 72, 48, 72)

    painter.end()
    return pm


class RecentFileGridCard(QFrame):
    """
    Grid card representing a recent PDF document in Grid View:
    - Fixed size: 172x214 px, 8px border radius
    - Top area: 126px page thumbnail / stylized doc preview
    - Bottom area: filename (12px Semi Bold), date/location (11px regular), size/pages (10px muted)
    - Hover highlight & selected state border (#1473E6)
    - Mouse interactions: left click (select), double click (open), right click (context menu)
    """

    clicked = Signal(dict)
    double_clicked = Signal(dict)
    context_menu_requested = Signal(dict, QPoint)

    def __init__(self, file_data: dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.is_selected = False
        self.setObjectName("recentGridCard")
        self.setFixedSize(172, 214)
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Preview Top Area (height: 126px)
        self.preview_area = QWidget()
        self.preview_area.setObjectName("gridCardPreviewArea")
        self.preview_area.setFixedHeight(126)
        p_layout = QVBoxLayout(self.preview_area)
        p_layout.setContentsMargins(10, 10, 10, 8)
        p_layout.setAlignment(Qt.AlignCenter)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("background: transparent;")
        p_layout.addWidget(self.thumbnail_label)

        layout.addWidget(self.preview_area)

        # 2. Divider line between preview and metadata
        self.divider = QFrame()
        self.divider.setObjectName("gridCardDivider")
        self.divider.setFixedHeight(1)
        layout.addWidget(self.divider)

        # 3. Metadata Bottom Area (height: 87px)
        self.meta_area = QWidget()
        self.meta_area.setObjectName("gridCardMetaArea")
        m_layout = QVBoxLayout(self.meta_area)
        m_layout.setContentsMargins(12, 8, 12, 10)
        m_layout.setSpacing(3)
        m_layout.setAlignment(Qt.AlignTop)

        # Line 1: Filename (12px Semi Bold)
        self.lbl_name = QLabel()
        self.lbl_name.setObjectName("gridCardName")
        font_name = QFont()
        font_name.setPointSize(10)
        font_name.setBold(True)
        self.lbl_name.setFont(font_name)
        fm = QFontMetrics(font_name)
        name = self.file_data.get("name", "Document.pdf")
        self.lbl_name.setText(fm.elidedText(name, Qt.ElideRight, 146))
        self.lbl_name.setToolTip(name)
        m_layout.addWidget(self.lbl_name)

        # Line 2: Relative Date / Subtitle (11px regular)
        date_str = self.file_data.get("date", "Recently")
        self.lbl_date = QLabel(date_str)
        self.lbl_date.setObjectName("gridCardDate")
        m_layout.addWidget(self.lbl_date)

        # Line 3: Size & Pages info (10px muted)
        size_str = self.file_data.get("size", "-")
        pages = self.file_data.get("pages")
        if pages:
            detail_str = f"{size_str} • {pages} pages"
        else:
            detail_str = size_str
        self.lbl_detail = QLabel(detail_str)
        self.lbl_detail.setObjectName("gridCardDetail")
        m_layout.addWidget(self.lbl_detail)

        layout.addWidget(self.meta_area)

        self.render_thumbnail()

    def render_thumbnail(self):
        is_dark = ThemeManager.is_dark()
        path = self.file_data.get("path", "")
        pixmap = None
        if path and os.path.exists(path):
            pixmap = get_cached_pdf_thumbnail(path, 130, 106)

        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
        else:
            self.thumbnail_label.setPixmap(create_placeholder_page_pixmap(is_dark))

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_data)
        elif event.button() == Qt.RightButton:
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.context_menu_requested.emit(self.file_data, pos)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)

    def refresh_theme(self):
        self.render_thumbnail()


class ResponsiveStackedWidget(QStackedWidget):
    """
    QStackedWidget that reports minimumSizeHint based on the active widget
    rather than the maximum across all stacked pages.
    """

    def minimumSizeHint(self) -> QSize:
        w = self.currentWidget()
        if w:
            hint = w.minimumSizeHint()
            if w.objectName() == "recentGridContainer":
                return QSize(172, hint.height())
            return hint
        return super().minimumSizeHint()

    def sizeHint(self) -> QSize:
        w = self.currentWidget()
        if w:
            return w.sizeHint()
        return super().sizeHint()


class RecentFilesTable(QWidget):
    """
    Recent documents section matching Figma specs:
    - Heading: 'Recent documents' + count badge
    - Controls: Search recent files (245x34px) + List/Grid view toggle buttons
    - Table: Checkbox | NAME (Two-line) | LAST OPENED ↓ | SIZE | Actions (⋯)
    - Interactive Context Menu: Open, Show in Explorer, Copy Path, Remove
    - Footer: 'Showing N of N recent files' + 'View all'
    """

    file_selected = Signal(dict)          # Emits selected file record
    file_double_clicked = Signal(dict)    # Emits double-clicked record
    file_open_requested = Signal(str)     # Emits file path to open
    view_all_clicked = Signal()
    view_mode_changed = Signal(str)       # Emits 'list' or 'grid'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recentFilesSection")
        self.current_category: str = "recent"
        self.current_view_mode: str = "list"
        self.grid_cards: List[RecentFileGridCard] = []
        self.manager = RecentFilesManager.get_instance()
        self._all_records: List[Dict[str, Any]] = self._load_initial_data()
        self.files_data: List[Dict[str, Any]] = list(self._all_records)
        self.init_ui()
        self.populate_rows()
        self.update_theme()

    def _load_initial_data(self) -> List[Dict[str, Any]]:
        records = self.manager.load_records()
        if records:
            return records
        return [dict(f) for f in PLACEHOLDER_RECENT_FILES]

    def refresh_from_store(self):
        """Reloads recent records from persistent manager and refreshes table."""
        records = self.manager.load_records()
        if records:
            self._all_records = records
        else:
            self._all_records = [dict(f) for f in PLACEHOLDER_RECENT_FILES]
        if self.current_category == "starred":
            self.files_data = [r for r in self._all_records if r.get("starred", False)]
        else:
            self.files_data = list(self._all_records)
        self.populate_rows()

    def set_category_filter(self, category: str):
        """Filters displayed documents by category ('recent' or 'starred')."""
        self.current_category = category
        if category == "starred":
            self.lbl_title.setText("Starred documents")
            self.search_input.setPlaceholderText("Search starred files")
            self.files_data = [r for r in self._all_records if r.get("starred", False)]
        else:
            self.lbl_title.setText("Recent documents")
            self.search_input.setPlaceholderText("Search recent files")
            self.files_data = list(self._all_records)

        if hasattr(self, "search_input") and self.search_input.text():
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)

        self.populate_rows()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(14)

        # ==========================================
        # 1. Heading Row (Figma: node 3:12791)
        # ==========================================
        heading_row = QWidget()
        heading_row.setObjectName("recentHeadingRow")
        h_layout = QHBoxLayout(heading_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignVCenter)

        # Left: Heading & Count (Figma: node 3:12792)
        self.lbl_title = QLabel("Recent documents")
        self.lbl_title.setObjectName("recentHeadingTitle")
        self.lbl_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        h_layout.addWidget(self.lbl_title)

        self.lbl_count = QLabel(str(len(self.files_data)))
        self.lbl_count.setObjectName("recentCountBadge")
        h_layout.addWidget(self.lbl_count)

        h_layout.addStretch(1)

        # Right: Search & View Mode (Figma: node 3:12795)
        controls_container = QWidget()
        controls_container.setObjectName("recentControlsContainer")
        c_layout = QHBoxLayout(controls_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(12)
        c_layout.setAlignment(Qt.AlignVCenter)

        # Search Box (245x34 px, 6px radius, leading search icon, clear button)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("recentSearchInput")
        self.search_input.setPlaceholderText("Search recent files")
        self.search_input.setFixedSize(245, 34)
        self.search_input.setClearButtonEnabled(True)
        self.search_action = self.search_input.addAction(
            load_themed_svg_icon("search.svg", "#626262", size=16),
            QLineEdit.LeadingPosition
        )
        self.search_input.textChanged.connect(self._on_search_query_changed)
        c_layout.addWidget(self.search_input)

        # View Mode Toggle Buttons (List / Grid)
        view_toggle_container = QWidget()
        view_toggle_container.setObjectName("viewToggleContainer")
        vt_layout = QHBoxLayout(view_toggle_container)
        vt_layout.setContentsMargins(0, 0, 0, 0)
        vt_layout.setSpacing(4)
        vt_layout.setAlignment(Qt.AlignVCenter)

        self.btn_list_view = QToolButton()
        self.btn_list_view.setObjectName("btnListView")
        self.btn_list_view.setFixedSize(34, 34)
        self.btn_list_view.setCursor(Qt.PointingHandCursor)
        self.btn_list_view.setToolTip("List view")
        self.btn_list_view.setIcon(load_themed_svg_icon("list.svg", "#1473E6", size=18))
        self.btn_list_view.setIconSize(QSize(18, 18))
        self.btn_list_view.setProperty("active", "true")
        self.btn_list_view.clicked.connect(lambda: self.set_view_mode("list"))
        vt_layout.addWidget(self.btn_list_view)

        self.btn_grid_view = QToolButton()
        self.btn_grid_view.setObjectName("btnGridView")
        self.btn_grid_view.setFixedSize(34, 34)
        self.btn_grid_view.setCursor(Qt.PointingHandCursor)
        self.btn_grid_view.setToolTip("Grid view")
        self.btn_grid_view.setIcon(load_themed_svg_icon("layout-grid.svg", "#626262", size=18))
        self.btn_grid_view.setIconSize(QSize(18, 18))
        self.btn_grid_view.setProperty("active", "false")
        self.btn_grid_view.clicked.connect(lambda: self.set_view_mode("grid"))
        vt_layout.addWidget(self.btn_grid_view)

        c_layout.addWidget(view_toggle_container)
        h_layout.addWidget(controls_container)

        self.main_layout.addWidget(heading_row)

        # ==========================================
        # 2. View Stack (List Table & Grid Workspace)
        # ==========================================
        self.view_stack = ResponsiveStackedWidget()
        self.view_stack.setObjectName("recentViewStack")

        # Page 0: Table Widget (Figma: node 3:12802)
        self.table = QTableWidget()
        self.table.setObjectName("recentTable")
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "NAME", "LAST OPENED ↓", "SIZE", ""])

        # Configure headers & selection
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(54)

        # Custom Two-Line Delegate for Column 1
        self.name_delegate = TwoLineFileNameDelegate(self.table)
        self.table.setItemDelegateForColumn(1, self.name_delegate)

        header = self.table.horizontalHeader()
        header.setFixedHeight(34)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)

        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 38)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Context Menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_custom_context_menu)

        self.view_stack.addWidget(self.table)

        # Page 1: Grid Container (Phase 9)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("recentGridContainer")
        self.grid_container.setMinimumSize(0, 0)
        self.grid_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.view_stack.addWidget(self.grid_container)

        # ==========================================
        # 3. Footer Row (Figma: node 3:12882)
        # ==========================================
        footer_row = QWidget()
        footer_row.setObjectName("recentFooterRow")
        f_layout = QHBoxLayout(footer_row)
        f_layout.setContentsMargins(0, 6, 0, 0)
        f_layout.setSpacing(10)

        self.lbl_footer_count = QLabel(f"Showing {len(self.files_data)} of {len(self.files_data)} recent files")
        self.lbl_footer_count.setObjectName("recentFooterText")
        self.lbl_footer_count.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.lbl_footer_count.setMinimumWidth(0)
        f_layout.addWidget(self.lbl_footer_count)

        f_layout.addStretch(1)

        self.btn_view_all = QPushButton("View all")
        self.btn_view_all.setObjectName("recentViewAllBtn")
        self.btn_view_all.setCursor(Qt.PointingHandCursor)
        self.btn_view_all.clicked.connect(self.view_all_clicked.emit)
        f_layout.addWidget(self.btn_view_all)

        # ==========================================
        # 4. Workspace Row (Figma: node 3:12801)
        # Table/Grid on Left, File Details Panel on Right
        # ==========================================
        workspace_widget = QWidget()
        workspace_widget.setObjectName("recentWorkspace")
        ws_layout = QHBoxLayout(workspace_widget)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(16)
        ws_layout.setAlignment(Qt.AlignTop)

        # Left Column: View Stack + Footer
        left_col = QWidget()
        left_col.setObjectName("recentLeftCol")
        lc_layout = QVBoxLayout(left_col)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setSpacing(10)
        lc_layout.setAlignment(Qt.AlignTop)

        lc_layout.addWidget(self.view_stack)
        lc_layout.addWidget(footer_row)
        ws_layout.addWidget(left_col, 1)

        # Right Column: File Details Panel (Figma: node 3:12885)
        self.details_panel = FileDetailsPanel(self)
        self.details_panel.open_requested.connect(self.file_open_requested.emit)
        self.details_panel.star_toggled.connect(self._on_details_star_toggled)
        ws_layout.addWidget(self.details_panel, 0, Qt.AlignTop)

        self.main_layout.addWidget(workspace_widget)

    def populate_rows(self):
        """Populates both the table rows and grid cards with the current file data."""
        noun = "starred files" if self.current_category == "starred" else "recent files"
        if hasattr(self, "lbl_count"):
            self.lbl_count.setText(str(len(self.files_data)))
        if hasattr(self, "lbl_footer_count"):
            self.lbl_footer_count.setText(f"Showing {len(self.files_data)} of {len(self.files_data)} {noun}")

        # 1. Populate Table View
        self.table.setRowCount(len(self.files_data))
        file_icon = load_themed_svg_icon("file-text.svg", "#EB1000", size=20)
        ellipsis_icon = load_themed_svg_icon("ellipsis.svg", "#626262", size=18)

        for row, item_data in enumerate(self.files_data):
            # Col 0: Checkbox container
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(10, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setCursor(Qt.PointingHandCursor)
            chk_layout.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_widget)

            # Col 1: Two-line delegate item
            name_item = QTableWidgetItem(file_icon, item_data["name"])
            name_item.setData(Qt.UserRole, item_data)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 1, name_item)

            # Col 2: Last Opened Date
            date_str = item_data.get("date", "Recently")
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 2, date_item)

            # Col 3: Size
            size_str = item_data.get("size", "-")
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 3, size_item)

            # Col 4: Ellipsis Action Menu Button
            btn_menu = QToolButton()
            btn_menu.setIcon(ellipsis_icon)
            btn_menu.setIconSize(QSize(18, 18))
            btn_menu.setCursor(Qt.PointingHandCursor)
            btn_menu.setStyleSheet("border: none; background: transparent; padding: 4px;")
            # Capture current row
            btn_menu.clicked.connect(lambda checked=False, r=row, b=btn_menu: self._show_row_menu_from_button(r, b))
            self.table.setCellWidget(row, 4, btn_menu)

            self.table.setRowHeight(row, 54)

        # Height based on row count
        total_height = 36 + len(self.files_data) * 54 + 4
        self.table.setFixedHeight(total_height)

        # 2. Populate Grid View
        if hasattr(self, "grid_layout"):
            while self.grid_layout.count():
                child = self.grid_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.grid_cards.clear()

            cols = self._calculate_grid_cols()
            for i, item_data in enumerate(self.files_data):
                card = RecentFileGridCard(item_data, self)
                card.clicked.connect(self._on_grid_card_clicked)
                card.double_clicked.connect(self._on_grid_card_double_clicked)
                card.context_menu_requested.connect(self._on_grid_card_context_menu)
                self.grid_cards.append(card)
                r = i // cols
                c = i % cols
                self.grid_layout.addWidget(card, r, c)

            self._adjust_grid_dimensions(len(self.files_data))

        # Select first row and card by default
        if self.files_data:
            self.table.selectRow(0)
            if self.grid_cards:
                self.grid_cards[0].set_selected(True)
            if hasattr(self, "details_panel"):
                self.details_panel.set_file_data(self.files_data[0])
        else:
            self.table.clearSelection()
            if hasattr(self, "details_panel"):
                self.details_panel.set_file_data(None)

        # Re-apply active search filter if any
        if hasattr(self, "search_input") and self.search_input.text():
            self._on_search_query_changed(self.search_input.text())

    def _calculate_grid_cols(self) -> int:
        """Dynamically calculates the number of grid card columns that fit the available width."""
        vp_w = 0
        p = self.parent()
        while p:
            if hasattr(p, "viewport") and callable(p.viewport):
                vp_w = p.viewport().width()
                break
            p = p.parent()

        dp_w = (self.details_panel.width() + 16) if hasattr(self, "details_panel") and not self.details_panel.isHidden() else 0

        if vp_w > 0:
            avail_w = vp_w - 56 - dp_w - 10
        elif hasattr(self, "view_stack") and self.view_stack.width() > 100:
            avail_w = self.view_stack.width()
        elif hasattr(self, "width") and self.width() > 300:
            avail_w = self.width() - dp_w - 32
        else:
            avail_w = 0

        card_w = 172
        gap = 16
        if avail_w <= 0:
            return 4
        cols = max(1, min(4, int((avail_w + gap) // (card_w + gap))))
        return cols

    def _adjust_grid_dimensions(self, visible_count: int = -1):
        if visible_count < 0:
            visible_count = sum(1 for c in self.grid_cards if not c.isHidden())
        cols = self._calculate_grid_cols()
        rows = (visible_count + cols - 1) // cols if visible_count > 0 else 0
        card_h = 214
        gap = 16
        total_h = rows * (card_h + gap) + 10
        self.grid_container.setFixedHeight(max(50, total_h))

    def _relayout_grid(self):
        """Re-packs currently visible grid cards into sequential grid positions."""
        if not hasattr(self, "grid_layout"):
            return
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        cols = self._calculate_grid_cols()
        visible_cards = [c for c in self.grid_cards if not c.isHidden()]
        for i, card in enumerate(visible_cards):
            r = i // cols
            c = i % cols
            self.grid_layout.addWidget(card, r, c)

        self._adjust_grid_dimensions(len(visible_cards))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "current_view_mode") and self.current_view_mode == "grid":
            self._relayout_grid()

    def _on_grid_card_clicked(self, file_data: dict):
        for card in self.grid_cards:
            card.set_selected(card.file_data == file_data)
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 1)
            if item:
                rec = item.data(Qt.UserRole) or {}
                if rec == file_data:
                    self.table.blockSignals(True)
                    self.table.selectRow(r)
                    self.table.blockSignals(False)
                    break
        if hasattr(self, "details_panel"):
            self.details_panel.set_file_data(file_data)
        self.file_selected.emit(file_data)

    def _on_grid_card_double_clicked(self, file_data: dict):
        self.file_double_clicked.emit(file_data)
        file_path = file_data.get("path")
        if file_path and os.path.exists(file_path):
            self.file_open_requested.emit(file_path)

    def _on_grid_card_context_menu(self, file_data: dict, global_pos: QPoint):
        idx = -1
        for i, rec in enumerate(self.files_data):
            if rec == file_data:
                idx = i
                break
        if idx >= 0:
            self._show_row_context_menu(idx, global_pos)

    def set_view_mode(self, mode: str):
        """Switches the view mode ('list' or 'grid') and updates button appearances."""
        if mode not in ("list", "grid"):
            return
        if self.current_view_mode == mode:
            return
        self.current_view_mode = mode
        self._update_view_toggle_styles()
        if hasattr(self, "view_stack"):
            if mode == "list":
                self.view_stack.setCurrentIndex(0)
            else:
                self.view_stack.setCurrentIndex(1)
                self._relayout_grid()
        self.view_mode_changed.emit(mode)

    def _update_view_toggle_styles(self):
        """Refreshes the active visual state and icon tint on the view mode buttons."""
        t = ThemeManager.get_tokens()
        active_color = t.accent
        muted_color = t.text_muted

        is_list = (self.current_view_mode == "list")
        self.btn_list_view.setProperty("active", "true" if is_list else "false")
        self.btn_grid_view.setProperty("active", "false" if is_list else "true")

        self.btn_list_view.setIcon(load_themed_svg_icon("list.svg", active_color if is_list else muted_color, size=18))
        self.btn_grid_view.setIcon(load_themed_svg_icon("layout-grid.svg", muted_color if is_list else active_color, size=18))

        self.btn_list_view.style().unpolish(self.btn_list_view)
        self.btn_list_view.style().polish(self.btn_list_view)
        self.btn_grid_view.style().unpolish(self.btn_grid_view)
        self.btn_grid_view.style().polish(self.btn_grid_view)

    def _on_search_query_changed(self, query: str):
        """Filters table rows and grid cards in real time based on search query matching file name or metadata."""
        q = query.strip().lower()
        visible_count = 0
        total_count = len(self.files_data)

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if not item:
                continue
            rec = item.data(Qt.UserRole) or {}
            name = (rec.get("name") or item.text() or "").lower()
            subtitle = (rec.get("subtitle") or "").lower()

            matches = (not q) or (q in name) or (q in subtitle)
            self.table.setRowHidden(row, not matches)
            if matches:
                visible_count += 1

        for card in self.grid_cards:
            name = (card.file_data.get("name") or "").lower()
            subtitle = (card.file_data.get("subtitle") or "").lower()
            card_matches = (not q) or (q in name) or (q in subtitle)
            card.setVisible(card_matches)

        self._relayout_grid()

        noun = "starred files" if self.current_category == "starred" else "recent files"
        if q:
            self.lbl_count.setText(str(visible_count))
            self.lbl_footer_count.setText(f"Showing {visible_count} of {total_count} {noun}")
        else:
            self.lbl_count.setText(str(total_count))
            self.lbl_footer_count.setText(f"Showing {total_count} of {total_count} {noun}")

        row_height = 54
        header_height = 36
        target_height = header_height + (visible_count * row_height) + 4
        self.table.setFixedHeight(max(40, target_height))

    def _show_row_menu_from_button(self, row: int, button: QToolButton):
        pos = button.mapToGlobal(QPoint(0, button.height()))
        self._show_row_context_menu(row, pos)

    def _on_custom_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            global_pos = self.table.viewport().mapToGlobal(pos)
            self._show_row_context_menu(row, global_pos)

    def _create_row_context_menu(self, row: int) -> Optional[QMenu]:
        """Creates the context menu with actions for a given row."""
        if not (0 <= row < len(self.files_data)):
            return None
        rec = self.files_data[row]
        path = rec.get("path", "")
        is_starred = bool(rec.get("starred", False))

        menu = QMenu(self)
        menu.setObjectName("recentContextMenu")
        act_open = menu.addAction("📄  Open PDF")
        act_open.setData("open")
        act_explorer = menu.addAction("📂  Show in Explorer")
        act_explorer.setData("explorer")
        act_copy = menu.addAction("📋  Copy Path")
        act_copy.setData("copy")
        menu.addSeparator()
        if is_starred:
            act_star = menu.addAction("★  Unstar file")
            act_star.setData("toggle_star")
        else:
            act_star = menu.addAction("⭐  Star file")
            act_star.setData("toggle_star")
        menu.addSeparator()
        act_remove = menu.addAction("❌  Remove from Recent")
        act_remove.setData("remove")

        if not path or not os.path.exists(path):
            act_explorer.setEnabled(False)

        return menu

    def _show_row_context_menu(self, row: int, global_pos: QPoint):
        menu = self._create_row_context_menu(row)
        if not menu:
            return
        rec = self.files_data[row]
        path = rec.get("path", "")

        chosen = menu.exec(global_pos)
        if not chosen:
            return
        action_type = chosen.data()
        if action_type == "open":
            if path and os.path.exists(path):
                self.file_open_requested.emit(path)
            else:
                self.file_selected.emit(rec)
        elif action_type == "explorer" and path and os.path.exists(path):
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
        elif action_type == "copy" and path:
            QApplication.clipboard().setText(path)
        elif action_type == "toggle_star":
            new_state = not rec.get("starred", False)
            rec["starred"] = new_state
            if path:
                self.manager.set_starred(path, new_state)
            norm_target = normalize_path(path)
            for r in self._all_records:
                if norm_target:
                    if normalize_path(r.get("path", "")) == norm_target:
                        r["starred"] = new_state
                elif r.get("name") == rec.get("name"):
                    r["starred"] = new_state
            if hasattr(self, "details_panel") and self.details_panel.file_data == rec:
                self.details_panel.btn_star.setChecked(new_state)
                self.details_panel._update_star_icon()
            if self.current_category == "starred":
                self.files_data = [r for r in self._all_records if r.get("starred", False)]
                self.populate_rows()
                if not new_state:
                    if self.files_data:
                        self.details_panel.set_file_data(self.files_data[0])
                    else:
                        self.details_panel.set_file_data(None)
        elif action_type == "remove":
            if path:
                self.manager.remove_file(path)
                norm_p = normalize_path(path)
                self._all_records = [r for r in self._all_records if normalize_path(r.get("path", "")) != norm_p]
            elif 0 <= row < len(self.files_data):
                rem_rec = self.files_data[row]
                self._all_records = [r for r in self._all_records if r != rem_rec]
            if self.current_category == "starred":
                self.files_data = [r for r in self._all_records if r.get("starred", False)]
            else:
                self.files_data = list(self._all_records)
            self.populate_rows()

    def _on_details_star_toggled(self, file_data: dict, is_starred: bool):
        path = file_data.get("path", "")
        file_data["starred"] = is_starred
        if path:
            self.manager.set_starred(path, is_starred)
        norm_target = normalize_path(path)
        for r in self._all_records:
            if norm_target:
                if normalize_path(r.get("path", "")) == norm_target:
                    r["starred"] = is_starred
            elif r.get("name") == file_data.get("name"):
                r["starred"] = is_starred

        if self.current_category == "starred":
            self.files_data = [r for r in self._all_records if r.get("starred", False)]
            self.populate_rows()
            if not is_starred:
                if self.files_data:
                    self.details_panel.set_file_data(self.files_data[0])
                else:
                    self.details_panel.set_file_data(None)

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            idx = rows[0].row()
            if 0 <= idx < len(self.files_data):
                rec = self.files_data[idx]
                self.file_selected.emit(rec)
                for card in self.grid_cards:
                    card.set_selected(card.file_data == rec)
                if hasattr(self, "details_panel"):
                    self.details_panel.set_file_data(rec)

    def _on_cell_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self.files_data):
            rec = self.files_data[row]
            self.file_double_clicked.emit(rec)
            file_path = rec.get("path")
            if file_path and os.path.exists(file_path):
                self.file_open_requested.emit(file_path)

    def get_selected_file(self) -> Optional[dict]:
        if self.current_view_mode == "grid":
            for card in self.grid_cards:
                if card.is_selected:
                    return card.file_data
        rows = self.table.selectionModel().selectedRows()
        if rows:
            idx = rows[0].row()
            if 0 <= idx < len(self.files_data):
                return self.files_data[idx]
        return None

    def update_theme(self):
        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        sel_bg = "#EAF3FF" if not is_dark else t.accent_subtle
        sel_text = t.accent if not is_dark else t.text
        border_color = "#D9D9D9" if not is_dark else t.border
        subtle_border = "#EAEAEA" if not is_dark else t.border_subtle
        input_bg = "#FFFFFF" if not is_dark else t.surface_raised
        toggle_active_bg = "#EAF3FF" if not is_dark else t.accent_subtle
        toggle_active_border = "#C4DCFA" if not is_dark else t.accent
        toggle_hover_bg = "#F2F2F2" if not is_dark else t.surface_raised

        card_bg = t.surface_raised
        card_hover_bg = "#FAFAFA" if not is_dark else "#2A2A2A"
        card_sel_bg = "#F0F6FF" if not is_dark else t.accent_subtle
        preview_bg = "#F6F6F8" if not is_dark else "#1E1E1E"

        if hasattr(self, "search_action"):
            self.search_action.setIcon(load_themed_svg_icon("search.svg", t.text_muted, size=16))

        if hasattr(self, "btn_list_view") and hasattr(self, "btn_grid_view"):
            self._update_view_toggle_styles()

        for card in self.grid_cards:
            card.refresh_theme()

        if hasattr(self, "details_panel"):
            self.details_panel.update_theme()

        self.setStyleSheet(f"""
            #recentFilesSection {{
                background-color: transparent;
            }}
            #recentHeadingRow {{
                background: transparent;
            }}
            #recentHeadingTitle {{
                font-size: 20px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #recentCountBadge {{
                font-size: 13px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
            #recentControlsContainer {{
                background: transparent;
            }}
            #recentSearchInput {{
                background-color: {input_bg};
                color: {t.text};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding-left: 6px;
                padding-right: 8px;
                font-size: 12px;
            }}
            #recentSearchInput:focus {{
                border: 1px solid {t.accent};
            }}
            #viewToggleContainer {{
                background: transparent;
            }}
            #btnListView, #btnGridView {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px;
            }}
            #btnListView:hover, #btnGridView:hover {{
                background-color: {toggle_hover_bg};
            }}
            #btnListView[active="true"], #btnGridView[active="true"] {{
                background-color: {toggle_active_bg};
                border: 1px solid {toggle_active_border};
            }}
            #recentViewStack {{
                background: transparent;
                border: none;
            }}
            #recentGridContainer {{
                background: transparent;
            }}
            #recentGridCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #recentGridCard:hover {{
                border: 1px solid {t.accent};
                background-color: {card_hover_bg};
            }}
            #recentGridCard[selected="true"] {{
                border: 2px solid {t.accent};
                background-color: {card_sel_bg};
            }}
            #gridCardPreviewArea {{
                background-color: {preview_bg};
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            #gridCardDivider {{
                background-color: {subtle_border};
                border: none;
            }}
            #gridCardMetaArea {{
                background: transparent;
            }}
            #gridCardName {{
                font-size: 12px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #gridCardDate {{
                font-size: 11px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
            #gridCardDetail {{
                font-size: 10px;
                font-weight: 400;
                color: {t.text_dim};
                background: transparent;
            }}
            #recentTable {{
                background-color: transparent;
                border: none;
            }}
            #recentTable::item {{
                border-bottom: 1px solid {subtle_border};
                padding-left: 8px;
                color: {t.text};
            }}
            #recentTable::item:selected {{
                background-color: {sel_bg};
                color: {sel_text};
            }}
            #recentTable QHeaderView::section {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {border_color};
                color: {t.text_muted};
                font-size: 11px;
                font-weight: 600;
                padding-left: 8px;
                text-transform: uppercase;
            }}
            #recentFooterText {{
                font-size: 11px;
                color: {t.text_muted};
                background: transparent;
            }}
            #recentViewAllBtn {{
                font-size: 12px;
                color: {t.accent};
                background: transparent;
                border: none;
                font-weight: 500;
            }}
            #recentViewAllBtn:hover {{
                color: {t.accent_hover};
                text-decoration: underline;
            }}
        """)
