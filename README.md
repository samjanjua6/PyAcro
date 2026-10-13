# PyAcro (PyAcrobat)

<p align="center">
  <strong>An Adobe Acrobat Pro-inspired, High-Performance PDF Workstation built with Python 3 & PySide6 (Qt6).</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/PDF%20Engine-PyMuPDF%20(fitz)-FF0000.svg" alt="PyMuPDF">
  <img src="https://img.shields.io/badge/OCR-Tesseract-blueviolet.svg" alt="Tesseract OCR">
  <img src="https://img.shields.io/badge/Speech-Neural%20Edge--TTS-orange.svg" alt="Edge-TTS">
  <img src="https://img.shields.io/badge/Standard-ISO%2032000%20Compliant-brightgreen.svg" alt="ISO 32000">
</p>

---

## 📖 Overview

**PyAcro** is an open-source, desktop PDF productivity workstation engineered to replicate the polish, responsiveness, and capabilities of **Adobe Acrobat Pro**. 

Designed with a strict architectural separation between core engines and UI components, PyAcro delivers a desktop experience featuring **High-DPI razor-sharp rasterization**, an **interactive Organize Pages workstation with fluid card-sliding physics**, **ISO 32000-compliant annotation serialization**, **embedded Tesseract OCR**, **Neural Read Aloud (Edge-TTS)**, and an **in-memory AI Document Copilot** with clickable page citations.

---

## ✨ Key Features

### 🖥️ 1. Adobe Spectrum-Inspired UI & Viewport
* **Continuous High-DPI Canvas:** High-resolution page rasterization with dynamic Device Pixel Ratio (DPR) supersampling, realistic page drop-shadows, and smooth continuous vertical scrolling.
* **Multi-Tab Workstation:** Open multiple PDF documents simultaneously with dirty-state change indicators (`*`) and non-destructive atomic saving.
* **Quick Tools Pill Ribbon:** Floating, compact toolbar providing instant access to Hand (`H`), Select (`V`), dynamic zoom (`Fit Width`, `Fit Page`, 50%–300%), and direct page jumping.
* **Left Navigation Rail:** Collapsible sidebar containing:
  * **Page Thumbnails:** Dynamic, scaled document gallery with selection syncing.
  * **Bookmarks & Outline:** Interactive Table of Contents (TOC) tree navigation.
  * **Find in Document:** Fast in-document full-text search with match highlighting.
* **Adobe Spectrum Design Tokens:** Symmetrical, high-contrast **Dark Theme** (`#1E1E1E`) and **Light Theme** (`#F5F5F7`) powered by a centralized token manager with zero hardcoded color overrides.
* **Screen-Bounds Protection:** Automatically calculates available display working area on Windows desktops to prevent window overlap or off-screen positioning.

### ✍️ 2. ISO 32000 Markup & Annotation Suite
* **Text Highlighting:** Multi-color highlighter palette (Acrobat Yellow, Mint Green, Cyan, Soft Pink) snapping to text runs.
* **Freehand Vector Pen:** Smooth freehand drawing with customizable line colors and stroke widths (1px, 2px, 4px).
* **Sticky Notes & Comments:** Pin annotations directly on pages with an interactive right-rail comments feed and deletion controls.
* **Standard PDF Serialization:** All highlights, vector strokes, and notes serialize as standard ISO 32000 PDF annotation objects, ensuring edits render natively in Adobe Acrobat, Apple Preview, and modern web browsers.

### 🗂️ 3. "Organize Pages" Interactive Workstation
* **Fluid Drag-and-Drop Reordering:** Live card sliding where pages physically glide aside with cubic easing when a dragged page hovers over slots.
* **Page Transformations:** Rotate selected pages clockwise/counter-clockwise (90° increments) or delete pages with confirmation.
* **Page Insertion & Duplication:** Insert blank pages anywhere in the document sequence or clone existing pages.
* **Merge & Split Engine:**
  * **Merge External PDFs:** Combine multiple PDF files into the active document.
  * **Split / Extract Pages:** Select specific page ranges (e.g., `1-3, 5, 8`) to export into new standalone PDF files.

### ⚡ 4. Power Productivity Modules
* **Local Tesseract OCR:**
  * Embedded Tesseract OCR engine (`tessdata/eng.traineddata`) with automated scanned-page detection.
  * Asynchronous background OCR processing (`QThread`) with live progress tracking.
  * Rich OCR Results dialog with character/word metrics, clipboard copying, and text export.
* **Neural Read Aloud (Edge-TTS):**
  * Natural neural voice synthesis (`en-US-AriaNeural`, `en-US-GuyNeural`, `en-US-JennyNeural`, `en-GB-SoniaNeural`).
  * Playback controls (Play, Pause, Resume, Stop) with speed multipliers (`0.75x` to `2.0x`).
  * Zero-dependency native Windows audio playback via `winmm.dll` MCI player with live progress indicators.
* **Asset Extraction & Document Export Suite:**
  * **Extract All Images:** Export all embedded raster images at their native resolutions.
  * **Export to Markdown:** Extract clean, structured `.md` files with headers and dividers.
  * **Export to Text:** Clean plain text extraction (`.txt`).
  * **Page Snapshot:** High-resolution page snapshot rendering to PNG (`300 DPI`).

### 🤖 5. AI Document Copilot & Smart Assistant
* **In-Memory Semantic Indexing:** Chunks and indexes document text, calculating frequency heuristics and section themes without uploading sensitive data.
* **Clickable Page Citations:** AI responses cite references as `[Page X]` pills; clicking any citation immediately scrolls the canvas directly to that exact page.
* **Quick Action Pills:** One-click shortcuts for `📑 Doc Summary`, `📄 Page Summary`, `📊 Tables`, and `💡 Key Terms`.
* **Pluggable AI Providers:**
  * **Smart Local Engine:** 100% private, offline, zero-config heuristic analysis.
  * **Google Gemini:** Cloud integration via REST API for deep reasoning.
  * **Ollama / OpenAI API:** Connect to local Ollama (`http://localhost:11434/v1`) or custom LLM endpoints.

### 🏠 6. Acrobat Home & Recent Files Hub
* **Recent Documents Grid & Table:** View recently opened files with live metadata (page counts, file sizes, last opened dates).
* **Search & Filter:** Search recent files in real-time or filter by document properties.
* **File Details Drawer:** Inspect document metadata, page statistics, and preview snapshots.

---

## 🏗️ Architecture & Project Structure

```
PyAcro/
├── pyacrobat/
│   ├── __init__.py
│   ├── main.py                     # Application entry point
│   ├── core/                       # Headless Core Engines
│   │   ├── pdf_document.py         # PyMuPDF wrapper & ISO annotations
│   │   ├── ocr_engine.py           # Local Tesseract OCR & worker threads
│   │   ├── tts_engine.py           # Neural Edge-TTS & native Windows audio player
│   │   ├── export_engine.py        # Markdown, text, image & snapshot export
│   │   ├── ai_copilot.py           # Document chunking, indexing & AI providers
│   │   └── recent_files.py         # Recent files store & persistence
│   ├── ui/                         # Qt6 (PySide6) Interface Layers
│   │   ├── styles.py               # Adobe Spectrum design token system (QSS)
│   │   ├── main_window.py          # Main workstation shell & tab controller
│   │   ├── home_view.py            # Acrobat Home landing screen
│   │   ├── organizer_grid.py       # Fluid drag-and-drop page organizer
│   │   ├── pdf_canvas.py           # High-DPI continuous PDF viewer
│   │   ├── ai_chat_panel.py        # AI conversational panel & settings
│   │   ├── right_drawer.py         # Power tools & annotations feed
│   │   ├── left_rail.py            # Thumbnails, TOC bookmarks & search
│   │   ├── recent_files_table.py   # Recent files card grid & table
│   │   ├── merge_dialog.py         # PDF merge & page split dialogs
│   │   └── ocr_dialog.py           # OCR text viewer & exporter
│   ├── assets/                     # UI SVG icon assets
│   ├── resources/                  # Application navigation icons
│   └── tessdata/                   # Tesseract language training models
├── requirements.txt                # Python package dependencies
├── run.bat                         # Quick launcher for Windows
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
* **Operating System:** Windows 10 or 11 (64-bit recommended)
* **Python:** Python 3.10 or higher

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/samjanjua6/PyAcro.git
   cd PyAcro
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch PyAcro:**
   ```bash
   python -m pyacrobat.main
   ```
   *Alternatively, double-click `run.bat`.*

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + O` | Open PDF Document |
| `Ctrl + S` | Save Active Document |
| `Ctrl + Shift + S` | Save As (New File) |
| `Ctrl + I` | Open & Focus AI Document Copilot |
| `Ctrl + +` / `Ctrl + =` | Zoom In |
| `Ctrl + -` | Zoom Out |
| `Ctrl + 0` | Fit Page to Viewport |
| `Page Up` / `Page Down` | Previous / Next Page |

---

## 🔒 Security & Privacy Invariants

* **Non-Destructive Operations:** PyAcro uses atomic file writes and never overwrites an existing document without explicit user confirmation.
* **100% Offline Capable:** The PDF rendering engine, Tesseract OCR, annotation serialization, and the Smart Local AI Engine execute entirely on your local machine with zero external network dependencies.
* **Data Privacy:** Document text is only transmitted to external cloud services (Google Gemini or OpenAI) when explicitly configured and initiated by the user.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
