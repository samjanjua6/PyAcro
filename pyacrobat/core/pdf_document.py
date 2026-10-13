"""
PDF Document Wrapper for PyMuPDF (pymupdf)
Provides high-performance rendering, High-DPI rasterization, TOC extraction, search,
smart text-snapping annotations, atomic saves, and Phase 3 Page Organizer manipulation.
"""

import os
import shutil
import tempfile
from typing import List, Tuple, Optional, Dict, Any
import pymupdf as fitz


class PDFDocument:
    """Encapsulates a fitz.Document instance with page organization & editing engine."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc: fitz.Document = fitz.open(file_path)
        self.page_count: int = len(self.doc)
        self.title: str = self._extract_title()
        self.is_dirty: bool = False

    def _extract_title(self) -> str:
        meta = self.doc.metadata or {}
        title = meta.get("title")
        if title and title.strip():
            return title.strip()
        return os.path.basename(self.file_path)

    def get_page(self, page_index: int) -> fitz.Page:
        if 0 <= page_index < self.page_count:
            return self.doc[page_index]
        raise IndexError(f"Page index {page_index} out of range (0..{self.page_count - 1})")

    def render_page_pixmap(
        self,
        page_index: int,
        scale: float = 1.0,
        dpr: float = 1.25,
        screen_dpi: float = 96.0
    ) -> Tuple[fitz.Pixmap, float]:
        """
        Renders a page at razor-sharp High-DPI scale.
        """
        page = self.get_page(page_index)
        dpi_factor = max(1.0, screen_dpi / 72.0)
        factor = dpi_factor * max(1.0, dpr)
        effective_scale = max(0.2, scale * factor)

        mat = fitz.Matrix(effective_scale, effective_scale)
        pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
        return pix, factor

    def render_thumbnail(self, page_index: int, target_width: int = 180) -> fitz.Pixmap:
        """Renders a high-quality thumbnail for sidebar and organize grid."""
        page = self.get_page(page_index)
        rect = page.rect
        scale = target_width / max(rect.width, 1.0)
        mat = fitz.Matrix(scale, scale)
        return page.get_pixmap(matrix=mat, alpha=False, annots=True)

    def get_toc(self) -> List[List[Any]]:
        try:
            return self.doc.get_toc()
        except Exception:
            return []

    def search_text(self, query: str) -> Dict[int, List[fitz.Rect]]:
        results = {}
        if not query.strip():
            return results

        for i in range(self.page_count):
            page = self.doc[i]
            rects = page.search_for(query)
            if rects:
                results[i] = rects
        return results

    def extract_text(self, page_index: int) -> str:
        page = self.get_page(page_index)
        return page.get_text("text")

    # ==========================================
    # Phase 3: Visual Page Organizer Engine
    # ==========================================

    def reorder_pages(self, new_order: List[int]):
        """
        Reorders document pages according to new_order (0-based indices).
        Example: [2, 0, 1] puts page 3 first, then page 1, then page 2.
        """
        if sorted(new_order) != list(range(self.page_count)):
            raise ValueError(f"Invalid page permutation: {new_order}")
        self.doc.select(new_order)
        self.page_count = len(self.doc)
        self.is_dirty = True

    def rotate_page(self, page_index: int, degrees: int = 90):
        """Rotates a single page by +90, -90, or 180 degrees."""
        page = self.get_page(page_index)
        page.set_rotation((page.rotation + degrees) % 360)
        self.is_dirty = True

    def rotate_pages(self, page_indices: List[int], degrees: int = 90):
        """Rotates multiple pages."""
        for idx in page_indices:
            self.rotate_page(idx, degrees)

    def delete_page(self, page_index: int) -> bool:
        """Deletes a page. Safeguards against deleting all pages."""
        if self.page_count <= 1:
            return False
        self.doc.delete_page(page_index)
        self.page_count = len(self.doc)
        self.is_dirty = True
        return True

    def delete_pages(self, page_indices: List[int]) -> bool:
        """Deletes multiple pages in descending order."""
        if len(page_indices) >= self.page_count:
            return False  # Cannot delete all pages
        # Delete from largest index to smallest to prevent index shifts
        for idx in sorted(page_indices, reverse=True):
            if 0 <= idx < len(self.doc):
                self.doc.delete_page(idx)
        self.page_count = len(self.doc)
        self.is_dirty = True
        return True

    def insert_blank_page(self, at_index: int, width: float = 595.0, height: float = 842.0) -> int:
        """Inserts a new blank page at the specified index."""
        target_idx = max(0, min(self.page_count, at_index))
        self.doc.new_page(pno=target_idx, width=width, height=height)
        self.page_count = len(self.doc)
        self.is_dirty = True
        return target_idx

    def duplicate_page(self, page_index: int) -> int:
        """Duplicates an existing page and inserts it right after."""
        target_idx = page_index + 1
        src_copy = fitz.open("pdf", self.doc.tobytes())
        self.doc.insert_pdf(
            src_copy, from_page=page_index, to_page=page_index, start_at=target_idx
        )
        src_copy.close()
        self.page_count = len(self.doc)
        self.is_dirty = True
        return target_idx

    def merge_external_pdf(self, other_pdf_path: str, insert_at: int = -1) -> int:
        """Merges an external PDF file into the active document."""
        other_doc = fitz.open(other_pdf_path)
        inserted_count = len(other_doc)
        target_idx = self.page_count if insert_at < 0 else insert_at
        self.doc.insert_pdf(other_doc, start_at=target_idx)
        other_doc.close()
        self.page_count = len(self.doc)
        self.is_dirty = True
        return inserted_count

    def extract_pages_to_file(self, page_indices: List[int], target_path: str):
        """Extracts specified pages into a standalone new PDF file."""
        new_doc = fitz.open()
        for idx in sorted(page_indices):
            new_doc.insert_pdf(self.doc, from_page=idx, to_page=idx)
        new_doc.save(target_path, garbage=3, deflate=True, clean=True)
        new_doc.close()

    @staticmethod
    def static_merge_pdfs(file_paths: List[str], target_path: str) -> int:
        """Combines multiple independent PDF files into a single unified PDF."""
        merged_doc = fitz.open()
        total_pages = 0
        for path in file_paths:
            src = fitz.open(path)
            merged_doc.insert_pdf(src)
            total_pages += len(src)
            src.close()
        merged_doc.save(target_path, garbage=3, deflate=True, clean=True)
        merged_doc.close()
        return total_pages

    # ==========================================
    # Smart ISO-32000 Annotations API
    # ==========================================

    def add_highlight_annotation(
        self,
        page_index: int,
        rect: fitz.Rect,
        color: Tuple[float, float, float] = (1.0, 0.88, 0.3)
    ) -> fitz.Annot:
        page = self.get_page(page_index)
        words = page.get_text("words")
        intersecting = [w for w in words if fitz.Rect(w[:4]).intersects(rect)]

        if intersecting:
            lines = {}
            for w in intersecting:
                key = (w[5], w[6])
                r = fitz.Rect(w[:4])
                if key not in lines:
                    lines[key] = fitz.Rect(r)
                else:
                    lines[key] = lines[key] | r

            first_annot = None
            for line_rect in lines.values():
                annot = page.add_highlight_annot(line_rect)
                annot.set_colors(stroke=color)
                annot.update()
                if first_annot is None:
                    first_annot = annot
            self.is_dirty = True
            return first_annot
        else:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
            self.is_dirty = True
            return annot

    def add_ink_annotation(
        self,
        page_index: int,
        strokes: List[List[Tuple[float, float]]],
        color: Tuple[float, float, float] = (0.88, 0.15, 0.11),
        width: float = 2.0
    ) -> fitz.Annot:
        page = self.get_page(page_index)
        annot = page.add_ink_annot(strokes)
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()
        self.is_dirty = True
        return annot

    def add_text_annotation(
        self,
        page_index: int,
        point: Tuple[float, float],
        content: str,
        author: str = "User"
    ) -> fitz.Annot:
        page = self.get_page(page_index)
        annot = page.add_text_annot(fitz.Point(*point), content, icon="Comment")
        annot.set_info(title=author, content=content)
        annot.update()
        self.is_dirty = True
        return annot

    def get_all_annotations(self) -> List[Dict[str, Any]]:
        items = []
        for p_idx in range(self.page_count):
            page = self.doc[p_idx]
            for annot in page.annots():
                info = annot.info or {}
                items.append({
                    "page": p_idx + 1,
                    "type": annot.type[1] if annot.type else "Annotation",
                    "author": info.get("title") or "User",
                    "content": info.get("content") or "",
                    "rect": annot.rect,
                    "xref": annot.xref,
                })
        return items

    def delete_annotation(self, page_index: int, annot_xref: int) -> bool:
        page = self.get_page(page_index)
        for annot in page.annots():
            if annot.xref == annot_xref:
                page.delete_annot(annot)
                self.is_dirty = True
                return True
        return False

    def save_document(self, target_path: Optional[str] = None) -> str:
        destination = target_path or self.file_path
        is_same_file = os.path.abspath(destination) == os.path.abspath(self.file_path)

        if is_same_file:
            temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(temp_fd)
            try:
                self.doc.save(temp_path, garbage=3, deflate=True, clean=True)
                self.doc.close()
                shutil.move(temp_path, destination)
                self.doc = fitz.open(destination)
                self.file_path = destination
                self.is_dirty = False
                return destination
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
        else:
            self.doc.save(destination, garbage=3, deflate=True, clean=True)
            self.file_path = destination
            self.is_dirty = False
            return destination

    def close(self):
        if self.doc:
            self.doc.close()
