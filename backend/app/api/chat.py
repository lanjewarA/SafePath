from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.llm.rag_chatbot import answer_copilot_query

router = APIRouter(prefix="/api/chat", tags=["Safety Copilot (RAG Assistant)"])

class ChatQueryRequest(BaseModel):
    user_query: str = Field(
        default="Why is the route via Senapati Bapat Marg flagged high risk at 10 PM?",
        description="Question about route safety, lighting conditions, or safe detours"
    )

class ChatQueryResponse(BaseModel):
    user_query: str
    answer: str
    retrieved_context: List[str]
    engine: str

@router.post("/ask", response_model=ChatQueryResponse)
def ask_safety_copilot(payload: ChatQueryRequest):
    """
    Query the Safety Copilot chatbot.
    Retrieves vector embeddings from ChromaDB and generates grounded explanations using Gemini LLM.
    """
    try:
        response = answer_copilot_query(payload.user_query)
        return response
    except Exception as e:
        print(f"[API Chat Error] Copilot query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Safety Copilot query failed: {str(e)}")
