"""
Export & Extraction Suite for PyAcrobat
Handles embedded image extraction, Markdown/Text conversion, and high-res page snapshots.
"""

import os
from typing import List, Dict, Any, Tuple
import pymupdf as fitz


class ExportEngine:
    """Provides document extraction and conversion utilities."""

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
        page = doc_wrapper.get_page(page_index)
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
        pix.save(target_file_path)
        return target_file_path
