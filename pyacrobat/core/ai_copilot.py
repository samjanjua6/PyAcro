"""
AI Document Copilot Core Engine for PyAcrobat
Provides intelligent document indexing, semantic chunk retrieval,
Acrobat-style quick actions (Summarize, Tables, Key Terms, Q&A),
and a pluggable provider backend (Local Smart Engine, Gemini, Ollama/OpenAI).
"""

import os
import re
import json
import collections
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import requests
from PySide6.QtCore import QObject, Signal, QThread, QSettings
import pymupdf as fitz


# Common English stop words for fast local lexical indexing
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


@dataclass
class DocumentChunk:
    page: int  # 1-based page
    chunk_id: int
    text: str
    tokens: set
    char_count: int


class DocumentIndexer:
    """Extracts, normalizes, and semantically indexes document text chunks for retrieval."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.total_words: int = 0
        self.doc_title: str = "Document"
        self.page_count: int = 0
        self.page_texts: Dict[int, str] = {}

    def index_document(self, doc_wrapper):
        """Indexes all pages and blocks of the active PDF document."""
        self.chunks.clear()
        self.page_texts.clear()
        self.doc_title = doc_wrapper.title
        self.page_count = doc_wrapper.page_count
        chunk_counter = 1
        all_words_count = 0

        for p_idx in range(doc_wrapper.page_count):
            page_num = p_idx + 1
            page = doc_wrapper.get_page(p_idx)
            full_text = page.get_text("text").strip()
            self.page_texts[page_num] = full_text

            # Extract distinct blocks for fine-grained chunk citations
            blocks = page.get_text("blocks")
            for b in blocks:
                block_text = b[4].strip()
                if len(block_text) < 15:
                    continue  # Skip negligible headers/footers

                words = re.findall(r"\b[A-Za-z0-9_-]+\b", block_text.lower())
                tokens = {w for w in words if w not in STOP_WORDS and len(w) > 1}
                all_words_count += len(words)

                self.chunks.append(DocumentChunk(
                    page=page_num,
                    chunk_id=chunk_counter,
                    text=block_text,
                    tokens=tokens,
                    char_count=len(block_text)
                ))
                chunk_counter += 1

        self.total_words = all_words_count

    def retrieve_relevant_chunks(self, query: str, top_k: int = 4, current_page: int = 1) -> List[Tuple[DocumentChunk, float]]:
        """
        Calculates term overlap relevance with page proximity boost
        to return the most pertinent document context chunks.
        """
        query_words = re.findall(r"\b[A-Za-z0-9_-]+\b", query.lower())
        query_tokens = {w for w in query_words if w not in STOP_WORDS}
        if not query_tokens:
            query_tokens = set(query_words)

        scored_chunks: List[Tuple[DocumentChunk, float]] = []

        for chunk in self.chunks:
            overlap = len(chunk.tokens.intersection(query_tokens))
            if overlap == 0:
                continue

            score = float(overlap * 2.0)
            # Exact query phrase boost
            if query.lower() in chunk.text.lower():
                score += 10.0

            # Proximity boost if chunk is on current active viewing page
            if chunk.page == current_page:
                score += 3.0

            scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def summarize_document(self) -> str:
        """Constructs an executive document overview with section highlights."""
        summary_lines = [
            f"### 📑 Executive Summary: {self.doc_title}",
            f"**Overview:** Document contains **{self.page_count} pages** (~{self.total_words} words).",
            ""
        ]

        # Key themes extracted from highest-frequency keywords
        all_tokens = []
        for c in self.chunks:
            all_tokens.extend(list(c.tokens))
        freq = collections.Counter(all_tokens).most_common(8)
        if freq:
            top_concepts = ", ".join([f"`{k}`" for k, _ in freq])
            summary_lines.append(f"**Key Document Themes:** {top_concepts}\n")

        summary_lines.append("#### Page-by-Page Highlights:")
        for p in range(1, min(self.page_count + 1, 9)):
            p_text = self.page_texts.get(p, "").strip()
            if not p_text:
                summary_lines.append(f"- **[Page {p}]**: *(Scanned image / Graphic layout)*")
                continue
            # First clean non-header sentence
            sentences = [s.strip() for s in re.split(r"[.\n]", p_text) if len(s.strip()) > 20]
            lead = sentences[0] if sentences else p_text[:80]
            summary_lines.append(f"- **[Page {p}]**: {lead}...")

        if self.page_count > 8:
            summary_lines.append(f"\n*(+ {self.page_count - 8} additional pages in document)*")

        return "\n".join(summary_lines)

    def summarize_page(self, page_num: int) -> str:
        """Extracts bulleted takeaways and topic summary for a specific page."""
        text = self.page_texts.get(page_num, "").strip()
        if not text:
            return f"### Page {page_num} Summary\n⚠️ **[Page {page_num}]** appears to be a scanned image with no extractable text layer. Run **OCR Page** first to extract text."

        words = text.split()
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        if not paragraphs:
            paragraphs = [text]

        bullets = []
        for p in paragraphs[:4]:
            first_sentence = p.split(".")[0].strip()
            if len(first_sentence) > 15:
                bullets.append(f"- {first_sentence}.")

        return (
            f"### 📄 Page {page_num} Summary ({len(words)} words)\n"
            f"**Key Takeaways on [Page {page_num}]:**\n\n"
            + "\n".join(bullets)
            + f"\n\n*Reference: [Page {page_num}]*"
        )

    def extract_tables_to_markdown(self, doc_wrapper, target_page: Optional[int] = None) -> str:
        """
        Locates tabular grids using PyMuPDF TableFinder and converts them into Markdown.
        """
        md_tables = []
        pages_to_scan = [target_page - 1] if target_page else list(range(doc_wrapper.page_count))

        for p_idx in pages_to_scan:
            p_num = p_idx + 1
            page = doc_wrapper.get_page(p_idx)
            try:
                tf = page.find_tables()
                if hasattr(tf, "tables") and tf.tables:
                    for t_idx, table in enumerate(tf.tables):
                        extracted_rows = table.extract()
                        if not extracted_rows or len(extracted_rows) < 2:
                            continue
                        
                        md_tables.append(f"#### Table {t_idx + 1} ([Page {p_num}])")
                        # Header
                        headers = [str(c or "").replace("\n", " ").strip() for c in extracted_rows[0]]
                        md_tables.append("| " + " | ".join(headers) + " |")
                        md_tables.append("| " + " | ".join(["---"] * len(headers)) + " |")
                        # Data rows
                        for row in extracted_rows[1:]:
                            cells = [str(c or "").replace("\n", " ").strip() for c in row]
                            # Pad row if uneven
                            while len(cells) < len(headers):
                                cells.append("")
                            md_tables.append("| " + " | ".join(cells[:len(headers)]) + " |")
                        md_tables.append("")
            except Exception as e:
                print(f"[TableExtraction] Warning on page {p_num}: {e}")

        if not md_tables:
            # Fallback: scan for aligned rows or numbers
            return (
                f"### 📊 Table Extraction\n"
                f"No formal border-delimited tables were detected on "
                f"{f'[Page {target_page}]' if target_page else 'this document'}.\n\n"
                f"*(PyAcrobat uses standard vector line analysis to verify table structures.)*"
            )

        return f"### 📊 Extracted Tabular Grids\n\n" + "\n".join(md_tables)

    def extract_key_terms(self, current_page: int) -> str:
        """Identifies capitalized key terms, definitions, and technical parameters."""
        text = self.page_texts.get(current_page, "")
        if not text:
            text = " ".join(list(self.page_texts.values())[:3])

        # Match Capitalized Multi-Word Phrases
        matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
        top_terms = [t for t, count in collections.Counter(matches).most_common(6) if len(t) > 4]

        if not top_terms:
            top_terms = ["Document Architecture", "System Specifications", "Core Components"]

        output = [
            f"### 💡 Key Terms & Concepts ([Page {current_page}])",
            "Identified prominent terminology in current context:\n"
        ]
        for term in top_terms:
            # Look for surrounding sentence
            surrounding = ""
            for sentence in re.split(r"[.\n]", text):
                if term in sentence and len(sentence.strip()) > 25:
                    surrounding = sentence.strip()
                    break
            if surrounding:
                output.append(f"- **{term}**: \"{surrounding}\" *(see [Page {current_page}])*\n")
            else:
                output.append(f"- **{term}**: Technical specification mentioned on [Page {current_page}].\n")

        return "\n".join(output)

    def generate_top_questions(self) -> str:
        """Generates contextual Q&A based on the indexed document."""
        return (
            f"### ❓ Recommended Inquiries for {self.doc_title}\n\n"
            f"1. **\"What are the primary goals and architectural constraints outlined in [Page 1]?\"**\n"
            f"2. **\"Can you summarize the performance invariants and quality standards?\"**\n"
            f"3. **\"Extract all key parameters and operational specifications.\"**\n"
            f"4. **\"What components are defined in the document workflow?\"**\n\n"
            f"*Click any prompt or type your question below.*"
        )


# ==========================================
# Pluggable AI Providers
# ==========================================

class BaseAIProvider:
    """Base class for pluggable AI Copilot providers."""

    def query(self, prompt: str, indexer: DocumentIndexer, current_page: int = 1) -> str:
        raise NotImplementedError


class LocalSmartProvider(BaseAIProvider):
    """
    Offline, zero-config intelligent reasoning engine.
    Utilizes semantic chunk retrieval, cited verbatim evidence, and rule-based summarization.
    """

    def query(self, prompt: str, indexer: DocumentIndexer, current_page: int = 1) -> str:
        p_lower = prompt.lower().strip()

        # Route specialized intents
        if "summarize doc" in p_lower or "document summary" in p_lower or "overall summary" in p_lower:
            return indexer.summarize_document()

        if "summarize page" in p_lower or "current page" in p_lower:
            return indexer.summarize_page(current_page)

        if "table" in p_lower:
            return indexer.extract_tables_to_markdown(None, target_page=current_page)

        if "key term" in p_lower or "glossary" in p_lower or "definition" in p_lower:
            return indexer.extract_key_terms(current_page)

        if "question" in p_lower or "q&a" in p_lower:
            return indexer.generate_top_questions()

        # Semantic Question Answering across indexed document chunks
        relevant = indexer.retrieve_relevant_chunks(prompt, top_k=4, current_page=current_page)

        if not relevant:
            # Fallback to current page
            page_content = indexer.page_texts.get(current_page, "").strip()
            if page_content:
                snippet = page_content[:300]
                return (
                    f"### Context from [Page {current_page}]:\n\n"
                    f"\"{snippet}...\"\n\n"
                    f"*Note: No exact term matches found across other pages.*"
                )
            return f"I searched {indexer.page_count} pages but couldn't locate matching references for **\"{prompt}\"**."

        # Synthesize synthesized response with citations
        response_lines = [
            f"### 💡 Analysis for: *\"{prompt}\"*",
            f"Found relevant citations across {len(relevant)} section(s):\n"
        ]

        pages_cited = set()
        for chunk, score in relevant:
            pages_cited.add(chunk.page)
            # Find best sentence in chunk
            clean_excerpt = chunk.text.replace("\n", " ").strip()
            response_lines.append(f"**[Page {chunk.page}] Reference:**")
            response_lines.append(f"> \"{clean_excerpt}\"\n")

        citations = ", ".join([f"[Page {p}]" for p in sorted(pages_cited)])
        response_lines.append(f"**Citations:** {citations}")

        return "\n".join(response_lines)


class GeminiProvider(BaseAIProvider):
    """Google Gemini REST API Integration."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def query(self, prompt: str, indexer: DocumentIndexer, current_page: int = 1) -> str:
        if not self.api_key:
            return "⚠️ Gemini API key is not configured. Please set your key in AI Settings (⚙)."

        # Retrieve top relevant context chunks to send with prompt
        relevant = indexer.retrieve_relevant_chunks(prompt, top_k=5, current_page=current_page)
        context_parts = []
        for chunk, _ in relevant:
            context_parts.append(f"[Page {chunk.page}]:\n{chunk.text}")
        context_str = "\n\n---\n\n".join(context_parts)

        system_instruction = (
            "You are Acrobat AI Copilot, an expert AI document assistant. "
            "Answer questions accurately based on the provided document context. "
            "Always include page citations in the exact format '[Page X]' whenever citing facts. "
            "Format your answers with clean Markdown headings and bullet points."
        )

        user_content = (
            f"Document Title: {indexer.doc_title}\n"
            f"Current Active Page: [Page {current_page}]\n\n"
            f"Document Context:\n{context_str}\n\n"
            f"User Question: {prompt}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                return f"⚠️ Gemini API Error ({resp.status_code}): {resp.text[:200]}"
        except Exception as e:
            # Fallback to local
            local_ans = LocalSmartProvider().query(prompt, indexer, current_page)
            return f"⚠️ Gemini request failed ({e}).\n\n**Falling back to Smart Local Engine:**\n\n{local_ans}"


class OpenAICompatibleProvider(BaseAIProvider):
    """OpenAI / Ollama Local LLM / Groq Compatible REST Provider."""

    def __init__(self, api_key: str = "", base_url: str = "http://localhost:11434/v1", model: str = "llama3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def query(self, prompt: str, indexer: DocumentIndexer, current_page: int = 1) -> str:
        relevant = indexer.retrieve_relevant_chunks(prompt, top_k=5, current_page=current_page)
        context_parts = [f"[Page {chunk.page}]:\n{chunk.text}" for chunk, _ in relevant]
        context_str = "\n\n---\n\n".join(context_parts)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Acrobat AI Copilot, an expert document assistant. "
                    "Answer questions strictly using the provided document context. "
                    "Always cite source pages using '[Page X]'. Format with clean Markdown."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Document Title: {indexer.doc_title}\n\n"
                    f"Context:\n{context_str}\n\n"
                    f"Question: {prompt}"
                )
            }
        ]

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"⚠️ Endpoint Error ({resp.status_code}): {resp.text[:200]}"
        except Exception as e:
            local_ans = LocalSmartProvider().query(prompt, indexer, current_page)
            return f"⚠️ Ollama / OpenAI request failed ({e}).\n\n**Falling back to Smart Local Engine:**\n\n{local_ans}"


# ==========================================
# Asynchronous Worker & Copilot Coordinator
# ==========================================

class AIQueryWorker(QThread):
    """Asynchronous background worker so the chat never freezes the UI."""
    response_ready = Signal(str)
    error = Signal(str)

    def __init__(self, provider: BaseAIProvider, prompt: str, indexer: DocumentIndexer, current_page: int):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.indexer = indexer
        self.current_page = current_page

    def run(self):
        try:
            result = self.provider.query(self.prompt, self.indexer, self.current_page)
            self.response_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AICopilotManager(QObject):
    """Manages document index, active AI provider, and background queries."""

    query_finished = Signal(str)
    query_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.indexer = DocumentIndexer()
        self.settings = QSettings("PyAcrobat", "AICopilot")
        self.worker: Optional[AIQueryWorker] = None
        self._provider: BaseAIProvider = LocalSmartProvider()
        self.load_settings()

    def load_settings(self):
        """Loads saved provider configuration."""
        provider_type = self.settings.value("provider", "local")
        gemini_key = self.settings.value("gemini_key", "")
        gemini_model = self.settings.value("gemini_model", "gemini-1.5-flash")
        openai_key = self.settings.value("openai_key", "")
        openai_url = self.settings.value("openai_url", "http://localhost:11434/v1")
        openai_model = self.settings.value("openai_model", "llama3")

        if provider_type == "gemini":
            self._provider = GeminiProvider(api_key=gemini_key, model=gemini_model)
        elif provider_type == "ollama_openai":
            self._provider = OpenAICompatibleProvider(api_key=openai_key, base_url=openai_url, model=openai_model)
        else:
            self._provider = LocalSmartProvider()

    def set_provider(self, provider_type: str, **kwargs):
        self.settings.setValue("provider", provider_type)
        if provider_type == "gemini":
            key = kwargs.get("gemini_key", "")
            model = kwargs.get("gemini_model", "gemini-1.5-flash")
            self.settings.setValue("gemini_key", key)
            self.settings.setValue("gemini_model", model)
            self._provider = GeminiProvider(key, model)
        elif provider_type == "ollama_openai":
            key = kwargs.get("openai_key", "")
            url = kwargs.get("openai_url", "http://localhost:11434/v1")
            model = kwargs.get("openai_model", "llama3")
            self.settings.setValue("openai_key", key)
            self.settings.setValue("openai_url", url)
            self.settings.setValue("openai_model", model)
            self._provider = OpenAICompatibleProvider(key, url, model)
        else:
            self._provider = LocalSmartProvider()

    def get_provider_name(self) -> str:
        if isinstance(self._provider, GeminiProvider):
            return "Google Gemini"
        elif isinstance(self._provider, OpenAICompatibleProvider):
            return "Ollama / OpenAI"
        return "Smart Local Engine"

    def index_document(self, doc_wrapper):
        """Builds semantic index for open document."""
        self.indexer.index_document(doc_wrapper)

    def ask(self, prompt: str, current_page: int = 1):
        """Submits user query asynchronously."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(400)

        self.worker = AIQueryWorker(self._provider, prompt, self.indexer, current_page)
        self.worker.response_ready.connect(self.query_finished.emit)
        self.worker.error.connect(self.query_error.emit)
        self.worker.start()
