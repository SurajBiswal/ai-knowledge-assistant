from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.conversations.router import (
    router as conversations_router,
)

app = FastAPI(
    title="AI Knowledge Assistant"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

app.include_router(conversations_router)