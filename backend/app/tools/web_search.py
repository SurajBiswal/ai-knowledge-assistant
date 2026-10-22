"""Native tool that lets the LLM request current public web information.

The tool validates the query, delegates external API details to
``WebSearchService``, and returns normalized results through Pydantic schemas.
"""

from __future__ import annotations

from app.services.web_search_service import WebSearchService
from app.tools.base import BaseTool
from app.tools.schemas import (
    WebSearchInput,
    WebSearchOutput,
    WebSearchResult,
)


class WebSearchTool(
    BaseTool[WebSearchInput, WebSearchOutput]
):
    """Expose Tavily-backed search under the public name ``web_search``.

    The tool validates structured arguments and delegates the actual
    web-search operation to ``WebSearchService``.
    """

    name = "web_search"

    description = (
        "Search the public web for current or external information "
        "that may not be available in the user's uploaded documents. "
        "Use this tool when up-to-date or web-based information is needed."
    )

    input_schema = WebSearchInput
    output_schema = WebSearchOutput

    def __init__(
        self,
        search_service: WebSearchService,
    ) -> None:
        """Store the web-search service used when the tool executes."""
        self.search_service = search_service

    def execute(
        self,
        arguments: WebSearchInput,
    ) -> WebSearchOutput:
        """Validate model arguments, run the search, and validate its output."""

        validated_arguments = self.validate_input(arguments)

        raw_results = self.search_service.search(
            query=validated_arguments.query,
            max_results=validated_arguments.max_results,
        )

        results = [
            WebSearchResult(
                title=result["title"],
                url=result["url"],
                snippet=result["snippet"],
                source=result["source"],
            )
            for result in raw_results
        ]

        return self.validate_output(
            WebSearchOutput(
                results=results,
            )
        )
