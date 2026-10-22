"""Import every SQLAlchemy model so all database tables are registered.

``database/base.py`` imports this package after creating ``Base``. Repositories
then use these model classes to read and write users, documents, conversations,
messages, document chunks, LLM profiles, and user-owned MCP connections/tools.
"""

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.llm_provider import LLMProvider
from app.models.llm_provider_profile import LLMProviderProfile
from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool
