"""Pydantic input and output models for native application tools.

The LLM receives JSON Schemas generated from these classes. Before execution,
``BaseTool`` validates model-supplied arguments; outputs are validated again
before they are returned through LangGraph.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ToolInputModel(BaseModel):
    """Base configuration for all tool input schemas.

    extra="forbid" prevents the LLM from silently supplying arguments
    that the tool did not declare.
    """

    model_config = ConfigDict(extra="forbid")


class ToolOutputModel(BaseModel):
    """Base output model that rejects fields outside the declared contract."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Tool 1: search_documents
# ---------------------------------------------------------------------------

class SearchDocumentsInput(ToolInputModel):
    """Search phrase and result limit accepted by ``DocumentSearchTool``."""

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
    """One retrieved passage and its source and relevance information."""

    document_id: str | None = None
    document: str
    page: int | None = None
    chunk_index: int
    content: str
    score: float


class SearchDocumentsOutput(ToolOutputModel):
    """Complete document-search response returned to the selected LLM."""

    results: list[DocumentSearchResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool 2: get_workspace_stats
# ---------------------------------------------------------------------------

class WorkspaceStatsInput(ToolInputModel):
    """Workspace statistics need no model-supplied arguments."""


class WorkspaceStatsOutput(ToolOutputModel):
    """Counts of the authenticated user's stored workspace records."""

    documents: int = Field(ge=0)
    chunks: int = Field(ge=0)
    conversations: int = Field(ge=0)
    messages: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Tool 3: web_search
# ---------------------------------------------------------------------------

class WebSearchInput(ToolInputModel):
    """Web query and maximum result count accepted by ``WebSearchTool``."""

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
    """Normalized title, URL, snippet, and domain for one web result."""

    title: str = Field(
        description="Title of the web page.",
    )
    url: str = Field(
        description="URL of the web page.",
    )
    snippet: str = Field(
        description="Relevant content extracted from the web page.",
    )
    source: str = Field(
        description="Human-readable source or domain of the result.",
    )


class WebSearchOutput(ToolOutputModel):
    """Complete web-search response returned to the selected LLM."""

    results: list[WebSearchResult] = Field(
        default_factory=list,
    )
