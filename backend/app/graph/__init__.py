"""LangGraph workflow package for chat and tool execution.

``graph.py`` assembles the active Agent -> optional Tool Node -> Agent loop.
``state.py`` defines data shared between nodes, and ``routing.py`` chooses the
next node from the model's structured tool-call decision.
"""
