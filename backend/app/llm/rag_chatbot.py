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
collection = chroma_client.get_or_create_collection(name="safepath_nagpur_knowledge_base")

# Knowledge Base Documents for Nagpur, Maharashtra Region
SAFETY_KNOWLEDGE_DOCS = [
    {
        "id": "doc-ngp-01",
        "title": "Sitabuldi Market & Main Station Corridor Overview",
        "text": "Sitabuldi Market and Nagpur Railway Station approach have high crowd density (score 0.85) during day and evening hours. However, narrow alleys behind Variety Square have dim streetlight coverage and low foot traffic after 10 PM. Recommended detour: Stick to main Wardha Road / Jhansi Rani Square road."
    },
    {
        "id": "doc-ngp-02",
        "title": "Pardi & Zone V Crime Risk Overview",
        "text": "Pardi police station area in East Nagpur has an elevated historical crime score based on city police reports. Walking through unlit industrial stretches in Zone V after 9 PM incurs a risk penalty. Recommended route: Use main Kamptee Road or Central Avenue with active street lighting."
    },
    {
        "id": "doc-ngp-03",
        "title": "Civil Lines & Ramdaspeth Safe Walk Corridor",
        "text": "Civil Lines and Ramdaspeth corridors have bright LED street lighting (0.90) maintained by Nagpur Municipal Corporation. Rated highly safe (score 88/100) for night walking."
    },
    {
        "id": "doc-ngp-04",
        "title": "Dharampeth & Gokulpeth Commercial Area",
        "text": "Dharampeth West High Court Road corridor is active with open shops and cafes until 10:30 PM. High crowd density and good lighting. Side lanes connecting towards Ram Nagar require caution late at night due to reduced foot traffic."
    },
    {
        "id": "doc-ngp-05",
        "title": "Hingna Road & Butibori Industrial Corridors",
        "text": "Hingna Industrial Belt and MIDC corridor stretches experience severe streetlight outages between 10 PM and 5 AM. High isolation score. Shift workers walking on foot should always enable SafeWalk live GPS tracking."
    },
    {
        "id": "doc-ngp-06",
        "title": "General Safe Walk Guidelines for Nagpur Smart City",
        "text": "Always select routes highlighted in green with a composite safety score above 75. For late-night travel across Nagpur, enable SafeWalk live GPS tracking and keep One-Tap Emergency SOS location sharing active."
    }
]

def index_safety_knowledge_base():
    """Index Nagpur safety knowledge documents into ChromaDB vector database."""
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
        print(f"[RAG Copilot] Indexed {len(ids)} Nagpur safety documents into ChromaDB collection.")

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
        route_context_str = "CURRENT CALCULATED NAGPUR ROUTE DATA:\n" + "\n".join(routes_summary) + "\n---\n"

    prompt = f"""You are SafePath AI's Safety Copilot for Nagpur, Maharashtra. Use ONLY the supplied application data below to answer the user's question accurately regarding route safety, lighting conditions, or detours across Nagpur. Do NOT invent safety facts.

{route_context_str}Retrieved Safety Knowledge Base Context (Nagpur Region):
{retrieved_context_str}

User Question: "{user_query}"

Provide a concise, grounded answer explaining route safety scores, lighting conditions, or detour trade-offs in Nagpur:"""

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
                "engine": "Gemini 2.5 Flash LLM + ChromaDB Vector Store"
            }
        except Exception as e:
            print(f"[RAG Copilot] Gemini API call error: {e}. Falling back to grounded retrieval response.")

    # Fallback grounded response using route metrics or vector context
    if route_context_str:
        fallback_answer = (
            f"Based on current calculated route data for your Nagpur journey:\n\n"
            f"{route_context_str}\n"
            f"Recommendation: Choose the Recommended Safe Route (Safety Score >= 75) which minimizes high-risk exposure across Nagpur within an acceptable detour."
        )
    else:
        fallback_answer = (
            f"Based on SafePath AI's safety database for Nagpur, Maharashtra:\n\n"
            f"{retrieved_context_str}\n\n"
            f"Recommendation: Choose routes highlighted green (Safety Score >= 75) on the Nagpur map and enable SafeWalk live tracking."
        )

    return {
        "user_query": user_query,
        "answer": fallback_answer,
        "retrieved_context": context_docs,
        "engine": "ChromaDB Vector Store (Fallback Grounded Engine)"
    }


if __name__ == "__main__":
    test_q = "Why is Pardi or Zone V flagged with lower safety scores at night?"
    res = answer_copilot_query(test_q)
    print(f"\nQuery: {res['user_query']}")
    print(f"Answer:\n{res['answer']}")