"""
Optical Character Recognition (OCR) Engine for PyAcrobat
Combines PyMuPDF native Tesseract C-API and local pytesseract fallback to
detect scanned pages, extract text, and inject searchable layers.
"""

import os
import sys
from typing import Optional, List, Dict, Tuple
import pymupdf as fitz
from PySide6.QtCore import QThread, Signal, QObject

try:
    import pytesseract
    from PIL import Image
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


def get_tessdata_dir() -> Optional[str]:
    """Resolves the tessdata directory from project assets or system paths."""
    # 1. Project bundled tessdata
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_tessdata = os.path.join(base_dir, "tessdata")
    if os.path.isdir(project_tessdata) and os.path.exists(os.path.join(project_tessdata, "eng.traineddata")):
        return project_tessdata

    # 2. Environment variable
    env_tessdata = os.environ.get("TESSDATA_PREFIX")
    if env_tessdata and os.path.isdir(env_tessdata):
        return env_tessdata

    # 3. Standard Windows installation paths
    std_paths = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tessdata")
    ]
    for p in std_paths:
        if os.path.isdir(p):
            return p

    return None


class OCREngine:
    """Core logic for OCR scanning and text recognition."""

    @staticmethod
    def is_page_scanned(page: fitz.Page, threshold_chars: int = 30) -> bool:
        """
        Returns True if the page has fewer extractable text characters than threshold,
        indicating a scanned image or raster-only PDF page.
        """
        text = page.get_text("text").strip()
        return len(text) < threshold_chars

    @staticmethod
    def ocr_page(page: fitz.Page, language: str = "eng", dpi: int = 300) -> str:
        """
        Performs high-resolution OCR on a single PDF page.
        Prioritizes PyMuPDF built-in Tesseract engine, falling back to pytesseract.
        """
        tessdata = get_tessdata_dir()

        # Method 1: PyMuPDF built-in Tesseract integration
        if hasattr(page, "get_textpage_ocr"):
            try:
                kwargs = {"language": language, "dpi": dpi, "full": True}
                if tessdata:
                    kwargs["tessdata"] = tessdata
                tp = page.get_textpage_ocr(**kwargs)
                extracted = tp.extractText()
                if extracted and extracted.strip():
                    return extracted.strip()
            except Exception as e:
                print(f"[OCREngine] PyMuPDF OCR warning: {e}")

        # Method 2: Fallback via PIL + pytesseract
        if HAS_PYTESSERACT:
            try:
                scale = dpi / 72.0
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                import io
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                config = ""
                if tessdata:
                    config = f'--tessdata-dir "{tessdata}"'
                
                text = pytesseract.image_to_string(img, lang=language, config=config)
                return text.strip()
            except Exception as e:
                print(f"[OCREngine] pytesseract fallback warning: {e}")

        return ""

    @staticmethod
    def ocr_document(doc_wrapper, page_indices: Optional[List[int]] = None, language: str = "eng", dpi: int = 300) -> Dict[int, str]:
        """Runs OCR on specified pages or all scanned pages in the document."""
        results = {}
        target_indices = page_indices if page_indices is not None else list(range(doc_wrapper.page_count))

        for idx in target_indices:
            page = doc_wrapper.get_page(idx)
            text = OCREngine.ocr_page(page, language=language, dpi=dpi)
            results[idx] = text

        return results


class OCRWorker(QThread):
    """Asynchronous worker for non-blocking OCR execution."""
    progress = Signal(int, int)        # current_step, total_steps
    page_done = Signal(int, str)       # page_index, recognized_text
    all_done = Signal(dict)            # dict of page_index -> text
    error = Signal(str)

    def __init__(self, doc_wrapper, page_indices: List[int], language: str = "eng", dpi: int = 300):
        super().__init__()
        self.doc_wrapper = doc_wrapper
        self.page_indices = page_indices
        self.language = language
        self.dpi = dpi
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            total = len(self.page_indices)
            results = {}
            for i, p_idx in enumerate(self.page_indices):
                if self._is_cancelled:
                    break
                self.progress.emit(i + 1, total)
                page = self.doc_wrapper.get_page(p_idx)
                text = OCREngine.ocr_page(page, language=self.language, dpi=self.dpi)
                results[p_idx] = text
                self.page_done.emit(p_idx, text)

            if not self._is_cancelled:
                self.all_done.emit(results)
        except Exception as e:
            self.error.emit(str(e))
