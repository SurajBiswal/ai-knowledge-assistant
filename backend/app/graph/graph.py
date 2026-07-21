from sqlalchemy.orm import Session

from langgraph.graph import START, END
from langgraph.graph import StateGraph

from app.graph.state import ChatState
from app.graph.nodes.chatbot import chatbot_node
from app.graph.nodes.rag import create_rag_node


def create_graph(db: Session):

    builder = StateGraph(ChatState)

    builder.add_node(
        "rag",
        create_rag_node(db),
    )

    builder.add_node(
        "chatbot",
        chatbot_node,
    )

    builder.add_edge(
        START,
        "rag",
    )

    builder.add_edge(
        "rag",
        "chatbot",
    )

    builder.add_edge(
        "chatbot",
        END,
    )

    return builder.compile()