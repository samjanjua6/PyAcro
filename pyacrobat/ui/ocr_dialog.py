"""
OCR Results Dialog for PyAcrobat
Displays optical character recognition output with one-click copy, save, and statistics.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt


class OCRResultDialog(QDialog):
    """Clean Adobe-style dialog displaying recognized OCR text."""

    def __init__(self, text: str, page_number: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"OCR Text Recognition - Page {page_number}")
        self.resize(560, 480)
        self.extracted_text = text
        self.page_number = page_number
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"🔍 OCR Output for Page {self.page_number}")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        words = len(self.extracted_text.split())
        chars = len(self.extracted_text)
        stats = QLabel(f"Words: {words} | Characters: {chars}")
        stats.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        header.addWidget(stats)
        layout.addLayout(header)

        # Text Editor / Display
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.extracted_text)
        self.text_edit.setStyleSheet(
            "background-color: #1A1A1A; color: #E0E0E0; font-family: 'Consolas', 'Segoe UI', monospace; "
            "font-size: 12px; border: 1px solid #333333; border-radius: 4px; padding: 8px;"
        )
        layout.addWidget(self.text_edit)

        # Button Ribbon
        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy to Clipboard")
        btn_copy.setStyleSheet("background-color: #0265DC; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold;")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(btn_copy)

        btn_save = QPushButton("💾 Save to File...")
        btn_save.setStyleSheet("padding: 6px 14px; border-radius: 4px;")
        btn_save.clicked.connect(self._save_to_file)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("padding: 6px 14px; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "Copied", "Recognized text copied to clipboard!")

    def _save_to_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save OCR Text", f"ocr_page_{self.page_number}.txt", "Text Files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())
            QMessageBox.information(self, "Saved", f"Text saved to {os.path.basename(path)}")
