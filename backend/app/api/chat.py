from pydantic import BaseModel
from fastapi import APIRouter
from fastapi import HTTPException
from app.graph.graph import graph


router = APIRouter()


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str   


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    result = graph.invoke(
        {
            "message": request.message
        }
    )

    return ChatResponse(response=result["response"])