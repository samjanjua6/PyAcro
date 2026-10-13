"""
Home View Dashboard for PyAcrobat.
Displays the Acrobat-inspired Welcome screen, Quick Tools, and Recent Documents workstation
when no PDF is actively open.
"""

import getpass
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.ui.home_left_rail import (
    HomeLeftRail, load_themed_svg_icon, load_themed_svg_pixmap
)
from pyacrobat.ui.recent_files_table import RecentFilesTable


class QuickActionCard(QFrame):
    """
    Figma node 3:12775 Quick Action Card:
    - Fixed height: 132px
    - Border radius: 8px
    - 23x23 vector action icon
    - 14px Semi Bold title
    - 12px Regular description
    - Hover highlight with accent border and elevation
    """

    clicked = Signal(str)

    def __init__(self, card_id: str, title: str, description: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.title_text = title
        self.desc_text = description
        self.icon_name = icon_name

        self.setObjectName("quickActionCard")
        self.setFixedHeight(132)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignTop)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(23, 23)
        self.icon_label.setPixmap(load_themed_svg_pixmap(self.icon_name, size=23))
        self.icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("cardTitle")
        layout.addWidget(self.title_label)

        # Description
        self.desc_label = QLabel(self.desc_text)
        self.desc_label.setObjectName("cardDesc")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.card_id)
        super().mousePressEvent(event)

    def refresh_icon(self):
        self.icon_label.setPixmap(load_themed_svg_pixmap(self.icon_name, size=23))


class HomeView(QWidget):
    """
    Home dashboard container displayed when no document tabs are open.
    Matches Figma node 3:12727 ("Workspace").
    Phase 5 integrates the Recent Documents Table skeleton.
    """

    open_file_requested = Signal()
    file_open_requested = Signal(str)
    combine_files_requested = Signal()
    export_pdf_requested = Signal()
    navigation_changed = Signal(str)
    file_selected = Signal(dict)
    view_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeView")
        self.cards: List[QuickActionCard] = []
        self.init_ui()
        self.update_theme()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Left Navigation Rail (Fixed 232px width)
        self.left_rail = HomeLeftRail(self)
        self.left_rail.open_computer_requested.connect(self.open_file_requested.emit)
        self.left_rail.navigation_changed.connect(self.navigation_changed.emit)
        self.left_rail.navigation_changed.connect(self._on_navigation_changed)
        self.main_layout.addWidget(self.left_rail)

        # 2. Main Content Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("homeScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_container = QWidget()
        self.content_container.setObjectName("homeContentArea")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(36, 24, 36, 18)
        self.content_layout.setSpacing(24)
        self.content_layout.setAlignment(Qt.AlignTop)

        # ==========================================
        # Phase 3: Welcome Section (Figma: node 3:12767)
        # ==========================================
        self.welcome_widget = QWidget()
        self.welcome_widget.setObjectName("welcomeWidget")
        welcome_layout = QHBoxLayout(self.welcome_widget)
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setSpacing(16)
        welcome_layout.setAlignment(Qt.AlignVCenter)

        greeting_col = QWidget()
        greeting_layout = QVBoxLayout(greeting_col)
        greeting_layout.setContentsMargins(0, 0, 0, 0)
        greeting_layout.setSpacing(7)

        try:
            username = getpass.getuser().capitalize()
            if not username or username.lower() in ("root", "user"):
                username = "Alex"
        except Exception:
            username = "Alex"

        self.header_label = QLabel(f"Welcome back, {username}")
        self.header_label.setObjectName("welcomeTitle")
        greeting_layout.addWidget(self.header_label)

        self.subtitle_label = QLabel("Pick up where you left off, or start something new.")
        self.subtitle_label.setObjectName("welcomeSubtitle")
        greeting_layout.addWidget(self.subtitle_label)

        welcome_layout.addWidget(greeting_col, 1)

        self.btn_open = QPushButton("  Open a file")
        self.btn_open.setObjectName("welcomeOpenBtn")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.setFixedHeight(34)
        self.btn_open.setIcon(load_themed_svg_icon("folder-open.svg", "#FFFFFF", size=16))
        self.btn_open.setIconSize(QSize(16, 16))
        self.btn_open.clicked.connect(self.open_file_requested.emit)
        welcome_layout.addWidget(self.btn_open, 0, Qt.AlignVCenter)

        self.content_layout.addWidget(self.welcome_widget)

        # ==========================================
        # Phase 4: Quick Action Cards (Figma: node 3:12774)
        # ==========================================
        self.cards_row = QWidget()
        self.cards_row.setObjectName("quickActionsRow")
        cards_layout = QHBoxLayout(self.cards_row)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(14)

        # Card 1: Edit a PDF
        self.card_edit = QuickActionCard(
            "edit", "Edit a PDF", "Update text and images.", "pencil.svg", self
        )
        self.card_edit.clicked.connect(lambda: self.open_file_requested.emit())
        self.cards.append(self.card_edit)
        cards_layout.addWidget(self.card_edit, 1)

        # Card 2: Export a PDF
        self.card_export = QuickActionCard(
            "export", "Export a PDF", "Convert to Word, Excel, and more.", "file-output.svg", self
        )
        self.card_export.clicked.connect(self._on_card_export_clicked)
        self.cards.append(self.card_export)
        cards_layout.addWidget(self.card_export, 1)

        # Card 3: Combine files
        self.card_combine = QuickActionCard(
            "combine", "Combine files", "Bring your files into one PDF.", "files.svg", self
        )
        self.card_combine.clicked.connect(lambda: self.combine_files_requested.emit())
        self.cards.append(self.card_combine)
        cards_layout.addWidget(self.card_combine, 1)

        self.content_layout.addWidget(self.cards_row)

        # ==========================================
        # Phase 5: Recent Documents Table Skeleton
        # ==========================================
        self.recent_table = RecentFilesTable(self)
        self.recent_table.file_selected.connect(self.file_selected.emit)
        self.recent_table.file_open_requested.connect(self.file_open_requested.emit)
        self.recent_table.view_mode_changed.connect(self.view_mode_changed.emit)
        self.content_layout.addWidget(self.recent_table)

        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(self.scroll_area, 1)

    def _on_card_export_clicked(self):
        self.open_file_requested.emit()
        self.export_pdf_requested.emit()

    def _on_navigation_changed(self, item_id: str):
        """Dispatches navigation rail selection to the workstation."""
        if item_id in ("recent", "starred"):
            if hasattr(self, "recent_table"):
                self.recent_table.set_category_filter(item_id)

    def set_category(self, category: str):
        """Selects a navigation item on the rail programmatically."""
        if hasattr(self, "left_rail"):
            self.left_rail.select_item(category)

    def update_theme(self):
        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        if hasattr(self, "left_rail"):
            self.left_rail.update_theme()

        if hasattr(self, "recent_table"):
            self.recent_table.update_theme()

        self.btn_open.setIcon(load_themed_svg_icon("folder-open.svg", "#FFFFFF", size=16))

        for card in self.cards:
            card.refresh_icon()

        card_hover_bg = "#FAFAFA" if not is_dark else "#2A2A2A"

        self.setStyleSheet(f"""
            #homeView {{
                background-color: {t.bg};
            }}
            #homeScrollArea {{
                background-color: {t.bg};
                border: none;
            }}
            #homeContentArea {{
                background-color: {t.bg};
            }}
            #welcomeTitle {{
                font-size: 28px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #welcomeSubtitle {{
                font-size: 13px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
            #welcomeOpenBtn {{
                background-color: {t.accent};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                border-radius: 17px;
                padding: 0px 18px 0px 14px;
                border: none;
            }}
            #welcomeOpenBtn:hover {{
                background-color: {t.accent_hover};
            }}
            #quickActionCard {{
                background-color: {t.surface_raised};
                border: 1px solid {t.border};
                border-radius: 8px;
            }}
            #quickActionCard:hover {{
                border: 1px solid {t.accent};
                background-color: {card_hover_bg};
            }}
            #cardTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #cardDesc {{
                font-size: 12px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
        """)
