"""
Asynchronous High-DPI Page Rasterization Engine for Spectra PDF.
Offloads PyMuPDF page rasterization to background worker threads using QThreadPool,
keeping the PySide6 UI thread silky-smooth (60fps) during scrolling and zooming.
Supports job cancellation, priority scheduling, and thread-safe PyMuPDF rendering.
"""

from typing import Dict, Set, Optional, List
import threading
import os

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtGui import QImage
import pymupdf as fitz

from pyacrobat.core.pdf_document import PDFDocument
DocumentWrapper = PDFDocument


class RenderSignals(QObject):
    """Signals emitted across threads from page rasterization workers."""
    page_rendered = Signal(int, QImage, float, float, int)  # (page_idx, image, factor, scale, version)
    page_failed = Signal(int, str, int)                     # (page_idx, error_message, version)


class PageRenderTask(QRunnable):
    """
    Background worker task that renders a single PDF page at high-DPI
    and passes the resulting QImage back to the main UI thread.
    """

    def __init__(
        self,
        doc_wrapper: DocumentWrapper,
        page_idx: int,
        scale: float,
        dpr: float,
        dpi: float,
        version: int,
        signals: RenderSignals,
        lock: threading.Lock
    ):
        super().__init__()
        self.doc_wrapper = doc_wrapper
        self.page_idx = page_idx
        self.scale = scale
        self.dpr = dpr
        self.dpi = dpi
        self.version = version
        self.signals = signals
        self.lock = lock
        self._is_cancelled = False

    def cancel(self):
        """Marks this task as cancelled so it aborts before rendering."""
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return

        try:
            # Thread-safe rasterization via PyMuPDF
            with self.lock:
                if self._is_cancelled:
                    return

                pix, factor = self.doc_wrapper.render_page_pixmap(
                    self.page_idx,
                    scale=self.scale,
                    dpr=self.dpr,
                    screen_dpi=self.dpi
                )

                # Convert fitz.Pixmap to independent QImage
                # Using .copy() creates an isolated Qt buffer safe for cross-thread delivery
                qimage = QImage(
                    pix.samples,
                    pix.width,
                    pix.height,
                    pix.stride,
                    QImage.Format_RGB888
                ).copy()

            if not self._is_cancelled:
                self.signals.page_rendered.emit(
                    self.page_idx, qimage, factor, self.scale, self.version
                )
        except Exception as e:
            if not self._is_cancelled:
                self.signals.page_failed.emit(self.page_idx, str(e), self.version)


class PageRenderManager(QObject):
    """
    Coordinates background page rendering, request prioritization,
    and cancellation for the PDF Canvas viewport.
    """

    page_ready = Signal(int, QImage, float, float)  # (page_idx, qimage, factor, scale)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = RenderSignals()
        self.signals.page_rendered.connect(self._on_page_rendered)
        self.signals.page_failed.connect(self._on_page_failed)

        self._render_lock = threading.Lock()
        self._thread_pool = QThreadPool.globalInstance()
        # Ensure bounded concurrency to prevent CPU thrashing
        max_threads = max(2, min(4, os.cpu_count() or 2))
        self._thread_pool.setMaxThreadCount(max_threads)

        self.doc_wrapper: Optional[DocumentWrapper] = None
        self.current_scale: float = 1.0
        self.current_dpr: float = 1.25
        self.current_dpi: float = 96.0
        self.current_version: int = 1

        # Track active tasks: page_idx -> PageRenderTask
        self._active_tasks: Dict[int, PageRenderTask] = {}
        # Track pages currently rendered or in flight for current version
        self._rendered_pages: Set[int] = set()

    def set_document(self, doc_wrapper: DocumentWrapper):
        """Binds a new active document and resets cache version."""
        self.cancel_all()
        self.doc_wrapper = doc_wrapper
        self.current_version += 1
        self._rendered_pages.clear()

    def set_scale_and_dpi(self, scale: float, dpr: float, dpi: float):
        """Updates rendering parameters; invalidates current rendering generation."""
        if (
            abs(self.current_scale - scale) > 0.001
            or abs(self.current_dpr - dpr) > 0.001
            or abs(self.current_dpi - dpi) > 0.1
        ):
            self.cancel_all()
            self.current_scale = scale
            self.current_dpr = dpr
            self.current_dpi = dpi
            self.current_version += 1
            self._rendered_pages.clear()

    def invalidate_page(self, page_idx: int):
        """Forces a re-render of a specific page (e.g. after editing or annotation)."""
        if page_idx in self._active_tasks:
            self._active_tasks[page_idx].cancel()
            del self._active_tasks[page_idx]
        self._rendered_pages.discard(page_idx)

    def invalidate_all_pages(self):
        """Forces re-render of all pages."""
        self.cancel_all()
        self.current_version += 1
        self._rendered_pages.clear()

    def request_pages(self, desired_indices: List[int], priority_indices: Optional[List[int]] = None):
        """
        Submits background render requests for pages in desired_indices.
        Cancels any active tasks for pages no longer in desired_indices.
        Pages in priority_indices are queued first.
        """
        if not self.doc_wrapper:
            return

        desired_set = set(desired_indices)
        prio_set = set(priority_indices or [])

        # 1. Cancel in-flight tasks for pages no longer desired
        for p_idx in list(self._active_tasks.keys()):
            if p_idx not in desired_set:
                self._active_tasks[p_idx].cancel()
                del self._active_tasks[p_idx]

        # 2. Queue missing pages: priority first, then remaining
        ordered_pages = [p for p in desired_indices if p in prio_set and p not in self._rendered_pages and p not in self._active_tasks]
        ordered_pages += [p for p in desired_indices if p not in prio_set and p not in self._rendered_pages and p not in self._active_tasks]

        for p_idx in ordered_pages:
            if 0 <= p_idx < self.doc_wrapper.page_count:
                task = PageRenderTask(
                    doc_wrapper=self.doc_wrapper,
                    page_idx=p_idx,
                    scale=self.current_scale,
                    dpr=self.current_dpr,
                    dpi=self.current_dpi,
                    version=self.current_version,
                    signals=self.signals,
                    lock=self._render_lock
                )
                self._active_tasks[p_idx] = task
                self._thread_pool.start(task)

    def cancel_all(self):
        """Cancels all currently pending and running background rendering tasks."""
        for task in self._active_tasks.values():
            task.cancel()
        self._active_tasks.clear()

    def _on_page_rendered(self, page_idx: int, image: QImage, factor: float, scale: float, version: int):
        # Ignore results from superseded render versions
        if version != self.current_version:
            return

        if page_idx in self._active_tasks:
            del self._active_tasks[page_idx]

        self._rendered_pages.add(page_idx)
        self.page_ready.emit(page_idx, image, factor, scale)

    def _on_page_failed(self, page_idx: int, error_msg: str, version: int):
        if page_idx in self._active_tasks:
            del self._active_tasks[page_idx]
