import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.llm.rag_chatbot import retrieve_safety_context, answer_copilot_query

client = TestClient(app)

def test_chromadb_context_retrieval():
    docs = retrieve_safety_context("Senapati Bapat Marg lighting risk", n_results=2)
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert any("Senapati Bapat Marg" in d for d in docs)

def test_answer_copilot_query_rag():
    query = "Is Dadar West Station exit safe after 9 PM?"
    result = answer_copilot_query(query)

    assert result["user_query"] == query
    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 10
    assert "retrieved_context" in result

def test_chat_ask_api_endpoint():
    payload = {
        "user_query": "Why is the route via Senapati Bapat Marg flagged high risk at 10 PM?"
    }
    response = client.post("/api/chat/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["user_query"] == payload["user_query"]
    assert "answer" in data
    assert len(data["retrieved_context"]) > 0
