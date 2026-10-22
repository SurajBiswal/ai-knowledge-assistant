"""Backend package for the AI Knowledge Assistant.

The main request flow is:
API router -> service -> repository -> SQLAlchemy model -> PostgreSQL.

Chat requests also use:
ChatService -> LangGraph -> selected LLM -> native or MCP tool -> LLM answer.

Each subpackage owns one part of that flow so HTTP handling, business rules,
database access, AI orchestration, and external tools remain separate.
"""
