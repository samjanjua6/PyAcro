"""
File Details Panel for PyAcrobat Home Dashboard.
Matches Figma node 3:12885 ("Selected document details"):
- Fixed 276px width, 8px border radius, 20px padding
- Heading: 'File preview' with ✕ close button
- 148x192px thumbnail frame with drop shadow (PyMuPDF page-1 preview or stylized doc sheet)
- Filename (14px Semi Bold), metadata ('PDF document • N pages • X MB')
- Divider, Modified date & folder location path
- Primary Buttons: 'Open PDF' (blue pill) & 'Share file' (white pill with share icon)
- Secondary Actions: Star toggle, Download, More (⋯)
"""

import os
import subprocess
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QFrame, QGraphicsDropShadowEffect, QApplication, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QFontMetrics, QColor, QPen

from pyacrobat.ui.styles import ThemeManager
from pyacrobat.ui.home_left_rail import load_themed_svg_icon, load_themed_svg_pixmap

_THUMBNAIL_CACHE: Dict[str, QPixmap] = {}


def get_cached_pdf_thumbnail(path: str, max_w: int = 144, max_h: int = 188) -> Optional[QPixmap]:
    """Renders page 0 of a real PDF using PyMuPDF and returns a cached high-DPI QPixmap."""
    if not path or not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        cache_key = f"{path}_{mtime}_{max_w}_{max_h}"
        if cache_key in _THUMBNAIL_CACHE:
            return _THUMBNAIL_CACHE[cache_key]

        import pymupdf
        doc = pymupdf.open(path)
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        rect = page.rect
        scale = min(max_w / rect.width, max_h / rect.height) * 2.0
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()

        pm = QPixmap()
        pm.loadFromData(img_bytes)
        pm.setDevicePixelRatio(2.0)
        _THUMBNAIL_CACHE[cache_key] = pm
        return pm
    except Exception:
        return None


def create_detailed_placeholder_pixmap(name: str = "Document.pdf", is_dark: bool = False) -> QPixmap:
    """Generates a high-DPI 144x188 stylized page preview matching Figma node 3:12890."""
    w, h = 144, 188
    pm = QPixmap(w * 2, h * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)

    bg_color = QColor("#303030" if is_dark else "#FFFFFF")
    border_color = QColor("#444444" if is_dark else "#E0E0E0")
    line_color = QColor("#505050" if is_dark else "#ECECEC")
    text_color = QColor("#E0E0E0" if is_dark else "#242424")
    muted_color = QColor("#888888" if is_dark else "#8C9B9D")

    # Sheet background with subtle border
    painter.setBrush(bg_color)
    painter.setPen(QPen(border_color, 1))
    painter.drawRoundedRect(0, 0, w, h, 4, 4)

    # Top brand / title
    font_bold = QFont("Inter", 8)
    font_bold.setBold(True)
    painter.setFont(font_bold)
    painter.setPen(text_color)
    fm = QFontMetrics(font_bold)
    display_title = fm.elidedText(name.replace(".pdf", "").replace("_", " ").upper(), Qt.ElideRight, w - 24)
    painter.drawText(12, 22, display_title)

    # Centered PDF vector icon
    icon_pm = load_themed_svg_pixmap("file-text.svg", "#EB1000", size=32)
    if not icon_pm.isNull():
        painter.drawPixmap((w - 32) // 2, 40, icon_pm)

    # Faux paragraph lines
    painter.setPen(QPen(line_color, 2))
    painter.drawLine(16, 92, w - 16, 92)
    painter.drawLine(16, 102, w - 16, 102)
    painter.drawLine(16, 112, w - 28, 112)
    painter.drawLine(16, 122, w - 42, 122)

    # Bottom footer rule
    painter.setPen(QPen(line_color, 1))
    painter.drawLine(12, h - 24, w - 12, h - 24)

    # Footer detail & page 1
    font_sub = QFont("Inter", 7)
    painter.setFont(font_sub)
    painter.setPen(muted_color)
    painter.drawText(12, h - 10, "PDF DOCUMENT")
    painter.drawText(w - 20, h - 10, "1")

    painter.end()
    return pm


class FileDetailsPanel(QFrame):
    """
    Selected document details pane (Figma node 3:12885):
    - Width: 276px fixed
    - Embedded to the right of the recent files workstation
    - Displays high-DPI page preview, metadata, actions, and star controls
    """

    open_requested = Signal(str)
    share_requested = Signal(str)
    star_toggled = Signal(dict, bool)
    download_requested = Signal(str)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileDetailsPanel")
        self.setFixedWidth(276)
        self.file_data: Optional[Dict[str, Any]] = None
        self.init_ui()
        self.update_theme()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(13)
        self.main_layout.setAlignment(Qt.AlignTop)

        # ==========================================
        # 1. Heading Row (Figma: node 3:12886)
        # ==========================================
        heading_row = QWidget()
        heading_row.setObjectName("detailsHeadingRow")
        h_layout = QHBoxLayout(heading_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        self.lbl_heading = QLabel("File preview")
        self.lbl_heading.setObjectName("detailsHeadingTitle")
        h_layout.addWidget(self.lbl_heading)

        h_layout.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setObjectName("detailsCloseBtn")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Close preview")
        self.btn_close.setIcon(load_themed_svg_icon("x.svg", "#626262", size=14))
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.clicked.connect(self._on_close_clicked)
        h_layout.addWidget(self.btn_close)

        self.main_layout.addWidget(heading_row)

        # ==========================================
        # 2. Document Preview Frame (Figma: node 3:12890)
        # ==========================================
        preview_container = QWidget()
        preview_container.setObjectName("detailsPreviewContainer")
        p_layout = QHBoxLayout(preview_container)
        p_layout.setContentsMargins(0, 4, 0, 4)
        p_layout.setAlignment(Qt.AlignCenter)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("detailsThumbnailFrame")
        self.thumbnail_frame.setFixedSize(148, 192)

        tf_layout = QVBoxLayout(self.thumbnail_frame)
        tf_layout.setContentsMargins(2, 2, 2, 2)
        tf_layout.setAlignment(Qt.AlignCenter)

        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setStyleSheet("background: transparent;")
        tf_layout.addWidget(self.lbl_thumbnail)

        # Soft drop-shadow effect
        shadow = QGraphicsDropShadowEffect(self.thumbnail_frame)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 36))
        shadow.setOffset(0, 3)
        self.thumbnail_frame.setGraphicsEffect(shadow)

        p_layout.addWidget(self.thumbnail_frame)
        self.main_layout.addWidget(preview_container)

        # ==========================================
        # 3. File Identity (Figma: node 3:12901 - 3:12902)
        # ==========================================
        self.lbl_filename = QLabel("Northstar_Proposal.pdf")
        self.lbl_filename.setObjectName("detailsFilename")
        self.lbl_filename.setWordWrap(True)
        self.main_layout.addWidget(self.lbl_filename)

        self.lbl_meta = QLabel("PDF document • 8 pages • 2.4 MB")
        self.lbl_meta.setObjectName("detailsMetaText")
        self.main_layout.addWidget(self.lbl_meta)

        # ==========================================
        # 4. Divider (Figma: node 3:12903)
        # ==========================================
        self.divider = QFrame()
        self.divider.setObjectName("detailsDivider")
        self.divider.setFixedHeight(1)
        self.main_layout.addWidget(self.divider)

        # ==========================================
        # 5. Metadata Lines (Figma: node 3:12904 - 3:12906)
        # ==========================================
        meta_col = QWidget()
        meta_col.setObjectName("detailsMetaCol")
        mc_layout = QVBoxLayout(meta_col)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.setSpacing(6)

        self.lbl_modified = QLabel("Modified Oct 9, 2026 at 10:42 AM")
        self.lbl_modified.setObjectName("detailsModified")
        mc_layout.addWidget(self.lbl_modified)

        self.lbl_path = QLabel("Documents / Riverside Workplace")
        self.lbl_path.setObjectName("detailsPath")
        self.lbl_path.setWordWrap(True)
        mc_layout.addWidget(self.lbl_path)

        self.main_layout.addWidget(meta_col)

        # ==========================================
        # 6. Primary Action Buttons (Figma: node 3:12907 - 3:12911)
        # ==========================================
        self.btn_open = QPushButton("Open PDF")
        self.btn_open.setObjectName("detailsOpenBtn")
        self.btn_open.setFixedHeight(34)
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._on_open_clicked)
        self.main_layout.addWidget(self.btn_open)

        self.btn_share = QPushButton("  Share file")
        self.btn_share.setObjectName("detailsShareBtn")
        self.btn_share.setFixedHeight(34)
        self.btn_share.setCursor(Qt.PointingHandCursor)
        self.btn_share.setIcon(load_themed_svg_icon("share-2.svg", "#242424", size=16))
        self.btn_share.setIconSize(QSize(16, 16))
        self.btn_share.clicked.connect(self._on_share_clicked)
        self.main_layout.addWidget(self.btn_share)

        # ==========================================
        # 7. Secondary Action Icons (Figma: node 3:12912 - 3:12915)
        # ==========================================
        actions_row = QWidget()
        actions_row.setObjectName("detailsActionsRow")
        a_layout = QHBoxLayout(actions_row)
        a_layout.setContentsMargins(14, 6, 14, 0)
        a_layout.setSpacing(18)
        a_layout.setAlignment(Qt.AlignCenter)

        # Star toggle
        self.btn_star = QToolButton()
        self.btn_star.setObjectName("detailsStarBtn")
        self.btn_star.setFixedSize(30, 30)
        self.btn_star.setCursor(Qt.PointingHandCursor)
        self.btn_star.setToolTip("Star document")
        self.btn_star.setCheckable(True)
        self.btn_star.setIcon(load_themed_svg_icon("star.svg", "#626262", size=18))
        self.btn_star.setIconSize(QSize(18, 18))
        self.btn_star.clicked.connect(self._on_star_clicked)
        a_layout.addWidget(self.btn_star)

        # Download / export
        self.btn_download = QToolButton()
        self.btn_download.setObjectName("detailsDownloadBtn")
        self.btn_download.setFixedSize(30, 30)
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setToolTip("Save a copy")
        self.btn_download.setIcon(load_themed_svg_icon("download.svg", "#626262", size=18))
        self.btn_download.setIconSize(QSize(18, 18))
        self.btn_download.clicked.connect(self._on_download_clicked)
        a_layout.addWidget(self.btn_download)

        # More (⋯)
        self.btn_more = QToolButton()
        self.btn_more.setObjectName("detailsMoreBtn")
        self.btn_more.setFixedSize(30, 30)
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setToolTip("More options")
        self.btn_more.setIcon(load_themed_svg_icon("ellipsis.svg", "#626262", size=18))
        self.btn_more.setIconSize(QSize(18, 18))
        self.btn_more.clicked.connect(self._on_more_clicked)
        a_layout.addWidget(self.btn_more)

        self.main_layout.addWidget(actions_row)

    def set_file_data(self, file_data: Optional[Dict[str, Any]]):
        """Updates the panel with the selected document record."""
        self.file_data = file_data
        if not file_data:
            self.lbl_filename.setText("No file selected")
            self.lbl_meta.setText("-")
            self.lbl_modified.setText("-")
            self.lbl_path.setText("-")
            self.btn_open.setEnabled(False)
            self.btn_share.setEnabled(False)
            return

        self.setVisible(True)
        name = file_data.get("name", "Document.pdf")
        size = file_data.get("size", "-")
        pages = file_data.get("pages")
        date_str = file_data.get("date", "Recently")
        path = file_data.get("path", "")
        starred = bool(file_data.get("starred", False))

        self.lbl_filename.setText(name)
        if pages:
            self.lbl_meta.setText(f"PDF document • {pages} pages • {size}")
        else:
            self.lbl_meta.setText(f"PDF document • {size}")

        self.lbl_modified.setText(f"Modified {date_str}")
        self.lbl_path.setText(path if path else "Your computer")
        self.lbl_path.setToolTip(path)

        self.btn_open.setEnabled(True)
        self.btn_share.setEnabled(True)
        self.btn_star.setChecked(starred)
        self._update_star_icon()

        self._render_thumbnail()

    def _render_thumbnail(self):
        if not self.file_data:
            return
        path = self.file_data.get("path", "")
        name = self.file_data.get("name", "Document.pdf")
        pixmap = None
        if path and os.path.exists(path):
            pixmap = get_cached_pdf_thumbnail(path, 144, 188)

        if pixmap and not pixmap.isNull():
            self.lbl_thumbnail.setPixmap(pixmap)
        else:
            is_dark = ThemeManager.is_dark()
            self.lbl_thumbnail.setPixmap(create_detailed_placeholder_pixmap(name, is_dark))

    def _on_close_clicked(self):
        self.hide()
        self.close_requested.emit()

    def _on_open_clicked(self):
        if not self.file_data:
            return
        path = self.file_data.get("path", "")
        self.open_requested.emit(path)

    def _on_share_clicked(self):
        if not self.file_data:
            return
        path = self.file_data.get("path", "")
        if path and os.path.exists(path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            except Exception:
                pass
        self.share_requested.emit(path)

    def _on_star_clicked(self):
        if not self.file_data:
            return
        new_state = self.btn_star.isChecked()
        self.file_data["starred"] = new_state
        self._update_star_icon()
        self.star_toggled.emit(self.file_data, new_state)

    def _update_star_icon(self):
        is_starred = self.btn_star.isChecked()
        color = "#FFA000" if is_starred else ("#A0A0A0" if ThemeManager.is_dark() else "#626262")
        self.btn_star.setIcon(load_themed_svg_icon("star.svg", color, size=18))

    def _on_download_clicked(self):
        if not self.file_data:
            return
        path = self.file_data.get("path", "")
        self.download_requested.emit(path)

    def _on_more_clicked(self):
        if not self.file_data:
            return
        menu = QMenu(self)
        menu.addAction("📄  Open PDF", self._on_open_clicked)
        menu.addAction("📂  Show in Explorer", self._on_share_clicked)
        path = self.file_data.get("path", "")
        if path:
            menu.addAction("📋  Copy Path", lambda: QApplication.clipboard().setText(path))
        menu.exec(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))

    def update_theme(self):
        t = ThemeManager.get_tokens()
        is_dark = ThemeManager.is_dark()

        panel_bg = "#F8F8F8" if not is_dark else t.surface_raised
        border_color = "#D9D9D9" if not is_dark else t.border
        subtle_border = "#EAEAEA" if not is_dark else t.border_subtle
        thumb_bg = "#FFFFFF" if not is_dark else "#262626"
        share_btn_bg = "#FFFFFF" if not is_dark else t.surface
        btn_hover_bg = "#EBEBEB" if not is_dark else t.accent_subtle

        self.btn_close.setIcon(load_themed_svg_icon("x.svg", t.text_muted, size=14))
        self.btn_share.setIcon(load_themed_svg_icon("share-2.svg", t.text, size=16))
        self.btn_download.setIcon(load_themed_svg_icon("download.svg", t.text_muted, size=18))
        self.btn_more.setIcon(load_themed_svg_icon("ellipsis.svg", t.text_muted, size=18))
        self._update_star_icon()
        self._render_thumbnail()

        self.setStyleSheet(f"""
            #fileDetailsPanel {{
                background-color: {panel_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #detailsHeadingTitle {{
                font-size: 12px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #detailsCloseBtn {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            #detailsCloseBtn:hover {{
                background-color: {btn_hover_bg};
            }}
            #detailsThumbnailFrame {{
                background-color: {thumb_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            #detailsFilename {{
                font-size: 14px;
                font-weight: 600;
                color: {t.text};
                background: transparent;
            }}
            #detailsMetaText {{
                font-size: 11px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
            #detailsDivider {{
                background-color: {subtle_border};
                border: none;
            }}
            #detailsModified, #detailsPath {{
                font-size: 11px;
                font-weight: 400;
                color: {t.text_muted};
                background: transparent;
            }}
            #detailsOpenBtn {{
                background-color: {t.accent};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                border-radius: 17px;
                border: none;
            }}
            #detailsOpenBtn:hover {{
                background-color: {t.accent_hover};
            }}
            #detailsShareBtn {{
                background-color: {share_btn_bg};
                color: {t.text};
                font-size: 13px;
                font-weight: 600;
                border: 1px solid {border_color};
                border-radius: 17px;
            }}
            #detailsShareBtn:hover {{
                background-color: {btn_hover_bg};
            }}
            #detailsStarBtn, #detailsDownloadBtn, #detailsMoreBtn {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            #detailsStarBtn:hover, #detailsDownloadBtn:hover, #detailsMoreBtn:hover {{
                background-color: {btn_hover_bg};
            }}
        """)
