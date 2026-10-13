"""
Interactive PDF Canvas Viewport with High-DPI Razor-Sharp Rendering
Handles dynamic device pixel ratio, text highlight selection, freehand drawing,
and Adobe Acrobat Edit PDF interactive bounding boxes, selection handles,
floating text toolbar (322px pill), inline live text editing overlay, and bottom tip banner.
"""

from typing import List, Tuple, Optional, Dict
import pymupdf as fitz

from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QPointF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QMouseEvent, QPaintEvent, QCursor, QResizeEvent
)

from pyacrobat.core.pdf_editor import ContentBlock, ContentBlockType, FontStyle
from pyacrobat.ui.selected_text_toolbar import SelectedTextToolbar
from pyacrobat.ui.inline_text_editor import InlineTextEditor, EditingTipBanner


class PageCardWidget(QFrame):
    """
    Interactive container for a single rendered PDF page.
    Renders with native screen pixel density (High-DPI supersampling) for razor-sharp text.
    Supports Adobe Acrobat interactive content block selection, bounding boxes, handles,
    and inline overlay text editing.
    """

    # Existing annotation signals
    highlight_created = Signal(int, object)        # (page_idx, fitz.Rect)
    ink_drawn = Signal(int, list)                  # (page_idx, list of (x, y) tuples)
    note_created = Signal(int, tuple, str)         # (page_idx, (x, y), comment_text)

    # Phase 3 & 4: Interactive Edit Mode signals
    block_selected = Signal(int, object)           # (page_idx, ContentBlock)
    block_deselected = Signal(int)                 # (page_idx)
    block_rect_changed = Signal(int, object, object) # (page_idx, ContentBlock, fitz.Rect new_rect)
    block_double_clicked = Signal(int, object)     # (page_idx, ContentBlock)
    block_text_edited = Signal(int, object, str)   # (page_idx, ContentBlock, new_text)
    new_textbox_created = Signal(int, object)      # (page_idx, fitz.Rect)

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.scale: float = 1.0
        self.dpr_factor: float = 1.0
        self.current_tool: str = "select"
        self.base_pixmap: Optional[QPixmap] = None

        # Content blocks & Edit mode state
        self.content_blocks: List[ContentBlock] = []
        self.selected_block: Optional[ContentBlock] = None
        self.hovered_block: Optional[ContentBlock] = None
        self.is_edit_mode: bool = False
        self.show_bounding_boxes: bool = True

        # Handle interaction states
        self._is_dragging_block: bool = False
        self._is_resizing_block: bool = False
        self._resize_handle: Optional[str] = None  # 'nw', 'ne', 'sw', 'se'
        self._drag_start_pos: QPointF = QPointF()
        self._orig_block_rect: Optional[fitz.Rect] = None

        # New textbox creation state (when tool == 'text')
        self._is_creating_textbox: bool = False
        self._create_textbox_start: Optional[QPointF] = None
        self._create_textbox_current: Optional[QPointF] = None

        # Live drawing states
        self.is_drawing: bool = False
        self.current_stroke: List[QPointF] = []
        self.draw_color: QColor = QColor(225, 37, 27)
        self.draw_width: float = 2.0

        # Live highlight states
        self.is_highlighting: bool = False
        self.highlight_start: Optional[QPointF] = None
        self.highlight_current: Optional[QPointF] = None
        self.highlight_color: QColor = QColor(255, 224, 102, 120)

        self.setObjectName("pdfPageCard")
        self.init_ui()

    def init_ui(self):
        # Adobe Acrobat Figma spec drop-shadow: 0px 2px 7px rgba(0, 0, 0, 0.14)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(7)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 36))  # 0.14 * 255 ≈ 36
        self.setGraphicsEffect(shadow)
        self.setMouseTracking(True)

        # Inline overlay text editor
        self.inline_editor = InlineTextEditor(self)
        self.inline_editor.hide()
        self.inline_editor.editing_committed.connect(self._on_inline_editing_committed)
        self.inline_editor.editing_canceled.connect(self._on_inline_editing_canceled)

    def set_page_image(self, qimage: QImage, dpr_factor: float, scale: float):
        """Sets the rasterized image with native High-DPI device pixel ratio."""
        self.base_pixmap = QPixmap.fromImage(qimage)
        self.base_pixmap.setDevicePixelRatio(dpr_factor)
        self.scale = max(0.1, scale)
        self.dpr_factor = dpr_factor

        # Set widget to logical device-independent dimensions
        indep_size = self.base_pixmap.deviceIndependentSize()
        self.setFixedSize(int(round(indep_size.width())), int(round(indep_size.height())))
        self.update()

    # ==========================================
    # Coordinate Mapping Helpers
    # ==========================================

    def pdf_to_screen_rect(self, rect: fitz.Rect) -> QRectF:
        """Converts logical 72-DPI PDF coordinates to screen pixel coordinates."""
        return QRectF(
            rect.x0 * self.scale,
            rect.y0 * self.scale,
            (rect.x1 - rect.x0) * self.scale,
            (rect.y1 - rect.y0) * self.scale
        )

    def screen_to_pdf_rect(self, rect: QRectF) -> fitz.Rect:
        """Converts screen pixel coordinates back to logical PDF points."""
        return fitz.Rect(
            rect.left() / self.scale,
            rect.top() / self.scale,
            rect.right() / self.scale,
            rect.bottom() / self.scale
        )

    def get_handle_rects(self, screen_rect: QRectF) -> Dict[str, QRectF]:
        """
        Calculates the 4 corner handle rectangles (6x6 px white squares with blue borders)
        positioned at (-3, -3) offset from corners matching Figma spec #3:13310-#3:13313.
        """
        hw, hh = 6.0, 6.0
        return {
            'nw': QRectF(screen_rect.left() - 3.0, screen_rect.top() - 3.0, hw, hh),
            'ne': QRectF(screen_rect.right() - 3.0, screen_rect.top() - 3.0, hw, hh),
            'sw': QRectF(screen_rect.left() - 3.0, screen_rect.bottom() - 3.0, hw, hh),
            'se': QRectF(screen_rect.right() - 3.0, screen_rect.bottom() - 3.0, hw, hh),
        }

    def hit_test_handle(self, screen_pos: QPointF, screen_rect: QRectF) -> Optional[str]:
        """Hit tests mouse position against the 4 corner resize handles with generous 4px tolerance."""
        handles = self.get_handle_rects(screen_rect)
        for h_id, h_rect in handles.items():
            if h_rect.adjusted(-4, -4, 4, 4).contains(screen_pos):
                return h_id
        return None

    def block_at(self, screen_pos: QPointF) -> Optional[ContentBlock]:
        """Returns the ContentBlock under the given screen position, or None."""
        pdf_pt = fitz.Point(screen_pos.x() / self.scale, screen_pos.y() / self.scale)
        # Search backwards so top-most/later blocks hit first
        for block in reversed(self.content_blocks):
            if block.rect.contains(pdf_pt):
                return block
        return None

    # ==========================================
    # Edit Mode Configuration
    # ==========================================

    def set_content_blocks(self, blocks: List[ContentBlock]):
        """Sets structured content blocks for interactive editing."""
        self.content_blocks = list(blocks)
        if self.selected_block and self.selected_block not in self.content_blocks:
            self.selected_block = None
            self.block_deselected.emit(self.page_index)
        self.update()

    def set_edit_mode(self, enabled: bool, show_bounding_boxes: bool = True):
        """Enables/disables interactive PDF Edit Mode."""
        self.is_edit_mode = enabled
        self.show_bounding_boxes = show_bounding_boxes
        if not enabled:
            self.selected_block = None
            self.hovered_block = None
            if self.inline_editor.isVisible():
                self.inline_editor.cancel()
        self.update()

    def set_show_bounding_boxes(self, enabled: bool):
        """Toggles rendering of unselected content bounding boxes."""
        self.show_bounding_boxes = enabled
        self.update()

    def select_block(self, block: Optional[ContentBlock]):
        """Explicitly selects or deselects a block."""
        if self.selected_block != block:
            if self.inline_editor.isVisible():
                self.inline_editor.commit()
            self.selected_block = block
            if block:
                self.block_selected.emit(self.page_index, block)
            else:
                self.block_deselected.emit(self.page_index)
            self.update()

    def start_inline_editing(self, block: ContentBlock):
        """Positions and activates the inline text editor directly over the target block."""
        if not block.is_text:
            return
        self.selected_block = block
        s_rect = self.pdf_to_screen_rect(block.rect)

        # Extra padding for typing expansion
        edit_x = max(0, int(round(s_rect.x() - 2)))
        edit_y = max(0, int(round(s_rect.y() - 2)))
        edit_w = int(round(max(120.0, s_rect.width() + 16)))
        edit_h = int(round(max(36.0, s_rect.height() + 8)))

        self.inline_editor.setGeometry(edit_x, edit_y, edit_w, edit_h)
        self.inline_editor.start_editing(block.text, block.font_style, self.scale)

    def _on_inline_editing_committed(self, new_text: str):
        if self.selected_block:
            if new_text != self.selected_block.text:
                self.selected_block.text = new_text
                self.block_text_edited.emit(self.page_index, self.selected_block, new_text)
        self.update()

    def _on_inline_editing_canceled(self):
        self.update()

    # ==========================================
    # Painting Pipeline
    # ==========================================

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 1. Base High-DPI rasterized PDF page
        if self.base_pixmap and not self.base_pixmap.isNull():
            painter.drawPixmap(0, 0, self.base_pixmap)
        else:
            painter.fillRect(self.rect(), Qt.white)

        # 2. Interactive Edit Mode Bounding Boxes & Selection Overlays
        if self.is_edit_mode:
            # 2a. Unselected bounding boxes (if show_bounding_boxes enabled)
            if self.show_bounding_boxes:
                dash_pen = QPen(QColor(160, 190, 230, 140), 1.0, Qt.DashLine)
                for block in self.content_blocks:
                    if block == self.selected_block:
                        continue
                    s_rect = self.pdf_to_screen_rect(block.rect)
                    if block == self.hovered_block:
                        # Soft hover fill and solid border
                        painter.fillRect(s_rect, QColor(20, 115, 230, 25))
                        hover_pen = QPen(QColor(20, 115, 230, 180), 1.0, Qt.SolidLine)
                        painter.setPen(hover_pen)
                        painter.drawRect(s_rect)
                    else:
                        painter.setPen(dash_pen)
                        painter.drawRect(s_rect)

            # 2b. Selected block (Solid #1473E6 border + 4 Corner Handles)
            # Only draw handle frame if inline text editor is not actively editing
            if self.selected_block and not self.inline_editor.isVisible():
                sel_rect = self.pdf_to_screen_rect(self.selected_block.rect)

                # Solid 1px border in Adobe Blue #1473E6
                border_pen = QPen(QColor("#1473E6"), 1.2, Qt.SolidLine)
                painter.setPen(border_pen)
                painter.drawRect(sel_rect)

                # Draw 4 corner selection handles (6x6 px white square with #1473E6 border)
                handle_rects = self.get_handle_rects(sel_rect)
                for h_rect in handle_rects.values():
                    painter.fillRect(h_rect, QColor("#FFFFFF"))
                    painter.setPen(QPen(QColor("#1473E6"), 1.0))
                    painter.drawRect(h_rect)

            # 2c. In-progress new textbox creation rubber band
            if self._is_creating_textbox and self._create_textbox_start and self._create_textbox_current:
                new_box = QRectF(self._create_textbox_start, self._create_textbox_current).normalized()
                painter.fillRect(new_box, QColor(20, 115, 230, 20))
                painter.setPen(QPen(QColor("#1473E6"), 1.0, Qt.DashLine))
                painter.drawRect(new_box)

        # 3. Live freehand drawing stroke
        if self.is_drawing and len(self.current_stroke) > 1:
            pen = QPen(self.draw_color, self.draw_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            for i in range(len(self.current_stroke) - 1):
                painter.drawLine(self.current_stroke[i], self.current_stroke[i + 1])

        # 4. Live highlight selection rectangle
        if self.is_highlighting and self.highlight_start and self.highlight_current:
            rect = QRectF(self.highlight_start, self.highlight_current).normalized()
            painter.fillRect(rect, self.highlight_color)
            painter.setPen(QPen(QColor(self.highlight_color.rgb()), 1, Qt.DashLine))
            painter.drawRect(rect)

        painter.end()

    # ==========================================
    # Mouse Interaction Pipeline
    # ==========================================

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = event.position()

            # A. Edit Mode interactions
            if self.is_edit_mode:
                # 1. New text tool click-drag
                if self.current_tool == "text":
                    self._is_creating_textbox = True
                    self._create_textbox_start = pos
                    self._create_textbox_current = pos
                    self.update()
                    event.accept()
                    return

                # 2. Check if clicked on a corner handle of the selected block
                if self.selected_block:
                    s_rect = self.pdf_to_screen_rect(self.selected_block.rect)
                    handle = self.hit_test_handle(pos, s_rect)
                    if handle:
                        self._is_resizing_block = True
                        self._is_dragging_block = False
                        self._resize_handle = handle
                        self._drag_start_pos = pos
                        self._orig_block_rect = fitz.Rect(self.selected_block.rect)
                        event.accept()
                        return

                    # 3. Check if clicked inside selected block -> Potential drag to move
                    if s_rect.contains(pos):
                        self._is_dragging_block = False
                        self._is_resizing_block = False
                        self._drag_start_pos = pos
                        self._orig_block_rect = fitz.Rect(self.selected_block.rect)
                        event.accept()
                        return

                # 4. Check if clicked on another block -> Select it
                clicked_block = self.block_at(pos)
                if clicked_block:
                    self.select_block(clicked_block)
                    self._is_dragging_block = False
                    self._is_resizing_block = False
                    self._drag_start_pos = pos
                    self._orig_block_rect = fitz.Rect(clicked_block.rect)
                    event.accept()
                    return
                else:
                    # Clicked on empty canvas -> Deselect
                    self.select_block(None)
                    self._is_dragging_block = False
                    self._is_resizing_block = False
                    self._drag_start_pos = None
                    self._orig_block_rect = None
                    event.accept()
                    return

            # B. Standard reading / annotation tools
            if self.current_tool == "draw":
                self.is_drawing = True
                self.current_stroke = [pos]
                self.update()
            elif self.current_tool == "highlight":
                self.is_highlighting = True
                self.highlight_start = pos
                self.highlight_current = pos
                self.update()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        # A. Edit Mode Dragging / Resizing / Hover
        if self.is_edit_mode:
            # 1. New textbox creation dragging
            if self._is_creating_textbox:
                self._create_textbox_current = pos
                self.update()
                event.accept()
                return

            # 2. Resizing selected block via handle
            if self._is_resizing_block and self.selected_block and self._orig_block_rect and self._drag_start_pos is not None:
                dx = (pos.x() - self._drag_start_pos.x()) / self.scale
                dy = (pos.y() - self._drag_start_pos.y()) / self.scale
                r = fitz.Rect(self._orig_block_rect)

                if self._resize_handle == 'nw':
                    r.x0 = min(r.x1 - 10.0, r.x0 + dx)
                    r.y0 = min(r.y1 - 10.0, r.y0 + dy)
                elif self._resize_handle == 'ne':
                    r.x1 = max(r.x0 + 10.0, r.x1 + dx)
                    r.y0 = min(r.y1 - 10.0, r.y0 + dy)
                elif self._resize_handle == 'sw':
                    r.x0 = min(r.x1 - 10.0, r.x0 + dx)
                    r.y1 = max(r.y0 + 10.0, r.y1 + dy)
                elif self._resize_handle == 'se':
                    r.x1 = max(r.x0 + 10.0, r.x1 + dx)
                    r.y1 = max(r.y0 + 10.0, r.y1 + dy)

                self.selected_block.rect = r
                self.update()
                event.accept()
                return

            # 3. Moving selected block (requires drag distance threshold)
            if self.selected_block and self._orig_block_rect and self._drag_start_pos is not None and not self._is_resizing_block:
                dx_screen = pos.x() - self._drag_start_pos.x()
                dy_screen = pos.y() - self._drag_start_pos.y()
                if not self._is_dragging_block and (abs(dx_screen) >= 3.0 or abs(dy_screen) >= 3.0):
                    self._is_dragging_block = True

                if self._is_dragging_block:
                    dx = dx_screen / self.scale
                    dy = dy_screen / self.scale
                    new_rect = fitz.Rect(
                        self._orig_block_rect.x0 + dx,
                        self._orig_block_rect.y0 + dy,
                        self._orig_block_rect.x1 + dx,
                        self._orig_block_rect.y1 + dy
                    )
                    self.selected_block.rect = new_rect
                    self.update()
                    event.accept()
                    return

            # 4. Hover cursor updates
            if self.current_tool == "text":
                self.setCursor(Qt.IBeamCursor)
            elif self.selected_block and not self.inline_editor.isVisible():
                s_rect = self.pdf_to_screen_rect(self.selected_block.rect)
                handle = self.hit_test_handle(pos, s_rect)
                if handle in ('nw', 'se'):
                    self.setCursor(Qt.SizeFDiagCursor)
                elif handle in ('ne', 'sw'):
                    self.setCursor(Qt.SizeBDiagCursor)
                elif s_rect.contains(pos):
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    hovered = self.block_at(pos)
                    if hovered:
                        self.setCursor(Qt.PointingHandCursor)
                        if self.hovered_block != hovered:
                            self.hovered_block = hovered
                            self.update()
                    else:
                        self.setCursor(Qt.ArrowCursor)
                        if self.hovered_block:
                            self.hovered_block = None
                            self.update()
            else:
                hovered = self.block_at(pos)
                if hovered:
                    self.setCursor(Qt.PointingHandCursor)
                    if self.hovered_block != hovered:
                        self.hovered_block = hovered
                        self.update()
                else:
                    self.setCursor(Qt.ArrowCursor)
                    if self.hovered_block:
                        self.hovered_block = None
                        self.update()

        # B. Standard Tools
        if self.is_drawing:
            self.current_stroke.append(pos)
            self.update()
        elif self.is_highlighting:
            self.highlight_current = pos
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = event.position()

            # A. Edit Mode Release
            if self.is_edit_mode:
                # 1. New textbox creation completed
                if self._is_creating_textbox and self._create_textbox_start:
                    self._is_creating_textbox = False
                    screen_rect = QRectF(self._create_textbox_start, pos).normalized()
                    if screen_rect.width() < 15 or screen_rect.height() < 15:
                        # Click without drag -> sensible default box (220 x 40 pt)
                        pdf_origin = QPointF(self._create_textbox_start.x() / self.scale, self._create_textbox_start.y() / self.scale)
                        target_rect = fitz.Rect(pdf_origin.x(), pdf_origin.y(), pdf_origin.x() + 220.0, pdf_origin.y() + 40.0)
                    else:
                        target_rect = self.screen_to_pdf_rect(screen_rect)

                    self._create_textbox_start = None
                    self._create_textbox_current = None
                    self.new_textbox_created.emit(self.page_index, target_rect)
                    self.update()
                    event.accept()
                    return

                # 2. Resizing or Dragging completed -> emit block_rect_changed ONLY if moved
                if self.selected_block and self._orig_block_rect and (self._is_resizing_block or self._is_dragging_block):
                    old_r = fitz.Rect(self._orig_block_rect)
                    new_r = fitz.Rect(self.selected_block.rect)
                    has_moved = (
                        abs(old_r.x0 - new_r.x0) >= 0.5 or
                        abs(old_r.y0 - new_r.y0) >= 0.5 or
                        abs(old_r.x1 - new_r.x1) >= 0.5 or
                        abs(old_r.y1 - new_r.y1) >= 0.5
                    )
                    self._is_resizing_block = False
                    self._is_dragging_block = False
                    self._resize_handle = None
                    self._drag_start_pos = None
                    self._orig_block_rect = None

                    if has_moved:
                        self.selected_block.orig_rect = old_r
                        self.block_rect_changed.emit(self.page_index, self.selected_block, new_r)
                        self.update()
                    event.accept()
                    return

                # Normal click release without movement
                self._is_resizing_block = False
                self._is_dragging_block = False
                self._resize_handle = None
                self._drag_start_pos = None
                self._orig_block_rect = None

            # B. Standard tool release
            if self.is_drawing:
                self.is_drawing = False
                if len(self.current_stroke) > 1:
                    pdf_points = [(p.x() / self.scale, p.y() / self.scale) for p in self.current_stroke]
                    self.ink_drawn.emit(self.page_index, pdf_points)
                self.current_stroke = []
                self.update()

            elif self.is_highlighting:
                self.is_highlighting = False
                if self.highlight_start:
                    rect = QRectF(self.highlight_start, pos).normalized()
                    if rect.width() > 4 and rect.height() > 4:
                        pdf_rect = fitz.Rect(
                            rect.left() / self.scale,
                            rect.top() / self.scale,
                            rect.right() / self.scale,
                            rect.bottom() / self.scale
                        )
                        self.highlight_created.emit(self.page_index, pdf_rect)
                self.highlight_start = None
                self.highlight_current = None
                self.update()

            elif self.current_tool == "note":
                pdf_pt = (pos.x() / self.scale, pos.y() / self.scale)
                comment, ok = QInputDialog.getMultiLineText(
                    self, "Add Sticky Note", f"Enter comment for Page {self.page_index + 1}:"
                )
                if ok and comment.strip():
                    self.note_created.emit(self.page_index, pdf_pt, comment.strip())

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.is_edit_mode:
            pos = event.position()
            target_block = self.block_at(pos)
            if target_block and target_block.is_text:
                self.select_block(target_block)
                self.start_inline_editing(target_block)
                self.block_double_clicked.emit(self.page_index, target_block)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)


class PDFCanvas(QScrollArea):
    """
    Continuous vertical scrolling canvas for PDF document pages.
    Coordinates High-DPI rasterization, interactive Edit Mode bounding boxes,
    selection sync, floating quick format toolbar (322px pill), inline text editing,
    and bottom tip banner.
    """

    page_scrolled_to = Signal(int)

    # Standard tool signals
    highlight_requested = Signal(int, object)
    ink_requested = Signal(int, list)
    note_requested = Signal(int, tuple, str)

    # Phase 3 & 4: Interactive Block & Editing signals
    block_selected = Signal(int, object)           # (page_idx, ContentBlock)
    block_deselected = Signal(int)                 # (page_idx)
    block_rect_changed = Signal(int, object, object) # (page_idx, ContentBlock, fitz.Rect new_rect)
    block_double_clicked = Signal(int, object)     # (page_idx, ContentBlock)
    block_text_edited = Signal(int, object, str)   # (page_idx, ContentBlock, new_text)
    block_font_style_changed = Signal(int, object, object) # (page_idx, ContentBlock, FontStyle)
    new_textbox_requested = Signal(int, object)    # (page_idx, fitz.Rect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_widgets: List[PageCardWidget] = []
        self.current_zoom: float = 1.0
        self.current_tool: str = "select"
        self.is_edit_mode: bool = False
        self.show_bounding_boxes: bool = True

        self._is_panning = False
        self._pan_start = QPoint()

        self.init_ui()

    def init_ui(self):
        self.setObjectName("pdfCanvasArea")
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)

        self.container = QWidget()
        self.container.setObjectName("pdfCanvasContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.container_layout.setContentsMargins(20, 24, 20, 30)
        self.container_layout.setSpacing(24)

        self.setWidget(self.container)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # Phase 4: Floating Quick Format Toolbar (322px pill)
        self.floating_text_toolbar = SelectedTextToolbar(self.viewport())
        self.floating_text_toolbar.hide()
        self.floating_text_toolbar.font_style_changed.connect(self._on_toolbar_font_style_changed)

        # Phase 4: Bottom Editing Tip Banner
        self.editing_tip_banner = EditingTipBanner(self.viewport())
        self.editing_tip_banner.hide()

    def clear(self):
        for w in self.page_widgets:
            w.setParent(None)
            w.deleteLater()
        self.page_widgets.clear()
        self.floating_text_toolbar.hide()
        self.editing_tip_banner.hide()

    def setup_pages(self, page_count: int):
        self.clear()
        for i in range(page_count):
            card = PageCardWidget(page_index=i, parent=self.container)
            card.current_tool = self.current_tool
            card.set_edit_mode(self.is_edit_mode, self.show_bounding_boxes)

            # Annotation signal forwarding
            card.highlight_created.connect(self.highlight_requested.emit)
            card.ink_drawn.connect(self.ink_requested.emit)
            card.note_created.connect(self.note_requested.emit)

            # Edit Mode signal forwarding
            card.block_selected.connect(self._on_page_block_selected)
            card.block_deselected.connect(self._on_page_block_deselected)
            card.block_rect_changed.connect(self.block_rect_changed.emit)
            card.block_double_clicked.connect(self.block_double_clicked.emit)
            card.block_text_edited.connect(self.block_text_edited.emit)
            card.new_textbox_created.connect(self.new_textbox_requested.emit)

            self.container_layout.addWidget(card)
            self.page_widgets.append(card)

    def update_page_pixmap(self, page_index: int, qimage: QImage, dpr_factor: float, scale: float):
        if 0 <= page_index < len(self.page_widgets):
            self.page_widgets[page_index].set_page_image(qimage, dpr_factor, scale)

    # ==========================================
    # Phase 3 & 4: Interactive Edit Mode Methods
    # ==========================================

    def set_edit_mode(self, enabled: bool, show_bounding_boxes: bool = True):
        """Enables or disables interactive Edit Mode across all page cards."""
        self.is_edit_mode = enabled
        self.show_bounding_boxes = show_bounding_boxes
        for card in self.page_widgets:
            card.set_edit_mode(enabled, show_bounding_boxes)

        if enabled:
            self._reposition_tip_banner()
            self.editing_tip_banner.show()
        else:
            self.floating_text_toolbar.hide()
            self.editing_tip_banner.hide()

    def set_show_bounding_boxes(self, enabled: bool):
        """Toggles bounding boxes visibility across all page cards."""
        self.show_bounding_boxes = enabled
        for card in self.page_widgets:
            card.set_show_bounding_boxes(enabled)

    def set_page_content_blocks(self, page_index: int, blocks: List[ContentBlock]):
        """Populates structured content blocks for a specific page."""
        if 0 <= page_index < len(self.page_widgets):
            self.page_widgets[page_index].set_content_blocks(blocks)

    def get_selected_block(self) -> Optional[Tuple[int, ContentBlock]]:
        """Returns (page_index, ContentBlock) of currently active selection, or None."""
        for card in self.page_widgets:
            if card.selected_block:
                return (card.page_index, card.selected_block)
        return None

    def deselect_all_blocks(self):
        """Deselects any selected blocks across all page cards."""
        for card in self.page_widgets:
            card.select_block(None)
        self.floating_text_toolbar.hide()

    def _on_page_block_selected(self, page_index: int, block: ContentBlock):
        # Deselect any blocks on other pages to ensure single active selection
        for card in self.page_widgets:
            if card.page_index != page_index and card.selected_block:
                card.selected_block = None
                card.update()

        if self.is_edit_mode and block.is_text:
            self.floating_text_toolbar.set_font_style(block.font_style)
            self._reposition_floating_toolbar(page_index, block)
            self.floating_text_toolbar.show()
            self.floating_text_toolbar.raise_()
        else:
            self.floating_text_toolbar.hide()

        self.block_selected.emit(page_index, block)

    def _on_page_block_deselected(self, page_index: int):
        self.floating_text_toolbar.hide()
        self.block_deselected.emit(page_index)

    def _on_toolbar_font_style_changed(self, new_style: FontStyle):
        active = self.get_selected_block()
        if active:
            p_idx, block = active
            block.font_style = new_style
            self.block_font_style_changed.emit(p_idx, block, new_style)

    def _reposition_floating_toolbar(self, page_index: int, block: ContentBlock):
        if 0 <= page_index < len(self.page_widgets):
            card = self.page_widgets[page_index]
            s_rect = card.pdf_to_screen_rect(block.rect)
            # Map top-left to viewport coordinates
            vp_tl = card.mapTo(self.viewport(), s_rect.topLeft().toPoint())
            vp_block_rect = QRectF(vp_tl.x(), vp_tl.y(), s_rect.width(), s_rect.height())
            self.floating_text_toolbar.position_over_screen_rect(vp_block_rect, self.viewport().rect())

    def _reposition_tip_banner(self):
        if self.is_edit_mode:
            banner_w = min(420, self.viewport().width() - 48)
            banner_h = 32
            self.editing_tip_banner.setFixedWidth(banner_w)
            self.editing_tip_banner.move(24, max(10, self.viewport().height() - banner_h - 16))
            self.editing_tip_banner.show()
            self.editing_tip_banner.raise_()
        else:
            self.editing_tip_banner.hide()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._reposition_tip_banner()
        active = self.get_selected_block()
        if active and self.floating_text_toolbar.isVisible():
            self._reposition_floating_toolbar(active[0], active[1])

    # ==========================================
    # Tool & Canvas Controls
    # ==========================================

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        for card in self.page_widgets:
            card.current_tool = tool_name
            if not card.is_edit_mode:
                if tool_name == "draw":
                    card.setCursor(Qt.CrossCursor)
                elif tool_name == "highlight":
                    card.setCursor(Qt.IBeamCursor)
                elif tool_name == "note":
                    card.setCursor(Qt.PointingHandCursor)
                elif tool_name == "hand":
                    card.setCursor(Qt.OpenHandCursor)
                else:
                    card.setCursor(Qt.ArrowCursor)

    def set_highlight_color(self, rgb: Tuple[float, float, float]):
        qc = QColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 130)
        for card in self.page_widgets:
            card.highlight_color = qc

    def set_draw_style(self, rgb: Tuple[float, float, float], width: float):
        qc = QColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        for card in self.page_widgets:
            card.draw_color = qc
            card.draw_width = width

    def scroll_to_page(self, page_number: int):
        idx = page_number - 1
        if 0 <= idx < len(self.page_widgets):
            card = self.page_widgets[idx]
            self.ensureWidgetVisible(card, 0, 10)
            self.page_scrolled_to.emit(page_number)

    def _on_scroll(self, value: int):
        viewport_center_y = self.viewport().rect().center().y()
        for idx, card in enumerate(self.page_widgets):
            top_in_viewport = card.mapTo(self.viewport(), QPoint(0, 0)).y()
            bottom_in_viewport = top_in_viewport + card.height()
            if top_in_viewport <= viewport_center_y <= bottom_in_viewport:
                self.page_scrolled_to.emit(idx + 1)
                break

        # Reposition floating toolbar while scrolling if visible
        active = self.get_selected_block()
        if active and self.floating_text_toolbar.isVisible():
            self._reposition_floating_toolbar(active[0], active[1])

    # Panning Hand Tool
    def mousePressEvent(self, event: QMouseEvent):
        if self.current_tool == "hand" and event.button() == Qt.LeftButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning and event.button() == Qt.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def update_theme(self):
        if hasattr(self, "floating_text_toolbar"):
            self.floating_text_toolbar.update_theme()
        if hasattr(self, "editing_tip_banner"):
            self.editing_tip_banner.update_theme()
        for card in self.page_widgets:
            card.update()
