"""
Adobe Acrobat-style AI Document Assistant Chat Panel & Settings Dialog.
Features message cards with clickable page citations, quick action pills,
markdown rendering, copy-to-clipboard, and pluggable provider settings.
"""

import os
import re
from typing import Optional, List, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QComboBox, QDialog, QFormLayout,
    QMessageBox, QApplication, QFrame, QScrollArea, QToolButton
)
from PySide6.QtCore import Qt, Signal, QUrl

from pyacrobat.core.ai_copilot import AICopilotManager
from pyacrobat.ui.styles import ThemeManager


class AISettingsDialog(QDialog):
    """Configuration dialog for AI Copilot providers (Local, Gemini, Ollama/OpenAI)."""

    def __init__(self, manager: AICopilotManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Assistant Settings")
        self.resize(440, 320)
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.combo_provider = QComboBox()
        self.combo_provider.addItem("Smart Local Engine (Offline & 100% Private)", "local")
        self.combo_provider.addItem("Google Gemini (Cloud API)", "gemini")
        self.combo_provider.addItem("Ollama / Local LLM (http://localhost:11434)", "ollama_openai")

        current_prov = self.manager.settings.value("provider", "local")
        idx = self.combo_provider.findData(current_prov)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("AI Provider:", self.combo_provider)

        # Gemini settings
        self.input_gemini_key = QLineEdit()
        self.input_gemini_key.setEchoMode(QLineEdit.Password)
        self.input_gemini_key.setText(self.manager.settings.value("gemini_key", ""))
        self.input_gemini_key.setPlaceholderText("Paste Gemini API Key here...")
        form.addRow("Gemini API Key:", self.input_gemini_key)

        self.input_gemini_model = QLineEdit()
        self.input_gemini_model.setText(self.manager.settings.value("gemini_model", "gemini-1.5-flash"))
        form.addRow("Gemini Model:", self.input_gemini_model)

        # Ollama / OpenAI settings
        self.input_openai_url = QLineEdit()
        self.input_openai_url.setText(self.manager.settings.value("openai_url", "http://localhost:11434/v1"))
        form.addRow("Ollama / API URL:", self.input_openai_url)

        self.input_openai_model = QLineEdit()
        self.input_openai_model.setText(self.manager.settings.value("openai_model", "llama3"))
        form.addRow("Ollama Model:", self.input_openai_model)

        self.input_openai_key = QLineEdit()
        self.input_openai_key.setEchoMode(QLineEdit.Password)
        self.input_openai_key.setText(self.manager.settings.value("openai_key", ""))
        self.input_openai_key.setPlaceholderText("Optional for local Ollama")
        form.addRow("Ollama/OpenAI Key:", self.input_openai_key)

        layout.addLayout(form)

        # Button Row
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("accentButton")
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        self._on_provider_changed()

    def _on_provider_changed(self):
        prov = self.combo_provider.currentData()
        is_gemini = (prov == "gemini")
        is_ollama = (prov == "ollama_openai")

        self.input_gemini_key.setEnabled(is_gemini)
        self.input_gemini_model.setEnabled(is_gemini)
        self.input_openai_url.setEnabled(is_ollama)
        self.input_openai_model.setEnabled(is_ollama)
        self.input_openai_key.setEnabled(is_ollama)

    def _save_settings(self):
        prov = self.combo_provider.currentData()
        self.manager.set_provider(
            prov,
            gemini_key=self.input_gemini_key.text().strip(),
            gemini_model=self.input_gemini_model.text().strip(),
            openai_url=self.input_openai_url.text().strip(),
            openai_model=self.input_openai_model.text().strip(),
            openai_key=self.input_openai_key.text().strip()
        )
        self.accept()


class AIChatPanel(QWidget):
    """
    Acrobat-styled conversational assistant panel with quick pills,
    markdown rendering, and interactive page citations.
    """

    page_jump_requested = Signal(int)  # 1-based page number to scroll canvas to

    def __init__(self, manager: Optional[AICopilotManager] = None, parent=None):
        super().__init__(parent)
        self.manager = manager or AICopilotManager()
        self.current_page: int = 1
        self.chat_history: List[Tuple[str, str]] = []
        self.init_ui()
        self.manager.query_finished.connect(self._on_query_success)
        self.manager.query_error.connect(self._on_query_error)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(4)

        self.lbl_title = QLabel("✨ AI Assistant")
        self.lbl_title.setObjectName("drawerHeaderTitle")
        header.addWidget(self.lbl_title)

        self.lbl_provider_badge = QLabel(f"[{self.manager.get_provider_name()}]")
        self.lbl_provider_badge.setObjectName("providerBadge")
        header.addWidget(self.lbl_provider_badge)
        header.addStretch()

        btn_settings = QToolButton()
        btn_settings.setText("⚙")
        btn_settings.setToolTip("Configure AI Provider & Keys")
        btn_settings.setObjectName("ghostToolButton")
        btn_settings.clicked.connect(self.open_settings)
        header.addWidget(btn_settings)

        btn_clear = QToolButton()
        btn_clear.setText("🗑")
        btn_clear.setToolTip("Clear Chat History")
        btn_clear.setObjectName("ghostToolButton")
        btn_clear.clicked.connect(self.clear_chat)
        header.addWidget(btn_clear)

        layout.addLayout(header)

        # Quick Action Pills Row
        pill_layout = QHBoxLayout()
        pill_layout.setSpacing(4)

        btn_doc_summary = QPushButton("📑 Doc")
        btn_doc_summary.setToolTip("Generate Executive Document Summary")
        btn_doc_summary.setObjectName("pillButton")
        btn_doc_summary.clicked.connect(lambda: self.ask("Summarize document"))
        pill_layout.addWidget(btn_doc_summary)

        btn_page_summary = QPushButton("📄 Page")
        btn_page_summary.setToolTip("Summarize Visible Page")
        btn_page_summary.setObjectName("pillButton")
        btn_page_summary.clicked.connect(lambda: self.ask("Summarize page"))
        pill_layout.addWidget(btn_page_summary)

        btn_tables = QPushButton("📊 Tables")
        btn_tables.setToolTip("Extract Tabular Grids to Markdown")
        btn_tables.setObjectName("pillButton")
        btn_tables.clicked.connect(lambda: self.ask("Extract tables"))
        pill_layout.addWidget(btn_tables)

        btn_terms = QPushButton("💡 Terms")
        btn_terms.setToolTip("Extract Key Terms & Definitions")
        btn_terms.setObjectName("pillButton")
        btn_terms.clicked.connect(lambda: self.ask("Key terms"))
        pill_layout.addWidget(btn_terms)

        layout.addLayout(pill_layout)

        # Chat Conversation Browser
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(False)
        self.chat_browser.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_browser.setMinimumHeight(160)
        self.chat_browser.setObjectName("chatBrowser")
        layout.addWidget(self.chat_browser)

        # Status indicator
        self.lbl_status = QLabel("Ready to assist")
        self.lbl_status.setObjectName("statusLabel")
        layout.addWidget(self.lbl_status)

        # Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(4)

        self.input_query = QLineEdit()
        self.input_query.setPlaceholderText("Ask about this document...")
        self.input_query.returnPressed.connect(self._on_send_clicked)
        input_row.addWidget(self.input_query)

        self.btn_send = QPushButton("Ask")
        self.btn_send.setObjectName("accentButton")
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

        self._show_welcome_message()

    def set_current_page(self, page_num: int):
        self.current_page = page_num

    def update_theme(self):
        """Refreshes chat display colors to match the active theme tokens."""
        self.lbl_provider_badge.setText(f"[{self.manager.get_provider_name()}]")
        self.chat_browser.clear()
        self._show_welcome_message()
        for role, text in self.chat_history:
            if role == "user":
                self._render_user_message(text)
            else:
                self._render_ai_message(text)

    def _show_welcome_message(self):
        tokens = ThemeManager.get_tokens()
        welcome_html = (
            f"<div style='color: {tokens.text_muted}; font-size: 11px; margin-bottom: 8px;'>"
            f"<b>👋 Welcome to Acrobat AI Copilot</b><br>"
            f"Ask questions, summarize key sections, or extract structured data.<br>"
            f"<i>Click any page citation e.g. <a href='page://1' style='color: {tokens.accent}; text-decoration: underline;'>[Page 1]</a> to jump directly to it!</i>"
            f"</div><hr style='border: 0; border-top: 1px solid {tokens.border};'><br>"
        )
        self.chat_browser.setHtml(welcome_html)

    def _on_anchor_clicked(self, url: QUrl):
        if url.scheme() == "page":
            val = url.path().lstrip("/") or url.host()
            try:
                self.page_jump_requested.emit(int(val))
                return
            except ValueError:
                pass
        m = re.findall(r"\d+", url.toString())
        if m:
            self.page_jump_requested.emit(int(m[-1]))

    def _format_markdown_to_html(self, text: str) -> str:
        """Converts basic markdown, headings, bullet points, and [Page X] links to rich HTML."""
        tokens = ThemeManager.get_tokens()
        html = text

        # Replace [Page X] with clickable links
        def page_repl(m):
            p = m.group(1)
            return (
                f"<a href='page:{p}' style='background-color: {tokens.accent}; color: {tokens.text_on_accent}; "
                f"padding: 1px 5px; border-radius: 3px; text-decoration: none; font-weight: bold;'>Page {p}</a>"
            )

        html = re.sub(r"\[Page\s*(\d+)\]", page_repl, html)

        # Bold & Code
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)
        html = re.sub(
            r"`(.*?)`",
            rf"<code style='background-color: {tokens.surface_raised}; border: 1px solid {tokens.border}; padding: 1px 4px; border-radius: 2px; color: {tokens.text};'>\1</code>",
            html
        )

        # Headings
        html = re.sub(r"###\s*(.*?)\n", rf"<h4 style='color: {tokens.text}; margin-top: 6px; margin-bottom: 2px;'>\1</h4>", html)
        html = re.sub(r"####\s*(.*?)\n", rf"<h5 style='color: {tokens.text_muted}; margin-top: 4px; margin-bottom: 2px;'>\1</h5>", html)

        # Lists & Line breaks
        html = html.replace("\n- ", "<br>• ")
        html = html.replace("\n", "<br>")
        return html

    def _render_user_message(self, message: str):
        tokens = ThemeManager.get_tokens()
        user_html = (
            f"<div style='margin-top: 6px; margin-bottom: 6px; text-align: right;'>"
            f"<span style='background-color: {tokens.accent}; color: {tokens.text_on_accent}; padding: 4px 8px; border-radius: 6px; display: inline-block; font-size: 11px;'>"
            f"<b>You:</b> {message}</span></div>"
        )
        self.chat_browser.append(user_html)

    def append_user_message(self, message: str):
        self.chat_history.append(("user", message))
        self._render_user_message(message)

    def _render_ai_message(self, markdown_text: str):
        tokens = ThemeManager.get_tokens()
        formatted = self._format_markdown_to_html(markdown_text)
        ai_html = (
            f"<div style='margin-top: 6px; margin-bottom: 8px; background-color: {tokens.surface_raised}; border: 1px solid {tokens.border}; border-radius: 6px; padding: 8px; color: {tokens.text};'>"
            f"<div style='color: {tokens.accent}; font-weight: bold; font-size: 11px; margin-bottom: 4px;'>🤖 AI Copilot</div>"
            f"<div style='line-height: 1.4;'>{formatted}</div>"
            f"</div>"
        )
        self.chat_browser.append(ai_html)
        scrollbar = self.chat_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_ai_message(self, markdown_text: str):
        self.chat_history.append(("ai", markdown_text))
        self._render_ai_message(markdown_text)

    def ask(self, prompt: str):
        clean_p = prompt.strip()
        if not clean_p:
            return

        self.append_user_message(clean_p)
        self.lbl_status.setText("Thinking...")
        self.btn_send.setEnabled(False)
        self.input_query.setEnabled(False)

        self.manager.ask(clean_p, current_page=self.current_page)

    def _on_send_clicked(self):
        text = self.input_query.text().strip()
        if text:
            self.input_query.clear()
            self.ask(text)

    def _on_query_success(self, response: str):
        self.lbl_status.setText("Ready to assist")
        self.btn_send.setEnabled(True)
        self.input_query.setEnabled(True)
        self.append_ai_message(response)

    def _on_query_error(self, error_msg: str):
        self.lbl_status.setText("Error occurred")
        self.btn_send.setEnabled(True)
        self.input_query.setEnabled(True)
        self.append_ai_message(f"⚠️ Error: {error_msg}")

    def open_settings(self):
        dlg = AISettingsDialog(self.manager, parent=self)
        if dlg.exec():
            self.lbl_provider_badge.setText(f"[{self.manager.get_provider_name()}]")
            QMessageBox.information(self, "AI Settings Saved", f"Active AI Provider updated to {self.manager.get_provider_name()}.")

    def clear_chat(self):
        self.chat_history.clear()
        self.chat_browser.clear()
        self._show_welcome_message()

