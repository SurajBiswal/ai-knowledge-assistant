"""Week 9 tool architecture package.

This package contains the common tool contract and structured schemas
used by the application's LLM-callable tools.
"""
"""Native and remote tool contracts used by the LangGraph agent.

Native tools implement application features such as document search, workspace
statistics, and web search. MCP adapters follow the same registry contract, so
the Agent and Tool Nodes do not need separate execution systems.
"""
