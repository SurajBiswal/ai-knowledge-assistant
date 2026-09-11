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


def create_graph(
    db: Session,
):
    """
    Create the Part 7 LangGraph tool-calling workflow.

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

    Gemini decides whether a tool is required.

    LangGraph controls routing and execution flow.
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
        ),
    )

    builder.add_node(
        "tools",
        create_tool_node(
            db=db,
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