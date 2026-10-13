"""
PDF Content Editor Engine (Adobe Acrobat Style)
Provides high-performance primitives for discovering, selecting, redacting,
replacing, inserting, and transforming text and visual content in PDF documents.
Follows ISO 32000 standards via PyMuPDF (pymupdf).
"""

import os
import re
from datetime import datetime
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union
import pymupdf as fitz


class ContentBlockType(IntEnum):
    """Categorizes the content payload of a PDF block."""
    TEXT = 0
    IMAGE = 1


@dataclass
class FontStyle:
    """Typography and appearance metadata for a text run or block."""
    font_name: str = "Inter"
    font_size: float = 11.0
    color_rgb: Tuple[float, float, float] = (0.14, 0.14, 0.14)
    is_bold: bool = False
    is_italic: bool = False
    is_underline: bool = False
    is_strike: bool = False
    line_spacing: float = 1.2
    char_spacing: float = 0.0
    alignment: int = fitz.TEXT_ALIGN_LEFT  # 0=Left, 1=Center, 2=Right, 3=Justify

    @property
    def color_hex(self) -> str:
        """Returns standard #RRGGBB hex string."""
        r = max(0, min(255, int(round(self.color_rgb[0] * 255))))
        g = max(0, min(255, int(round(self.color_rgb[1] * 255))))
        b = max(0, min(255, int(round(self.color_rgb[2] * 255))))
        return f"#{r:02X}{g:02X}{b:02X}"

    @classmethod
    def from_color_hex(cls, hex_str: str, **kwargs) -> "FontStyle":
        """Instantiates FontStyle parsing a hex color string like #1473E6."""
        hex_clean = hex_str.lstrip("#")
        if len(hex_clean) == 6:
            r = int(hex_clean[0:2], 16) / 255.0
            g = int(hex_clean[2:4], 16) / 255.0
            b = int(hex_clean[4:6], 16) / 255.0
            color = (r, g, b)
        else:
            color = (0.14, 0.14, 0.14)
        return cls(color_rgb=color, **kwargs)

    @classmethod
    def from_srgb_int(cls, color_int: int, **kwargs) -> "FontStyle":
        """Converts PyMuPDF sRGB integer into RGB float tuple (0.0..1.0)."""
        r = ((color_int >> 16) & 0xFF) / 255.0
        g = ((color_int >> 8) & 0xFF) / 255.0
        b = (color_int & 0xFF) / 255.0
        return cls(color_rgb=(r, g, b), **kwargs)

    def get_py_mupdf_fontname(self) -> str:
        """
        Resolves friendly font names into valid PyMuPDF Base-14 font identifiers.
        Handles Sans-Serif / Inter / Arial -> helv/hebo/heit/hebi
        Serif / Times -> times/tibo/tiit/tibi
        Monospace / Courier -> couri/cobo/coit/cobi
        """
        name_lower = self.font_name.lower()
        if any(f in name_lower for f in ("times", "serif", "georgia", "roman")):
            if self.is_bold and self.is_italic:
                return "tibi"
            elif self.is_bold:
                return "tibo"
            elif self.is_italic:
                return "tiit"
            return "tiro"
        elif any(f in name_lower for f in ("courier", "mono", "consolas", "code")):
            if self.is_bold and self.is_italic:
                return "cobi"
            elif self.is_bold:
                return "cobo"
            elif self.is_italic:
                return "coit"
            return "cour"
        else:
            # Default to standard Helvetica family (Inter / Arial / Sans-Serif)
            if self.is_bold and self.is_italic:
                return "hebi"
            elif self.is_bold:
                return "hebo"
            elif self.is_italic:
                return "heit"
            return "helv"


@dataclass
class ContentBlock:
    """Represents a discrete selectable, editable text or visual block on a PDF page."""
    block_id: int
    page_index: int
    block_type: ContentBlockType
    rect: fitz.Rect
    text: str = ""
    font_style: FontStyle = field(default_factory=FontStyle)
    image_xref: Optional[int] = None
    image_ext: Optional[str] = None
    raw_lines: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_text(self) -> bool:
        return self.block_type == ContentBlockType.TEXT

    @property
    def is_image(self) -> bool:
        return self.block_type == ContentBlockType.IMAGE


class PDFEditorEngine:
    """Headless engine executing content discovery, redaction, and PDF vector modifications."""

    @staticmethod
    def extract_page_content_blocks(doc: fitz.Document, page_index: int) -> List[ContentBlock]:
        """
        Extracts all structured content blocks from a given page.
        Identifies bounding boxes, typography, colors, and embedded images.
        """
        if not (0 <= page_index < len(doc)):
            return []

        page = doc[page_index]
        page_dict = page.get_text("dict")
        raw_blocks = page_dict.get("blocks", [])
        content_blocks: List[ContentBlock] = []

        block_counter = 0
        for raw in raw_blocks:
            b_type = raw.get("type", 0)
            bbox = raw.get("bbox")
            if not bbox:
                continue

            rect = fitz.Rect(bbox)
            if rect.width < 1.0 or rect.height < 1.0:
                continue

            if b_type == 0:  # Text block
                lines = raw.get("lines", [])
                full_text_parts = []
                primary_style: Optional[FontStyle] = None

                for line in lines:
                    line_spans = line.get("spans", [])
                    line_text = "".join(span.get("text", "") for span in line_spans)
                    if line_text:
                        full_text_parts.append(line_text)

                    # Determine primary typography from first meaningful span
                    if not primary_style:
                        for span in line_spans:
                            stext = span.get("text", "").strip()
                            if stext:
                                flags = span.get("flags", 0)
                                is_bold = bool(flags & 16) or "bold" in span.get("font", "").lower()
                                is_italic = bool(flags & 2) or "italic" in span.get("font", "").lower() or "oblique" in span.get("font", "").lower()
                                primary_style = FontStyle.from_srgb_int(
                                    color_int=span.get("color", 0),
                                    font_name=span.get("font", "Inter"),
                                    font_size=float(span.get("size", 11.0)),
                                    is_bold=is_bold,
                                    is_italic=is_italic
                                )
                                break

                full_text = "\n".join(full_text_parts).strip()
                if not full_text:
                    continue

                if not primary_style:
                    primary_style = FontStyle()

                content_blocks.append(
                    ContentBlock(
                        block_id=block_counter,
                        page_index=page_index,
                        block_type=ContentBlockType.TEXT,
                        rect=rect,
                        text=full_text,
                        font_style=primary_style,
                        raw_lines=lines
                    )
                )
                block_counter += 1

            elif b_type == 1:  # Image block
                image_info = raw.get("image", None)
                xref = raw.get("xref", 0)
                ext = raw.get("ext", "png")
                content_blocks.append(
                    ContentBlock(
                        block_id=block_counter,
                        page_index=page_index,
                        block_type=ContentBlockType.IMAGE,
                        rect=rect,
                        text="[Image]",
                        image_xref=xref if xref > 0 else None,
                        image_ext=ext
                    )
                )
                block_counter += 1

        return content_blocks

    @staticmethod
    def replace_text_block(
        doc: fitz.Document,
        page_index: int,
        old_rect: fitz.Rect,
        new_text: str,
        font_style: Optional[FontStyle] = None,
        padding: float = 1.0,
        expand_for_text: bool = True
    ) -> fitz.Rect:
        """
        Executes atomic redact-and-replace:
        1. Redacts the target rectangular area to remove existing text and vectors.
        2. Injects the new text with requested font, size, color, and alignment.
        Returns the final bounding rectangle of the modified text block.
        """
        if not (0 <= page_index < len(doc)):
            raise IndexError(f"Page index {page_index} out of range")

        page = doc[page_index]
        style = font_style or FontStyle()
        fontname = style.get_py_mupdf_fontname()

        # 1. Atomic Redaction of original bounds (slightly padded to prevent remnants)
        redact_rect = fitz.Rect(
            old_rect.x0 - padding,
            old_rect.y0 - padding,
            old_rect.x1 + padding,
            old_rect.y1 + padding
        )
        page.add_redact_annot(redact_rect, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # 2. Text layout calculation
        target_rect = fitz.Rect(old_rect)
        if expand_for_text:
            # Estimate text height if new text is longer than original
            lines = new_text.split("\n")
            est_line_height = style.font_size * style.line_spacing
            est_total_height = max(target_rect.height, len(lines) * est_line_height + 4)
            target_rect.y1 = max(target_rect.y1, target_rect.y0 + est_total_height + 6.0)
            target_rect.x1 = max(target_rect.x1, target_rect.x0 + 10.0) + 6.0

        # 3. Vector text insertion
        rem = page.insert_textbox(
            target_rect,
            new_text,
            fontname=fontname,
            fontsize=style.font_size,
            color=style.color_rgb,
            align=style.alignment
        )

        # If text overflowed, gracefully expand downward/horizontally and re-try
        if rem < 0 and expand_for_text:
            target_rect.y1 += abs(rem) + style.font_size * 2.0
            target_rect.x1 += 10.0
            rem2 = page.insert_textbox(
                target_rect,
                new_text,
                fontname=fontname,
                fontsize=style.font_size,
                color=style.color_rgb,
                align=style.alignment
            )
            if rem2 < 0:
                # Fallback to direct text insertion at baseline so content is never lost
                baseline_y = old_rect.y0 + style.font_size
                page.insert_text(
                    (old_rect.x0, baseline_y),
                    new_text,
                    fontname=fontname,
                    fontsize=style.font_size,
                    color=style.color_rgb
                )

        return target_rect

    @staticmethod
    def insert_new_text_box(
        doc: fitz.Document,
        page_index: int,
        rect: fitz.Rect,
        text: str,
        font_style: Optional[FontStyle] = None
    ) -> fitz.Rect:
        """Inserts a brand-new vector text box at the specified coordinates."""
        if not (0 <= page_index < len(doc)):
            raise IndexError(f"Page index {page_index} out of range")

        page = doc[page_index]
        style = font_style or FontStyle()
        fontname = style.get_py_mupdf_fontname()

        target_rect = fitz.Rect(rect)
        lines = text.split("\n")
        est_line_height = style.font_size * style.line_spacing
        est_total_height = max(target_rect.height, len(lines) * est_line_height + 4.0)
        target_rect.y1 = max(target_rect.y1, target_rect.y0 + est_total_height + 6.0)
        target_rect.x1 = max(target_rect.x1, target_rect.x0 + 10.0) + 6.0

        rem = page.insert_textbox(
            target_rect,
            text,
            fontname=fontname,
            fontsize=style.font_size,
            color=style.color_rgb,
            align=style.alignment
        )
        if rem < 0:
            target_rect.y1 += abs(rem) + style.font_size * 2.0
            target_rect.x1 += 10.0
            rem2 = page.insert_textbox(
                target_rect,
                text,
                fontname=fontname,
                fontsize=style.font_size,
                color=style.color_rgb,
                align=style.alignment
            )
            if rem2 < 0:
                baseline_y = rect.y0 + style.font_size
                page.insert_text(
                    (rect.x0, baseline_y),
                    text,
                    fontname=fontname,
                    fontsize=style.font_size,
                    color=style.color_rgb
                )
        return rect

    @staticmethod
    def insert_image_box(
        doc: fitz.Document,
        page_index: int,
        rect: fitz.Rect,
        image_path: str
    ) -> None:
        """Embeds a raster image (PNG, JPG, BMP) at the specified rectangle."""
        if not (0 <= page_index < len(doc)):
            raise IndexError(f"Page index {page_index} out of range")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        page = doc[page_index]
        page.insert_image(rect, filename=image_path)

    @staticmethod
    def add_hyperlink(
        doc: fitz.Document,
        page_index: int,
        rect: fitz.Rect,
        uri: str
    ) -> None:
        """Creates an ISO-compliant web hyperlink annotation over the target area."""
        if not (0 <= page_index < len(doc)):
            raise IndexError(f"Page index {page_index} out of range")

        page = doc[page_index]
        page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": uri})

    @staticmethod
    def apply_watermark(
        doc: fitz.Document,
        text: str,
        opacity: float = 0.25,
        angle: float = 45.0,
        font_size: float = 48.0,
        color: Optional[Tuple[float, float, float]] = None,
        color_rgb: Optional[Tuple[float, float, float]] = None,
        page_indices: Optional[List[int]] = None
    ) -> int:
        """
        Applies a diagonal, centered vector watermark across specified pages.
        Uses exact morph rotation around the page midpoint.
        """
        targets = page_indices if page_indices is not None else list(range(len(doc)))
        count = 0
        final_color = color if color is not None else (color_rgb if color_rgb is not None else (0.5, 0.5, 0.5))

        for p_idx in targets:
            if 0 <= p_idx < len(doc):
                page = doc[p_idx]
                p_rect = page.rect
                text_len = fitz.get_text_length(text, fontname="hebo", fontsize=font_size)
                origin = fitz.Point(p_rect.width / 2 - text_len / 2, p_rect.height / 2)
                center = fitz.Point(p_rect.width / 2, p_rect.height / 2)
                mat = fitz.Matrix(angle)

                page.insert_text(
                    origin,
                    text,
                    fontname="hebo",
                    fontsize=font_size,
                    color=final_color,
                    morph=(center, mat)
                )
                count += 1

        return count

    @staticmethod
    def apply_header_footer(
        doc: fitz.Document,
        header_left: str = "",
        header_center: str = "",
        header_right: str = "",
        footer_left: str = "",
        footer_center: str = "",
        footer_right: str = "",
        font_size: float = 9.0,
        color: Optional[Tuple[float, float, float]] = None,
        color_rgb: Optional[Tuple[float, float, float]] = None,
        margin: float = 36.0,
        page_indices: Optional[List[int]] = None,
        title: Optional[str] = None
    ) -> int:
        """
        Adds customizable headers and footers with dynamic token replacement:
        Supported tokens: <<Page>>, <<Total>>, <<Date>>, <<Title>>.
        """
        targets = page_indices if page_indices is not None else list(range(len(doc)))
        total_pages = len(doc)
        date_str = datetime.now().strftime("%Y-%m-%d")
        meta = doc.metadata or {}
        title_str = title if title is not None else (meta.get("title") or "Document")
        final_color = color if color is not None else (color_rgb if color_rgb is not None else (0.4, 0.4, 0.4))
        count = 0

        for p_idx in targets:
            if not (0 <= p_idx < total_pages):
                continue
            page = doc[p_idx]
            p_rect = page.rect
            cur_page = str(p_idx + 1)

            def _replace_tokens(tmpl: str) -> str:
                res = tmpl.replace("<<Page>>", cur_page).replace("[Page]", cur_page)
                res = res.replace("<<Total>>", str(total_pages)).replace("[Total]", str(total_pages))
                res = res.replace("<<Date>>", date_str).replace("[Date]", date_str)
                res = res.replace("<<Title>>", title_str).replace("[Title]", title_str)
                return res

            # Headers (Top)
            y_header = margin
            if header_left:
                txt = _replace_tokens(header_left)
                page.insert_text(fitz.Point(margin, y_header), txt, fontsize=font_size, fontname="helv", color=final_color)
            if header_center:
                txt = _replace_tokens(header_center)
                t_len = fitz.get_text_length(txt, fontname="helv", fontsize=font_size)
                page.insert_text(fitz.Point((p_rect.width - t_len) / 2, y_header), txt, fontsize=font_size, fontname="helv", color=final_color)
            if header_right:
                txt = _replace_tokens(header_right)
                t_len = fitz.get_text_length(txt, fontname="helv", fontsize=font_size)
                page.insert_text(fitz.Point(p_rect.width - margin - t_len, y_header), txt, fontsize=font_size, fontname="helv", color=final_color)

            # Footers (Bottom)
            y_footer = p_rect.height - margin + font_size
            if footer_left:
                txt = _replace_tokens(footer_left)
                page.insert_text(fitz.Point(margin, y_footer), txt, fontsize=font_size, fontname="helv", color=final_color)
            if footer_center:
                txt = _replace_tokens(footer_center)
                t_len = fitz.get_text_length(txt, fontname="helv", fontsize=font_size)
                page.insert_text(fitz.Point((p_rect.width - t_len) / 2, y_footer), txt, fontsize=font_size, fontname="helv", color=final_color)
            if footer_right:
                txt = _replace_tokens(footer_right)
                t_len = fitz.get_text_length(txt, fontname="helv", fontsize=font_size)
                page.insert_text(fitz.Point(p_rect.width - margin - t_len, y_footer), txt, fontsize=font_size, fontname="helv", color=final_color)

            count += 1

        return count

    @staticmethod
    def apply_crop_box(
        doc: fitz.Document,
        page_index: int,
        crop_rect: fitz.Rect
    ) -> fitz.Rect:
        """Sets the active display crop box on the specified page."""
        if not (0 <= page_index < len(doc)):
            raise IndexError(f"Page index {page_index} out of range")

        page = doc[page_index]
        page.set_cropbox(crop_rect)
        return page.rect
