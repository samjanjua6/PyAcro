"""
Adobe Spectrum-inspired Design Token System and Dynamic QSS Generator for PyAcrobat.
Centralizes all theme colors behind semantic tokens (bg, surface, text, text-muted, border, accent)
so that no UI component hardcodes white or black.
"""

import os
from dataclasses import dataclass
from typing import Optional
from PySide6.QtGui import QIcon


@dataclass(frozen=True)
class ThemeTokens:
    name: str              # 'dark' or 'light'
    bg: str                # Window base background
    surface: str           # Drawer, rail, toolbar, panel surfaces
    surface_raised: str    # Elevated cards, tool boxes, popup containers
    surface_sunken: str    # Inputs, chat browser, list views
    canvas_bg: str         # PDF canvas backdrop behind pages
    text: str              # Primary foreground text
    text_muted: str        # Subtitles, placeholder text, secondary labels
    text_dim: str          # Subtle captions, counts
    text_on_accent: str    # Text on accent buttons (#FFFFFF)
    border: str            # Standard card & divider border
    border_subtle: str     # Light dividers, rail separators
    border_strong: str     # Card hover / active borders
    accent: str            # Adobe Acrobat Blue (#1473E6)
    accent_hover: str      # Hover blue (#0D66D0)
    accent_subtle: str     # Selection tint background
    danger: str            # Red for destructive actions (#FF5252 in dark / #D32F2F in light)
    success: str           # Status verified (#4CAF50 in dark / #2E7D32 in light)
    warning: str           # Scanned badge / warnings (#FFB020 in dark / #E65100 in light)


# Dark Mode Theme Tokens (Acrobat Dark Spectrum)
DARK_TOKENS = ThemeTokens(
    name="dark",
    bg="#181818",
    surface="#1E1E1E",
    surface_raised="#252525",
    surface_sunken="#161616",
    canvas_bg="#1A1A1A",
    text="#F5F5F7",
    text_muted="#A0A0A0",
    text_dim="#707070",
    text_on_accent="#FFFFFF",
    border="#333333",
    border_subtle="#2A2A2A",
    border_strong="#4A4A4A",
    accent="#1473E6",
    accent_hover="#0D66D0",
    accent_subtle="#1E3A5F",
    danger="#FF5252",
    success="#4CAF50",
    warning="#FFB020"
)

# Light Mode Theme Tokens (Acrobat Light Spectrum - Matches Figma 3:12925)
LIGHT_TOKENS = ThemeTokens(
    name="light",
    bg="#F8F8F8",
    surface="#FFFFFF",
    surface_raised="#FFFFFF",
    surface_sunken="#FFFFFF",
    canvas_bg="#E8E8E8",
    text="#242424",
    text_muted="#626262",
    text_dim="#858585",
    text_on_accent="#FFFFFF",
    border="#D9D9D9",
    border_subtle="#E8E8E8",
    border_strong="#B0B0B0",
    accent="#1473E6",
    accent_hover="#0D66D0",
    accent_subtle="#EAF3FF",
    danger="#EB1000",
    success="#268E6C",
    warning="#E65100"
)


class ThemeManager:
    """Manages active theme state and token retrieval across the application."""
    _current: ThemeTokens = LIGHT_TOKENS

    @classmethod
    def get_tokens(cls) -> ThemeTokens:
        return cls._current

    @classmethod
    def set_theme(cls, name: str) -> ThemeTokens:
        cls._current = LIGHT_TOKENS if name.lower() == "light" else DARK_TOKENS
        return cls._current

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current.name == "dark"


def generate_theme_stylesheet(t: ThemeTokens) -> str:
    """
    Generates a complete, symmetrical Qt stylesheet strictly utilizing the semantic tokens.
    """
    return f"""
/* Global Reset & Base Typography */
QWidget {{
    background-color: {t.surface};
    color: {t.text};
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 12px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
}}

QMainWindow {{
    background-color: {t.bg};
}}

/* Application Menu Bar (Acrobat-style top menu, #F8F8F8 in light) */
QMenuBar {{
    background-color: {t.surface if t.name == "dark" else "#F8F8F8"};
    color: {t.text};
    border-bottom: 1px solid {t.border};
    font-size: 11px;
    padding: 2px 8px;
    spacing: 4px;
}}

QMenuBar::item {{
    background: transparent;
    color: {t.text};
    padding: 4px 10px;
    margin: 2px 0px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {t.surface_raised if t.name == "dark" else "#ECECEC"};
    color: {t.text};
}}

QMenuBar::item:pressed {{
    background-color: {t.accent_subtle if t.name == "dark" else "#E5E5E5"};
    color: {t.text};
}}

#menuTitleLabel {{
    color: {t.text_muted};
    font-size: 11px;
    padding-right: 14px;
    font-weight: 400;
}}

/* Top Ribbon & Action Bars */
QToolBar {{
    background-color: {t.surface};
    border-bottom: 1px solid {t.border};
    padding: 2px 6px;
    spacing: 4px;
}}

QToolButton {{
    background-color: transparent;
    color: {t.text};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 6px;
    font-weight: 500;
}}

QToolButton:hover {{
    background-color: {t.surface_raised};
    color: {t.text};
    border: 1px solid {t.border};
}}

QToolButton:pressed, QToolButton:checked {{
    background-color: {t.accent};
    color: {t.text_on_accent};
    border: 1px solid {t.accent};
}}

/* Floating Quick Tools Pill Ribbon */
#quickToolsFrame {{
    background-color: {t.surface_raised};
    border: 1px solid {t.border};
    border-radius: 18px;
    padding: 2px 6px;
}}

#quickToolsFrame QPushButton, #quickToolsFrame QToolButton {{
    background-color: transparent;
    color: {t.text};
    border: none;
    border-radius: 12px;
    padding: 4px 6px;
    font-size: 12px;
}}

#quickToolsFrame QPushButton:hover, #quickToolsFrame QToolButton:hover {{
    background-color: {t.surface};
    color: {t.text};
}}

#quickToolsFrame QPushButton:checked, #quickToolsFrame QToolButton:checked {{
    background-color: {t.accent};
    color: {t.text_on_accent};
}}

/* Tab System */
QTabWidget::pane {{
    border-top: 1px solid {t.border};
    background-color: {t.surface};
}}

QTabBar::tab {{
    background-color: {t.bg};
    color: {t.text_muted};
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    border: 1px solid transparent;
    border-top: 2px solid transparent;
    min-width: 90px;
}}

QTabBar::tab:hover {{
    background-color: {t.surface_raised};
    color: {t.text};
}}

QTabBar::tab:selected {{
    background-color: {t.surface};
    color: {t.text};
    border-top: 2px solid {t.accent};
}}

/* Scroll Areas & Studio Canvas */
QScrollArea {{
    background-color: {t.surface};
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: {t.surface};
}}

#pdfCanvasArea {{
    background-color: {t.canvas_bg};
    border: none;
}}

#pdfCanvasArea > QWidget > QWidget {{
    background-color: {t.canvas_bg};
}}

#pdfCanvasContainer {{
    background-color: {t.canvas_bg};
}}

#documentViewportContainer {{
    background-color: {t.canvas_bg};
}}

#floatingToolsContainer {{
    background-color: transparent;
}}

/* Splitters & Dividers */
QSplitter::handle:horizontal {{
    width: 4px;
    background-color: {t.border_subtle};
}}

QSplitter::handle:horizontal:hover {{
    background-color: {t.accent};
}}

/* Custom Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: {t.surface};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {t.border_strong};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t.text_dim};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {t.surface};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {t.border_strong};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {t.text_dim};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Inputs, Text Editors & Combos */
QLineEdit {{
    background-color: {t.surface_sunken};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 3px 6px;
}}

QLineEdit:focus {{
    border: 1px solid {t.accent};
}}

QTextEdit, QTextBrowser {{
    background-color: {t.surface_sunken};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 4px;
}}

QPushButton {{
    background-color: {t.surface_raised};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 4px 8px;
}}

QPushButton:hover {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.border_strong};
}}

QComboBox {{
    background-color: {t.surface_raised};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 3px 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {t.surface_raised};
    color: {t.text};
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    border: 1px solid {t.border};
}}

/* List & Tree Views */
QListWidget, QTreeWidget {{
    background-color: {t.surface_sunken};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 4px;
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {t.surface_raised};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {t.accent};
    color: {t.text_on_accent};
}}

/* Popup Menus */
QMenu {{
    background-color: {t.surface_raised};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 18px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {t.accent};
    color: {t.text_on_accent};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t.border};
    margin: 4px 6px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {t.surface if t.name == "dark" else "#F8F8F8"};
    color: {t.text_muted};
    border-top: 1px solid {t.border};
    font-size: 11px;
    padding: 2px 8px;
}}

QStatusBar QLabel {{
    background: transparent;
    color: {t.text_muted};
    font-size: 11px;
    padding: 0px 4px;
}}

#statusBarSaveBadge {{
    color: {t.success if t.name == "light" else "#4CAF50"};
    font-weight: 500;
}}

#statusBarSaveBadgeDirty {{
    color: {t.warning if t.name == "light" else "#FFB020"};
    font-weight: 500;
}}

#statusBarInfoBadge {{
    color: {t.text_muted};
    font-size: 11px;
}}

#statusBarSecurityBadge {{
    color: {t.text_muted};
    font-size: 11px;
    padding-right: 8px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {t.border_subtle};
    border-radius: 2px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: 2px;
}}

/* ==========================================
   Semantic Theme Classes & Object Names
   ========================================== */

#drawerHeaderTitle {{
    font-weight: bold;
    color: {t.text};
    font-size: 13px;
}}

#powerSectionTitle {{
    color: {t.text_muted};
    font-weight: bold;
    font-size: 11px;
}}

#powerBox {{
    background-color: {t.surface_raised};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 6px;
}}

#powerListWidget {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.border};
    border-radius: 4px;
    color: {t.text};
}}

#chatBrowser {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 6px;
    color: {t.text};
}}

#pillButton {{
    background-color: {t.surface_raised};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 10px;
    font-size: 10px;
    padding: 3px 6px;
}}

#pillButton:hover {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.accent};
}}

#accentButton {{
    background-color: {t.accent};
    color: {t.text_on_accent};
    font-weight: bold;
    border-radius: 4px;
    border: 1px solid {t.accent};
}}

#accentButton:hover {{
    background-color: {t.accent_hover};
    border: 1px solid {t.accent_hover};
}}

#dangerButton {{
    background-color: transparent;
    color: {t.danger};
    border: 1px solid {t.border};
    border-radius: 4px;
}}

#dangerButton:hover {{
    background-color: {t.danger};
    color: {t.text_on_accent};
    border: 1px solid {t.danger};
}}

#subtleLabel {{
    color: {t.text_muted};
    font-size: 11px;
}}

#statusLabel {{
    color: {t.text_dim};
    font-size: 10px;
}}

#dividerLine {{
    color: {t.border};
    background-color: {t.border};
}}

#leftRail {{
    background-color: {t.surface};
    border-right: 1px solid {t.border_subtle};
}}

#sidebarDrawer {{
    background-color: {t.surface};
    border-right: 1px solid {t.border};
}}

#rightDrawer {{
    background-color: {t.surface};
    border-left: 1px solid {t.border};
}}

#organizerToolbar {{
    background-color: {t.surface};
    border-bottom: 1px solid {t.border};
    padding: 4px;
}}

#organizerCanvasArea {{
    background-color: {t.canvas_bg};
    border: none;
}}

#aiRibbonButton {{
    color: {t.accent};
    font-weight: bold;
}}

#providerBadge {{
    color: {t.success};
    font-size: 10px;
    font-weight: bold;
}}

#ghostToolButton {{
    border: none;
    padding: 2px 4px;
    font-size: 13px;
    color: {t.text_muted};
}}

#ghostToolButton:hover {{
    color: {t.text};
}}
"""


ACROBAT_DARK_THEME = generate_theme_stylesheet(DARK_TOKENS)
ACROBAT_LIGHT_THEME = generate_theme_stylesheet(LIGHT_TOKENS)


def get_app_icon() -> QIcon:
    """Returns the multi-resolution Spectra PDF application QIcon."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_dir, "resources", "icons", "spectra_icon.ico")
    png_path = os.path.join(base_dir, "resources", "icons", "spectra_icon.png")
    svg_path = os.path.join(base_dir, "resources", "icons", "spectra_icon.svg")

    if not os.path.exists(ico_path):
        ico_path = os.path.join(base_dir, "resources", "icons", "adobe_acrobat.ico")
        png_path = os.path.join(base_dir, "resources", "icons", "adobe_acrobat.png")
        svg_path = os.path.join(base_dir, "resources", "icons", "adobe_acrobat.svg")

    icon = QIcon()
    if os.path.exists(ico_path):
        icon.addFile(ico_path)
    if os.path.exists(png_path):
        icon.addFile(png_path)
    if os.path.exists(svg_path):
        icon.addFile(svg_path)
    return icon

