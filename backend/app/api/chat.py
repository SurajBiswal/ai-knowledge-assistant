from pydantic import BaseModel
from fastapi import APIRouter

from app.graph.graph import graph


router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest):

    result = graph.invoke(
        {
            "message": request.message
        }
    )

    return {
        "response": result["response"]
    }