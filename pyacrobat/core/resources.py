"""
Centralized Resource and Asset Path Resolver for Spectra PDF.
Ensures seamless asset discovery both during source development
and when bundled into a standalone Windows executable with PyInstaller.
"""
import os
import sys
from typing import Optional


def get_base_dir() -> str:
    """
    Returns the root directory for assets.
    When running under PyInstaller, sys._MEIPASS is the temporary bundle root.
    When running from source, points to the pyacrobat package directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(*subpaths: str) -> str:
    """Returns absolute path to a resource inside pyacrobat/resources."""
    base = get_base_dir()
    direct = os.path.join(base, "resources", *subpaths)
    if os.path.exists(direct):
        return direct
    alt = os.path.join(base, "pyacrobat", "resources", *subpaths)
    if os.path.exists(alt):
        return alt
    return direct


def get_icons_dir() -> str:
    """Returns the absolute path to the resources/icons directory."""
    return get_resource_path("icons")


def get_icon_path(icon_name: str) -> str:
    """Returns absolute path to an icon file inside resources/icons."""
    return os.path.join(get_icons_dir(), icon_name)


def get_tessdata_path() -> Optional[str]:
    """Returns absolute path to bundled tessdata directory if available."""
    base = get_base_dir()
    direct = os.path.join(base, "tessdata")
    if os.path.isdir(direct) and os.path.exists(os.path.join(direct, "eng.traineddata")):
        return direct
    alt = os.path.join(base, "pyacrobat", "tessdata")
    if os.path.isdir(alt) and os.path.exists(os.path.join(alt, "eng.traineddata")):
        return alt
    return None
