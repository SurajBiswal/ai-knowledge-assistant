"""HTTP API package.

The routers in this package receive browser requests, validate them with
Pydantic schemas, obtain the authenticated user, and call application services.
Routers should not contain database or AI business logic themselves.
"""
