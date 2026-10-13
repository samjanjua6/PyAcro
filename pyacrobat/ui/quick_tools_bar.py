"""
Quick Tools Ribbon / Document Toolbar (Figma Acrobat Alignment)
Houses workspace tabs (All tools, Edit, Convert, E-Sign), utility icons, Share, and AI Assistant.
"""

from pyacrobat.ui.document_toolbar import (
    DocumentToolbar,
    WorkspaceTabButton,
    WorkspaceTabStrip,
    ToolbarIconButton,
    ToolbarSeparator,
    SharePillButton,
    AIAssistantPillButton,
)


class QuickToolsBar(DocumentToolbar):
    """
    Figma 56px Document Toolbar.
    Maintains class name QuickToolsBar for backward compatibility with existing tests and MainWindow.
    """
    pass
