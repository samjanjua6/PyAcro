"""
About Adobe Acrobat Dialog for PyAcrobat Workstation.
Displays application version, architectural specs, and developer information:
- Developer: Shaheer Ul Hassan
- Website: shaheerulhassan.com
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QFont, QPixmap, QDesktopServices, QIcon

from pyacrobat.ui.styles import ThemeManager, get_app_icon


class AboutDialog(QDialog):
    """
    Modern Adobe Spectrum-styled modal dialog displaying about information,
    credits, version, and developer details.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Adobe Acrobat")
        self.setWindowIcon(get_app_icon())
        self.setModal(True)
        self.setFixedSize(460, 540)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        # ==========================================
        # 1. Header with App Icon and Title
        # ==========================================
        header_widget = QWidget()
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(16)
        h_layout.setAlignment(Qt.AlignVCenter)

        # App Icon Badge
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        icon_pixmap = get_app_icon().pixmap(QSize(64, 64))
        self.icon_label.setPixmap(icon_pixmap)
        self.icon_label.setScaledContents(True)
        h_layout.addWidget(self.icon_label)

        # Title + Version Column
        title_col = QWidget()
        tc_layout = QVBoxLayout(title_col)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(4)
        tc_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_title = QLabel("Adobe Acrobat")
        self.lbl_title.setObjectName("aboutTitle")
        font_title = QFont("Inter", 18, QFont.Bold)
        self.lbl_title.setFont(font_title)
        tc_layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel("High-Performance Desktop PDF Workstation")
        self.lbl_subtitle.setObjectName("aboutSubtitle")
        tc_layout.addWidget(self.lbl_subtitle)

        self.lbl_version = QLabel("Version 2026.1.0 · ISO 32000 Compliant")
        self.lbl_version.setObjectName("aboutVersion")
        tc_layout.addWidget(self.lbl_version)

        h_layout.addWidget(title_col, 1)
        layout.addWidget(header_widget)

        # Divider
        self.divider1 = self._create_divider()
        layout.addWidget(self.divider1)

        # ==========================================
        # 2. Developer Card
        # ==========================================
        self.dev_card = QFrame()
        self.dev_card.setObjectName("aboutDevCard")
        dc_layout = QVBoxLayout(self.dev_card)
        dc_layout.setContentsMargins(18, 14, 18, 14)
        dc_layout.setSpacing(8)

        self.lbl_dev_heading = QLabel("DEVELOPER & ARCHITECT")
        self.lbl_dev_heading.setObjectName("aboutDevHeading")
        dc_layout.addWidget(self.lbl_dev_heading)

        self.lbl_dev_name = QLabel("Shaheer Ul Hassan")
        self.lbl_dev_name.setObjectName("aboutDevName")
        font_dev = QFont("Inter", 14, QFont.DemiBold)
        self.lbl_dev_name.setFont(font_dev)
        dc_layout.addWidget(self.lbl_dev_name)

        # Website link
        self.lbl_dev_web = QLabel('Website: <a href="https://shaheerulhassan.com" style="color: #1473E6; text-decoration: none; font-weight: 600;">shaheerulhassan.com</a>')
        self.lbl_dev_web.setObjectName("aboutDevWeb")
        self.lbl_dev_web.setOpenExternalLinks(True)
        dc_layout.addWidget(self.lbl_dev_web)

        layout.addWidget(self.dev_card)

        # ==========================================
        # 3. Technologies & Engine Architecture Card
        # ==========================================
        self.tech_card = QFrame()
        self.tech_card.setObjectName("aboutTechCard")
        t_layout = QVBoxLayout(self.tech_card)
        t_layout.setContentsMargins(18, 14, 18, 14)
        t_layout.setSpacing(8)

        self.lbl_tech_heading = QLabel("CORE ENGINES & TECHNOLOGIES")
        self.lbl_tech_heading.setObjectName("aboutTechHeading")
        t_layout.addWidget(self.lbl_tech_heading)

        tech_items = [
            ("PDF Core Engine", "PyMuPDF (fitz) High-DPI rasterization & page transforms"),
            ("UI Framework", "PySide6 (Qt6) with Adobe Spectrum design tokens"),
            ("OCR & Speech", "Local Tesseract OCR & Neural Edge-TTS engine"),
            ("Standards", "Full ISO 32000 PDF annotation compliance")
        ]
        for title, desc in tech_items:
            row = QLabel(f"• <b>{title}:</b> {desc}")
            row.setObjectName("aboutTechRow")
            row.setWordWrap(True)
            t_layout.addWidget(row)

        layout.addWidget(self.tech_card)

        layout.addStretch(1)

        # ==========================================
        # 4. Action Buttons Footer
        # ==========================================
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(10)

        self.btn_website = QPushButton("Visit Website")
        self.btn_website.setObjectName("aboutWebsiteBtn")
        self.btn_website.setCursor(Qt.PointingHandCursor)
        self.btn_website.setFixedHeight(34)
        self.btn_website.clicked.connect(self._open_website)
        footer_layout.addWidget(self.btn_website)

        footer_layout.addStretch(1)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("aboutCloseBtn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedHeight(34)
        self.btn_close.setFixedWidth(90)
        self.btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(self.btn_close)

        layout.addLayout(footer_layout)

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setFixedHeight(1)
        line.setObjectName("aboutDivider")
        return line

    def _open_website(self):
        QDesktopServices.openUrl(QUrl("https://shaheerulhassan.com"))

    def apply_theme(self):
        t = ThemeManager.get_tokens()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg};
                color: {t.text};
            }}
            #aboutTitle {{
                color: {t.text};
                font-weight: 700;
            }}
            #aboutSubtitle {{
                color: {t.text_muted};
                font-size: 12px;
            }}
            #aboutVersion {{
                color: {t.accent};
                font-size: 11px;
                font-weight: 600;
            }}
            #aboutDivider {{
                background-color: {t.border};
                border: none;
            }}
            #aboutDevCard, #aboutTechCard {{
                background-color: {t.surface_raised};
                border: 1px solid {t.border};
                border-radius: 8px;
            }}
            #aboutDevHeading, #aboutTechHeading {{
                color: {t.text_dim};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            #aboutDevName {{
                color: {t.text};
                font-size: 14px;
                font-weight: 600;
            }}
            #aboutDevWeb {{
                color: {t.text_muted};
                font-size: 12px;
            }}
            #aboutTechRow {{
                color: {t.text};
                font-size: 11px;
            }}
            #aboutWebsiteBtn {{
                background-color: transparent;
                border: 1px solid {t.border_strong};
                color: {t.text};
                border-radius: 17px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            #aboutWebsiteBtn:hover {{
                border-color: {t.accent};
                color: {t.accent};
                background-color: {t.surface_raised};
            }}
            #aboutCloseBtn {{
                background-color: {t.accent};
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            #aboutCloseBtn:hover {{
                background-color: {t.accent_hover};
            }}
        """)
