"""
Organize Pages Interactive Workstation (Adobe Acrobat Pro Alignment)
Features fluid, real-time card shifting where pages physically glide aside when dragged,
snap cleanly into place, and support multi-page reordering, rotation, and deletion.
"""

from typing import List, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QFrame, QMessageBox, QFileDialog, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, Signal, QPoint, QRect, QPropertyAnimation, QEasingCurve, QSize
)
from PySide6.QtGui import (
    QPixmap, QImage, QColor, QMouseEvent, QPainter, QPen
)

from pyacrobat.ui.styles import ThemeManager


class PageCardWidget(QFrame):
    """
    Individual Page Card displaying thumbnail, page badge, and selection outline.
    """

    clicked = Signal(object)          # (PageCardWidget)
    double_clicked = Signal(object)   # (PageCardWidget)
    rotate_requested = Signal(object) # (PageCardWidget)
    delete_requested = Signal(object) # (PageCardWidget)

    CARD_WIDTH = 190
    CARD_HEIGHT = 265

    def __init__(self, page_index: int, thumbnail_pixmap: Any, parent=None):
        super().__init__(parent)
        self.original_page_index = page_index  # 0-based original document index
        self.is_selected = False

        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setObjectName("organizerPageCard")
        self.init_ui(thumbnail_pixmap)

    def init_ui(self, pixmap_data: Any):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Page Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(170, 215)
        tokens = ThemeManager.get_tokens()
        self.thumb_label.setStyleSheet(
            f"background-color: #FFFFFF; border: 1px solid {tokens.border}; border-radius: 4px;"
        )

        if pixmap_data:
            img = QImage(
                pixmap_data.samples, pixmap_data.width, pixmap_data.height,
                pixmap_data.stride, QImage.Format_RGB888
            )
            qpix = QPixmap.fromImage(img).scaled(
                170, 215, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.thumb_label.setPixmap(qpix)

        layout.addWidget(self.thumb_label)

        # 2. Bottom Label: "Page 1"
        self.title_label = QLabel(f"Page {self.original_page_index + 1}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("drawerHeaderTitle")
        layout.addWidget(self.title_label)

        # Drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(14)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(3)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(self.shadow)

        self.update_style()

    def set_page_number(self, num: int):
        self.title_label.setText(f"Page {num}")

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def set_dragging_visual(self, dragging: bool):
        tokens = ThemeManager.get_tokens()
        if dragging:
            self.shadow.setBlurRadius(28)
            self.shadow.setYOffset(10)
            self.shadow.setColor(QColor(20, 115, 230, 160))  # Acrobat Blue glow
            self.setStyleSheet(f"""
                QFrame#organizerPageCard {{
                    background-color: {tokens.surface_raised};
                    border: 2px solid {tokens.accent};
                    border-radius: 8px;
                }}
            """)
        else:
            self.shadow.setBlurRadius(14)
            self.shadow.setYOffset(3)
            self.shadow.setColor(QColor(0, 0, 0, 100))
            self.update_style()

    def update_style(self):
        tokens = ThemeManager.get_tokens()
        self.thumb_label.setStyleSheet(
            f"background-color: #FFFFFF; border: 1px solid {tokens.border}; border-radius: 4px;"
        )
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame#organizerPageCard {{
                    background-color: {tokens.surface_raised};
                    border: 2px solid {tokens.accent};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#organizerPageCard {{
                    background-color: {tokens.surface};
                    border: 1px solid {tokens.border};
                    border-radius: 8px;
                }}
                QFrame#organizerPageCard:hover {{
                    border: 1px solid {tokens.border_strong};
                    background-color: {tokens.surface_raised};
                }}
            """)


class InteractivePageCanvas(QWidget):
    """
    Fluid canvas where page cards slide aside in real time when you drag across slots.
    """

    order_rearranged = Signal(list)  # Emits list of original page indices
    page_double_clicked = Signal(int)
    selection_changed = Signal()

    CARD_W = PageCardWidget.CARD_WIDTH
    CARD_H = PageCardWidget.CARD_HEIGHT
    SPACING = 22
    MARGIN = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: List[PageCardWidget] = []
        self.animations: List[QPropertyAnimation] = []

        # Drag state
        self.drag_card: Optional[PageCardWidget] = None
        self.drag_start_pos: QPoint = QPoint()
        self.drag_offset: QPoint = QPoint()
        self.is_dragging: bool = False

        self.setObjectName("organizerCanvasArea")
        self.setMouseTracking(True)

    def update_theme(self):
        for c in self.cards:
            c.update_style()

    def set_cards(self, thumbnails: List[Any]):
        """Populates cards from rendered pixmaps."""
        # Clean up old cards
        for c in self.cards:
            c.setParent(None)
            c.deleteLater()
        self.cards.clear()
        self.animations.clear()

        for idx, pix in enumerate(thumbnails):
            card = PageCardWidget(page_index=idx, thumbnail_pixmap=pix, parent=self)
            card.show()
            self.cards.append(card)

        if self.cards:
            self.cards[0].set_selected(True)

        self.relayout_cards(animate=False)
        self.selection_changed.emit()

    def calculate_columns(self) -> int:
        available_w = max(self.CARD_W + 2 * self.MARGIN, self.width())
        cols = (available_w - 2 * self.MARGIN + self.SPACING) // (self.CARD_W + self.SPACING)
        return max(1, int(cols))

    def calculate_slot_pos(self, slot_idx: int) -> QPoint:
        cols = self.calculate_columns()
        col = slot_idx % cols
        row = slot_idx // cols
        x = self.MARGIN + col * (self.CARD_W + self.SPACING)
        y = self.MARGIN + row * (self.CARD_H + self.SPACING)
        return QPoint(int(x), int(y))

    def relayout_cards(self, animate: bool = True):
        """Positions all cards at their current slot positions, smoothly sliding if animated."""
        cols = self.calculate_columns()
        total_rows = (len(self.cards) + cols - 1) // cols if self.cards else 1
        canvas_h = self.MARGIN * 2 + total_rows * (self.CARD_H + self.SPACING)
        self.setFixedHeight(max(500, int(canvas_h)))

        # Stop previous animations
        for a in self.animations:
            a.stop()
        self.animations.clear()

        for i, card in enumerate(self.cards):
            target_pos = self.calculate_slot_pos(i)
            if card == self.drag_card:
                continue  # Dragged card follows cursor directly

            if animate and card.isVisible() and card.pos() != target_pos:
                anim = QPropertyAnimation(card, b"pos", self)
                anim.setDuration(160)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.setEndValue(target_pos)
                anim.start()
                self.animations.append(anim)
            else:
                card.move(target_pos)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_cards(animate=False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            card = self._card_at_pos(pos)
            if card:
                self.drag_card = card
                self.drag_start_pos = pos
                self.drag_offset = pos - card.pos()
                self.is_dragging = False

                # Update selection
                for c in self.cards:
                    c.set_selected(c == card)
                self.selection_changed.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_card and event.buttons() & Qt.LeftButton:
            pos = event.position().toPoint()
            if not self.is_dragging:
                # Require 6px movement threshold before initiating drag
                if (pos - self.drag_start_pos).manhattanLength() > 6:
                    self.is_dragging = True
                    self.drag_card.raise_()
                    self.drag_card.set_dragging_visual(True)

            if self.is_dragging:
                # 1. Dragged card directly follows mouse cursor
                new_pos = pos - self.drag_offset
                self.drag_card.move(new_pos)

                # 2. Determine target slot under dragged card center
                center = self.drag_card.geometry().center()
                target_slot = self._calculate_target_slot(center)

                current_slot = self.cards.index(self.drag_card)
                if target_slot != current_slot:
                    # 3. REARRANGE CARDS IN REAL TIME & GLIDE ASIDE
                    self.cards.remove(self.drag_card)
                    self.cards.insert(target_slot, self.drag_card)
                    self.relayout_cards(animate=True)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.drag_card:
            if self.is_dragging:
                self.is_dragging = False
                self.drag_card.set_dragging_visual(False)

                # Smoothly snap dragged card to its final slot position
                current_slot = self.cards.index(self.drag_card)
                target_pos = self.calculate_slot_pos(current_slot)

                snap_anim = QPropertyAnimation(self.drag_card, b"pos", self)
                snap_anim.setDuration(120)
                snap_anim.setEasingCurve(QEasingCurve.OutCubic)
                snap_anim.setEndValue(target_pos)
                snap_anim.start()
                self.animations.append(snap_anim)

                # Update page title badges
                for i, c in enumerate(self.cards):
                    c.set_page_number(i + 1)

                # Emit reorder permutation
                new_order = [c.original_page_index for c in self.cards]
                for i, c in enumerate(self.cards):
                    c.original_page_index = i

                self.order_rearranged.emit(new_order)
            else:
                self.drag_card.set_dragging_visual(False)

            self.drag_card = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        card = self._card_at_pos(pos)
        if card:
            slot = self.cards.index(card)
            self.page_double_clicked.emit(slot + 1)
        super().mouseDoubleClickEvent(event)

    def _card_at_pos(self, pos: QPoint) -> Optional[PageCardWidget]:
        for c in reversed(self.cards):  # Top-most first
            if c.geometry().contains(pos):
                return c
        return None

    def _calculate_target_slot(self, center: QPoint) -> int:
        cols = self.calculate_columns()
        col = max(0, min(cols - 1, (center.x() - self.MARGIN + self.SPACING // 2) // (self.CARD_W + self.SPACING)))
        row = max(0, (center.y() - self.MARGIN + self.SPACING // 2) // (self.CARD_H + self.SPACING))
        slot = int(row * cols + col)
        return max(0, min(len(self.cards) - 1, slot))

    def move_selected(self, delta: int):
        """Moves selected card left (-1) or right (+1)."""
        sel_card = next((c for c in self.cards if c.is_selected), None)
        if not sel_card:
            return
        idx = self.cards.index(sel_card)
        new_idx = idx + delta
        if 0 <= new_idx < len(self.cards):
            self.cards.remove(sel_card)
            self.cards.insert(new_idx, sel_card)
            self.relayout_cards(animate=True)

            for i, c in enumerate(self.cards):
                c.set_page_number(i + 1)

            new_order = [c.original_page_index for c in self.cards]
            for i, c in enumerate(self.cards):
                c.original_page_index = i

            self.order_rearranged.emit(new_order)


class OrganizerGridWidget(QWidget):
    """Full-screen visual workstation for managing document pages."""

    back_to_reading_requested = Signal()
    page_double_clicked = Signal(int)
    reorder_requested = Signal(list)
    rotate_requested = Signal(list, int)
    delete_requested = Signal(list)
    insert_blank_requested = Signal(int)
    duplicate_requested = Signal(list)
    merge_requested = Signal()
    extract_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top Action Ribbon
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("organizerToolbar")
        tb_layout = QHBoxLayout(toolbar_frame)
        tb_layout.setContentsMargins(12, 6, 12, 6)
        tb_layout.setSpacing(8)

        btn_back = QToolButton()
        btn_back.setText("← Back to Document")
        btn_back.setObjectName("pillButton")
        btn_back.clicked.connect(self.back_to_reading_requested.emit)
        tb_layout.addWidget(btn_back)

        tb_layout.addWidget(self._create_divider())

        # Page Reordering Buttons
        btn_move_left = QToolButton()
        btn_move_left.setText("◀ Move Left")
        btn_move_left.setToolTip("Move Selected Page Left")
        btn_move_left.clicked.connect(lambda: self.canvas.move_selected(-1))
        tb_layout.addWidget(btn_move_left)

        btn_move_right = QToolButton()
        btn_move_right.setText("Move Right ▶")
        btn_move_right.setToolTip("Move Selected Page Right")
        btn_move_right.clicked.connect(lambda: self.canvas.move_selected(1))
        tb_layout.addWidget(btn_move_right)

        tb_layout.addWidget(self._create_divider())

        # Transformations
        btn_rot_cw = QToolButton()
        btn_rot_cw.setText("↻ Rotate Right")
        btn_rot_cw.clicked.connect(lambda: self._on_rotate(90))
        tb_layout.addWidget(btn_rot_cw)

        btn_rot_ccw = QToolButton()
        btn_rot_ccw.setText("↺ Rotate Left")
        btn_rot_ccw.clicked.connect(lambda: self._on_rotate(-90))
        tb_layout.addWidget(btn_rot_ccw)

        btn_delete = QToolButton()
        btn_delete.setText("🗑 Delete")
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(self._on_delete)
        tb_layout.addWidget(btn_delete)

        tb_layout.addWidget(self._create_divider())

        btn_insert = QToolButton()
        btn_insert.setText("➕ Insert Blank")
        btn_insert.clicked.connect(self._on_insert_blank)
        tb_layout.addWidget(btn_insert)

        btn_duplicate = QToolButton()
        btn_duplicate.setText("📋 Duplicate")
        btn_duplicate.clicked.connect(self._on_duplicate)
        tb_layout.addWidget(btn_duplicate)

        tb_layout.addWidget(self._create_divider())

        btn_merge = QToolButton()
        btn_merge.setText("🔀 Merge PDF...")
        btn_merge.clicked.connect(self.merge_requested.emit)
        tb_layout.addWidget(btn_merge)

        btn_extract = QToolButton()
        btn_extract.setText("✂ Extract Pages...")
        btn_extract.clicked.connect(self._on_extract)
        tb_layout.addWidget(btn_extract)

        tb_layout.addStretch()

        lbl_info = QLabel("Drag & drop to reorder — other pages slide aside smoothly | Double-click to view")
        lbl_info.setObjectName("subtleLabel")
        tb_layout.addWidget(lbl_info)

        layout.addWidget(toolbar_frame)

        # 2. Scroll Area containing Interactive Page Canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("organizerCanvasArea")

        self.canvas = InteractivePageCanvas(self.scroll_area)
        self.canvas.order_rearranged.connect(self.reorder_requested.emit)
        self.canvas.page_double_clicked.connect(self.page_double_clicked.emit)

        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area)

    def update_theme(self):
        """Refreshes all page cards to match active theme tokens."""
        self.canvas.update_theme()

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("dividerLine")
        return line

    def populate_grid(self, thumbnails: List[Any]):
        self.canvas.set_cards(thumbnails)

    def get_selected_indices(self) -> List[int]:
        for idx, card in enumerate(self.canvas.cards):
            if card.is_selected:
                return [idx]
        return []

    def _on_rotate(self, degrees: int):
        sel = self.get_selected_indices()
        if sel:
            self.rotate_requested.emit(sel, degrees)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select a page to rotate.")

    def _on_delete(self):
        sel = self.get_selected_indices()
        if not sel:
            QMessageBox.information(self, "No Page Selected", "Please select a page to delete.")
            return

        if len(self.canvas.cards) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "A document must contain at least one page.")
            return

        page_num = sel[0] + 1
        ret = QMessageBox.question(
            self,
            "Delete Page",
            f"Are you sure you want to permanently delete Page {page_num}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.delete_requested.emit(sel)

    def _on_insert_blank(self):
        sel = self.get_selected_indices()
        insert_idx = sel[-1] + 1 if sel else len(self.canvas.cards)
        self.insert_blank_requested.emit(insert_idx)

    def _on_duplicate(self):
        sel = self.get_selected_indices()
        if sel:
            self.duplicate_requested.emit(sel)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select a page to duplicate.")

    def _on_extract(self):
        sel = self.get_selected_indices()
        if sel:
            self.extract_requested.emit(sel)
        else:
            QMessageBox.information(self, "No Page Selected", "Please select a page to extract.")
