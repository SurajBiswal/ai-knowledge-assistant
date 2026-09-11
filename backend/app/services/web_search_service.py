from __future__ import annotations

from typing import Any
from tavily import TavilyClient
from urllib.parse import urlparse

class WebSearchService:
    """
    Application service responsible for interacting with Tavily.

    This class hides all Tavily-specific API details from the tool layer.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("TAVILY_API_KEY is not configured.")

        self.client = TavilyClient(api_key=api_key)

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search the web through Tavily and return normalized results.

        The service intentionally returns only the fields our application
        needs instead of exposing the raw Tavily response.
        """

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        response = self.client.search(
            query=query.strip(),
            max_results=max_results,
        )

        results: list[dict[str, Any]] = []

        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get(
                        "content",
                        item.get("snippet", ""),
                    ),
                    "source": self._extract_source(item.get("url", "")),
                }
            )

        return results


    @staticmethod
    def _extract_source(url: str) -> str:
        """Return the domain name from a URL."""

        if not url:
            return ""

        parsed = urlparse(url)

        return parsed.netloc.removeprefix("www.")