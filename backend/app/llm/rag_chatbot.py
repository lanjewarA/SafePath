import os
import sys
import json
import chromadb
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

# Add backend directory to sys.path for standalone script execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Initialize ChromaDB in-memory client
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="safepath_knowledge_base")

# Knowledge Base Documents for West India (Mumbai / Pune Region)
SAFETY_KNOWLEDGE_DOCS = [
    {
        "id": "doc-01",
        "title": "Senapati Bapat Marg Safety Overview",
        "text": "Senapati Bapat Marg in Mumbai has moderate safety (score 54/100) after 9 PM due to ongoing flyover construction, dim streetlight coverage, and isolated sections near closed industrial mills. Detour recommendation: Use well-lit Gokhale Road or Ranade Road."
    },
    {
        "id": "doc-02",
        "title": "Dadar Station West Exit Guidelines",
        "text": "Dadar West Station area is heavily populated during peak hours (crowd score 0.85). However, the north stairway underpass has broken CCTV cameras and poor lighting. Recommended walk path: Use the main Dadar TT Circle footbridge."
    },
    {
        "id": "doc-03",
        "title": "Lower Parel Commercial Corridor",
        "text": "Lower Parel financial district has high CCTV surveillance (density 0.88) and active security guards until midnight. Extremely safe walking path along Phoenix Mills lane."
    },
    {
        "id": "doc-04",
        "title": "Bandra Kurla Complex (BKC) Night Walk",
        "text": "BKC wide avenues have bright LED lighting (score 0.90) and frequent police patrols. High safety rating (88/100). Safe for night walking."
    },
    {
        "id": "doc-05",
        "title": "Mahim Junction Underpass Caution",
        "text": "Mahim Creek connector has low crowd density after 10 PM and elevated historical harassment reports. Always prefer taking the main L.J. Road."
    },
    {
        "id": "doc-06",
        "title": "General Safe Walk Guidelines for Smart Cities",
        "text": "Always choose routes with composite safety scores above 75. Look for green polylines on the SafePath map. If walking after 10 PM, enable SafeWalk live GPS tracking and keep Emergency SOS ready."
    }
]

def index_safety_knowledge_base():
    """Index safety knowledge documents into ChromaDB vector database."""
    existing_count = collection.count()
    if existing_count == 0:
        ids = [d["id"] for d in SAFETY_KNOWLEDGE_DOCS]
        documents = [f"{d['title']}: {d['text']}" for d in SAFETY_KNOWLEDGE_DOCS]
        metadatas = [{"title": d["title"]} for d in SAFETY_KNOWLEDGE_DOCS]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"[RAG Copilot] Indexed {len(ids)} safety documents into ChromaDB collection.")

# Pre-index on module load
index_safety_knowledge_base()

def retrieve_safety_context(query: str, n_results: int = 2) -> List[str]:
    """Retrieve top matching safety documents from ChromaDB vector store."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        docs = results.get("documents", [[]])[0]
        return docs if docs else [d["text"] for d in SAFETY_KNOWLEDGE_DOCS[:2]]
    except Exception as e:
        print(f"[RAG Copilot] Vector search error: {e}")
        return [d["text"] for d in SAFETY_KNOWLEDGE_DOCS[:2]]

def answer_copilot_query(user_query: str, route_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Answer route safety questions using structured route data + ChromaDB retrieval + Gemini generation."""
    context_docs = retrieve_safety_context(user_query, n_results=2)
    retrieved_context_str = "\n---\n".join(context_docs)

    route_context_str = ""
    if route_context and isinstance(route_context, dict) and "routes" in route_context:
        routes_summary = []
        for r in route_context.get("routes", []):
            routes_summary.append(
                f"Route '{r.get('name')}' (ID: {r.get('route_id')}, Recommended: {r.get('is_recommended', False)}):\n"
                f"  - Total Distance: {r.get('total_distance_km')} km ({r.get('estimated_walk_minutes')} min walk)\n"
                f"  - Composite Safety Score: {r.get('composite_safety_score')}/100\n"
                f"  - Safety Exposure (Length-Weighted Risk): {r.get('safety_exposure')}\n"
                f"  - Max Segment Risk: {r.get('max_segment_risk')}\n"
                f"  - High-Risk Distance Exposure: {r.get('high_risk_exposure_pct')}%\n"
                f"  - Detour: +{r.get('detour_percentage')}%\n"
                f"  - Rationale: {r.get('rationale')}\n"
            )
        route_context_str = "CURRENT CALCULATED ROUTE DATA:\n" + "\n".join(routes_summary) + "\n---\n"

    prompt = f"""You are SafePath AI's Safety Copilot. Use ONLY the supplied application data below to answer the user's question accurately. Do NOT invent safety facts.

{route_context_str}Retrieved Safety Knowledge Base Context:
{retrieved_context_str}

User Question: "{user_query}"

Provide a concise, grounded answer explaining route safety scores, lighting conditions, or detour trade-offs:"""

    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            answer_text = response.text.strip()
            return {
                "user_query": user_query,
                "answer": answer_text,
                "retrieved_context": context_docs,
                "engine": "Gemini LLM + ChromaDB Vector Store"
            }
        except Exception as e:
            print(f"[RAG Copilot] Gemini API call error: {e}. Falling back to grounded retrieval response.")

    # Fallback grounded response using route metrics or vector context
    if route_context_str:
        fallback_answer = (
            f"Based on current calculated route data for your journey:\n\n"
            f"{route_context_str}\n"
            f"Recommendation: Choose the Recommended Safe Route (Safety Score >= 75) which minimizes high-risk exposure within an acceptable detour."
        )
    else:
        fallback_answer = (
            f"Based on SafePath AI's safety database for West India:\n\n"
            f"{retrieved_context_str}\n\n"
            f"Recommendation: Choose routes highlighted green (Safety Score >= 75) on the map and enable SafeWalk live tracking."
        )

    return {
        "user_query": user_query,
        "answer": fallback_answer,
        "retrieved_context": context_docs,
        "engine": "ChromaDB Vector Store (Fallback Grounded Engine)"
    }


if __name__ == "__main__":
    test_q = "Why is Senapati Bapat Marg flagged high risk at 10 PM?"
    res = answer_copilot_query(test_q)
    print(f"\nQuery: {res['user_query']}")
    print(f"Answer:\n{res['answer']}")
