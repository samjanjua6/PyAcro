"""
Right Power Tools Drawer (Adobe Acrobat Pro Power Tools Suite)
Houses Annotations Feed, OCR Engine, Neural Read Aloud (TTS), Document Export Suite,
and AI Document Assistant in a compact, scrollable side rail.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QFrame, QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QProgressBar, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from pyacrobat.core.tts_engine import SUPPORTED_VOICES
from pyacrobat.ui.ai_chat_panel import AIChatPanel
from pyacrobat.ui.styles import ThemeManager


class RightDrawerWidget(QWidget):
    """Collapsible right drawer housing all Acrobat power tools."""

    # Page & Document Signals
    rotate_cw_requested = Signal()
    rotate_ccw_requested = Signal()
    delete_page_requested = Signal()

    # OCR Signals
    ocr_current_page_requested = Signal()
    ocr_all_pages_requested = Signal()

    # Neural TTS Signals
    tts_play_requested = Signal(str, float)  # voice, speed
    tts_pause_requested = Signal()
    tts_stop_requested = Signal()

    # Export Suite Signals
    export_images_requested = Signal()
    export_markdown_requested = Signal()
    export_text_requested = Signal()
    export_page_image_requested = Signal()

    # AI & Annotations Signals
    ai_ask_requested = Signal(str)
    ai_page_jump_requested = Signal(int)     # Page citation clicked in AI response
    annotation_jump_requested = Signal(int)  # 1-based page
    delete_annotation_requested = Signal(int, int)  # (page_idx, xref)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightDrawer")
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for responsive display on compact screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Header
        title = QLabel("⚡ Acrobat Power Suite")
        title.setObjectName("drawerHeaderTitle")
        layout.addWidget(title)

        # ==========================================
        # SECTION 1: Comments & Annotations Feed
        # ==========================================
        self.sec_annot_label = QLabel("COMMENTS & ANNOTATIONS (0)")
        self.sec_annot_label.setObjectName("powerSectionTitle")
        layout.addWidget(self.sec_annot_label)

        self.annot_list = QListWidget()
        self.annot_list.setMaximumHeight(110)
        self.annot_list.setObjectName("powerListWidget")
        self.annot_list.itemClicked.connect(self._on_annot_item_clicked)
        layout.addWidget(self.annot_list)

        annot_btn_layout = QHBoxLayout()
        btn_del_annot = QPushButton("Delete Note")
        btn_del_annot.clicked.connect(self._on_delete_annot)
        annot_btn_layout.addWidget(btn_del_annot)
        annot_btn_layout.addStretch()
        layout.addLayout(annot_btn_layout)

        # ==========================================
        # SECTION 2: Page Quick Tools
        # ==========================================
        sec_page_label = QLabel("PAGE TOOLS")
        sec_page_label.setObjectName("powerSectionTitle")
        layout.addWidget(sec_page_label)

        page_tools_layout = QHBoxLayout()
        btn_rotate_ccw = QPushButton("↺ 90°")
        btn_rotate_ccw.setToolTip("Rotate Page Counter-Clockwise")
        btn_rotate_ccw.clicked.connect(self.rotate_ccw_requested.emit)
        page_tools_layout.addWidget(btn_rotate_ccw)

        btn_rotate_cw = QPushButton("↻ 90°")
        btn_rotate_cw.setToolTip("Rotate Page Clockwise")
        btn_rotate_cw.clicked.connect(self.rotate_cw_requested.emit)
        page_tools_layout.addWidget(btn_rotate_cw)

        btn_del_page = QPushButton("🗑 Delete")
        btn_del_page.setObjectName("dangerButton")
        btn_del_page.setToolTip("Delete Current Page")
        btn_del_page.clicked.connect(self.delete_page_requested.emit)
        page_tools_layout.addWidget(btn_del_page)
        layout.addLayout(page_tools_layout)

        # ==========================================
        # SECTION 3: Optical Character Recognition (OCR)
        # ==========================================
        sec_ocr_label = QLabel("OPTICAL CHARACTER RECOGNITION (OCR)")
        sec_ocr_label.setObjectName("powerSectionTitle")
        layout.addWidget(sec_ocr_label)

        ocr_box = QFrame()
        ocr_box.setObjectName("powerBox")
        ocr_box_layout = QVBoxLayout(ocr_box)
        ocr_box_layout.setContentsMargins(6, 6, 6, 6)
        ocr_box_layout.setSpacing(6)

        self.lbl_ocr_page_status = QLabel("Page Status: Selectable text")
        self.lbl_ocr_page_status.setObjectName("subtleLabel")
        ocr_box_layout.addWidget(self.lbl_ocr_page_status)

        ocr_btns = QHBoxLayout()
        self.btn_ocr_page = QPushButton("🔍 OCR Page")
        self.btn_ocr_page.setToolTip("Extract text from current page using OCR")
        self.btn_ocr_page.clicked.connect(self.ocr_current_page_requested.emit)
        ocr_btns.addWidget(self.btn_ocr_page)

        self.btn_ocr_doc = QPushButton("📑 OCR All")
        self.btn_ocr_doc.setToolTip("Extract OCR text from all scanned pages")
        self.btn_ocr_doc.clicked.connect(self.ocr_all_pages_requested.emit)
        ocr_btns.addWidget(self.btn_ocr_doc)
        ocr_box_layout.addLayout(ocr_btns)

        layout.addWidget(ocr_box)

        # ==========================================
        # SECTION 4: Neural Read Aloud (Edge-TTS)
        # ==========================================
        sec_tts_label = QLabel("NEURAL READ ALOUD (TTS)")
        sec_tts_label.setObjectName("powerSectionTitle")
        layout.addWidget(sec_tts_label)

        tts_box = QFrame()
        tts_box.setObjectName("powerBox")
        tts_box_layout = QVBoxLayout(tts_box)
        tts_box_layout.setContentsMargins(6, 6, 6, 6)
        tts_box_layout.setSpacing(6)

        # Voice Selector
        voice_row = QHBoxLayout()
        voice_lbl = QLabel("Voice:")
        voice_lbl.setObjectName("subtleLabel")
        voice_row.addWidget(voice_lbl)

        self.combo_voices = QComboBox()
        for voice_id, label in SUPPORTED_VOICES:
            self.combo_voices.addItem(label, voice_id)
        voice_row.addWidget(self.combo_voices)
        tts_box_layout.addLayout(voice_row)

        # Speed Selector
        speed_row = QHBoxLayout()
        speed_lbl = QLabel("Speed:")
        speed_lbl.setObjectName("subtleLabel")
        speed_row.addWidget(speed_lbl)

        self.combo_speed = QComboBox()
        self.combo_speed.addItem("0.75x Slower", 0.75)
        self.combo_speed.addItem("1.0x Normal", 1.0)
        self.combo_speed.addItem("1.25x Fast", 1.25)
        self.combo_speed.addItem("1.5x Brisk", 1.5)
        self.combo_speed.addItem("2.0x Double", 2.0)
        self.combo_speed.setCurrentIndex(1)
        speed_row.addWidget(self.combo_speed)
        tts_box_layout.addLayout(speed_row)

        # Status & Progress
        self.lbl_tts_status = QLabel("Status: Idle")
        self.lbl_tts_status.setObjectName("subtleLabel")
        tts_box_layout.addWidget(self.lbl_tts_status)

        self.tts_progress = QProgressBar()
        self.tts_progress.setTextVisible(False)
        self.tts_progress.setFixedHeight(4)
        self.tts_progress.setRange(0, 100)
        self.tts_progress.setValue(0)
        tts_box_layout.addWidget(self.tts_progress)

        # Controls
        tts_ctrl_row = QHBoxLayout()
        self.btn_tts_play = QPushButton("▶ Play Page")
        self.btn_tts_play.setObjectName("accentButton")
        self.btn_tts_play.clicked.connect(self._on_play_pause_clicked)
        tts_ctrl_row.addWidget(self.btn_tts_play)

        self.btn_tts_stop = QPushButton("⏹ Stop")
        self.btn_tts_stop.clicked.connect(self.tts_stop_requested.emit)
        tts_ctrl_row.addWidget(self.btn_tts_stop)
        tts_box_layout.addLayout(tts_ctrl_row)

        layout.addWidget(tts_box)

        # ==========================================
        # SECTION 5: Document Export Suite
        # ==========================================
        sec_export_label = QLabel("EXPORT & ASSET EXTRACTION")
        sec_export_label.setObjectName("powerSectionTitle")
        layout.addWidget(sec_export_label)

        export_box = QFrame()
        export_box.setObjectName("powerBox")
        export_layout = QVBoxLayout(export_box)
        export_layout.setContentsMargins(6, 6, 6, 6)
        export_layout.setSpacing(6)

        btn_exp_images = QPushButton("🖼 Extract All Images...")
        btn_exp_images.setToolTip("Export all embedded images at original quality")
        btn_exp_images.clicked.connect(self.export_images_requested.emit)
        export_layout.addWidget(btn_exp_images)

        btn_exp_md = QPushButton("📝 Export as Markdown (.md)...")
        btn_exp_md.setToolTip("Export document text to structured Markdown")
        btn_exp_md.clicked.connect(self.export_markdown_requested.emit)
        export_layout.addWidget(btn_exp_md)

        btn_exp_txt = QPushButton("📄 Export as Plain Text (.txt)...")
        btn_exp_txt.setToolTip("Export clean text layout")
        btn_exp_txt.clicked.connect(self.export_text_requested.emit)
        export_layout.addWidget(btn_exp_txt)

        btn_exp_page = QPushButton("📸 Export Page as PNG...")
        btn_exp_page.setToolTip("Render and save high-resolution page snapshot")
        btn_exp_page.clicked.connect(self.export_page_image_requested.emit)
        export_layout.addWidget(btn_exp_page)

        layout.addWidget(export_box)

        # ==========================================
        # SECTION 6: AI Document Assistant
        # ==========================================
        self.ai_chat_panel = AIChatPanel(parent=self)
        self.ai_chat_panel.page_jump_requested.connect(self.ai_page_jump_requested.emit)
        layout.addWidget(self.ai_chat_panel)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_play_pause_clicked(self):
        text = self.btn_tts_play.text()
        if "Play" in text:
            voice = self.combo_voices.currentData()
            speed = float(self.combo_speed.currentData())
            self.tts_play_requested.emit(voice, speed)
        elif "Pause" in text:
            self.tts_pause_requested.emit()
        elif "Resume" in text:
            self.tts_pause_requested.emit()

    def set_tts_state(self, state: str, detail: str = ""):
        if state == "generating":
            self.lbl_tts_status.setText("Status: Generating neural voice...")
            self.btn_tts_play.setText("⏳ Generating...")
            self.btn_tts_play.setEnabled(False)
        elif state == "playing":
            self.lbl_tts_status.setText("Status: Playing audio" + (f" ({detail})" if detail else ""))
            self.btn_tts_play.setText("⏸ Pause")
            self.btn_tts_play.setEnabled(True)
        elif state == "paused":
            self.lbl_tts_status.setText("Status: Paused")
            self.btn_tts_play.setText("▶ Resume")
            self.btn_tts_play.setEnabled(True)
        elif state in ("stopped", "finished", "idle"):
            self.lbl_tts_status.setText("Status: Idle")
            self.btn_tts_play.setText("▶ Play Page")
            self.btn_tts_play.setEnabled(True)
            self.tts_progress.setValue(0)

    def set_tts_progress(self, current_ms: int, total_ms: int):
        if total_ms > 0:
            pct = int((current_ms / total_ms) * 100)
            self.tts_progress.setValue(pct)
            cur_s = current_ms // 1000
            tot_s = total_ms // 1000
            self.lbl_tts_status.setText(f"Playing: {cur_s // 60}:{cur_s % 60:02d} / {tot_s // 60}:{tot_s % 60:02d}")

    def update_page_ocr_status(self, is_scanned: bool, char_count: int):
        tokens = ThemeManager.get_tokens()
        if is_scanned:
            self.lbl_ocr_page_status.setText(f"Page Status: ⚠️ Scanned image ({char_count} chars)")
            self.lbl_ocr_page_status.setStyleSheet(f"color: {tokens.warning}; font-size: 11px; font-weight: 500;")
        else:
            self.lbl_ocr_page_status.setText(f"Page Status: ✅ Text layer ({char_count} chars)")
            self.lbl_ocr_page_status.setStyleSheet(f"color: {tokens.success}; font-size: 11px; font-weight: 500;")

    def update_annotations_feed(self, annotations: List[Dict[str, Any]]):
        self.annot_list.clear()
        self.sec_annot_label.setText(f"COMMENTS & ANNOTATIONS ({len(annotations)})")

        for item in annotations:
            page = item["page"]
            atype = item["type"]
            content = item["content"]
            display_text = f"P.{page} [{atype}]"
            if content:
                display_text += f": {content[:20]}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, (page, item.get("xref")))
            self.annot_list.addItem(list_item)

    def _on_annot_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            page, _ = data
            self.annotation_jump_requested.emit(page)

    def _on_delete_annot(self):
        item = self.annot_list.currentItem()
        if item:
            page, xref = item.data(Qt.UserRole)
            if xref:
                self.delete_annotation_requested.emit(page - 1, xref)

    def set_current_page(self, page_num: int):
        self.ai_chat_panel.set_current_page(page_num)

    def append_ai_message(self, sender: str, message: str):
        if sender == "You":
            self.ai_chat_panel.append_user_message(message)
        else:
            self.ai_chat_panel.append_ai_message(message)

    def update_theme(self):
        self.ai_chat_panel.update_theme()

