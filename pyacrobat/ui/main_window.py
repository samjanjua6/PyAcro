"""
Main Application Window for PyAcrobat (Phase 3 Visual Page Organizer & Document Workstation)
Orchestrates multi-tab documents, Adobe Acrobat UI layout, High-DPI rasterization,
annotations, atomic saving, and responsive screen-bounds management.
"""

import os
from typing import Dict, Optional, Tuple, List
import pymupdf as fitz

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QFileDialog, QMessageBox, QSplitter, QStatusBar,
    QToolButton, QLabel, QApplication, QStackedWidget, QMenu, QMenuBar,
    QFrame
)
from PySide6.QtCore import Qt, Signal, QRect, QThreadPool
from PySide6.QtGui import QAction, QImage, QKeySequence, QShortcut, QFont, QUndoStack, QUndoGroup

from pyacrobat.core.pdf_document import PDFDocument
from pyacrobat.core.ocr_engine import OCREngine, OCRWorker
from pyacrobat.core.tts_engine import TTSController
from pyacrobat.core.export_engine import (
    ExportEngine, ExportWorker, get_format_display_name,
    FORMAT_DOCX, FORMAT_XLSX, FORMAT_PPTX, FORMAT_PNG, FORMAT_IMAGE
)
from pyacrobat.ui.export_progress_dialog import ExportProgressDialog, ExportSuccessDialog
from pyacrobat.ui.styles import (
    ACROBAT_DARK_THEME, ACROBAT_LIGHT_THEME, ThemeManager, generate_theme_stylesheet,
    get_app_icon
)
from pyacrobat.ui.app_nav_bar import AppNavBar
from pyacrobat.ui.quick_tools_bar import QuickToolsBar
from pyacrobat.ui.page_controls_bar import PageControlsBar
from pyacrobat.ui.floating_tools import FloatingQuickTools
from pyacrobat.ui.all_tools_panel import AllToolsPanel
from pyacrobat.ui.right_nav_rail import RightNavRail
from pyacrobat.ui.left_rail import LeftRailWidget
from pyacrobat.ui.right_drawer import RightDrawerWidget
from pyacrobat.ui.comments_panel import CommentsPanel
from pyacrobat.ui.thumbnails_panel import PageThumbnailsPanel
from pyacrobat.ui.bookmarks_panel import BookmarksPanel
from pyacrobat.ui.tts_player import TTSMiniPlayer
from pyacrobat.ui.pdf_canvas import PDFCanvas
from pyacrobat.ui.organizer_grid import OrganizerGridWidget
from pyacrobat.ui.merge_dialog import MergeDialog, SplitExtractDialog
from pyacrobat.ui.ocr_dialog import OCRResultDialog
from pyacrobat.ui.about_dialog import AboutDialog
from pyacrobat.ui.home_view import HomeView
from pyacrobat.core.recent_files import RecentFilesManager
from pyacrobat.ui.edit_pdf_panel import EditPdfPanel
from pyacrobat.ui.export_pdf_panel import ExportPdfPanel
from pyacrobat.core.pdf_editor import FontStyle, ContentBlock
from pyacrobat.ui.page_utility_dialogs import (
    HeaderFooterDialog, WatermarkDialog, CropPagesDialog, LinkDialog
)
from pyacrobat.core.undo_commands import (
    PageSnapshotManager,
    PageSnapshotCommand,
    RotatePageCommand,
    CropPageCommand,
    DeletePagesCommand,
    InsertBlankPageCommand,
    DuplicatePageCommand,
    ReorderPagesCommand,
    AddAnnotationCommand,
    DeleteAnnotationCommand,
    AddLinkCommand
)


class ViewportContainer(QWidget):
    """Viewport container housing toolbar, canvas, and controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("documentViewportContainer")

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(350, 200)


class DocumentTab(QWidget):
    """
    Container for an open PDF document.
    Switches between Reading View (continuous scroll) and Organize Pages View (thumbnail grid).
    """

    dirty_state_changed = Signal(bool)
    view_mode_changed = Signal(bool)  # True = Organize View, False = Reading View

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.doc_wrapper = PDFDocument(file_path)
        self.current_zoom = 1.0
        self.current_page = 1

        self.current_tool = "select"
        self.highlight_color = (1.0, 0.88, 0.3)
        self.draw_color = (0.88, 0.15, 0.11)
        self.draw_width = 2.0
        self.is_edit_mode = False
        self.is_convert_mode = False

        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(50)
        self.undo_stack.cleanChanged.connect(self._on_undo_clean_changed)

        self.init_ui()
        self.load_document()

    def _on_undo_clean_changed(self, is_clean: bool):
        is_dirty = not is_clean
        self.doc_wrapper.is_dirty = is_dirty
        self.dirty_state_changed.emit(is_dirty)

    def undo(self):
        """Undoes the most recent action on this document."""
        if self.undo_stack.canUndo():
            self.undo_stack.undo()

    def redo(self):
        """Redoes the most recent undone action on this document."""
        if self.undo_stack.canRedo():
            self.undo_stack.redo()

    def _on_undo_redo_modified(self, affected_pages: List[int], structure_changed: bool = False):
        if structure_changed:
            page_count = self.doc_wrapper.page_count
            self.current_page = max(1, min(page_count, self.current_page))
            if self.is_organize_view_active():
                self.show_organize_view()
            else:
                self.canvas.setup_pages(page_count)
                self.render_all_pages()
                self.refresh_sidebars()
                self.go_to_page(self.current_page)
                if self.is_edit_mode:
                    self.load_content_blocks()
            if hasattr(self, "page_controls"):
                self.page_controls.update_page_info(self.current_page, page_count)
        else:
            if self.is_organize_view_active():
                self.show_organize_view()
            else:
                pages_to_render = affected_pages if affected_pages else list(range(self.doc_wrapper.page_count))
                for p in pages_to_render:
                    if 0 <= p < self.doc_wrapper.page_count:
                        self.re_render_page(p)
                        if self.is_edit_mode:
                            self.canvas.set_page_content_blocks(p, self.doc_wrapper.get_content_blocks(p))
                self.refresh_annotations_feed()
                self.update_current_page_status()

        win = self.window()
        if win and hasattr(win, "_update_status_bar_info"):
            win._update_status_bar_info()

    def get_screen_dpr_and_dpi(self) -> Tuple[float, float]:
        screen = self.screen() or QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.25
        dpi = screen.logicalDotsPerInch() if screen else 96.0
        return dpr, dpi

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Page 0: Reading View (4-Column Layout: All Tools Panel | Viewport | Right Drawer | Nav Rail)
        self.reading_view = QWidget()
        rv_layout = QHBoxLayout(self.reading_view)
        rv_layout.setContentsMargins(0, 0, 0, 0)
        rv_layout.setSpacing(0)

        # 1. Column 1: All Tools Panel (232px fixed, collapsible)
        self.all_tools_panel = AllToolsPanel(self)
        self.all_tools_panel.collapse_requested.connect(self.toggle_all_tools_panel)
        self.all_tools_panel.tool_selected.connect(self._on_all_tool_action)
        rv_layout.addWidget(self.all_tools_panel)

        # Edit PDF Tool Drawer (284px fixed, Figma #3:13204)
        self.edit_pdf_panel = EditPdfPanel(self)
        self.edit_pdf_panel.setVisible(False)
        self.edit_pdf_panel.close_requested.connect(self._on_edit_panel_closed)
        self.edit_pdf_panel.tool_selected.connect(self._on_edit_tool_selected)
        self.edit_pdf_panel.font_style_changed.connect(self._on_panel_font_style_changed)
        self.edit_pdf_panel.header_footer_requested.connect(self._on_edit_header_footer)
        self.edit_pdf_panel.watermark_requested.connect(self._on_edit_watermark)
        self.edit_pdf_panel.crop_requested.connect(self._on_edit_crop)
        rv_layout.addWidget(self.edit_pdf_panel)

        # Export PDF Tool Drawer (308px fixed, Figma #3:13809)
        self.export_pdf_panel = ExportPdfPanel(self)
        self.export_pdf_panel.setVisible(False)
        self.export_pdf_panel.close_requested.connect(self._on_export_panel_closed)
        self.export_pdf_panel.export_requested.connect(self._on_export_requested)
        rv_layout.addWidget(self.export_pdf_panel)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)

        # Left Rail Drawer (Thumbnails, TOC, Search) - initial width 0 (drawer closed)
        self.left_rail = LeftRailWidget()
        self.left_rail.setVisible(False)
        self.left_rail.page_selected.connect(self.go_to_page)
        self.left_rail.search_requested.connect(self.search_text)
        self.splitter.addWidget(self.left_rail)

        # 2. Column 2: Central PDF Viewport (Page Controls Bar + Floating Tools Pill + Canvas)
        self.viewport_container = ViewportContainer()
        vp_layout = QVBoxLayout(self.viewport_container)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(0)

        # In-viewport Page Controls Bar (Centered above canvas)
        self.page_controls = PageControlsBar(self.viewport_container)
        self.page_controls.zoom_in_requested.connect(self.zoom_in)
        self.page_controls.zoom_out_requested.connect(self.zoom_out)
        self.page_controls.zoom_level_changed.connect(self.set_zoom)
        self.page_controls.fit_width_requested.connect(self.fit_width)
        self.page_controls.fit_page_requested.connect(self.fit_page)
        self.page_controls.page_jump_requested.connect(self.go_to_page)
        self.page_controls.rotate_cw_requested.connect(self.rotate_current_page_cw)
        self.page_controls.rotate_ccw_requested.connect(self.rotate_current_page_ccw)
        self.page_controls.delete_page_requested.connect(self.delete_current_page)
        self.page_controls.organize_pages_requested.connect(self.show_organize_view)
        self.page_controls.tts_toggle_requested.connect(self.toggle_tts_player)
        vp_layout.addWidget(self.page_controls)

        # Neural Read Aloud Mini-Player (Embedded under toolbar)
        self.tts_player = TTSMiniPlayer(self.viewport_container)
        self.tts_player.setVisible(False)
        self.tts_player.play_requested.connect(self.play_read_aloud)
        self.tts_player.pause_requested.connect(self.pause_read_aloud)
        self.tts_player.stop_requested.connect(self.stop_read_aloud)
        vp_layout.addWidget(self.tts_player)

        # Floating Quick Tools Pill Container
        self.floating_tools_container = QWidget()
        self.floating_tools_container.setObjectName("floatingToolsContainer")
        ft_layout = QHBoxLayout(self.floating_tools_container)
        ft_layout.setContentsMargins(0, 6, 0, 6)
        ft_layout.setAlignment(Qt.AlignCenter)
        self.floating_tools = FloatingQuickTools(self.floating_tools_container)
        self.floating_tools.tool_changed.connect(self.set_tool)
        self.floating_tools.highlight_color_changed.connect(self.set_highlight_color)
        self.floating_tools.draw_style_changed.connect(self.set_draw_style)
        ft_layout.addWidget(self.floating_tools)
        vp_layout.addWidget(self.floating_tools_container)

        self.canvas = PDFCanvas()
        self.canvas.page_scrolled_to.connect(self._on_canvas_scrolled_to_page)
        self.canvas.highlight_requested.connect(self._on_highlight_created)
        self.canvas.ink_requested.connect(self._on_ink_drawn)
        self.canvas.note_requested.connect(self._on_note_created)

        # Canvas Edit Mode Signal Wiring
        self.edit_pdf_panel.bounding_boxes_toggled.connect(self.canvas.set_show_bounding_boxes)
        self.canvas.block_selected.connect(self._on_canvas_block_selected)
        self.canvas.block_text_edited.connect(self._on_canvas_block_text_edited)
        self.canvas.block_font_style_changed.connect(self._on_canvas_block_font_style_changed)
        self.canvas.block_rect_changed.connect(self._on_canvas_block_rect_changed)
        self.canvas.new_textbox_requested.connect(self._on_canvas_new_textbox_requested)

        vp_layout.addWidget(self.canvas)

        # Convert Mode Preview Floating Badge (Figma #3:13915)
        self.preview_badge_container = QWidget()
        self.preview_badge_container.setObjectName("previewBadgeContainer")
        pbc_layout = QHBoxLayout(self.preview_badge_container)
        pbc_layout.setContentsMargins(14, 6, 14, 8)
        pbc_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.preview_badge_pill = QFrame()
        self.preview_badge_pill.setObjectName("previewBadgePill")
        pill_layout = QHBoxLayout(self.preview_badge_pill)
        pill_layout.setContentsMargins(10, 4, 12, 4)
        pill_layout.setSpacing(6)

        self.icon_badge_eye = QLabel()
        self.icon_badge_eye.setFixedSize(16, 16)
        pill_layout.addWidget(self.icon_badge_eye)

        self.lbl_preview_badge = QLabel("Preview of original PDF • All pages will be exported")
        self.lbl_preview_badge.setFont(QFont("Inter", 8))
        pill_layout.addWidget(self.lbl_preview_badge)

        pbc_layout.addWidget(self.preview_badge_pill)
        self.preview_badge_container.setVisible(False)
        vp_layout.addWidget(self.preview_badge_container)

        self.splitter.addWidget(self.viewport_container)


        # 3. Column 3: Stacked right panel (CommentsPanel | Power Tools Drawer) 268px
        # Page 0 = CommentsPanel (Figma #3:13075)
        # Page 1 = RightDrawerWidget (Power Suite: OCR, TTS, Export, AI)
        self.right_panel_stack = QStackedWidget()
        self.right_panel_stack.setObjectName("rightPanelStack")
        self.right_panel_stack.setMinimumWidth(260)
        self.right_panel_stack.setMaximumWidth(650)

        # CommentsPanel (Figma-faithful, primary view)
        self.comments_panel = CommentsPanel()
        self.comments_panel.close_requested.connect(self._on_comments_panel_close)
        self.comments_panel.comment_added.connect(self._on_comment_added)
        self.comments_panel.comment_deleted.connect(self._on_delete_annotation)
        self.comments_panel.page_jump_requested.connect(self.go_to_page)
        self.right_panel_stack.addWidget(self.comments_panel)   # index 0

        # Right Power Suite Drawer (OCR, TTS, Export, AI)
        self.right_drawer = RightDrawerWidget()
        self.right_drawer.rotate_cw_requested.connect(self.rotate_current_page_cw)
        self.right_drawer.rotate_ccw_requested.connect(self.rotate_current_page_ccw)
        self.right_drawer.delete_page_requested.connect(self.delete_current_page)
        self.right_drawer.ocr_current_page_requested.connect(self.run_ocr_current_page)
        self.right_drawer.ocr_all_pages_requested.connect(self.run_ocr_all_pages)
        self.right_drawer.tts_play_requested.connect(self.play_read_aloud)
        self.right_drawer.tts_pause_requested.connect(self.pause_read_aloud)
        self.right_drawer.tts_stop_requested.connect(self.stop_read_aloud)
        self.right_drawer.export_images_requested.connect(self.export_all_images)
        self.right_drawer.export_markdown_requested.connect(self.export_markdown)
        self.right_drawer.export_text_requested.connect(self.export_text)
        self.right_drawer.export_page_image_requested.connect(self.export_page_image)
        self.right_drawer.ai_ask_requested.connect(self.ask_ai)
        self.right_drawer.ai_page_jump_requested.connect(self.go_to_page)
        self.right_drawer.annotation_jump_requested.connect(self.go_to_page)
        self.right_drawer.delete_annotation_requested.connect(self._on_delete_annotation)
        self.right_drawer.close_requested.connect(self._on_right_panel_close)
        self.right_panel_stack.addWidget(self.right_drawer)     # index 1

        # Page Thumbnails Panel (Figma right drawer page 2)
        self.thumbnails_panel = PageThumbnailsPanel()
        self.thumbnails_panel.page_selected.connect(self.go_to_page)
        self.thumbnails_panel.close_requested.connect(self._on_right_panel_close)
        self.right_panel_stack.addWidget(self.thumbnails_panel) # index 2

        # Bookmarks & Table of Contents Panel (Figma right drawer page 3)
        self.bookmarks_panel = BookmarksPanel()
        self.bookmarks_panel.page_selected.connect(self.go_to_page)
        self.bookmarks_panel.close_requested.connect(self._on_right_panel_close)
        self.right_panel_stack.addWidget(self.bookmarks_panel)  # index 3

        # Default: show CommentsPanel first (matches Figma)
        self.right_panel_stack.setCurrentIndex(0)

        self.splitter.addWidget(self.right_panel_stack)

        # TTS Controller
        self.tts_controller = TTSController(self)
        self.tts_controller.state_changed.connect(self._on_tts_state_changed)
        self.tts_controller.progress_updated.connect(self._on_tts_progress)
        self.tts_controller.error_occurred.connect(self._on_tts_error)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([0, 750, 310])

        rv_layout.addWidget(self.splitter)

        # 4. Column 4: Far Right Navigation Rail (48px fixed)
        self.right_nav_rail = RightNavRail(self)
        self.right_nav_rail.tab_selected.connect(self._on_right_nav_tab_selected)
        rv_layout.addWidget(self.right_nav_rail)

        self.stack.addWidget(self.reading_view)

        # Page 1: Organize Pages Grid Workstation
        self.organizer_grid = OrganizerGridWidget()
        self.organizer_grid.back_to_reading_requested.connect(self.show_reading_view)
        self.organizer_grid.page_double_clicked.connect(self._on_grid_double_click)
        self.organizer_grid.reorder_requested.connect(self._on_reorder_pages)
        self.organizer_grid.rotate_requested.connect(self._on_rotate_grid_pages)
        self.organizer_grid.delete_requested.connect(self._on_delete_grid_pages)
        self.organizer_grid.insert_blank_requested.connect(self._on_insert_blank_page)
        self.organizer_grid.duplicate_requested.connect(self._on_duplicate_pages)
        self.organizer_grid.merge_requested.connect(self._on_merge_external)
        self.organizer_grid.extract_requested.connect(self._on_extract_pages)
        self.organizer_grid.replace_requested.connect(self._on_replace_grid_pages)
        self.organizer_grid.split_requested.connect(self._on_split_grid_pages)
        self.organizer_grid.crop_requested.connect(self._on_crop_grid_pages)
        self.organizer_grid.page_labels_requested.connect(self._on_page_labels_requested)
        self.organizer_grid.right_nav_rail.tab_selected.connect(self._on_organizer_nav_tab_selected)
        self.stack.addWidget(self.organizer_grid)

        layout.addWidget(self.stack)

    def load_document(self):
        page_count = self.doc_wrapper.page_count
        dpr, dpi = self.get_screen_dpr_and_dpi()
        page_dims = [
            (self.doc_wrapper.get_page(i).rect.width, self.doc_wrapper.get_page(i).rect.height)
            for i in range(page_count)
        ]
        self.canvas.setup_document(self.doc_wrapper, page_dims, self.current_zoom, dpr, dpi)
        self.refresh_sidebars()
        self.update_current_page_status()
        if hasattr(self, "page_controls"):
            self.page_controls.update_page_info(self.current_page, page_count)
            self.page_controls.update_zoom_display(self.current_zoom)
        self.right_drawer.set_document(self.doc_wrapper, self.file_path)
        self.right_drawer.ai_chat_panel.manager.index_document(self.doc_wrapper)

    def update_current_page_status(self):
        if 0 <= self.current_page - 1 < self.doc_wrapper.page_count:
            page = self.doc_wrapper.get_page(self.current_page - 1)
            text = page.get_text("text").strip()
            is_scanned = OCREngine.is_page_scanned(page)
            self.right_drawer.update_page_ocr_status(is_scanned, len(text))
            self.right_drawer.set_current_page(self.current_page)
            if hasattr(self, "comments_panel"):
                self.comments_panel.set_current_page(self.current_page)
            if hasattr(self, "thumbnails_panel"):
                self.thumbnails_panel.set_current_page(self.current_page)
            if hasattr(self, "bookmarks_panel"):
                self.bookmarks_panel.set_current_page(self.current_page)

    def refresh_sidebars(self):
        page_count = self.doc_wrapper.page_count
        thumbnails = [self.doc_wrapper.render_thumbnail(i, target_width=180) for i in range(page_count)]
        if hasattr(self, "thumbnails_panel"):
            self.thumbnails_panel.load_thumbnails(thumbnails)
        if hasattr(self, "bookmarks_panel"):
            self.bookmarks_panel.load_outline(self.doc_wrapper.get_toc())
        self.left_rail.load_thumbnails(thumbnails)
        self.left_rail.load_outline(self.doc_wrapper.get_toc())
        self.refresh_annotations_feed()

    def render_all_pages(self):
        dpr, dpi = self.get_screen_dpr_and_dpi()
        if hasattr(self.canvas, "render_manager"):
            self.canvas.render_manager.set_scale_and_dpi(self.current_zoom, dpr, dpi)
            self.canvas.render_manager.invalidate_all_pages()
        self.canvas.update_visible_pages_cache()

    def re_render_page(self, page_index: int):
        if hasattr(self.canvas, "render_manager"):
            self.canvas.render_manager.invalidate_page(page_index)
        self.canvas.update_visible_pages_cache()

    # ==========================================
    # View Switching
    # ==========================================

    def is_organize_view_active(self) -> bool:
        return self.stack.currentIndex() == 1

    def show_organize_view(self):
        if hasattr(self.canvas, "render_manager"):
            self.canvas.render_manager.cancel_all()
        thumbnails = [
            self.doc_wrapper.render_thumbnail(i, target_width=170)
            for i in range(self.doc_wrapper.page_count)
        ]
        file_name = os.path.basename(self.file_path) if self.file_path else "Document.pdf"
        toc = self.doc_wrapper.get_toc()
        self.organizer_grid.populate_grid(thumbnails, file_name=file_name, bookmarks=toc)
        self.stack.setCurrentIndex(1)
        self.view_mode_changed.emit(True)

    def show_reading_view(self):
        self.stack.setCurrentIndex(0)
        dpr, dpi = self.get_screen_dpr_and_dpi()
        page_dims = [
            (self.doc_wrapper.get_page(i).rect.width, self.doc_wrapper.get_page(i).rect.height)
            for i in range(self.doc_wrapper.page_count)
        ]
        self.canvas.setup_document(self.doc_wrapper, page_dims, self.current_zoom, dpr, dpi)
        self.refresh_sidebars()
        self.go_to_page(min(self.current_page, self.doc_wrapper.page_count))
        self.view_mode_changed.emit(False)

    def _on_grid_double_click(self, page_number: int):
        self.show_reading_view()
        self.go_to_page(page_number)

    # ==========================================
    # Page Operations
    # ==========================================

    def _on_reorder_pages(self, new_order: List[int]):
        cmd = ReorderPagesCommand(
            self.doc_wrapper,
            new_order,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_rotate_grid_pages(self, page_indices: List[int], degrees: int):
        cmd = RotatePageCommand(
            self.doc_wrapper,
            page_indices,
            degrees,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_delete_grid_pages(self, page_indices: List[int]):
        if len(page_indices) >= self.doc_wrapper.page_count:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete all pages in the document.")
            return
        cmd = DeletePagesCommand(
            self.doc_wrapper,
            page_indices,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_insert_blank_page(self, at_index: int):
        clamped_idx = max(0, min(self.doc_wrapper.page_count, at_index))
        cmd = InsertBlankPageCommand(
            self.doc_wrapper,
            clamped_idx,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_duplicate_pages(self, page_indices: List[int]):
        if not page_indices:
            return
        if len(page_indices) > 1:
            self.undo_stack.beginMacro(f"Duplicate {len(page_indices)} Pages")
        for idx in sorted(page_indices, reverse=True):
            cmd = DuplicatePageCommand(
                self.doc_wrapper,
                idx,
                on_modified=self._on_undo_redo_modified,
                already_executed=False
            )
            self.undo_stack.push(cmd)
        if len(page_indices) > 1:
            self.undo_stack.endMacro()

    def _on_merge_external(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File to Insert", "", "PDF Files (*.pdf)"
        )
        if file_path:
            count = self.doc_wrapper.merge_external_pdf(file_path)
            self.show_organize_view()
            self.dirty_state_changed.emit(True)
            QMessageBox.information(self, "Merged", f"Inserted {count} pages from {os.path.basename(file_path)}.")

    def _on_extract_pages(self, page_indices: List[int]):
        dialog = SplitExtractDialog(self.doc_wrapper, preselected_indices=page_indices, parent=self)
        dialog.exec()

    def _on_replace_grid_pages(self, page_indices: List[int]):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to Replace Page(s)", "", "PDF Files (*.pdf)"
        )
        if file_path:
            insert_at = page_indices[0] if page_indices else 0
            self.doc_wrapper.merge_external_pdf(file_path)
            self.show_organize_view()
            self.dirty_state_changed.emit(True)

    def _on_split_grid_pages(self, page_indices: List[int]):
        dialog = SplitExtractDialog(self.doc_wrapper, preselected_indices=page_indices, parent=self)
        dialog.exec()

    def _on_crop_grid_pages(self, page_indices: List[int]):
        QMessageBox.information(
            self, "Crop Pages",
            "To crop specific page margins, double-click to view the page and use Page Setup."
        )

    def _on_page_labels_requested(self):
        QMessageBox.information(
            self, "Page Labels",
            "Page labels are dynamically synchronized with document bookmarks and section outlines."
        )

    def _on_organizer_nav_tab_selected(self, tab_id: str):
        if tab_id != "pages":
            self.show_reading_view()
            self._on_right_nav_tab_selected(tab_id)

    # ==========================================
    # Reading View Controls
    # ==========================================

    def go_to_page(self, page_number: int):
        self.current_page = max(1, min(self.doc_wrapper.page_count, page_number))
        self.canvas.scroll_to_page(self.current_page)
        self.update_current_page_status()
        if hasattr(self, "page_controls"):
            self.page_controls.update_page_info(self.current_page, self.doc_wrapper.page_count)
        win = self.window()
        if win and hasattr(win, "_update_status_bar_info"):
            win._update_status_bar_info()

    def set_zoom(self, zoom: float):
        self.current_zoom = max(0.25, min(4.0, zoom))
        dpr, dpi = self.get_screen_dpr_and_dpi()
        self.canvas.set_zoom(self.current_zoom, dpr, dpi)
        if hasattr(self, "page_controls"):
            self.page_controls.update_zoom_display(self.current_zoom)

    def zoom_in(self):
        self.set_zoom(self.current_zoom + 0.2)

    def zoom_out(self):
        self.set_zoom(self.current_zoom - 0.2)

    def fit_width(self):
        vp_width = self.canvas.viewport().width() - 80
        if vp_width > 100:
            p0 = self.doc_wrapper.get_page(0)
            target_scale = vp_width / max(1.0, p0.rect.width)
            self.set_zoom(target_scale)

    def fit_page(self):
        vp_height = self.canvas.viewport().height() - 80
        if vp_height > 100:
            p0 = self.doc_wrapper.get_page(0)
            target_scale = vp_height / max(1.0, p0.rect.height)
            self.set_zoom(target_scale)

    def _on_canvas_scrolled_to_page(self, page_number: int):
        self.current_page = page_number
        self.update_current_page_status()
        if hasattr(self, "page_controls"):
            self.page_controls.update_page_info(self.current_page, self.doc_wrapper.page_count)
        win = self.window()
        if win and hasattr(win, "_update_status_bar_info"):
            win._update_status_bar_info()

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.canvas.set_tool(tool_name)
        if hasattr(self, "floating_tools"):
            self.floating_tools.set_tool(tool_name, emit_signal=False)

    def set_highlight_color(self, rgb: Tuple[float, float, float]):
        self.highlight_color = rgb
        self.canvas.set_highlight_color(rgb)

    def set_draw_style(self, rgb: Tuple[float, float, float], width: float):
        self.draw_color = rgb
        self.draw_width = width
        self.canvas.set_draw_style(rgb, width)

    def _on_highlight_created(self, page_index: int, rect: fitz.Rect):
        cmd = AddAnnotationCommand(
            self.doc_wrapper,
            page_index,
            "highlight",
            {"rect": rect, "color": self.highlight_color},
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_ink_drawn(self, page_index: int, points: list):
        cmd = AddAnnotationCommand(
            self.doc_wrapper,
            page_index,
            "ink",
            {"strokes": [points], "color": self.draw_color, "width": self.draw_width},
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_note_created(self, page_index: int, pt: tuple, text: str):
        cmd = AddAnnotationCommand(
            self.doc_wrapper,
            page_index,
            "note",
            {"point": pt, "content": text, "author": "Reviewer"},
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_delete_annotation(self, page_index: int, xref: int):
        annot_dict = None
        for a in self.doc_wrapper.get_all_annotations():
            if a.get("xref") == xref:
                annot_dict = a
                break
        if not annot_dict:
            annot_dict = {"xref": xref, "type": "Annotation"}
        cmd = DeleteAnnotationCommand(
            self.doc_wrapper,
            page_index,
            annot_dict,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def refresh_annotations_feed(self):
        annots = self.doc_wrapper.get_all_annotations()
        self.right_drawer.update_annotations_feed(annots)
        if hasattr(self, "comments_panel"):
            self.comments_panel.populate_from_annotations(annots)

    def _on_comment_added(self, page_num: int, text: str):
        """Called when user posts a comment in CommentsPanel."""
        # Anchor the note near the top-left of the page (PDF user-space coords)
        try:
            page = self.doc_wrapper.get_page(page_num - 1)
            rect = page.rect
            pt = (rect.x0 + 36, rect.y0 + 36)
        except Exception:
            pt = (36, 36)
        cmd = AddAnnotationCommand(
            self.doc_wrapper,
            page_num - 1,
            "note",
            {"point": pt, "content": text, "author": "Reviewer"},
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def _on_right_panel_close(self):
        """Hide right panel when ✕ is clicked in any right drawer panel header."""
        self.right_panel_stack.setVisible(False)
        self.right_nav_rail.set_active_tab(None)

    def _on_comments_panel_close(self):
        """Hide right panel when ✕ is clicked in CommentsPanel header."""
        self._on_right_panel_close()

    def search_text(self, query: str):
        results = self.doc_wrapper.search_text(query)
        self.left_rail.set_search_results(results)

    def rotate_current_page_cw(self):
        cmd = RotatePageCommand(
            self.doc_wrapper,
            [self.current_page - 1],
            90,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def rotate_current_page_ccw(self):
        cmd = RotatePageCommand(
            self.doc_wrapper,
            [self.current_page - 1],
            -90,
            on_modified=self._on_undo_redo_modified,
            already_executed=False
        )
        self.undo_stack.push(cmd)

    def delete_current_page(self):
        if self.doc_wrapper.page_count <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the only page in the document.")
            return
        res = QMessageBox.question(
            self, "Delete Page", f"Are you sure you want to delete Page {self.current_page}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            idx = self.current_page - 1
            cmd = DeletePagesCommand(
                self.doc_wrapper,
                [idx],
                on_modified=self._on_undo_redo_modified,
                already_executed=False
            )
            self.undo_stack.push(cmd)

    # ==========================================
    # OCR Engine Handlers
    # ==========================================

    def run_ocr_current_page(self):
        page_idx = self.current_page - 1
        page = self.doc_wrapper.get_page(page_idx)
        text = OCREngine.ocr_page(page, language="eng", dpi=300)
        if not text:
            text = page.get_text("text").strip()
        if not text:
            text = "[No text recognized on this page]"
        dialog = OCRResultDialog(text, self.current_page, parent=self)
        dialog.exec()

    def run_ocr_all_pages(self):
        scanned_indices = [
            i for i in range(self.doc_wrapper.page_count)
            if OCREngine.is_page_scanned(self.doc_wrapper.get_page(i))
        ]
        if not scanned_indices:
            res = QMessageBox.question(
                self, "OCR All Pages",
                "All pages already contain selectable text layers. Run OCR across all pages anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.No:
                return
            scanned_indices = list(range(self.doc_wrapper.page_count))

        self.ocr_worker = OCRWorker(self.doc_wrapper, scanned_indices, language="eng", dpi=300)
        self.ocr_worker.all_done.connect(self._on_ocr_all_done)
        self.ocr_worker.error.connect(lambda err: QMessageBox.warning(self, "OCR Error", err))
        self.right_drawer.append_ai_message("OCR Engine", f"Running background OCR across {len(scanned_indices)} page(s)...")
        self.ocr_worker.start()

    def _on_ocr_all_done(self, results: Dict[int, str]):
        total_words = sum(len(txt.split()) for txt in results.values())
        self.right_drawer.append_ai_message(
            "OCR Engine",
            f"OCR completed! Recognized {total_words} words across {len(results)} pages."
        )
        combined_text = "\n\n".join([f"=== PAGE {p + 1} ===\n{t}" for p, t in sorted(results.items())])
        dialog = OCRResultDialog(combined_text, 1, parent=self)
        dialog.setWindowTitle("OCR Output - All Recognized Pages")
        dialog.exec()

    # ==========================================
    # Neural Read Aloud Handlers
    # ==========================================

    def play_read_aloud(self, voice: str, speed: float):
        page_idx = self.current_page - 1
        page = self.doc_wrapper.get_page(page_idx)
        text = page.get_text("text").strip()
        if not text:
            text = OCREngine.ocr_page(page, language="eng", dpi=300)

        if not text.strip():
            QMessageBox.information(
                self, "Read Aloud",
                f"Page {self.current_page} has no readable text or OCR content."
            )
            self.right_drawer.set_tts_state("idle")
            if hasattr(self, "tts_player"):
                self.tts_player.set_state("idle")
            return

        self.tts_controller.read_text(text, self.current_page, voice, speed)

    def pause_read_aloud(self):
        self.tts_controller.toggle_play_pause()

    def stop_read_aloud(self):
        self.tts_controller.stop()

    def toggle_tts_player(self):
        """Toggle visibility of the TTS mini-player bar."""
        if hasattr(self, "tts_player"):
            self.tts_player.setVisible(not self.tts_player.isVisible())

    def _on_tts_progress(self, current_ms: int, total_ms: int):
        self.right_drawer.set_tts_progress(current_ms, total_ms)
        if hasattr(self, "tts_player"):
            self.tts_player.set_progress(current_ms, total_ms)

    def _on_tts_state_changed(self, state: str):
        self.right_drawer.set_tts_state(state, f"Page {self.current_page}")
        if hasattr(self, "tts_player"):
            self.tts_player.set_state(state, f"Page {self.current_page}")

    def _on_tts_error(self, err_msg: str):
        self.right_drawer.set_tts_state("idle")
        if hasattr(self, "tts_player"):
            self.tts_player.set_state("idle")
        QMessageBox.warning(self, "Read Aloud", err_msg)

    def _on_floating_ai_clicked(self):
        """Open Attachments & Details panel (where AI Assistant lives) and focus AI input."""
        if self.right_panel_stack.isVisible() and self.right_panel_stack.currentIndex() == 1:
            if hasattr(self.right_drawer, "ai_chat_panel") and self.right_drawer.ai_chat_panel.input_query.hasFocus():
                self.right_panel_stack.setVisible(False)
                self.right_nav_rail.set_active_tab(None)
            else:
                self.right_drawer.ai_chat_panel.input_query.setFocus()
        else:
            self.right_panel_stack.setCurrentIndex(1)
            self.right_panel_stack.setVisible(True)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab("attachments")
            if hasattr(self.right_drawer, "ai_chat_panel"):
                self.right_drawer.ai_chat_panel.input_query.setFocus()

    # ==========================================
    # Export Suite Handlers
    # ==========================================

    def export_all_images(self):
        target_dir = QFileDialog.getExistingDirectory(
            self, "Select Folder to Save Extracted Images"
        )
        if not target_dir:
            return
        saved_paths = ExportEngine.extract_images(self.doc_wrapper, target_dir)
        count = len(saved_paths)
        if count == 0:
            QMessageBox.information(self, "Extract Images", "No embedded raster images found in this document.")
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Images Extracted")
            msg.setText(f"Successfully extracted {count} image(s) to:\n{target_dir}")
            btn_open = msg.addButton("Open Folder", QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Ok)
            msg.exec()
            if msg.clickedButton() == btn_open:
                import subprocess
                subprocess.Popen(f'explorer "{target_dir}"')

    def export_markdown(self):
        default_name = os.path.splitext(os.path.basename(self.file_path))[0] + ".md"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as Markdown", default_name, "Markdown Files (*.md)"
        )
        if path:
            ExportEngine.export_to_markdown(self.doc_wrapper, path)
            QMessageBox.information(self, "Export Markdown", f"Document exported to {os.path.basename(path)}")

    def export_text(self):
        default_name = os.path.splitext(os.path.basename(self.file_path))[0] + ".txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as Plain Text", default_name, "Text Files (*.txt)"
        )
        if path:
            ExportEngine.export_to_text(self.doc_wrapper, path)
            QMessageBox.information(self, "Export Plain Text", f"Document exported to {os.path.basename(path)}")

    def export_page_image(self):
        default_name = f"{os.path.splitext(os.path.basename(self.file_path))[0]}_page_{self.current_page}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Page as Image", default_name, "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        if path:
            ExportEngine.export_page_as_image(self.doc_wrapper, self.current_page - 1, path, dpi=300.0)
            QMessageBox.information(self, "Export Page Image", f"Page {self.current_page} saved to {os.path.basename(path)}")

    def ask_ai(self, prompt: str):
        self.right_drawer.ai_chat_panel.ask(prompt)

    def save(self) -> str:
        saved_path = self.doc_wrapper.save_document()
        self.undo_stack.setClean()
        self.dirty_state_changed.emit(False)
        return saved_path

    def save_as(self, path: str) -> str:
        saved_path = self.doc_wrapper.save_document(path)
        self.file_path = saved_path
        self.undo_stack.setClean()
        self.dirty_state_changed.emit(False)
        return saved_path

    def close(self):
        if hasattr(self, "canvas") and hasattr(self.canvas, "render_manager"):
            self.canvas.render_manager.cancel_all()
        if hasattr(self, "tts_controller"):
            self.tts_controller.cleanup()
        if hasattr(self, "undo_stack"):
            self.undo_stack.clear()
        self.doc_wrapper.close()

    def toggle_all_tools_panel(self):
        self.all_tools_panel.setVisible(not self.all_tools_panel.isVisible())

    def _on_all_tool_action(self, tool_id: str):
        if tool_id == "organize":
            self.show_organize_view()
        elif tool_id == "ocr":
            self.run_ocr_current_page()
        elif tool_id == "export":
            self.enter_convert_mode()
            win = self.window()
            if win and hasattr(win, "quick_tools"):
                win.quick_tools.workspace_tabs.set_active_tab("convert", emit_signal=False)
        elif tool_id == "create":
            win = self.window()
            if win and hasattr(win, "open_file_dialog"):
                win.open_file_dialog()
        elif tool_id == "combine":
            win = self.window()
            if win and hasattr(win, "open_merge_dialog"):
                win.open_merge_dialog()
        elif tool_id in ("edit", "fill_sign", "esign"):
            if tool_id == "edit":
                self.enter_edit_mode()
                win = self.window()
                if win and hasattr(win, "quick_tools"):
                    win.quick_tools.workspace_tabs.set_active_tab("edit", emit_signal=False)
            else:
                self.set_tool("draw")
        elif tool_id == "comments":
            # Show CommentsPanel (stack page 0)
            self.right_panel_stack.setCurrentIndex(0)
            self.right_panel_stack.setVisible(True)
            self.right_nav_rail.set_active_tab("comments")
        elif tool_id == "stamp":
            self.set_tool("note")

    def _on_right_nav_tab_selected(self, tab_id: str):
        if tab_id == "close":
            self.right_panel_stack.setVisible(False)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab(None)
        elif tab_id == "comments":
            # CommentsPanel is stack page 0
            self.right_panel_stack.setCurrentIndex(0)
            self.right_panel_stack.setVisible(True)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab("comments")
        elif tab_id == "attachments":
            # Power Suite drawer is stack page 1
            self.right_panel_stack.setCurrentIndex(1)
            self.right_panel_stack.setVisible(True)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab("attachments")
        elif tab_id == "pages":
            # Page Thumbnails panel is stack page 2
            self.right_panel_stack.setCurrentIndex(2)
            self.right_panel_stack.setVisible(True)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab("pages")
            if hasattr(self, "thumbnails_panel"):
                self.thumbnails_panel.set_current_page(self.current_page)
        elif tab_id == "bookmarks":
            # Bookmarks & Table of Contents panel is stack page 3
            self.right_panel_stack.setCurrentIndex(3)
            self.right_panel_stack.setVisible(True)
            self.left_rail.close_drawer()
            self.left_rail.setVisible(False)
            self.right_nav_rail.set_active_tab("bookmarks")
            if hasattr(self, "bookmarks_panel"):
                self.bookmarks_panel.set_current_page(self.current_page)

    # ==========================================
    # Phase 6: Edit PDF Workstation Integration
    # ==========================================

    def is_edit_mode_active(self) -> bool:
        return self.is_edit_mode

    def enter_edit_mode(self):
        if self.is_organize_view_active():
            self.show_reading_view()
        self.is_edit_mode = True
        self.all_tools_panel.setVisible(False)
        self.edit_pdf_panel.setVisible(True)
        if hasattr(self, "floating_tools_container"):
            self.floating_tools_container.setVisible(False)
        self.canvas.set_edit_mode(True, show_bounding_boxes=self.edit_pdf_panel.show_bounding_boxes)
        self.load_content_blocks()

    def exit_edit_mode(self):
        self.is_edit_mode = False
        self.edit_pdf_panel.setVisible(False)
        self.canvas.set_edit_mode(False)
        if hasattr(self, "floating_tools_container"):
            self.floating_tools_container.setVisible(True)
        self.all_tools_panel.setVisible(True)

    def load_content_blocks(self):
        for i in range(self.doc_wrapper.page_count):
            blocks = self.doc_wrapper.get_content_blocks(i)
            self.canvas.set_page_content_blocks(i, blocks)

    def _on_edit_panel_closed(self):
        self.exit_edit_mode()
        win = self.window()
        if win and hasattr(win, "quick_tools"):
            win.quick_tools.workspace_tabs.set_active_tab("all_tools", emit_signal=False)

    def is_convert_mode_active(self) -> bool:
        return getattr(self, "is_convert_mode", False)

    def enter_convert_mode(self):
        if self.is_organize_view_active():
            self.show_reading_view()
        if self.is_edit_mode_active():
            self.exit_edit_mode()

        self.is_convert_mode = True
        self.all_tools_panel.setVisible(False)
        self.edit_pdf_panel.setVisible(False)
        if hasattr(self, "export_pdf_panel"):
            self.export_pdf_panel.set_document_info(
                self.doc_wrapper.file_path,
                self.doc_wrapper.page_count
            )
            self.export_pdf_panel.setVisible(True)
        if hasattr(self, "preview_badge_container"):
            p_text = f"Preview of original PDF • All {self.doc_wrapper.page_count} pages will be exported"
            self.lbl_preview_badge.setText(p_text)
            self.preview_badge_container.setVisible(True)

    def exit_convert_mode(self):
        self.is_convert_mode = False
        if hasattr(self, "export_pdf_panel"):
            self.export_pdf_panel.setVisible(False)
        if hasattr(self, "preview_badge_container"):
            self.preview_badge_container.setVisible(False)
        self.all_tools_panel.setVisible(True)

    def _on_export_panel_closed(self):
        self.exit_convert_mode()
        win = self.window()
        if win and hasattr(win, "quick_tools"):
            win.quick_tools.workspace_tabs.set_active_tab("all_tools", emit_signal=False)

    def _on_export_requested(self, target_path: str, format_key: str, options: dict):
        win = self.window()
        if win and hasattr(win, "execute_document_export"):
            win.execute_document_export(self, target_path, format_key, options)

    def _on_edit_tool_selected(self, tool_id: str):
        if tool_id == "text":
            self.canvas.set_tool("text")
        elif tool_id == "image":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
            )
            if file_path:
                target_page = max(0, min(self.current_page - 1, self.doc_wrapper.page_count - 1))
                page = self.doc_wrapper.get_page(target_page)
                p_rect = page.rect
                img_w, img_h = 200, 200
                x0 = (p_rect.width - img_w) / 2
                y0 = 100
                rect = fitz.Rect(x0, y0, x0 + img_w, y0 + img_h)
                before_snap = {target_page: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, target_page)}
                self.doc_wrapper.insert_image_block(target_page, rect, file_path)
                after_snap = {target_page: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, target_page)}
                self.re_render_page(target_page)
                self.canvas.set_page_content_blocks(target_page, self.doc_wrapper.get_content_blocks(target_page))
                cmd = PageSnapshotCommand(
                    self.doc_wrapper,
                    "Insert Image",
                    [target_page],
                    before_snap,
                    after_snap,
                    on_modified=self._on_undo_redo_modified,
                    already_executed=True
                )
                self.undo_stack.push(cmd)
        elif tool_id == "link":
            active = self.canvas.get_selected_block()
            target_page = active[0] if active else max(0, min(self.current_page - 1, self.doc_wrapper.page_count - 1))
            link_rect = active[1].rect if active else fitz.Rect(50, 100, 250, 130)
            dialog = LinkDialog(parent=self)
            if dialog.exec():
                url = dialog.get_url()
                if url:
                    cmd = AddLinkCommand(
                        self.doc_wrapper,
                        target_page,
                        link_rect,
                        url,
                        on_modified=self._on_undo_redo_modified,
                        already_executed=False
                    )
                    self.undo_stack.push(cmd)

    def _apply_text_block_edit(self, page_index: int, block: ContentBlock, text: str, font_style: FontStyle):
        if text == block.text and font_style == block.font_style:
            return
        before_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        new_rect = self.doc_wrapper.replace_text_block(
            page_index, block.rect, text, font_style=font_style
        )
        block.text = text
        block.rect = new_rect
        block.font_style = font_style
        after_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        self.re_render_page(page_index)
        self.canvas.set_page_content_blocks(page_index, self.doc_wrapper.get_content_blocks(page_index))
        cmd = PageSnapshotCommand(
            self.doc_wrapper,
            "Edit Text",
            [page_index],
            before_snap,
            after_snap,
            on_modified=self._on_undo_redo_modified,
            already_executed=True
        )
        self.undo_stack.push(cmd)

    def _on_panel_font_style_changed(self, new_style: FontStyle):
        active = self.canvas.get_selected_block()
        if active:
            p_idx, block = active
            if block.is_text:
                self._apply_text_block_edit(p_idx, block, block.text, new_style)

    def _on_canvas_block_selected(self, page_index: int, block: ContentBlock):
        if block and block.is_text and block.font_style:
            self.edit_pdf_panel.set_font_style(block.font_style)

    def _on_canvas_block_text_edited(self, page_index: int, block: ContentBlock, new_text: str):
        self._apply_text_block_edit(page_index, block, new_text, block.font_style)

    def _on_canvas_block_font_style_changed(self, page_index: int, block: ContentBlock, new_style: FontStyle):
        self.edit_pdf_panel.set_font_style(new_style)
        self._apply_text_block_edit(page_index, block, block.text, new_style)

    def _on_canvas_block_rect_changed(self, page_index: int, block: ContentBlock, new_rect: fitz.Rect):
        old_rect = getattr(block, "orig_rect", None) or block.rect

        if old_rect is not None and abs(old_rect.x0 - new_rect.x0) < 0.5 and abs(old_rect.y0 - new_rect.y0) < 0.5 and abs(old_rect.width - new_rect.width) < 0.5 and abs(old_rect.height - new_rect.height) < 0.5:
            return

        before_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        self.doc_wrapper.doc[page_index].add_redact_annot(old_rect, fill=(1, 1, 1))
        self.doc_wrapper.doc[page_index].apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        block.rect = new_rect
        self.doc_wrapper.insert_text_block(page_index, new_rect, block.text, font_style=block.font_style)
        after_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        self.re_render_page(page_index)
        self.canvas.set_page_content_blocks(page_index, self.doc_wrapper.get_content_blocks(page_index))
        cmd = PageSnapshotCommand(
            self.doc_wrapper,
            "Move Block",
            [page_index],
            before_snap,
            after_snap,
            on_modified=self._on_undo_redo_modified,
            already_executed=True
        )
        self.undo_stack.push(cmd)

    def _on_canvas_new_textbox_requested(self, page_index: int, rect: fitz.Rect):
        before_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        default_style = self.edit_pdf_panel.current_font_style
        self.doc_wrapper.insert_text_block(page_index, rect, "New Text", font_style=default_style)
        after_snap = {page_index: PageSnapshotManager.create_snapshot(self.doc_wrapper.doc, page_index)}
        self.re_render_page(page_index)
        blocks = self.doc_wrapper.get_content_blocks(page_index)
        self.canvas.set_page_content_blocks(page_index, blocks)
        for b in blocks:
            if b.rect.intersects(rect):
                self.canvas.page_widgets[page_index].select_block(b)
                break
        cmd = PageSnapshotCommand(
            self.doc_wrapper,
            "Insert Text Box",
            [page_index],
            before_snap,
            after_snap,
            on_modified=self._on_undo_redo_modified,
            already_executed=True
        )
        self.undo_stack.push(cmd)

    def _on_edit_header_footer(self):
        dialog = HeaderFooterDialog(
            page_count=self.doc_wrapper.page_count,
            current_page=self.current_page,
            parent=self
        )
        if dialog.exec():
            cfg = dialog.get_config()
            target_pages = cfg["page_indices"]
            before_snaps = PageSnapshotManager.create_multi_snapshot(self.doc_wrapper.doc, target_pages)
            self.doc_wrapper.add_header_footer(
                header_left=cfg["header_left"],
                header_center=cfg["header_center"],
                header_right=cfg["header_right"],
                footer_left=cfg["footer_left"],
                footer_center=cfg["footer_center"],
                footer_right=cfg["footer_right"],
                font_size=cfg["font_size"],
                color=cfg["color_rgb"],
                margin=cfg["margin"],
                page_indices=target_pages,
                title=self.doc_wrapper.get_title() or os.path.basename(self.file_path)
            )
            after_snaps = PageSnapshotManager.create_multi_snapshot(self.doc_wrapper.doc, target_pages)
            self.render_all_pages()
            self.load_content_blocks()
            cmd = PageSnapshotCommand(
                self.doc_wrapper,
                "Add Header & Footer",
                target_pages,
                before_snaps,
                after_snaps,
                on_modified=self._on_undo_redo_modified,
                already_executed=True
            )
            self.undo_stack.push(cmd)

    def _on_edit_watermark(self):
        dialog = WatermarkDialog(
            page_count=self.doc_wrapper.page_count,
            current_page=self.current_page,
            parent=self
        )
        if dialog.exec():
            cfg = dialog.get_config()
            target_pages = cfg["page_indices"]
            before_snaps = PageSnapshotManager.create_multi_snapshot(self.doc_wrapper.doc, target_pages)
            self.doc_wrapper.add_watermark(
                text=cfg["text"],
                opacity=cfg["opacity"],
                angle=cfg["angle"],
                font_size=cfg["font_size"],
                color=cfg["color_rgb"],
                page_indices=target_pages
            )
            after_snaps = PageSnapshotManager.create_multi_snapshot(self.doc_wrapper.doc, target_pages)
            self.render_all_pages()
            self.load_content_blocks()
            cmd = PageSnapshotCommand(
                self.doc_wrapper,
                "Add Watermark",
                target_pages,
                before_snaps,
                after_snaps,
                on_modified=self._on_undo_redo_modified,
                already_executed=True
            )
            self.undo_stack.push(cmd)

    def _on_edit_crop(self):
        target_idx = max(0, min(self.current_page - 1, self.doc_wrapper.page_count - 1))
        page = self.doc_wrapper.get_page(target_idx)
        dialog = CropPagesDialog(
            page_width=page.rect.width,
            page_height=page.rect.height,
            current_page=self.current_page,
            parent=self
        )
        if dialog.exec():
            cfg = dialog.get_config()
            l, t, r, b = cfg["crop_rect_coords"]
            crop_rect = fitz.Rect(l, t, r, b)
            pages = list(range(self.doc_wrapper.page_count)) if cfg["apply_all"] else [target_idx]
            old_cropboxes = {p: self.doc_wrapper.get_page(p).cropbox for p in pages}
            cmd = CropPageCommand(
                self.doc_wrapper,
                old_cropboxes,
                crop_rect,
                on_modified=self._on_undo_redo_modified,
                already_executed=False
            )
            self.undo_stack.push(cmd)

    def update_theme(self):
        self.right_drawer.update_theme()
        self.organizer_grid.update_theme()
        if hasattr(self, "page_controls"):
            self.page_controls.update_theme()
        if hasattr(self, "floating_tools"):
            self.floating_tools.update_theme()
        if hasattr(self, "all_tools_panel"):
            self.all_tools_panel.update_theme()
        if hasattr(self, "edit_pdf_panel"):
            self.edit_pdf_panel.update_theme()
        if hasattr(self, "export_pdf_panel"):
            self.export_pdf_panel.update_theme()
        if hasattr(self, "preview_badge_pill"):
            is_dark = ThemeManager.is_dark()
            bg = "#252528" if is_dark else "#FFFFFF"
            border = "#383838" if is_dark else "#D9D9D9"
            txt = "#9E9E9E" if is_dark else "#626262"
            self.preview_badge_pill.setStyleSheet(f"""
                QFrame#previewBadgePill {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 12px;
                }}
                QLabel {{
                    color: {txt};
                    background: transparent;
                }}
            """)
            from pyacrobat.ui.export_pdf_panel import load_themed_svg
            eye_svg = load_themed_svg("eye", "#4BA3FF" if is_dark else "#1473E6")
            if eye_svg and eye_svg.isValid():
                from PySide6.QtGui import QPixmap, QPainter
                pix = QPixmap(32, 32)
                pix.fill(Qt.transparent)
                p = QPainter(pix)
                eye_svg.render(p)
                p.end()
                self.icon_badge_eye.setPixmap(pix.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if hasattr(self, "canvas"):
            self.canvas.update_theme()
        if hasattr(self, "right_nav_rail"):
            self.right_nav_rail.update_theme()
        if hasattr(self, "comments_panel"):
            self.comments_panel.update_theme()
        if hasattr(self, "thumbnails_panel"):
            self.thumbnails_panel.update_theme()
        if hasattr(self, "bookmarks_panel"):
            self.bookmarks_panel.update_theme()
        if hasattr(self, "tts_player"):
            self.tts_player.update_theme()


class MainWindow(QMainWindow):
    """Main Application Window with Screen-Bounds Protection."""

    def __init__(self, start_dark: bool = False):
        super().__init__()
        self.setWindowTitle("Spectra PDF")
        app_icon = get_app_icon()
        self.setWindowIcon(app_icon)
        app = QApplication.instance()
        if app and app.windowIcon().isNull():
            app.setWindowIcon(app_icon)
        self.is_dark_theme = start_dark

        # Multi-document Undo/Redo Orchestrator
        self.undo_group = QUndoGroup(self)
        self.undo_group.canUndoChanged.connect(self._on_undo_availability_changed)
        self.undo_group.canRedoChanged.connect(self._on_redo_availability_changed)
        self.undo_group.undoTextChanged.connect(self._on_undo_text_changed)
        self.undo_group.redoTextChanged.connect(self._on_redo_text_changed)

        # Set Inter font globally (Task 6.3)
        app = QApplication.instance()
        if app:
            app.setFont(QFont("Inter", 10))

        self.init_ui()
        self.fit_screen_bounds()
        self.apply_theme()
        self.setup_shortcuts()

    def fit_screen_bounds(self):
        """Sizes and positions window safely inside available desktop working area."""
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Constrain to available desktop dimensions excluding Windows taskbar
            target_w = min(1280, avail.width() - 40)
            target_h = min(760, avail.height() - 40)
            target_x = avail.x() + (avail.width() - target_w) // 2
            target_y = avail.y() + (avail.height() - target_h) // 2
            self.setGeometry(target_x, target_y, target_w, target_h)
        else:
            self.resize(1200, 750)
        self.setMinimumSize(850, 520)

    def init_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        # Hide default tab bar; replaced by custom branded AppNavBar (Phase 2)
        self.tab_widget.tabBar().hide()

        btn_add_tab = QToolButton()
        btn_add_tab.setText("＋")
        btn_add_tab.setToolTip("Open New PDF (Ctrl O)")
        btn_add_tab.clicked.connect(self.open_file_dialog)
        self.tab_widget.setCornerWidget(btn_add_tab, Qt.TopRightCorner)

        # Application Menu Bar (Phase 1 Figma Spec)
        self.create_menu_bar()

        # Branded Application Navigation Bar (Phase 2 Figma Spec #3:12938)
        self.app_nav_bar = AppNavBar(self)
        self.app_nav_bar.home_clicked.connect(self._show_home_view)
        self.app_nav_bar.tab_selected.connect(self._on_nav_tab_selected)
        self.app_nav_bar.tab_close_requested.connect(self.close_tab)
        self.app_nav_bar.new_document_requested.connect(self.open_file_dialog)
        self.app_nav_bar.search_clicked.connect(self._trigger_find_in_doc)
        self.app_nav_bar.help_clicked.connect(self._show_about_dialog)
        self.app_nav_bar.theme_toggle_requested.connect(self.toggle_theme)

        # Document Toolbar (Phase 3 Figma Spec #3:12957)
        self.quick_tools = QuickToolsBar()
        self.quick_tools.zoom_in_requested.connect(self._zoom_in)
        self.quick_tools.zoom_out_requested.connect(self._zoom_out)
        self.quick_tools.zoom_level_changed.connect(self._zoom_to)
        self.quick_tools.fit_width_requested.connect(self._fit_width)
        self.quick_tools.fit_page_requested.connect(self._fit_page)
        self.quick_tools.page_jump_requested.connect(self._go_to_page)
        self.quick_tools.theme_toggle_requested.connect(self.toggle_theme)
        self.quick_tools.ai_toggle_requested.connect(self.focus_ai_copilot)
        self.quick_tools.undo_requested.connect(self.undo_active_document)
        self.quick_tools.redo_requested.connect(self.redo_active_document)
        self.quick_tools.search_requested.connect(self._trigger_find_in_doc)
        self.quick_tools.save_requested.connect(self.save_active_document)
        self.quick_tools.print_requested.connect(self._print_or_export_active_doc)
        self.quick_tools.share_requested.connect(self._share_active_doc)
        self.quick_tools.workspace_tab_changed.connect(self._on_workspace_tab_changed)

        self.quick_tools.tool_changed.connect(self._on_tool_changed)
        self.quick_tools.highlight_color_changed.connect(self._on_highlight_color_changed)
        self.quick_tools.draw_style_changed.connect(self._on_draw_style_changed)

        # Workspace Stack: Page 0 = Home Dashboard, Page 1 = Document Tabs
        self.home_view = HomeView(self)
        self.home_view.open_file_requested.connect(self._on_home_open_file_requested)
        self.home_view.file_open_requested.connect(self.open_document)
        self.home_view.combine_files_requested.connect(self.open_merge_dialog)
        self.home_view.export_pdf_requested.connect(self._on_home_export_requested)
        self.home_view.about_requested.connect(self._show_about_dialog)

        self.workspace_stack = QStackedWidget()
        self.workspace_stack.addWidget(self.home_view)
        self.workspace_stack.addWidget(self.tab_widget)

        central_container = QWidget()
        cc_layout = QVBoxLayout(central_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)
        cc_layout.addWidget(self.app_nav_bar)
        cc_layout.addWidget(self.quick_tools)
        cc_layout.addWidget(self.workspace_stack)

        self.setCentralWidget(central_container)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Enriched Status Bar (Task 6.6)
        # Left permanent: Save status ("☁ All changes saved")
        self.lbl_status_save = QLabel("☁ All changes saved")
        self.lbl_status_save.setObjectName("statusBarSaveBadge")
        self.status_bar.addWidget(self.lbl_status_save)

        # Right permanent widgets:
        # 1. Document metadata badge: "Page N of M · 8.5 × 11.0 in · PDF/A"
        self.lbl_status_doc_info = QLabel("")
        self.lbl_status_doc_info.setObjectName("statusBarInfoBadge")
        self.status_bar.addPermanentWidget(self.lbl_status_doc_info)

        # 2. Security badge: "🛡 Protected view off"
        self.lbl_status_security = QLabel("🛡 Protected view off")
        self.lbl_status_security.setObjectName("statusBarSecurityBadge")
        self.status_bar.addPermanentWidget(self.lbl_status_security)

        self._update_workspace_state()

    def create_menu_bar(self):
        """Builds clean OS-style application menu bar matching Figma Acrobat design."""
        menu_bar = self.menuBar()
        menu_bar.clear()
        menu_bar.setNativeMenuBar(False)

        # 1. File Menu
        self.menu_file = menu_bar.addMenu("&File")

        self.action_open = QAction("&Open...", self)
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_open.setStatusTip("Open PDF Document")
        self.action_open.triggered.connect(self.open_file_dialog)
        self.menu_file.addAction(self.action_open)

        self.action_save = QAction("&Save", self)
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save.setStatusTip("Save Document Annotations")
        self.action_save.triggered.connect(self.save_active_document)
        self.menu_file.addAction(self.action_save)

        self.action_save_as = QAction("Save &As...", self)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.setStatusTip("Save Copy of Document")
        self.action_save_as.triggered.connect(self.save_as_active_document)
        self.menu_file.addAction(self.action_save_as)

        self.menu_file.addSeparator()

        self.action_merge = QAction("&Merge Files...", self)
        self.action_merge.setStatusTip("Combine Multiple PDFs into One")
        self.action_merge.triggered.connect(self.open_merge_dialog)
        self.menu_file.addAction(self.action_merge)

        self.action_extract = QAction("&Extract Range...", self)
        self.action_extract.setStatusTip("Extract Specific Pages from Active PDF")
        self.action_extract.triggered.connect(self.open_extract_dialog)
        self.menu_file.addAction(self.action_extract)

        self.menu_file.addSeparator()

        # Export Submenu
        self.menu_export = QMenu("&Export", self)

        self.action_export_convert_all = QAction("&Convert and Export PDF...", self)
        self.action_export_convert_all.triggered.connect(lambda: self._export_to_format(None))
        self.menu_export.addAction(self.action_export_convert_all)

        self.menu_export.addSeparator()

        self.action_export_word = QAction("Microsoft &Word (.docx)...", self)
        self.action_export_word.triggered.connect(lambda: self._export_to_format(FORMAT_DOCX))
        self.menu_export.addAction(self.action_export_word)

        self.action_export_excel = QAction("Microsoft &Excel (.xlsx)...", self)
        self.action_export_excel.triggered.connect(lambda: self._export_to_format(FORMAT_XLSX))
        self.menu_export.addAction(self.action_export_excel)

        self.action_export_pptx = QAction("Microsoft &PowerPoint (.pptx)...", self)
        self.action_export_pptx.triggered.connect(lambda: self._export_to_format(FORMAT_PPTX))
        self.menu_export.addAction(self.action_export_pptx)

        self.action_export_img = QAction("&Image (PNG, JPEG, TIFF)...", self)
        self.action_export_img.triggered.connect(lambda: self._export_to_format(FORMAT_IMAGE))
        self.menu_export.addAction(self.action_export_img)

        self.menu_export.addSeparator()

        self.action_export_images = QAction("Extract All &Images...", self)
        self.action_export_images.triggered.connect(self.export_active_images)
        self.menu_export.addAction(self.action_export_images)

        self.action_export_md = QAction("Export as &Markdown (.md)...", self)
        self.action_export_md.triggered.connect(self.export_active_markdown)
        self.menu_export.addAction(self.action_export_md)

        self.action_export_txt = QAction("Export as Plain &Text (.txt)...", self)
        self.action_export_txt.triggered.connect(self.export_active_text)
        self.menu_export.addAction(self.action_export_txt)

        self.menu_export.addSeparator()

        self.action_export_page = QAction("Export Page as &PNG...", self)
        self.action_export_page.triggered.connect(self.export_active_page_image)
        self.menu_export.addAction(self.action_export_page)

        self.menu_file.addMenu(self.menu_export)

        self.menu_file.addSeparator()

        self.action_close_doc = QAction("&Close Document", self)
        self.action_close_doc.setShortcut(QKeySequence("Ctrl+W"))
        self.action_close_doc.triggered.connect(self._close_active_tab)
        self.menu_file.addAction(self.action_close_doc)

        self.action_exit = QAction("E&xit", self)
        self.action_exit.setShortcut(QKeySequence("Alt+F4"))
        self.action_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.action_exit)

        # 2. Edit Menu
        self.menu_edit = menu_bar.addMenu("&Edit")

        self.action_undo = self.undo_group.createUndoAction(self, "&Undo")
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.menu_edit.addAction(self.action_undo)

        self.action_redo = self.undo_group.createRedoAction(self, "&Redo")
        self.action_redo.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Shift+Z")])
        self.menu_edit.addAction(self.action_redo)

        self.menu_edit.addSeparator()

        self.action_find = QAction("&Find in Document...", self)
        self.action_find.setShortcut(QKeySequence("Ctrl+F"))
        self.action_find.triggered.connect(self._trigger_find_in_doc)
        self.menu_edit.addAction(self.action_find)

        self.action_ocr = QAction("OC&R Current Page...", self)
        self.action_ocr.triggered.connect(self.ocr_active_page)
        self.menu_edit.addAction(self.action_ocr)

        # 3. View Menu
        self.menu_view = menu_bar.addMenu("&View")

        self.action_zoom_in = QAction("Zoom &In", self)
        self.action_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        self.action_zoom_in.triggered.connect(self._zoom_in)
        self.menu_view.addAction(self.action_zoom_in)

        self.action_zoom_out = QAction("Zoom &Out", self)
        self.action_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.action_zoom_out.triggered.connect(self._zoom_out)
        self.menu_view.addAction(self.action_zoom_out)

        self.action_fit_width = QAction("Fit to &Width", self)
        self.action_fit_width.triggered.connect(self._fit_width)
        self.menu_view.addAction(self.action_fit_width)

        self.action_fit_page = QAction("Fit to &Page", self)
        self.action_fit_page.triggered.connect(self._fit_page)
        self.menu_view.addAction(self.action_fit_page)

        self.menu_view.addSeparator()

        self.action_toggle_organize = QAction("&Organize Pages", self)
        self.action_toggle_organize.triggered.connect(self.toggle_organize_view)
        self.menu_view.addAction(self.action_toggle_organize)

        self.menu_view.addSeparator()

        self.action_rotate_cw = QAction("Rotate &Clockwise (90°)", self)
        self.action_rotate_cw.setShortcut(QKeySequence("Ctrl+R"))
        self.action_rotate_cw.triggered.connect(self._rotate_active_page_cw)
        self.menu_view.addAction(self.action_rotate_cw)

        self.action_rotate_ccw = QAction("Rotate Counter-Clockwise (90°)", self)
        self.action_rotate_ccw.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self.action_rotate_ccw.triggered.connect(self._rotate_active_page_ccw)
        self.menu_view.addAction(self.action_rotate_ccw)

        self.menu_view.addSeparator()

        self.action_toggle_theme = QAction("Toggle &Dark / Light Theme", self)
        self.action_toggle_theme.triggered.connect(self.toggle_theme)
        self.menu_view.addAction(self.action_toggle_theme)

        # 4. Window Menu
        self.menu_window = menu_bar.addMenu("&Window")

        self.action_go_home = QAction("&Home Screen", self)
        self.action_go_home.triggered.connect(self._show_home_view)
        self.menu_window.addAction(self.action_go_home)

        self.action_next_doc = QAction("&Next Document", self)
        self.action_next_doc.setShortcut(QKeySequence("Ctrl+Tab"))
        self.action_next_doc.triggered.connect(self._next_document_tab)
        self.menu_window.addAction(self.action_next_doc)

        self.action_prev_doc = QAction("&Previous Document", self)
        self.action_prev_doc.setShortcut(QKeySequence("Ctrl+Shift+Tab"))
        self.action_prev_doc.triggered.connect(self._prev_document_tab)
        self.menu_window.addAction(self.action_prev_doc)

        self.menu_window.addSeparator()

        self.action_close_all = QAction("Close &All Documents", self)
        self.action_close_all.triggered.connect(self._close_all_tabs)
        self.menu_window.addAction(self.action_close_all)

        # 5. Help Menu
        self.menu_help = menu_bar.addMenu("&Help")

        self.action_ai_assistant = QAction("Spectra &AI Document Assistant", self)
        self.action_ai_assistant.setShortcut(QKeySequence("Ctrl+I"))
        self.action_ai_assistant.triggered.connect(self.focus_ai_copilot)
        self.menu_help.addAction(self.action_ai_assistant)

        self.menu_help.addSeparator()

        self.action_about = QAction("&About Spectra PDF", self)
        self.action_about.triggered.connect(self._show_about_dialog)
        self.menu_help.addAction(self.action_about)

        # Top-Right Document Title in Menu Bar
        self.menu_title_label = QLabel("Spectra PDF")
        self.menu_title_label.setObjectName("menuTitleLabel")
        menu_bar.setCornerWidget(self.menu_title_label, Qt.TopRightCorner)

        # Backward compatibility aliases for existing tests and state hooks
        self.btn_save = self.action_save
        self.btn_save_as = self.action_save_as
        self.btn_toggle_organize = self.action_toggle_organize
        self.btn_extract_tool = self.action_extract
        self.btn_ocr_bar = self.action_ocr
        self.btn_export = self.menu_export

    def _set_menu_title(self, text: str):
        if hasattr(self, "menu_title_label"):
            self.menu_title_label.setText(text)
            self.menu_title_label.adjustSize()

    def _close_active_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            self.close_tab(idx)

    def _close_all_tabs(self):
        while self.tab_widget.count() > 0:
            self.close_tab(0)

    def _show_home_view(self):
        self.workspace_stack.setCurrentIndex(0)
        self.quick_tools.setVisible(False)
        self._set_document_actions_enabled(False)
        self.status_bar.showMessage("Home | Spectra PDF Workstation")
        self.setWindowTitle("Spectra PDF")
        self._set_menu_title("Spectra PDF")
        if hasattr(self, "app_nav_bar"):
            self.app_nav_bar.set_home_active()

    def _on_nav_tab_selected(self, index: int):
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)
            self._update_workspace_state()

    def _next_document_tab(self):
        cnt = self.tab_widget.count()
        if cnt > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % cnt)

    def _prev_document_tab(self):
        cnt = self.tab_widget.count()
        if cnt > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % cnt)

    def _trigger_find_in_doc(self):
        tab = self._get_active_tab()
        if tab:
            tab.left_rail.open_drawer(2)
            tab.left_rail.search_input.setFocus()
            tab.left_rail.search_input.selectAll()

    def _print_or_export_active_doc(self):
        tab = self._get_active_tab()
        if tab:
            tab.export_page_image()

    def _share_active_doc(self):
        tab = self._get_active_tab()
        if tab:
            clipboard = QApplication.clipboard()
            clipboard.setText(tab.file_path)
            self.status_bar.showMessage(f"Document path copied to clipboard: {tab.file_path}", 4000)
            QMessageBox.information(
                self, "Share Document",
                f"Document link and path copied to clipboard:\n\n{tab.file_path}"
            )

    def _on_workspace_tab_changed(self, tab_id: str):
        tab = self._get_active_tab()
        if tab and hasattr(tab, "is_convert_mode_active") and tab.is_convert_mode_active() and tab_id != "convert":
            tab.exit_convert_mode()

        if tab_id == "all_tools":
            if tab:
                if tab.is_organize_view_active():
                    tab.show_reading_view()
                if tab.is_edit_mode_active():
                    tab.exit_edit_mode()
                elif hasattr(tab, "all_tools_panel"):
                    tab.all_tools_panel.setVisible(True)
            self.status_bar.showMessage("Workspace: All tools view active", 3000)
            self._update_status_bar_info()
        elif tab_id == "edit":
            if tab:
                tab.enter_edit_mode()
            self.status_bar.showMessage("Workspace: Edit PDF mode active", 3000)
            self._update_status_bar_info()
        elif tab_id == "convert":
            if tab:
                if tab.is_edit_mode_active():
                    tab.exit_edit_mode()
                tab.enter_convert_mode()
            self.status_bar.showMessage("Workspace: Convert & export ready", 3000)
            self._update_status_bar_info()
        elif tab_id == "esign":
            if tab:
                if tab.is_edit_mode_active():
                    tab.exit_edit_mode()
                tab.set_tool("draw")
            self.status_bar.showMessage("Workspace: E-Sign & pen signature mode active", 3000)
            self._update_status_bar_info()

    def _on_home_open_file_requested(self):
        """Triggered from HomeView when open_file_requested is emitted."""
        if getattr(self, "_handling_home_export", False):
            return
        self.open_file_dialog()

    def _on_home_export_requested(self):
        """Triggered from HomeView 'Export a PDF' quick action card."""
        self._handling_home_export = True
        try:
            tab = self._get_active_tab()
            if tab:
                self.workspace_stack.setCurrentIndex(1)
                self.quick_tools.setVisible(True)
                self.quick_tools.workspace_tabs.select_tab("convert")
            else:
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Select PDF to Convert", "", "PDF Files (*.pdf);;All Files (*.*)"
                )
                if file_path:
                    self.open_document(file_path)
                    active_tab = self._get_active_tab()
                    if active_tab:
                        self.quick_tools.workspace_tabs.select_tab("convert")
        finally:
            self._handling_home_export = False

    def _export_to_format(self, format_key: Optional[str] = None):
        """Enters Convert mode with a pre-selected export format from the File menu."""
        tab = self._get_active_tab()
        if not tab:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select PDF to Export", "", "PDF Files (*.pdf);;All Files (*.*)"
            )
            if file_path:
                self.open_document(file_path)
                tab = self._get_active_tab()
            else:
                return

        if tab:
            self.workspace_stack.setCurrentIndex(1)
            self.quick_tools.setVisible(True)
            self.quick_tools.workspace_tabs.select_tab("convert")
            if format_key and hasattr(tab, "export_pdf_panel"):
                tab.export_pdf_panel.select_format(format_key)

    def execute_document_export(self, tab, target_path: str, format_key: str, options: dict):
        """Asynchronously executes multi-format document conversion with progress and prompts."""
        # Non-destructive / overwrite safety verification
        if os.path.exists(target_path):
            reply = QMessageBox.question(
                self, "Confirm File Replace",
                f"The file '{os.path.basename(target_path)}' already exists.\n\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.status_bar.showMessage("Export cancelled by user.", 3000)
                return

        format_display = get_format_display_name(format_key)
        source_name = os.path.basename(getattr(tab, "file_path", "Document.pdf"))
        target_name = os.path.basename(target_path)

        self.status_bar.showMessage(f"Exporting document to {target_name}...", 5000)

        # Show modal progress dialog
        self.active_progress_dlg = ExportProgressDialog(
            format_display=format_display,
            source_name=source_name,
            target_name=target_name,
            parent=self
        )
        self.active_progress_dlg.open()

        worker = ExportWorker(
            doc_wrapper=tab.doc_wrapper,
            target_path=target_path,
            format_key=format_key,
            options=options
        )

        self.active_progress_dlg.cancel_requested.connect(worker.cancel)

        def on_progress(cur, total, msg):
            self.status_bar.showMessage(f"Exporting ({cur}/{total}): {msg}")
            if hasattr(self, "active_progress_dlg") and self.active_progress_dlg:
                self.active_progress_dlg.set_progress(cur, total, msg)

        def on_finished(out_path):
            if hasattr(self, "active_progress_dlg") and self.active_progress_dlg:
                self.active_progress_dlg.close()
                self.active_progress_dlg = None
            self.status_bar.showMessage(f"Successfully exported to: {os.path.basename(out_path)}", 5000)
            self.active_success_dlg = ExportSuccessDialog(
                target_file_path=out_path,
                format_display=format_display,
                parent=self
            )
            self.active_success_dlg.open()

        def on_cancelled():
            if hasattr(self, "active_progress_dlg") and self.active_progress_dlg:
                self.active_progress_dlg.close()
                self.active_progress_dlg = None
            self.status_bar.showMessage("Export cancelled by user.", 3000)

        def on_error(err):
            if hasattr(self, "active_progress_dlg") and self.active_progress_dlg:
                self.active_progress_dlg.close()
                self.active_progress_dlg = None
            self.status_bar.showMessage(f"Export failed: {err}", 5000)
            QMessageBox.critical(self, "Export Error", f"Failed to export document:\n{err}")

        worker.signals.progress.connect(on_progress)
        worker.signals.finished.connect(on_finished)
        worker.signals.cancelled.connect(on_cancelled)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)

    def _rotate_active_page_cw(self):
        tab = self._get_active_tab()
        if tab:
            tab.rotate_current_page_cw()

    def _rotate_active_page_ccw(self):
        tab = self._get_active_tab()
        if tab:
            tab.rotate_current_page_ccw()

    def _show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file_dialog)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_active_document)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.save_as_active_document)
        QShortcut(QKeySequence("Ctrl+I"), self, self.focus_ai_copilot)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)

    def focus_ai_copilot(self):
        tab = self._get_active_tab()
        if tab:
            tab.right_panel_stack.setCurrentIndex(1)
            tab.right_panel_stack.setVisible(True)
            tab.left_rail.close_drawer()
            tab.left_rail.setVisible(False)
            tab.right_nav_rail.set_active_tab("attachments")
            sizes = tab.splitter.sizes()
            if len(sizes) > 2 and sizes[2] < 100:
                tab.splitter.setSizes([sizes[0], max(100, sizes[1] - 268), 268])
            if hasattr(tab.right_drawer, "ai_chat_panel"):
                tab.right_drawer.ai_chat_panel.input_query.setFocus()
            self.status_bar.showMessage("AI Assistant ready - Ask questions or choose an action", 3000)

    def apply_theme(self):
        # Save geometry before stylesheet change
        saved_geom = self.geometry()
        ThemeManager.set_theme("dark" if self.is_dark_theme else "light")
        stylesheet = generate_theme_stylesheet(ThemeManager.get_tokens())
        self.setStyleSheet(stylesheet)
        self.quick_tools.update_theme()
        if hasattr(self, "app_nav_bar"):
            self.app_nav_bar.update_theme()
        if hasattr(self, "home_view"):
            self.home_view.update_theme()
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, DocumentTab):
                tab.update_theme()

        # Constrain to available screen area to avoid being pushed off-screen
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            cur = self.geometry()
            target_w = min(cur.width(), avail.width())
            target_h = min(cur.height(), avail.height())
            target_x = max(avail.x(), min(cur.x(), avail.right() - target_w))
            target_y = max(avail.y(), min(cur.y(), avail.bottom() - target_h))
            self.setGeometry(target_x, target_y, target_w, target_h)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()
        theme_name = "Dark" if self.is_dark_theme else "Light"
        self.status_bar.showMessage(f"Switched to Acrobat {theme_name} Theme", 3000)

    def toggle_organize_view(self):
        tab = self._get_active_tab()
        if tab:
            if tab.is_organize_view_active():
                tab.show_reading_view()
            else:
                tab.show_organize_view()

    def _on_tab_view_mode_changed(self, tab: DocumentTab, is_organize: bool):
        if tab == self._get_active_tab():
            self.quick_tools.setVisible(True)
            if is_organize:
                if hasattr(self.quick_tools, "workspace_tabs"):
                    self.quick_tools.workspace_tabs.set_active_tab("all_tools", emit_signal=False)
            self.btn_toggle_organize.setText("Document View" if is_organize else "Organize Pages")
            self.status_bar.clearMessage()
            if not is_organize:
                self._update_quick_tools_for_active_tab()

    def open_merge_dialog(self):
        dlg = MergeDialog(parent=self)
        if dlg.exec() and dlg.output_file_path:
            self.open_document(dlg.output_file_path)

    def open_extract_dialog(self):
        tab = self._get_active_tab()
        if tab:
            dlg = SplitExtractDialog(tab.doc_wrapper, parent=self)
            dlg.exec()

    def ocr_active_page(self):
        tab = self._get_active_tab()
        if tab:
            tab.run_ocr_current_page()

    def export_active_images(self):
        tab = self._get_active_tab()
        if tab:
            tab.export_all_images()

    def export_active_markdown(self):
        tab = self._get_active_tab()
        if tab:
            tab.export_markdown()

    def export_active_text(self):
        tab = self._get_active_tab()
        if tab:
            tab.export_text()

    def export_active_page_image(self):
        tab = self._get_active_tab()
        if tab:
            tab.export_page_image()

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF Document", "", "PDF Files (*.pdf);;All Files (*.*)"
        )
        if file_path:
            self.open_document(file_path)

    def open_document(self, file_path: str):
        try:
            tab = DocumentTab(file_path, parent=self)
            self.undo_group.addStack(tab.undo_stack)
            self.undo_group.setActiveStack(tab.undo_stack)
            tab.dirty_state_changed.connect(lambda is_dirty: self._update_tab_dirty_state(tab, is_dirty))
            tab.view_mode_changed.connect(lambda is_org: self._on_tab_view_mode_changed(tab, is_org))

            tab_title = os.path.basename(file_path)
            self.setWindowTitle(f"{tab_title} — Spectra PDF")
            self._set_menu_title(f"{tab_title} — Spectra PDF")
            idx = self.tab_widget.addTab(tab, tab_title)
            if hasattr(self, "app_nav_bar"):
                self.app_nav_bar.add_document_tab(tab_title, file_path)
            self.tab_widget.setCurrentIndex(idx)

            tab.set_tool(self.quick_tools.active_tool)
            tab.set_highlight_color(self.quick_tools.current_highlight_color)
            tab.set_draw_style(self.quick_tools.current_draw_color, self.quick_tools.current_draw_width)

            self._update_workspace_state()
            try:
                RecentFilesManager.get_instance().record_file(file_path, tab.doc_wrapper.page_count)
                if hasattr(self, "home_view") and hasattr(self.home_view, "recent_table"):
                    self.home_view.recent_table.refresh_from_store()
            except Exception:
                pass
            self.status_bar.showMessage(f"Opened {tab_title} ({tab.doc_wrapper.page_count} pages)")
        except Exception as e:
            QMessageBox.critical(self, "Error Opening PDF", f"Could not load PDF:\n{str(e)}")

    def _update_tab_dirty_state(self, tab: DocumentTab, is_dirty: bool):
        tab.is_dirty = is_dirty
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.widget(idx) == tab:
                base = os.path.basename(tab.file_path)
                self.tab_widget.setTabText(idx, f"{base} *" if is_dirty else base)
                if hasattr(self, "app_nav_bar"):
                    self.app_nav_bar.set_tab_dirty(idx, is_dirty)
                break
        self._update_status_bar_info()

    def _update_status_bar_info(self):
        """Updates enriched status bar with save state, page metadata, and security info."""
        if not hasattr(self, "lbl_status_save"):
            return
        tab = self._get_active_tab()
        if not tab:
            self.lbl_status_save.setText("")
            self.lbl_status_doc_info.setText("")
            self.lbl_status_security.setText("")
            return

        is_dirty = getattr(tab, "is_dirty", False)
        if is_dirty:
            self.lbl_status_save.setText("☁ * Unsaved changes")
            self.lbl_status_save.setObjectName("statusBarSaveBadgeDirty")
        else:
            self.lbl_status_save.setText("☁ All changes saved")
            self.lbl_status_save.setObjectName("statusBarSaveBadge")

        self.lbl_status_save.style().unpolish(self.lbl_status_save)
        self.lbl_status_save.style().polish(self.lbl_status_save)

        total = tab.doc_wrapper.page_count
        curr = tab.current_page
        dims_str = "8.5 × 11.0 in"
        try:
            page = tab.doc_wrapper.get_page(curr - 1)
            w_in = page.rect.width / 72.0
            h_in = page.rect.height / 72.0
            dims_str = f"{w_in:.1f} × {h_in:.1f} in"
        except Exception:
            pass

        self.lbl_status_doc_info.setText(f"Page {curr} of {total} · {dims_str} · PDF/A")
        self.lbl_status_security.setText("🛡 Protected view off")

    def save_active_document(self):
        tab = self._get_active_tab()
        if tab:
            try:
                saved = tab.save()
                self._update_tab_dirty_state(tab, False)
                self.status_bar.showMessage(f"Successfully saved {os.path.basename(saved)}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save document:\n{str(e)}")

    def save_as_active_document(self):
        tab = self._get_active_tab()
        if tab:
            target_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF As", tab.file_path, "PDF Files (*.pdf)"
            )
            if target_path:
                try:
                    saved = tab.save_as(target_path)
                    self._update_tab_dirty_state(tab, False)
                    self.status_bar.showMessage(f"Saved copy to {os.path.basename(saved)}", 4000)
                except Exception as e:
                    QMessageBox.critical(self, "Save As Error", f"Failed to save copy:\n{str(e)}")

    def close_tab(self, index: int):
        tab = self.tab_widget.widget(index)
        if isinstance(tab, DocumentTab):
            self.undo_group.removeStack(tab.undo_stack)
            if tab.doc_wrapper.is_dirty:
                ret = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"'{os.path.basename(tab.file_path)}' has unsaved annotations or page changes. Save before closing?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if ret == QMessageBox.Save:
                    tab.save()
                elif ret == QMessageBox.Cancel:
                    self.undo_group.addStack(tab.undo_stack)
                    return

            tab.close()
        self.tab_widget.removeTab(index)
        if hasattr(self, "app_nav_bar"):
            self.app_nav_bar.remove_document_tab(index)
        self._update_workspace_state()

    def closeEvent(self, event):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, DocumentTab) and tab.doc_wrapper.is_dirty:
                ret = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"'{os.path.basename(tab.file_path)}' has unsaved changes. Save before exit?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if ret == QMessageBox.Save:
                    tab.save()
                elif ret == QMessageBox.Cancel:
                    event.ignore()
                    return
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, DocumentTab):
                tab.close()
        event.accept()

    def _get_active_tab(self) -> Optional[DocumentTab]:
        current = self.tab_widget.currentWidget()
        if isinstance(current, DocumentTab):
            return current
        return None

    def undo_active_document(self):
        tab = self._get_active_tab()
        if tab:
            tab.undo()

    def redo_active_document(self):
        tab = self._get_active_tab()
        if tab:
            tab.redo()

    def _on_undo_availability_changed(self, can_undo: bool):
        if hasattr(self, "quick_tools"):
            self.quick_tools.set_undo_enabled(can_undo)

    def _on_redo_availability_changed(self, can_redo: bool):
        if hasattr(self, "quick_tools"):
            self.quick_tools.set_redo_enabled(can_redo)

    def _on_undo_text_changed(self, text: str):
        if hasattr(self, "quick_tools"):
            self.quick_tools.set_undo_tooltip(text)

    def _on_redo_text_changed(self, text: str):
        if hasattr(self, "quick_tools"):
            self.quick_tools.set_redo_tooltip(text)

    def _on_tab_changed(self, index: int):
        self._update_workspace_state()
        tab = self._get_active_tab()
        if tab:
            self.undo_group.setActiveStack(tab.undo_stack)
            doc_name = os.path.basename(tab.file_path)
            self.setWindowTitle(f"{doc_name} — Spectra PDF")
            self._set_menu_title(f"{doc_name} — Spectra PDF")
            is_org = tab.is_organize_view_active()
            self.btn_toggle_organize.setText("Document View" if is_org else "Organize Pages")
            self.quick_tools.setVisible(not is_org)
            if hasattr(self.quick_tools, "workspace_tabs"):
                target_tab = "edit" if tab.is_edit_mode_active() else "all_tools"
                self.quick_tools.workspace_tabs.set_active_tab(target_tab, emit_signal=False)
            if hasattr(self, "app_nav_bar") and index >= 0:
                self.app_nav_bar.set_active_document_tab(index)
        else:
            self.undo_group.setActiveStack(None)
            self.setWindowTitle("Spectra PDF")
            self._set_menu_title("Spectra PDF")
            if hasattr(self, "app_nav_bar"):
                self.app_nav_bar.set_home_active()
        self._update_status_bar_info()

    def _update_workspace_state(self):
        has_documents = self.tab_widget.count() > 0
        if has_documents:
            self.workspace_stack.setCurrentIndex(1)
            tab = self._get_active_tab()
            is_org = tab.is_organize_view_active() if tab else False
            self.quick_tools.setVisible(not is_org)
            self._update_quick_tools_for_active_tab()
            self._set_document_actions_enabled(True)
            if hasattr(self, "app_nav_bar"):
                self.app_nav_bar.set_active_document_tab(self.tab_widget.currentIndex())
        else:
            self.workspace_stack.setCurrentIndex(0)
            self.quick_tools.setVisible(False)
            self._set_document_actions_enabled(False)
            self.status_bar.showMessage("Home | Spectra PDF Workstation")
            self.setWindowTitle("Spectra PDF")
            if hasattr(self, "menu_title_label"):
                self.menu_title_label.setText("Spectra PDF")
            if hasattr(self, "app_nav_bar"):
                self.app_nav_bar.set_home_active()
        self._update_status_bar_info()

    def _set_document_actions_enabled(self, enabled: bool):
        actions = [
            getattr(self, "action_save", None),
            getattr(self, "action_save_as", None),
            getattr(self, "action_toggle_organize", None),
            getattr(self, "action_extract", None),
            getattr(self, "action_ocr", None),
            getattr(self, "action_close_doc", None),
            getattr(self, "action_zoom_in", None),
            getattr(self, "action_zoom_out", None),
            getattr(self, "action_fit_width", None),
            getattr(self, "action_fit_page", None),
            getattr(self, "action_rotate_cw", None),
            getattr(self, "action_rotate_ccw", None),
            getattr(self, "action_find", None),
        ]
        for act in actions:
            if act:
                act.setEnabled(enabled)

        if hasattr(self, "btn_save") and self.btn_save:
            self.btn_save.setEnabled(enabled)
        if hasattr(self, "btn_save_as") and self.btn_save_as:
            self.btn_save_as.setEnabled(enabled)
        if hasattr(self, "btn_toggle_organize") and self.btn_toggle_organize:
            self.btn_toggle_organize.setEnabled(enabled)
        if hasattr(self, "btn_extract_tool") and self.btn_extract_tool:
            self.btn_extract_tool.setEnabled(enabled)
        if hasattr(self, "btn_ocr_bar") and self.btn_ocr_bar:
            self.btn_ocr_bar.setEnabled(enabled)
        if hasattr(self, "btn_export") and self.btn_export:
            self.btn_export.setEnabled(enabled)

    def _update_quick_tools_for_active_tab(self):
        tab = self._get_active_tab()
        if tab:
            self.quick_tools.update_page_info(tab.current_page, tab.doc_wrapper.page_count)
            self.quick_tools.update_zoom_display(tab.current_zoom)

    def _on_tool_changed(self, tool_name: str):
        tab = self._get_active_tab()
        if tab:
            tab.set_tool(tool_name)

    def _on_highlight_color_changed(self, rgb: tuple):
        tab = self._get_active_tab()
        if tab:
            tab.set_highlight_color(rgb)

    def _on_draw_style_changed(self, rgb: tuple, width: float):
        tab = self._get_active_tab()
        if tab:
            tab.set_draw_style(rgb, width)

    def _zoom_in(self):
        tab = self._get_active_tab()
        if tab:
            tab.zoom_in()
            self.quick_tools.update_zoom_display(tab.current_zoom)

    def _zoom_out(self):
        tab = self._get_active_tab()
        if tab:
            tab.zoom_out()
            self.quick_tools.update_zoom_display(tab.current_zoom)

    def _zoom_to(self, scale: float):
        tab = self._get_active_tab()
        if tab:
            tab.set_zoom(scale)

    def _fit_width(self):
        tab = self._get_active_tab()
        if tab:
            tab.fit_width()
            self.quick_tools.update_zoom_display(tab.current_zoom)

    def _fit_page(self):
        tab = self._get_active_tab()
        if tab:
            tab.fit_page()
            self.quick_tools.update_zoom_display(tab.current_zoom)

    def _go_to_page(self, page_number: int):
        tab = self._get_active_tab()
        if tab:
            tab.go_to_page(page_number)
