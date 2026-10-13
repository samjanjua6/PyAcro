"""
Export & Extraction Suite for PyAcrobat (Phase 1 Overhaul)
Provides comprehensive multi-format document conversion:
- Microsoft Word (.docx) via pdf2docx with structured docx fallback
- Microsoft Excel (.xlsx) via PyMuPDF table detection and openpyxl
- Microsoft PowerPoint (.pptx) via python-pptx
- High-res Image sequences (PNG, JPEG, multi-page TIFF, ZIP)
- Text and structured formats (Markdown, Plain Text, HTML, XML, RTF)
- Integrated OCR text recognition preprocessing
- Asynchronous QRunnable worker with thread-safe cancellation and progress signals
"""

import os
import io
import shutil
import tempfile
import zipfile
from typing import List, Dict, Any, Tuple, Optional, Callable
import pymupdf as fitz
from PySide6.QtCore import QObject, QRunnable, Signal

# Optional engine imports with safe availability flags
try:
    import pdf2docx
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False

try:
    import docx
    from docx.shared import Inches as DocxInches, Pt as DocxPt, RGBColor as DocxRGBColor
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

try:
    import openpyxl
    from openpyxl.styles import Font as XlsxFont, PatternFill as XlsxPatternFill, Alignment as XlsxAlignment, Border as XlsxBorder, Side as XlsxSide
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from pptx import Presentation
    from pptx.util import Inches as PptxInches, Pt as PptxPt
    HAS_PYTHON_PPTX = True
except ImportError:
    HAS_PYTHON_PPTX = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pyacrobat.core.ocr_engine import OCREngine
    HAS_OCR_ENGINE = True
except ImportError:
    HAS_OCR_ENGINE = False


# Format Constants
FORMAT_DOCX = "docx"
FORMAT_XLSX = "xlsx"
FORMAT_PPTX = "pptx"
FORMAT_IMAGE = "image"
FORMAT_PNG = "png"
FORMAT_JPEG = "jpeg"
FORMAT_TIFF = "tiff"
FORMAT_RTF = "rtf"
FORMAT_TXT = "txt"
FORMAT_HTML = "html"
FORMAT_XML = "xml"
FORMAT_MD = "markdown"

FORMAT_EXTENSIONS: Dict[str, str] = {
    FORMAT_DOCX: "docx",
    FORMAT_XLSX: "xlsx",
    FORMAT_PPTX: "pptx",
    FORMAT_IMAGE: "png",
    FORMAT_PNG: "png",
    FORMAT_JPEG: "jpg",
    FORMAT_TIFF: "tiff",
    FORMAT_RTF: "rtf",
    FORMAT_TXT: "txt",
    FORMAT_HTML: "html",
    FORMAT_XML: "xml",
    FORMAT_MD: "md",
}

FORMAT_FILTERS: Dict[str, str] = {
    FORMAT_DOCX: "Microsoft Word Document (*.docx);;All Files (*.*)",
    FORMAT_XLSX: "Microsoft Excel Workbook (*.xlsx);;All Files (*.*)",
    FORMAT_PPTX: "Microsoft PowerPoint Presentation (*.pptx);;All Files (*.*)",
    FORMAT_IMAGE: "Image Files (*.png *.jpg *.jpeg *.tiff);;PNG Image (*.png);;JPEG Image (*.jpg);;TIFF Image (*.tiff);;ZIP Archive (*.zip);;All Files (*.*)",
    FORMAT_PNG: "PNG Image (*.png);;All Files (*.*)",
    FORMAT_JPEG: "JPEG Image (*.jpg *.jpeg);;All Files (*.*)",
    FORMAT_TIFF: "TIFF Image (*.tiff *.tif);;All Files (*.*)",
    FORMAT_RTF: "Rich Text Format (*.rtf);;All Files (*.*)",
    FORMAT_TXT: "Plain Text Document (*.txt);;All Files (*.*)",
    FORMAT_HTML: "HTML Web Page (*.html *.htm);;All Files (*.*)",
    FORMAT_XML: "XML Document (*.xml);;All Files (*.*)",
    FORMAT_MD: "Markdown Document (*.md);;All Files (*.*)",
}

FORMAT_DISPLAY_NAMES: Dict[str, str] = {
    FORMAT_DOCX: "Microsoft Word (.docx)",
    FORMAT_XLSX: "Microsoft Excel (.xlsx)",
    FORMAT_PPTX: "Microsoft PowerPoint (.pptx)",
    FORMAT_IMAGE: "Image (JPEG, PNG, TIFF)",
    FORMAT_PNG: "PNG Image (.png)",
    FORMAT_JPEG: "JPEG Image (.jpg)",
    FORMAT_TIFF: "TIFF Image (.tiff)",
    FORMAT_RTF: "Rich Text Format (.rtf)",
    FORMAT_TXT: "Plain Text (.txt)",
    FORMAT_HTML: "HTML Web Page (.html)",
    FORMAT_XML: "XML Document (.xml)",
    FORMAT_MD: "Markdown (.md)",
}


def get_format_extension(format_key: str) -> str:
    """Returns the primary file extension for a given format key."""
    return FORMAT_EXTENSIONS.get(format_key.lower(), "docx")


def get_format_file_filter(format_key: str) -> str:
    """Returns the QFileDialog filter string corresponding to a format key."""
    return FORMAT_FILTERS.get(format_key.lower(), "All Files (*.*)")


def get_format_display_name(format_key: str) -> str:
    """Returns human-readable name of the format."""
    return FORMAT_DISPLAY_NAMES.get(format_key.lower(), format_key.upper())


def suggest_output_path(source_pdf_path: str, format_key: str, output_dir: Optional[str] = None) -> str:
    """
    Given a source PDF path and a format key, derives a recommended output path.
    Example: 'C:/docs/proposal.pdf' + 'docx' -> 'C:/docs/proposal.docx'.
    """
    if output_dir:
        base_dir = output_dir
    elif source_pdf_path and os.path.dirname(source_pdf_path):
        base_dir = os.path.dirname(source_pdf_path)
    else:
        base_dir = os.getcwd()

    stem = "document"
    if source_pdf_path:
        stem = os.path.splitext(os.path.basename(source_pdf_path))[0] or "document"

    ext = get_format_extension(format_key)
    return os.path.normpath(os.path.join(base_dir, f"{stem}.{ext}"))


class ExportWorkerSignals(QObject):
    """Signals for background document conversion worker."""
    started = Signal()
    progress = Signal(int, int, str)  # (current_page, total_pages, status_message)
    finished = Signal(str)           # output_file_path
    error = Signal(str)              # error_message
    cancelled = Signal()


class ExportWorker(QRunnable):
    """
    QRunnable background worker to execute document conversion asynchronously.
    Prevents UI thread freezing during large conversions, with progress & cancel support.
    """

    def __init__(
        self,
        doc_wrapper,
        target_path: str,
        format_key: str,
        options: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.doc_wrapper = doc_wrapper
        self.target_path = target_path
        self.format_key = format_key
        self.options = options or {}
        self.signals = ExportWorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        """Thread-safe request to cancel conversion."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def _progress_callback(self, current: int, total: int, status: str):
        if self._is_cancelled:
            raise InterruptedError("Export operation cancelled by user.")
        self.signals.progress.emit(current, total, status)

    def run(self):
        self.signals.started.emit()
        try:
            out_file = ExportEngine.export_document(
                doc_wrapper=self.doc_wrapper,
                target_file_path=self.target_path,
                format_key=self.format_key,
                options=self.options,
                progress_cb=self._progress_callback
            )
            if self._is_cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(str(out_file))
        except InterruptedError:
            self.signals.cancelled.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class ExportEngine:
    """Comprehensive document extraction and conversion suite."""

    # =========================================================================
    # Phase 1: Multi-Format Exporters
    # =========================================================================

    @staticmethod
    def export_to_docx(
        doc_wrapper,
        target_file_path: str,
        ocr: bool = False,
        language: str = "eng",
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """
        Converts document to Microsoft Word (.docx).
        Uses pdf2docx Converter for high fidelity, with fallback to python-docx.
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        total_pages = doc_wrapper.page_count

        if progress_cb:
            progress_cb(1, total_pages, "Preparing document for Word conversion...")

        # If document has unsaved edits in memory or no valid file path on disk, write to temp file
        temp_pdf_path = None
        source_path = getattr(doc_wrapper, "file_path", None)
        is_dirty = getattr(doc_wrapper, "is_dirty", False)

        if not source_path or not os.path.exists(source_path) or is_dirty:
            temp_fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
            os.close(temp_fd)
            doc_wrapper.doc.save(temp_pdf_path)
            source_path = temp_pdf_path

        conversion_succeeded = False
        last_error = None

        # Strategy 1: High-fidelity pdf2docx converter
        if HAS_PDF2DOCX:
            try:
                if progress_cb:
                    progress_cb(1, total_pages, "Analyzing document structure & styles...")

                cv = pdf2docx.Converter(source_path)
                cv.convert(target_file_path, start=0, end=None)
                cv.close()
                conversion_succeeded = True
            except Exception as e:
                last_error = e

        # Strategy 2: Structured python-docx fallback
        if not conversion_succeeded:
            if HAS_PYTHON_DOCX:
                ExportEngine._export_to_docx_fallback(
                    doc_wrapper=doc_wrapper,
                    target_file_path=target_file_path,
                    ocr=ocr,
                    language=language,
                    progress_cb=progress_cb
                )
                conversion_succeeded = True
            else:
                if last_error:
                    raise RuntimeError(f"Word conversion failed: {last_error}")
                raise ImportError("Neither 'pdf2docx' nor 'python-docx' is available for Word conversion.")

        # Cleanup temporary PDF if created
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

        if progress_cb:
            progress_cb(total_pages, total_pages, "Word conversion complete.")

        return target_file_path

    @staticmethod
    def _export_to_docx_fallback(
        doc_wrapper,
        target_file_path: str,
        ocr: bool = False,
        language: str = "eng",
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """Structured fallback converter using python-docx."""
        import docx
        doc = docx.Document()
        total_pages = doc_wrapper.page_count

        for p_idx in range(total_pages):
            if progress_cb:
                progress_cb(p_idx + 1, total_pages, f"Converting page {p_idx + 1} of {total_pages} to DOCX...")

            page = doc_wrapper.get_page(p_idx)

            # Check for scanned page OCR requirement
            page_text = page.get_text("text").strip()
            if ocr and HAS_OCR_ENGINE and (not page_text or len(page_text) < 30):
                ocr_text = OCREngine.ocr_page(page, language=language)
                if ocr_text:
                    page_text = ocr_text

            # Check if tables exist on page
            tables_found = []
            try:
                finder = page.find_tables()
                tables_found = finder.tables
            except Exception:
                tables_found = []

            if tables_found:
                for t_idx, table in enumerate(tables_found):
                    extracted = table.extract()
                    if not extracted:
                        continue
                    num_rows = len(extracted)
                    num_cols = max(len(r) for r in extracted) if num_rows else 0
                    if num_rows and num_cols:
                        tbl = doc.add_table(rows=num_rows, cols=num_cols)
                        tbl.style = 'Light Shading Accent 1' if 'Light Shading Accent 1' in [s.name for s in doc.styles] else 'Table Grid'
                        for r_i, row_data in enumerate(extracted):
                            for c_i, val in enumerate(row_data):
                                tbl.cell(r_i, c_i).text = str(val or "")
                        doc.add_paragraph()

            # Add regular paragraphs
            if page_text:
                for para in page_text.split("\n\n"):
                    clean = para.strip().replace("\n", " ")
                    if clean:
                        doc.add_paragraph(clean)

            # Page break between pages (except last)
            if p_idx < total_pages - 1:
                doc.add_page_break()

        doc.save(target_file_path)
        return target_file_path

    @staticmethod
    def export_to_xlsx(
        doc_wrapper,
        target_file_path: str,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """
        Converts document tables and structured content to Microsoft Excel (.xlsx).
        Detects tables using PyMuPDF and writes styled sheets using openpyxl.
        """
        if not HAS_OPENPYXL:
            raise ImportError("Package 'openpyxl' is required for Excel export.")

        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        wb = openpyxl.Workbook()
        # Remove default empty sheet
        default_sheet = wb.active

        total_pages = doc_wrapper.page_count
        header_fill = XlsxPatternFill(start_color="1473E6", end_color="1473E6", fill_type="solid")
        header_font = XlsxFont(name="Calibri", size=11, bold=True, color="FFFFFF")
        alt_fill = XlsxPatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
        thin_border = XlsxBorder(
            left=XlsxSide(style='thin', color='D9D9D9'),
            right=XlsxSide(style='thin', color='D9D9D9'),
            top=XlsxSide(style='thin', color='D9D9D9'),
            bottom=XlsxSide(style='thin', color='D9D9D9')
        )

        for p_idx in range(total_pages):
            if progress_cb:
                progress_cb(p_idx + 1, total_pages, f"Extracting tables from page {p_idx + 1} of {total_pages}...")

            page = doc_wrapper.get_page(p_idx)
            ws = wb.create_sheet(title=f"Page {p_idx + 1}")

            tables_found = []
            try:
                finder = page.find_tables()
                tables_found = finder.tables
            except Exception:
                tables_found = []

            current_row = 1
            if tables_found:
                for t_idx, table in enumerate(tables_found):
                    extracted = table.extract()
                    if not extracted:
                        continue

                    # Table section title
                    title_cell = ws.cell(row=current_row, column=1, value=f"Table {t_idx + 1}")
                    title_cell.font = XlsxFont(name="Calibri", size=12, bold=True, color="242424")
                    current_row += 1

                    for r_idx, row_data in enumerate(extracted):
                        for c_idx, val in enumerate(row_data):
                            cell = ws.cell(row=current_row, column=c_idx + 1, value=val if val is not None else "")
                            cell.border = thin_border
                            if r_idx == 0:
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = XlsxAlignment(horizontal="center", vertical="center")
                            else:
                                if r_idx % 2 == 1:
                                    cell.fill = alt_fill
                                cell.font = XlsxFont(name="Calibri", size=10)
                                cell.alignment = XlsxAlignment(vertical="center")
                        current_row += 1
                    current_row += 2  # spacing
            else:
                # Fallback: Write page text content line by line
                ws.cell(row=current_row, column=1, value=f"Page {p_idx + 1} Content").font = XlsxFont(name="Calibri", size=12, bold=True)
                current_row += 2
                text = page.get_text("text").strip()
                for line in text.split("\n"):
                    trimmed = line.strip()
                    if trimmed:
                        ws.cell(row=current_row, column=1, value=trimmed).font = XlsxFont(name="Calibri", size=10)
                        current_row += 1

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or '')
                    if val_str:
                        max_len = max(max_len, len(val_str.split('\n')[0]))
                ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 50))

        if default_sheet in wb.worksheets and len(wb.worksheets) > 1:
            wb.remove(default_sheet)

        wb.save(target_file_path)
        if progress_cb:
            progress_cb(total_pages, total_pages, "Excel export complete.")

        return target_file_path

    @staticmethod
    def export_to_pptx(
        doc_wrapper,
        target_file_path: str,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """
        Converts document pages to Microsoft PowerPoint (.pptx).
        Maintains high visual fidelity with crisp High-DPI slide rendering.
        """
        if not HAS_PYTHON_PPTX:
            raise ImportError("Package 'python-pptx' is required for PowerPoint export.")

        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        prs = Presentation()

        total_pages = doc_wrapper.page_count
        p0 = doc_wrapper.get_page(0)
        w_pt, h_pt = p0.rect.width, p0.rect.height

        # Set slide dimensions matching PDF page aspect ratio
        prs.slide_width = PptxInches(w_pt / 72.0)
        prs.slide_height = PptxInches(h_pt / 72.0)
        blank_layout = prs.slide_layouts[6]

        for p_idx in range(total_pages):
            if progress_cb:
                progress_cb(p_idx + 1, total_pages, f"Rendering slide {p_idx + 1} of {total_pages}...")

            page = doc_wrapper.get_page(p_idx)
            slide = prs.slides.add_slide(blank_layout)

            # High-DPI rasterization (150 DPI) of page for slide backdrop
            scale = 150.0 / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img_bytes = pix.tobytes("png")
            img_stream = io.BytesIO(img_bytes)

            slide.shapes.add_picture(
                img_stream, 0, 0,
                width=prs.slide_width,
                height=prs.slide_height
            )

        prs.save(target_file_path)
        if progress_cb:
            progress_cb(total_pages, total_pages, "PowerPoint export complete.")

        return target_file_path

    @staticmethod
    def export_to_images(
        doc_wrapper,
        target_path: str,
        image_format: str = "png",
        dpi: float = 150.0,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        """
        Renders all or selected pages to high-resolution images.
        Supports:
        - Multi-page TIFF (.tif, .tiff)
        - ZIP archive of images (.zip)
        - Individual image sequence files ({stem}_page_X.{ext})
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        total_pages = doc_wrapper.page_count
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        lower_path = target_path.lower()
        created_paths: List[str] = []

        # Case 1: Multi-page TIFF
        if lower_path.endswith((".tif", ".tiff")):
            if not HAS_PIL:
                raise ImportError("Pillow is required for multi-page TIFF export.")

            pil_images = []
            for p_idx in range(total_pages):
                if progress_cb:
                    progress_cb(p_idx + 1, total_pages, f"Rasterizing page {p_idx + 1} for TIFF...")
                page = doc_wrapper.get_page(p_idx)
                pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
                img = PILImage.open(io.BytesIO(pix.tobytes("png")))
                pil_images.append(img)

            if pil_images:
                pil_images[0].save(
                    target_path,
                    save_all=True,
                    append_images=pil_images[1:],
                    compression="tiff_deflate"
                )
                created_paths.append(target_path)

        # Case 2: ZIP Archive
        elif lower_path.endswith(".zip"):
            with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p_idx in range(total_pages):
                    if progress_cb:
                        progress_cb(p_idx + 1, total_pages, f"Rendering page {p_idx + 1} to ZIP...")
                    page = doc_wrapper.get_page(p_idx)
                    pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
                    img_bytes = pix.tobytes(image_format.lower())
                    zf.writestr(f"page_{p_idx + 1:03d}.{image_format.lower()}", img_bytes)
            created_paths.append(target_path)

        # Case 3: Image Sequence Files
        else:
            base_dir = os.path.dirname(os.path.abspath(target_path))
            stem = os.path.splitext(os.path.basename(target_path))[0]
            ext = image_format.lower()
            if ext in ("jpeg", "jpg"):
                ext = "jpg"

            # If single page and user gave an exact file name, save directly
            if total_pages == 1:
                page = doc_wrapper.get_page(0)
                pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
                out_file = target_path if os.path.splitext(target_path)[1] else f"{target_path}.{ext}"
                pix.save(out_file)
                created_paths.append(out_file)
            else:
                for p_idx in range(total_pages):
                    if progress_cb:
                        progress_cb(p_idx + 1, total_pages, f"Saving page {p_idx + 1} image...")
                    page = doc_wrapper.get_page(p_idx)
                    pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
                    out_file = os.path.join(base_dir, f"{stem}_page_{p_idx + 1:03d}.{ext}")
                    pix.save(out_file)
                    created_paths.append(out_file)

        if progress_cb:
            progress_cb(total_pages, total_pages, "Image export complete.")

        return created_paths

    @staticmethod
    def export_to_text_formats(
        doc_wrapper,
        target_file_path: str,
        format_type: str = FORMAT_TXT,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """
        Exports document to structured text formats:
        - Plain Text (.txt)
        - HTML Web Page (.html)
        - XML Document (.xml)
        - Rich Text Format (.rtf)
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        total_pages = doc_wrapper.page_count
        fmt = format_type.lower()

        if fmt == FORMAT_HTML:
            html_parts = [
                "<!DOCTYPE html>",
                "<html><head><meta charset='utf-8'><title>" + str(doc_wrapper.title) + "</title>",
                "<style>body{font-family:system-ui,sans-serif;margin:40px auto;max-width:800px;line-height:1.6;color:#242424;}",
                ".page{background:#fff;padding:40px;margin-bottom:30px;box-shadow:0 2px 8px rgba(0,0,0,0.1);border-radius:6px;}",
                ".page-num{font-size:12px;color:#888;margin-bottom:15px;border-bottom:1px solid #eee;padding-bottom:5px;}</style>",
                "</head><body>"
            ]
            for p_idx in range(total_pages):
                if progress_cb:
                    progress_cb(p_idx + 1, total_pages, f"Converting page {p_idx + 1} to HTML...")
                page = doc_wrapper.get_page(p_idx)
                html_parts.append(f"<div class='page'><div class='page-num'>Page {p_idx + 1} of {total_pages}</div>")
                html_parts.append(page.get_text("html"))
                html_parts.append("</div>")
            html_parts.append("</body></html>")
            full_html = "\n".join(html_parts)
            with open(target_file_path, "w", encoding="utf-8") as f:
                f.write(full_html)

        elif fmt == FORMAT_XML:
            xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<document title="' + str(doc_wrapper.title) + '">']
            for p_idx in range(total_pages):
                if progress_cb:
                    progress_cb(p_idx + 1, total_pages, f"Converting page {p_idx + 1} to XML...")
                page = doc_wrapper.get_page(p_idx)
                xml_parts.append(f"<page number='{p_idx + 1}'>\n" + page.get_text("xml") + "\n</page>")
            xml_parts.append("</document>")
            with open(target_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(xml_parts))

        elif fmt == FORMAT_RTF:
            # Standard minimal RTF 1.0 container
            rtf_header = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Inter;}}" + "\n"
            rtf_body = [rtf_header]
            for p_idx in range(total_pages):
                if progress_cb:
                    progress_cb(p_idx + 1, total_pages, f"Converting page {p_idx + 1} to RTF...")
                page = doc_wrapper.get_page(p_idx)
                rtf_body.append(f"\\b Page {p_idx + 1} \\b0 \\line\n")
                text = page.get_text("text").strip()
                for line in text.split("\n"):
                    safe_line = line.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                    rtf_body.append(f"{safe_line}\\line\n")
                if p_idx < total_pages - 1:
                    rtf_body.append("\\page\n")
            rtf_body.append("}\n")
            with open(target_file_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write("".join(rtf_body))

        else:  # Plain TXT fallback
            ExportEngine.export_to_text(doc_wrapper, target_file_path)

        if progress_cb:
            progress_cb(total_pages, total_pages, f"{fmt.upper()} export complete.")

        return target_file_path

    # =========================================================================
    # Unified Dispatcher
    # =========================================================================

    @staticmethod
    def export_document(
        doc_wrapper,
        target_file_path: str,
        format_key: str,
        options: Optional[Dict[str, Any]] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> Any:
        """
        Unified dispatcher routing to the requested format converter with supplied options.
        """
        opts = options or {}
        fmt = format_key.lower()

        target_dir = os.path.dirname(os.path.abspath(target_file_path))
        os.makedirs(target_dir, exist_ok=True)
        # Verify write permission on destination folder
        test_file = os.path.join(target_dir, f".perm_check_{os.getpid()}.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("")
            os.remove(test_file)
        except Exception as e:
            raise PermissionError(f"Cannot write to output directory '{target_dir}': {e}")

        if fmt == FORMAT_DOCX:
            return ExportEngine.export_to_docx(
                doc_wrapper=doc_wrapper,
                target_file_path=target_file_path,
                ocr=opts.get("ocr", False),
                language=opts.get("language", "eng"),
                progress_cb=progress_cb
            )

        elif fmt == FORMAT_XLSX:
            return ExportEngine.export_to_xlsx(
                doc_wrapper=doc_wrapper,
                target_file_path=target_file_path,
                progress_cb=progress_cb
            )

        elif fmt == FORMAT_PPTX:
            return ExportEngine.export_to_pptx(
                doc_wrapper=doc_wrapper,
                target_file_path=target_file_path,
                progress_cb=progress_cb
            )

        elif fmt in (FORMAT_IMAGE, FORMAT_PNG, FORMAT_JPEG, FORMAT_TIFF):
            image_format = opts.get("image_format", fmt if fmt != FORMAT_IMAGE else "png")
            dpi = float(opts.get("dpi", 150.0))
            return ExportEngine.export_to_images(
                doc_wrapper=doc_wrapper,
                target_path=target_file_path,
                image_format=image_format,
                dpi=dpi,
                progress_cb=progress_cb
            )

        elif fmt == FORMAT_MD:
            return ExportEngine.export_to_markdown(
                doc_wrapper=doc_wrapper,
                target_file_path=target_file_path
            )

        elif fmt in (FORMAT_HTML, FORMAT_XML, FORMAT_RTF, FORMAT_TXT):
            return ExportEngine.export_to_text_formats(
                doc_wrapper=doc_wrapper,
                target_file_path=target_file_path,
                format_type=fmt,
                progress_cb=progress_cb
            )

        else:
            raise ValueError(f"Unsupported export format key: '{format_key}'")

    # =========================================================================
    # Backward-Compatible Legacy Methods
    # =========================================================================

    @staticmethod
    def extract_images(doc_wrapper, target_dir: str) -> List[str]:
        """
        Extracts all embedded raster images from the document at native resolution.
        Returns list of saved image file paths.
        """
        os.makedirs(target_dir, exist_ok=True)
        extracted_paths = []
        image_counter = 1

        for p_idx in range(doc_wrapper.page_count):
            page = doc_wrapper.get_page(p_idx)
            image_list = page.get_images(full=True)

            for img_info in image_list:
                xref = img_info[0]
                base_image = doc_wrapper.doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                filename = f"image_p{p_idx + 1}_{image_counter}.{image_ext}"
                out_path = os.path.join(target_dir, filename)

                with open(out_path, "wb") as f:
                    f.write(image_bytes)

                extracted_paths.append(out_path)
                image_counter += 1

        return extracted_paths

    @staticmethod
    def export_to_markdown(doc_wrapper, target_file_path: str) -> str:
        """
        Converts document text to structured Markdown with page headers and section formatting.
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        md_lines = [
            f"# {doc_wrapper.title}\n",
            f"*Total Pages: {doc_wrapper.page_count}*\n",
            "---\n"
        ]

        for p_idx in range(doc_wrapper.page_count):
            page = doc_wrapper.get_page(p_idx)
            text = page.get_text("text").strip()

            md_lines.append(f"\n## Page {p_idx + 1}\n")
            if text:
                md_lines.append(text + "\n")
            else:
                md_lines.append("*(No extractable text on page - Scanned image)*\n")
            md_lines.append("\n---\n")

        full_md = "\n".join(md_lines)
        with open(target_file_path, "w", encoding="utf-8") as f:
            f.write(full_md)

        return target_file_path

    @staticmethod
    def export_to_text(doc_wrapper, target_file_path: str) -> str:
        """Exports full document text to plain text file."""
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        text_lines = []
        for p_idx in range(doc_wrapper.page_count):
            page = doc_wrapper.get_page(p_idx)
            text_lines.append(f"--- PAGE {p_idx + 1} ---")
            text_lines.append(page.get_text("text").strip())
            text_lines.append("")

        full_text = "\n".join(text_lines)
        with open(target_file_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        return target_file_path

    @staticmethod
    def export_page_as_image(doc_wrapper, page_index: int, target_file_path: str, dpi: float = 150.0) -> str:
        """Renders and saves a specific page as a high-resolution PNG or JPEG."""
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        page = doc_wrapper.get_page(page_index)
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
        pix.save(target_file_path)
        return target_file_path
