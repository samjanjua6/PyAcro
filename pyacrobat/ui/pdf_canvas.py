"""
Interactive PDF Canvas Viewport with High-DPI Razor-Sharp Rendering
Handles dynamic device pixel ratio, text highlight selection, and freehand drawing.
"""

from typing import List, Tuple, Optional
import pymupdf as fitz

from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QPointF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QMouseEvent, QPaintEvent
)


class PageCardWidget(QFrame):
    """
    Interactive container for a single rendered PDF page.
    Renders with native screen pixel density (High-DPI supersampling) for razor-sharp text.
    """

    highlight_created = Signal(int, object)        # (page_idx, fitz.Rect)
    ink_drawn = Signal(int, list)                  # (page_idx, list of (x, y) tuples)
    note_created = Signal(int, tuple, str)         # (page_idx, (x, y), comment_text)

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.scale: float = 1.0
        self.dpr_factor: float = 1.0
        self.current_tool: str = "select"
        self.base_pixmap: Optional[QPixmap] = None

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

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 1. Draw base High-DPI rasterized PDF page
        if self.base_pixmap and not self.base_pixmap.isNull():
            painter.drawPixmap(0, 0, self.base_pixmap)
        else:
            painter.fillRect(self.rect(), Qt.white)

        # 2. Draw in-progress freehand stroke
        if self.is_drawing and len(self.current_stroke) > 1:
            pen = QPen(self.draw_color, self.draw_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            for i in range(len(self.current_stroke) - 1):
                painter.drawLine(self.current_stroke[i], self.current_stroke[i + 1])

        # 3. Draw in-progress highlight selection rectangle
        if self.is_highlighting and self.highlight_start and self.highlight_current:
            rect = QRectF(self.highlight_start, self.highlight_current).normalized()
            painter.fillRect(rect, self.highlight_color)
            painter.setPen(QPen(QColor(self.highlight_color.rgb()), 1, Qt.DashLine))
            painter.drawRect(rect)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = event.position()
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


class PDFCanvas(QScrollArea):
    """Continuous vertical scrolling canvas for PDF document pages."""

    page_scrolled_to = Signal(int)

    highlight_requested = Signal(int, object)
    ink_requested = Signal(int, list)
    note_requested = Signal(int, tuple, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_widgets: List[PageCardWidget] = []
        self.current_zoom: float = 1.0
        self.current_tool: str = "select"

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

    def clear(self):
        for w in self.page_widgets:
            w.setParent(None)
            w.deleteLater()
        self.page_widgets.clear()

    def setup_pages(self, page_count: int):
        self.clear()
        for i in range(page_count):
            card = PageCardWidget(page_index=i, parent=self.container)
            card.current_tool = self.current_tool
            card.highlight_created.connect(self.highlight_requested.emit)
            card.ink_drawn.connect(self.ink_requested.emit)
            card.note_created.connect(self.note_requested.emit)
            self.container_layout.addWidget(card)
            self.page_widgets.append(card)

    def update_page_pixmap(self, page_index: int, qimage: QImage, dpr_factor: float, scale: float):
        if 0 <= page_index < len(self.page_widgets):
            self.page_widgets[page_index].set_page_image(qimage, dpr_factor, scale)

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        for card in self.page_widgets:
            card.current_tool = tool_name
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
