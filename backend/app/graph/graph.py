"""Build the active LangGraph conversation workflow.

ChatService creates this graph for a message. The Agent Node selects the user's
active LLM and available tools. If the model requests tools, the Tool Node runs
them and returns their results to the same model for the final answer.
"""

from sqlalchemy.orm import Session

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.graph.nodes.agent import (
    create_agent_node,
)
from app.graph.nodes.tools import (
    create_tool_node,
)
from app.graph.routing import (
    should_use_tool,
)
from app.graph.state import ChatState
from app.llm.factory import LLMProviderFactory
from app.tools.tool_registry_factory import create_unified_tool_registry


# Build one graph whose Agent and Tool Node share the same user-scoped registry.
def create_graph(
    db: Session,
    *,
    tool_registry_factory=create_unified_tool_registry,
    llm_provider_factory=LLMProviderFactory,
):
    """
    Create and compile the provider-neutral tool-calling workflow.

    Architecture:

                        START
                          │
                          ▼
                      Agent Node
                          │
                          ▼
                    Tool needed?
                      /      \
                    No        Yes
                    │          │
                    ▼          ▼
                   END      Tool Node
                                │
                                ▼
                            Agent Node
                                │
                                ▼
                          Tool needed?
                              │
                         ┌────┴────┐
                         │         │
                        Yes        No
                         │         │
                         ▼         ▼
                      Tool Node   END

    ``db`` is passed to factories that need repositories. Optional factories
    allow tests or later runtime configuration to supply different tools/LLMs.
    The user-selected LLM decides whether a tool is required; LangGraph only
    controls the execution order.
    """

    builder = StateGraph(
        ChatState
    )

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

    builder.add_node(
        "agent",
        create_agent_node(
            db=db,
            tool_registry_factory=tool_registry_factory,
            llm_provider_factory=llm_provider_factory,
        ),
    )

    builder.add_node(
        "tools",
        create_tool_node(
            db=db,
            tool_registry_factory=tool_registry_factory,
        ),
    )

    # ---------------------------------------------------------
    # START → Agent
    # ---------------------------------------------------------

    builder.add_edge(
        START,
        "agent",
    )

    # ---------------------------------------------------------
    # Agent → conditional route
    # ---------------------------------------------------------

    builder.add_conditional_edges(
        "agent",
        should_use_tool,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # ---------------------------------------------------------
    # Tool Node → Agent
    # ---------------------------------------------------------

    builder.add_edge(
        "tools",
        "agent",
    )

    return builder.compile()
