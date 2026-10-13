"""
Merge & Split Workstation Dialogs
Allows merging multiple independent PDF files or extracting custom page ranges.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QLineEdit, QRadioButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt

from pyacrobat.core.pdf_document import PDFDocument


class MergeDialog(QDialog):
    """Dialog to reorder and merge multiple PDF documents into one file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge PDF Documents")
        self.resize(560, 420)
        self.output_file_path: Optional[str] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl = QLabel("Select and arrange PDF files in the order you want to merge them:")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        # File list
        self.file_list = QListWidget()
        self.file_list.setStyleSheet(
            "background-color: #222222; border: 1px solid #383838; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.file_list)

        # File ordering buttons
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Add Files...")
        btn_add.clicked.connect(self._add_files)
        btn_layout.addWidget(btn_add)

        btn_up = QPushButton("⬆ Move Up")
        btn_up.clicked.connect(self._move_up)
        btn_layout.addWidget(btn_up)

        btn_down = QPushButton("⬇ Move Down")
        btn_down.clicked.connect(self._move_down)
        btn_layout.addWidget(btn_down)

        btn_remove = QPushButton("🗑 Remove")
        btn_remove.clicked.connect(self._remove_item)
        btn_layout.addWidget(btn_remove)
        layout.addLayout(btn_layout)

        layout.addWidget(self._create_divider())

        # Action buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_cancel)

        btn_merge = QPushButton("🔀 Merge & Save...")
        btn_merge.setStyleSheet("font-weight: bold; background-color: #1473E6; color: white;")
        btn_merge.clicked.connect(self._do_merge)
        bottom_layout.addWidget(btn_merge)

        layout.addLayout(bottom_layout)

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #404040; margin: 4px 0;")
        return line

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files to Merge", "", "PDF Files (*.pdf)"
        )
        for f in files:
            self.file_list.addItem(f)

    def _move_up(self):
        row = self.file_list.currentRow()
        if row > 0:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row - 1, item)
            self.file_list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.file_list.currentRow()
        if 0 <= row < self.file_list.count() - 1:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row + 1, item)
            self.file_list.setCurrentRow(row + 1)

    def _remove_item(self):
        row = self.file_list.currentRow()
        if row >= 0:
            self.file_list.takeItem(row)

    def _do_merge(self):
        if self.file_list.count() < 2:
            QMessageBox.warning(self, "Need Multiple Files", "Please add at least two PDF files to merge.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF As", "", "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        file_paths = [self.file_list.item(i).text() for i in range(self.file_list.count())]

        try:
            total_pages = PDFDocument.static_merge_pdfs(file_paths, out_path)
            self.output_file_path = out_path
            QMessageBox.information(
                self, "Merge Complete", f"Successfully merged {len(file_paths)} files ({total_pages} pages) into:\n{out_path}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Merge Error", f"Failed to merge PDFs:\n{str(e)}")


class SplitExtractDialog(QDialog):
    """Dialog to extract custom page ranges from the active document."""

    def __init__(self, doc_wrapper: PDFDocument, preselected_indices: Optional[List[int]] = None, parent=None):
        super().__init__(parent)
        self.doc_wrapper = doc_wrapper
        self.setWindowTitle("Extract Pages")
        self.resize(460, 260)
        self.output_file_path: Optional[str] = None
        self.preselected_indices = preselected_indices or []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl = QLabel(f"Document contains {self.doc_wrapper.page_count} pages.")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        # Preselected vs Custom Range
        self.rb_selected = QRadioButton("Extract currently selected page(s)")
        self.rb_range = QRadioButton("Specify custom page range (e.g. 1-2, 3)")

        if self.preselected_indices:
            sel_str = ", ".join(str(i + 1) for i in self.preselected_indices)
            self.rb_selected.setText(f"Extract currently selected pages ({sel_str})")
            self.rb_selected.setChecked(True)
        else:
            self.rb_selected.setEnabled(False)
            self.rb_range.setChecked(True)

        layout.addWidget(self.rb_selected)
        layout.addWidget(self.rb_range)

        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("e.g. 1-2, 3")
        if not self.preselected_indices:
            self.range_input.setText("1")
        layout.addWidget(self.range_input)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_cancel)

        btn_extract = QPushButton("✂ Extract & Save As...")
        btn_extract.setStyleSheet("font-weight: bold; background-color: #1473E6; color: white;")
        btn_extract.clicked.connect(self._do_extract)
        bottom_layout.addWidget(btn_extract)

        layout.addLayout(bottom_layout)

    def _parse_range(self, text: str) -> List[int]:
        """Parses page ranges like '1-3, 5' into 0-based page indices."""
        indices = set()
        parts = text.split(",")
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if "-" in p:
                start_s, end_s = p.split("-", 1)
                start, end = int(start_s), int(end_s)
                for page_num in range(min(start, end), max(start, end) + 1):
                    if 1 <= page_num <= self.doc_wrapper.page_count:
                        indices.add(page_num - 1)
            else:
                page_num = int(p)
                if 1 <= page_num <= self.doc_wrapper.page_count:
                    indices.add(page_num - 1)
        return sorted(list(indices))

    def _do_extract(self):
        if self.rb_selected.isChecked() and self.preselected_indices:
            pages = self.preselected_indices
        else:
            try:
                pages = self._parse_range(self.range_input.text())
            except Exception:
                QMessageBox.warning(self, "Invalid Range", "Please enter a valid page range (e.g. '1-2, 3').")
                return

        if not pages:
            QMessageBox.warning(self, "No Pages", "No valid pages specified for extraction.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Pages As", "", "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        try:
            self.doc_wrapper.extract_pages_to_file(pages, out_path)
            self.output_file_path = out_path
            QMessageBox.information(
                self, "Extraction Complete", f"Successfully extracted {len(pages)} pages to:\n{out_path}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract pages:\n{str(e)}")
