# -*- mode: python ; coding: utf-8 -*-
"""
Spectra PDF Standalone Build Specification for PyInstaller.
Packages Spectra PDF into a production-hardened standalone Windows executable
with embedded Tesseract OCR data, Spectra vector icons, and PySide6 Qt6 runtime.
"""

import sys
import os

block_cipher = None

project_root = os.path.abspath(SPECPATH)

added_files = [
    (os.path.join(project_root, 'pyacrobat', 'resources'), 'resources'),
    (os.path.join(project_root, 'pyacrobat', 'resources'), os.path.join('pyacrobat', 'resources')),
    (os.path.join(project_root, 'pyacrobat', 'assets'), 'assets'),
    (os.path.join(project_root, 'pyacrobat', 'assets'), os.path.join('pyacrobat', 'assets')),
    (os.path.join(project_root, 'pyacrobat', 'tessdata'), 'tessdata'),
    (os.path.join(project_root, 'pyacrobat', 'tessdata'), os.path.join('pyacrobat', 'tessdata')),
]

hidden_imports = [
    'pymupdf',
    'fitz',
    'pytesseract',
    'edge_tts',
    'PIL',
    'PIL.Image',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'pyacrobat',
    'pyacrobat.core',
    'pyacrobat.core.pdf_document',
    'pyacrobat.core.pdf_editor',
    'pyacrobat.core.ocr_engine',
    'pyacrobat.core.export_engine',
    'pyacrobat.core.tts_engine',
    'pyacrobat.core.ai_copilot',
    'pyacrobat.core.recent_files',
    'pyacrobat.core.undo_commands',
    'pyacrobat.core.resources',
    'pyacrobat.ui',
    'pyacrobat.ui.styles',
    'pyacrobat.ui.main_window',
    'pyacrobat.ui.pdf_canvas',
    'pyacrobat.ui.page_render_manager',
    'pyacrobat.ui.selected_text_toolbar',
    'pyacrobat.ui.inline_text_editor',
    'pyacrobat.ui.app_nav_bar',
    'pyacrobat.ui.all_tools_panel',
    'pyacrobat.ui.edit_pdf_panel',
    'pyacrobat.ui.export_pdf_panel',
    'pyacrobat.ui.organizer_grid',
    'pyacrobat.ui.page_controls_bar',
    'pyacrobat.ui.page_utility_dialogs',
    'pyacrobat.ui.home_view',
    'pyacrobat.ui.about_dialog',
]

a = Analysis(
    [os.path.join(project_root, 'pyacrobat', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'tkinter', 'notebook', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpectraPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'pyacrobat', 'resources', 'icons', 'spectra_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SpectraPDF',
)
