from app.core.config import settings
from app.services.web_search_service import WebSearchService
from app.tools.web_search import WebSearchTool


def main():
    print("\n=== REAL TAVILY WEB SEARCH TEST ===")

    # Verify configuration exists.
    if not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is not configured in the environment."
        )

    # Create the real Tavily-backed service.
    search_service = WebSearchService(
        api_key=settings.TAVILY_API_KEY,
    )

    # Create the actual tool.
    tool = WebSearchTool(
        search_service=search_service,
    )

    # Execute a real search.
    result = tool.execute(
        {
            "query": "where is PM Modi had tour on August 29–30, 2026",
            "max_results": 5,
        }
    )

    print(f"\nTotal results: {len(result.results)}")

    for index, item in enumerate(result.results, start=1):
        print(f"\n--- Result {index} ---")
        print(f"Title:   {item.title}")
        print(f"URL:     {item.url}")
        print(f"Source:  {item.source}")
        print(f"Snippet: {item.snippet[:500]}")


if __name__ == "__main__":
    main()