from langgraph.graph import StateGraph
from langgraph.graph import START, END

from app.graph.state import ChatState
from app.graph.nodes import chatbot_node


builder = StateGraph(ChatState)

builder.add_node("chatbot", chatbot_node)

builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

graph = builder.compile()