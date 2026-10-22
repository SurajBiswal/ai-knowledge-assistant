"""Business-logic layer between API routers and lower-level components.

Services coordinate validation and multi-step work. They call repositories for
database access, RAG components for document search, LLM factories for model
clients, and external-service wrappers where needed.
"""
