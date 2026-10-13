"""
CommentsPanel — Phase 5 Figma Implementation
Threaded comments side panel matching Figma frame "Comments panel" #3:13075.

Layout (268 px, left border 1px #D9D9D9, padding 22px 16px 18px):
  ┌─ Tool heading ──────────────────────────────────────────┐
  │  [Comments]  SemiBold 18px              [✕]            │
  │  [3 comments] SemiBold 12px    [filter] [sort]         │
  ├─ Add comment ───────────────────────────────────────────┤
  │  [ Add a comment…                          ] 66px       │
  ├─ Page grouping ─────────────────────────────────────────┤
  │  ▼ Page 1                                              │
  ├─ Comment card (#EAF3FF / white in dark) ────────────────┤
  │  [JL]  Jamie Lee  ·  Today, 10:24 AM    [⋯]           │
  │  Comment text (multi-line)                             │
  │  [Reply]                         [Page 1]             │
  └─────────────────────────────────────────────────────────┘
  <flexible space>
  ─ divider ─
  ┌─ Review sharing CTA ────────────────────────────────────┐
  │  Keep feedback together. Invite your team…             │
  │  [👥 Share for review] outline pill, fill width        │
  └─────────────────────────────────────────────────────────┘

Annotation sync: Comments are drawn from PDFDocument.get_all_annotations()
and serialized as ISO 32000 text annotations via add_text_annotation().
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QTextEdit, QScrollArea, QFrame, QPushButton, QSizePolicy, QMenu,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QAction
from PySide6.QtSvgWidgets import QSvgWidget

from pyacrobat.ui.styles import ThemeManager

# ─── Icon helper ────────────────────────────────────────────────────────────

_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "icons")


def _svg_icon(name: str, size: int = 16) -> QSvgWidget:
    """Return a themed QSvgWidget for a named icon."""
    path = os.path.join(_ICONS_DIR, f"{name}.svg")
    w = QSvgWidget(path)
    w.setFixedSize(size, size)
    return w


# ─── Avatar circle ──────────────────────────────────────────────────────────

class _AvatarWidget(QWidget):
    """28×28 circle with 2-letter initials, matching Figma EL-9d79d57e."""

    def __init__(self, initials: str = "?", bg: str = "#E8EFED", fg: str = "#203C42", parent=None):
        super().__init__(parent)
        self.initials = initials[:2].upper()
        self.bg_color = QColor(bg)
        self.fg_color = QColor(fg)
        self.setFixedSize(28, 28)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(self.bg_color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 28, 28)

        font = QFont("Inter", 10, QFont.Bold)
        p.setFont(font)
        p.setPen(self.fg_color)
        p.drawText(self.rect(), Qt.AlignCenter, self.initials)
        p.end()

    def update_colors(self, bg: str, fg: str):
        self.bg_color = QColor(bg)
        self.fg_color = QColor(fg)
        self.update()


# ─── Single Comment Card ─────────────────────────────────────────────────────

class CommentCard(QFrame):
    """
    One comment card matching Figma #3:13090.
    Active (first) comment: #EAF3FF bg + 1px #1473E6 border.
    Other comments: #FFFFFF bg + 1px #D9D9D9 border.
    Resolved comment: shows "✓ Resolved" in green.
    """

    reply_clicked   = Signal(str)   # author
    resolve_clicked = Signal()
    delete_clicked  = Signal()

    def __init__(
        self,
        author: str,
        timestamp: str,
        text: str,
        page: int = 1,
        resolved: bool = False,
        active: bool = True,
        xref: Optional[int] = None,
        parent=None
    ):
        super().__init__(parent)
        self.author = author
        self.page_num = page
        self.xref_val = xref
        self.is_resolved = resolved
        self.active = active
        self._build_ui(author, timestamp, text, page, resolved, active)

    def _build_ui(self, author, timestamp, text, page, resolved, active):
        self.setObjectName("commentCardActive" if active else "commentCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # ── Author row ──────────────────────────────────────────────────
        author_row = QHBoxLayout()
        author_row.setSpacing(9)

        initials = "".join(w[0] for w in author.split()[:2]).upper() if author.strip() else "?"
        self.avatar = _AvatarWidget(initials)
        author_row.addWidget(self.avatar)

        details_col = QVBoxLayout()
        details_col.setSpacing(1)
        self.lbl_author = QLabel(author)
        self.lbl_author.setObjectName("commentAuthorName")
        details_col.addWidget(self.lbl_author)

        self.lbl_time = QLabel(timestamp)
        self.lbl_time.setObjectName("commentTimestamp")
        details_col.addWidget(self.lbl_time)
        author_row.addLayout(details_col)
        author_row.addStretch()

        btn_menu = QToolButton()
        btn_menu.setObjectName("commentMenuBtn")
        btn_menu.setFixedSize(20, 20)
        btn_menu.setIcon(_svg_icon("ellipsis", 16).grab().toImage() if False else btn_menu.icon())  # styled via CSS
        btn_menu.setText("⋯")
        btn_menu.setCursor(Qt.PointingHandCursor)

        menu = QMenu(btn_menu)
        act_resolve = QAction("✓ Mark as resolved" if not resolved else "Reopen", btn_menu)
        act_resolve.triggered.connect(self.resolve_clicked.emit)
        act_delete = QAction("🗑 Delete", btn_menu)
        act_delete.triggered.connect(self.delete_clicked.emit)
        menu.addAction(act_resolve)
        menu.addSeparator()
        menu.addAction(act_delete)
        btn_menu.setMenu(menu)
        btn_menu.setPopupMode(QToolButton.InstantPopup)
        author_row.addWidget(btn_menu)

        layout.addLayout(author_row)

        # ── Comment text ────────────────────────────────────────────────
        self.lbl_text = QLabel(text)
        self.lbl_text.setObjectName("commentBody")
        self.lbl_text.setWordWrap(True)
        layout.addWidget(self.lbl_text)

        # ── Actions row ─────────────────────────────────────────────────
        actions_row = QHBoxLayout()

        if resolved:
            lbl_resolved = QLabel("✓ Resolved")
            lbl_resolved.setObjectName("commentResolved")
            actions_row.addWidget(lbl_resolved)
        else:
            btn_reply = QToolButton()
            btn_reply.setText("Reply")
            btn_reply.setObjectName("commentReplyBtn")
            btn_reply.setCursor(Qt.PointingHandCursor)
            btn_reply.clicked.connect(lambda: self.reply_clicked.emit(author))
            actions_row.addWidget(btn_reply)

        actions_row.addStretch()

        lbl_page = QLabel(f"Page {page}")
        lbl_page.setObjectName("commentPageLabel")
        actions_row.addWidget(lbl_page)

        layout.addLayout(actions_row)

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        if self.active:
            self.setStyleSheet(f"""
                QFrame#commentCardActive {{
                    background: {tokens.accent_subtle};
                    border: 1px solid {tokens.accent};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#commentCard {{
                    background: {tokens.surface_raised};
                    border: 1px solid {tokens.border};
                    border-radius: 6px;
                }}
            """)
        self.avatar.update_colors(
            "#E8EFED" if tokens.name == "light" else "#2A4040",
            "#203C42" if tokens.name == "light" else "#8CBCB8"
        )


# ─── Page Grouping Header ────────────────────────────────────────────────────

class PageGroupHeader(QWidget):
    """Accordion row: ▼ Page N  (collapsible in future)."""

    def __init__(self, page_num: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._chevron = _svg_icon("chevron-down", 13)
        layout.addWidget(self._chevron)

        self.lbl = QLabel(f"Page {page_num}")
        self.lbl.setObjectName("pageGroupLabel")
        layout.addWidget(self.lbl)
        layout.addStretch()


# ─── Comments Panel ──────────────────────────────────────────────────────────

class CommentsPanel(QWidget):
    """
    Full-height threaded comments panel (268 px).
    Matches Figma "Comments panel" #3:13075.

    Signals
    -------
    comment_added(page_num, text)   – user typed in Add-comment box and submitted
    comment_deleted(page_num, xref) – user deleted a comment card
    comment_replied(page_num, text) – user replied to a thread
    close_requested()               – user clicked ✕ in panel header
    page_jump_requested(page_num)   – user clicked a page badge on a comment card
    """

    comment_added    = Signal(int, str)   # page_num, text
    comment_deleted  = Signal(int, int)   # page_num (1-based), xref
    comment_replied  = Signal(int, str)   # page_num, reply_text
    close_requested  = Signal()
    page_jump_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("commentsPanel")
        self.setFixedWidth(268)
        self._current_page = 1
        self._cards: List[CommentCard] = []
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Scroll area ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("commentsPanelScroll")

        self._content = QWidget()
        self._content.setObjectName("commentsPanelContent")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(16, 22, 16, 18)
        self._layout.setSpacing(15)
        self._layout.setAlignment(Qt.AlignTop)

        # ── Section 1: Tool heading ──────────────────────────────────────
        heading_col = QVBoxLayout()
        heading_col.setSpacing(10)

        # Title row: "Comments" + ✕
        title_row = QHBoxLayout()
        self.lbl_title = QLabel("Comments")
        self.lbl_title.setObjectName("commentsPanelTitle")
        title_row.addWidget(self.lbl_title)
        title_row.addStretch()
        btn_close = QToolButton()
        btn_close.setObjectName("commentsPanelCloseBtn")
        btn_close.setFixedSize(20, 20)
        btn_close.setText("✕")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close_requested.emit)
        title_row.addWidget(btn_close)
        heading_col.addLayout(title_row)

        # Filters row: "N comments" + filter + sort icons
        filter_row = QHBoxLayout()
        self.lbl_count = QLabel("0 comments")
        self.lbl_count.setObjectName("commentsCount")
        filter_row.addWidget(self.lbl_count)
        filter_row.addStretch()

        self._icon_filter = _svg_icon("list-filter", 17)
        self._icon_filter.setCursor(Qt.PointingHandCursor)
        self._icon_filter.setToolTip("Filter comments")
        filter_row.addWidget(self._icon_filter)

        self._icon_sort = _svg_icon("arrow-down-wide-narrow", 17)
        self._icon_sort.setCursor(Qt.PointingHandCursor)
        self._icon_sort.setToolTip("Sort comments")
        filter_row.addWidget(self._icon_sort)
        heading_col.addLayout(filter_row)

        self._layout.addLayout(heading_col)

        # ── Section 2: Add comment ───────────────────────────────────────
        self.add_comment_box = QTextEdit()
        self.add_comment_box.setObjectName("addCommentBox")
        self.add_comment_box.setPlaceholderText("Add a comment…")
        self.add_comment_box.setFixedHeight(66)
        self.add_comment_box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._layout.addWidget(self.add_comment_box)

        # Submit button (appears below the text box)
        submit_row = QHBoxLayout()
        submit_row.addStretch()
        self.btn_submit = QPushButton("Post")
        self.btn_submit.setObjectName("commentSubmitBtn")
        self.btn_submit.setFixedHeight(28)
        self.btn_submit.clicked.connect(self._on_submit_comment)
        submit_row.addWidget(self.btn_submit)
        self._layout.addLayout(submit_row)

        # ── Section 3: Page grouping header ─────────────────────────────
        self._page_group_header = PageGroupHeader(1)
        self._layout.addWidget(self._page_group_header)

        # ── Section 4: Cards container ──────────────────────────────────
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._layout.addWidget(self._cards_container)

        # ── Flexible space ───────────────────────────────────────────────
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(spacer)

        # ── Divider ──────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("commentsDivider")
        self._layout.addWidget(divider)

        # ── Section 5: Review sharing CTA ───────────────────────────────
        cta_col = QVBoxLayout()
        cta_col.setSpacing(10)

        self.lbl_cta_text = QLabel("Keep feedback together. Invite your team to review this PDF.")
        self.lbl_cta_text.setObjectName("commentsCTALabel")
        self.lbl_cta_text.setWordWrap(True)
        cta_col.addWidget(self.lbl_cta_text)

        self.btn_share = QPushButton("  Share for review")
        self.btn_share.setObjectName("shareForReviewBtn")
        self.btn_share.setFixedHeight(34)
        self.btn_share.setCursor(Qt.PointingHandCursor)
        cta_col.addLayout(self._make_share_btn_row())

        self._layout.addLayout(cta_col)

        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def _make_share_btn_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        users_icon = _svg_icon("users", 16)
        self.btn_share = QPushButton("Share for review")
        self.btn_share.setObjectName("shareForReviewBtn")
        self.btn_share.setFixedHeight(34)
        self.btn_share.setCursor(Qt.PointingHandCursor)
        # Stub – no backend needed per roadmap
        self.btn_share.clicked.connect(lambda: QMessageBox.information(
            self, "Share for Review",
            "Review sharing functionality is not yet implemented."
        ))
        row.addWidget(users_icon)
        row.addWidget(self.btn_share)
        return row

    # ── Public API ──────────────────────────────────────────────────────────

    def set_current_page(self, page_num: int):
        """Track which page is active so new comments attach to correct page."""
        self._current_page = page_num

    def populate_from_annotations(self, annotations: List[Dict[str, Any]]):
        """
        Rebuild the card list from the annotation list produced by
        PDFDocument.get_all_annotations().  Each item is:
          { "page": int, "type": str, "content": str, "xref": int }
        Only Text/Note annotations become comment cards.
        """
        # Clear old cards
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Filter to Note/Text annotations only
        notes = [a for a in annotations if a.get("type", "").lower() in ("text", "note", "freetext")]

        self.lbl_count.setText(f"{len(notes)} comment{'s' if len(notes) != 1 else ''}")

        # Group by page (show first page group for now)
        if notes:
            first_page = notes[0]["page"]
            self._page_group_header.lbl.setText(f"Page {first_page}")
            self._page_group_header.setVisible(True)
        else:
            self._page_group_header.setVisible(bool(notes))

        for i, note in enumerate(notes):
            author   = note.get("author") or "Reviewer"
            content  = note.get("content") or ""
            page_num = note.get("page", 1)
            xref     = note.get("xref")
            ts       = _format_timestamp(note.get("created") or note.get("modified"))
            resolved = note.get("flags", 0) & 0x4  # PDF /F Locked == resolved

            card = CommentCard(
                author=author,
                timestamp=ts,
                text=content,
                page=page_num,
                resolved=bool(resolved),
                active=(i == 0),
                xref=xref,
            )
            card.reply_clicked.connect(self._on_reply)
            card.resolve_clicked.connect(lambda _c=card: self._on_resolve(_c))
            card.delete_clicked.connect(lambda _c=card: self._on_delete(_c))
            card.update_theme()
            self._cards.append(card)
            self._cards_layout.addWidget(card)

    def update_theme(self):
        tokens = ThemeManager.get_tokens()
        # Panel background + left border
        self.setStyleSheet(f"""
            QWidget#commentsPanel {{
                background: {tokens.surface_raised};
                border-left: 1px solid {tokens.border};
            }}
            QWidget#commentsPanelContent {{
                background: {tokens.surface_raised};
            }}
            QLabel#commentsPanelTitle {{
                font-family: Inter;
                font-weight: 600;
                font-size: 18px;
                color: {tokens.text};
            }}
            QToolButton#commentsPanelCloseBtn {{
                background: transparent;
                border: none;
                color: {tokens.text_muted};
                font-size: 13px;
            }}
            QToolButton#commentsPanelCloseBtn:hover {{
                color: {tokens.text};
            }}
            QLabel#commentsCount {{
                font-family: Inter;
                font-weight: 600;
                font-size: 12px;
                color: {tokens.text};
            }}
            QTextEdit#addCommentBox {{
                background: {tokens.surface_raised};
                border: 1px solid {tokens.border};
                border-radius: 6px;
                padding: 10px 12px;
                font-family: Inter;
                font-size: 12px;
                color: {tokens.text};
            }}
            QPushButton#commentSubmitBtn {{
                background: {tokens.accent};
                color: {tokens.text_on_accent};
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-family: Inter;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#commentSubmitBtn:hover {{
                background: {tokens.accent_hover};
            }}
            QLabel#pageGroupLabel {{
                font-family: Inter;
                font-size: 11px;
                color: {tokens.text_muted};
            }}
            QLabel#commentAuthorName {{
                font-family: Inter;
                font-weight: 600;
                font-size: 11px;
                color: {tokens.text};
            }}
            QLabel#commentTimestamp {{
                font-family: Inter;
                font-size: 9px;
                color: {tokens.text_muted};
            }}
            QLabel#commentBody {{
                font-family: Inter;
                font-size: 12px;
                color: {tokens.text};
            }}
            QToolButton#commentReplyBtn {{
                background: transparent;
                border: none;
                color: {tokens.accent};
                font-family: Inter;
                font-size: 11px;
                padding: 0;
            }}
            QToolButton#commentReplyBtn:hover {{
                text-decoration: underline;
            }}
            QLabel#commentResolved {{
                font-family: Inter;
                font-size: 11px;
                color: #268E6C;
            }}
            QLabel#commentPageLabel {{
                font-family: Inter;
                font-size: 10px;
                color: {tokens.text_muted};
            }}
            QToolButton#commentMenuBtn {{
                background: transparent;
                border: none;
                color: {tokens.text_muted};
                font-size: 13px;
                padding: 0;
            }}
            QToolButton#commentMenuBtn:hover {{
                color: {tokens.text};
            }}
            QFrame#commentsDivider {{
                color: {tokens.border};
                max-height: 1px;
            }}
            QLabel#commentsCTALabel {{
                font-family: Inter;
                font-size: 11px;
                color: {tokens.text_muted};
            }}
            QPushButton#shareForReviewBtn {{
                background: {tokens.surface_raised};
                border: 1px solid {tokens.border};
                border-radius: 17px;
                padding: 0 14px;
                font-family: Inter;
                font-weight: 600;
                font-size: 13px;
                color: {tokens.text};
            }}
            QPushButton#shareForReviewBtn:hover {{
                background: {tokens.surface};
            }}
            QScrollArea#commentsPanelScroll {{
                border: none;
                background: transparent;
            }}
        """)

        # Refresh all cards
        for card in self._cards:
            card.update_theme()

    # ── Internal slots ──────────────────────────────────────────────────────

    def _on_submit_comment(self):
        text = self.add_comment_box.toPlainText().strip()
        if not text:
            return
        self.comment_added.emit(self._current_page, text)
        self.add_comment_box.clear()

    def _on_reply(self, author: str):
        self.add_comment_box.setFocus()
        self.add_comment_box.setPlainText(f"@{author.split()[0]} ")
        cursor = self.add_comment_box.textCursor()
        cursor.movePosition(cursor.End)
        self.add_comment_box.setTextCursor(cursor)

    def _on_resolve(self, card: CommentCard):
        # Toggle resolved state – in future sync with annotation flags
        pass

    def _on_delete(self, card: CommentCard):
        if card.xref_val is not None:
            self.comment_deleted.emit(card.page_num, card.xref_val)


# ─── Timestamp formatter ─────────────────────────────────────────────────────

def _format_timestamp(ts) -> str:
    """Convert a PDF date string or datetime to a human-readable label."""
    if ts is None:
        return "Just now"
    try:
        if isinstance(ts, str) and ts.startswith("D:"):
            # PDF date format: D:YYYYMMDDHHmmSS
            ts = ts[2:16]
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        elif isinstance(ts, datetime):
            dt = ts
        else:
            return str(ts)
        now = datetime.now()
        delta = now - dt
        if delta.days == 0:
            return f"Today, {dt.strftime('%I:%M %p').lstrip('0')}"
        elif delta.days == 1:
            return f"Yesterday, {dt.strftime('%I:%M %p').lstrip('0')}"
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return "Unknown"
