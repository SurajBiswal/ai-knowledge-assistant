from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ToolInputModel(BaseModel):
    """Base configuration for all tool input schemas.

    extra="forbid" prevents the LLM from silently supplying arguments
    that the tool did not declare.
    """

    model_config = ConfigDict(extra="forbid")


class ToolOutputModel(BaseModel):
    """Base configuration for all structured tool outputs."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Tool 1: search_documents
# ---------------------------------------------------------------------------

class SearchDocumentsInput(ToolInputModel):
    """Arguments accepted by the future search_documents tool."""

    query: str = Field(
        ...,
        min_length=1,
        description="The user's knowledge-base search query.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of relevant chunks to return.",
    )


class DocumentSearchResult(ToolOutputModel):
    """One normalized document-search result."""

    document: str
    chunk_index: int
    content: str
    score: float


class SearchDocumentsOutput(ToolOutputModel):
    """Structured result returned by the future search_documents tool."""

    results: list[DocumentSearchResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool 2: get_workspace_stats
# ---------------------------------------------------------------------------

class WorkspaceStatsInput(ToolInputModel):
    """No user-supplied arguments are required for workspace statistics."""


class WorkspaceStatsOutput(ToolOutputModel):
    """Read-only workspace statistics returned by the future tool."""

    documents: int = Field(ge=0)
    chunks: int = Field(ge=0)
    conversations: int = Field(ge=0)
    messages: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Tool 3: web_search
# ---------------------------------------------------------------------------

class WebSearchInput(ToolInputModel):
    """Arguments accepted by the future web_search tool."""

    query: str = Field(
        ...,
        min_length=1,
        description="The public-web search query.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of web results to return.",
    )


class WebSearchResult(ToolOutputModel):
    """One normalized web-search result."""

    title: str
    url: str
    snippet: str


class WebSearchOutput(ToolOutputModel):
    """Structured result returned by the future web_search tool."""

    results: list[WebSearchResult] = Field(default_factory=list)
