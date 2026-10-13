# PyAcrobat Project Guidelines & Architectural Standards

## 1. Architecture & Technology Stack
- **Language:** Python 3.10+
- **UI Framework:** PySide6 (Qt6). Favor clean widget composition, modern QSS stylesheets, and QThreadPool for async operations.
- **PDF Core Engine:** PyMuPDF (`fitz`) for all rasterization, text extraction, annotation parsing, and page transformations.
- **Power Engines:** Local Tesseract OCR (`pytesseract`), Neural TTS (`edge-tts`), and pluggable AI providers.

## 2. UI/UX Paradigm (Adobe Acrobat Alignment)
- **Top Bar:** Document tab system supporting multiple open files with dirty-state indicators (`*`).
- **Quick Tools Ribbon:** Floating or centered pill-shaped action bar containing selection/hand modes, dynamic zoom controls (`Fit Width`, `Fit Page`), and direct page jump.
- **Left Navigation Rail:** Collapsible slim icon bar housing Thumbnails gallery, Table of Contents (Outline) tree, and Full-Text Search drawer.
- **Right Power Tools Drawer:** Collapsible panel for Organize Pages, OCR, Read Aloud, and AI Copilot.
- **Canvas Viewport:** Neutral studio background (`#1E1E1E` dark / `#F5F5F7` light) with realistic page drop-shadows and smooth continuous vertical scrolling.

## 3. Quality & Implementation Invariants
- **High-DPI Rendering:** Render pages at dynamic scale factors matching screen DPI and zoom level.
- **Annotation Compliance:** Always serialize annotations as standard ISO 32000 PDF annotation objects so edits render in other PDF readers.
- **Non-Destructive Operations:** Never overwrite source files without explicit save confirmation; use atomic writes.
- **Performance:** Keep memory footprint bounded by caching only visible pages ± 2 adjacent pages.
