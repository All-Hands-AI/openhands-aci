"""Text-based web browser implementation."""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SimpleTextBrowser:
    """Simple text-based web browser."""

    viewport_size: int = 5120
    downloads_folder: str = "downloads"
    request_kwargs: Dict[str, Any] = None
    serpapi_key: Optional[str] = None

    def __post_init__(self):
        """Initialize browser state."""
        self.current_url = None
        self.current_page = None
        self.current_text = None
        self.current_position = 0
        self.search_position = 0
        self.search_term = None
        self.request_kwargs = self.request_kwargs or {}
        os.makedirs(self.downloads_folder, exist_ok=True)

    def visit(self, url: str) -> str:
        """Visit a URL and return its text content."""
        try:
            response = requests.get(url, **self.request_kwargs)
            response.raise_for_status()
            self.current_url = url
            self.current_page = response.text
            soup = BeautifulSoup(response.text, "html.parser")
            self.current_text = soup.get_text()
            self.current_position = 0
            self.search_position = 0
            self.search_term = None
            return self._get_current_viewport()
        except Exception as e:
            logger.error(f"Error visiting URL {url}: {e}")
            return f"Error: {str(e)}"

    def page_up(self) -> str:
        """Move viewport up."""
        if not self.current_text:
            return "No page loaded"
        self.current_position = max(0, self.current_position - self.viewport_size)
        return self._get_current_viewport()

    def page_down(self) -> str:
        """Move viewport down."""
        if not self.current_text:
            return "No page loaded"
        self.current_position = min(
            len(self.current_text) - self.viewport_size,
            self.current_position + self.viewport_size,
        )
        return self._get_current_viewport()

    def find(self, term: str) -> str:
        """Find text in current page."""
        if not self.current_text:
            return "No page loaded"
        self.search_term = term.lower()
        self.search_position = 0
        return self.find_next()

    def find_next(self) -> str:
        """Find next occurrence of search term."""
        if not self.current_text or not self.search_term:
            return "No search term set"
        text_lower = self.current_text.lower()
        pos = text_lower.find(self.search_term, self.search_position)
        if pos == -1:
            return "Term not found"
        self.search_position = pos + 1
        self.current_position = max(0, pos - self.viewport_size // 2)
        return self._get_current_viewport()

    def _get_current_viewport(self) -> str:
        """Get current viewport text."""
        if not self.current_text:
            return "No page loaded"
        end = min(len(self.current_text), self.current_position + self.viewport_size)
        return self.current_text[self.current_position:end]


class TextBrowserTool:
    """Base class for text browser tools."""

    def __init__(self, browser: SimpleTextBrowser):
        """Initialize tool with browser instance."""
        self.browser = browser