"""Web browser tools implementation."""

import json
import os
from typing import Optional
from urllib.parse import quote_plus

import requests

from .browser import SimpleTextBrowser, TextBrowserTool


class SearchInformationTool(TextBrowserTool):
    """Tool for searching information on the web."""

    def search(self, query: str) -> str:
        """Search for information using SerpAPI or direct Google search."""
        if self.browser.serpapi_key:
            return self._serpapi_search(query)
        return self._direct_search(query)

    def _serpapi_search(self, query: str) -> str:
        """Search using SerpAPI."""
        params = {
            "q": query,
            "api_key": self.browser.serpapi_key,
            "engine": "google",
        }
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        return json.dumps(results.get("organic_results", []), indent=2)

    def _direct_search(self, query: str) -> str:
        """Direct Google search."""
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        return self.browser.visit(url)


class VisitTool(TextBrowserTool):
    """Tool for visiting URLs."""

    def visit(self, url: str) -> str:
        """Visit a URL."""
        return self.browser.visit(url)


class PageUpTool(TextBrowserTool):
    """Tool for scrolling up."""

    def page_up(self) -> str:
        """Scroll viewport up."""
        return self.browser.page_up()


class PageDownTool(TextBrowserTool):
    """Tool for scrolling down."""

    def page_down(self) -> str:
        """Scroll viewport down."""
        return self.browser.page_down()


class FinderTool(TextBrowserTool):
    """Tool for finding text in page."""

    def find(self, term: str) -> str:
        """Find text in current page."""
        return self.browser.find(term)


class FindNextTool(TextBrowserTool):
    """Tool for finding next occurrence."""

    def find_next(self) -> str:
        """Find next occurrence of search term."""
        return self.browser.find_next()


class ArchiveSearchTool(TextBrowserTool):
    """Tool for searching Internet Archive."""

    def search_archive(self, url: str, timestamp: Optional[str] = None) -> str:
        """Search Internet Archive for URL."""
        archive_url = f"https://web.archive.org/web/{timestamp or '*'}/{url}"
        return self.browser.visit(archive_url)