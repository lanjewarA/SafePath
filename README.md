# SafePath AI — Urban Safety Routing & Copilot

SafePath AI is an intelligent safety routing system designed for smart cities (focused on West India — Mumbai/Pune, Maharashtra). It prioritizes user safety over pure distance by combining:

1. **Graph Neural Network (GNN) Risk Propagation**: Road network modeling where street risk depends on connected spatial neighbors.
2. **Gemini LLM Report Verification**: Automated filter ensuring user safety reports are coherent and authentic before altering route scores.
3. **RAG Safety Copilot**: Context-aware AI assistant explaining route safety factors and suggesting safe alternatives.
4. **SafeWalk & Mobile SOS**: Real-time journey deviation detection and location sharing via Web Share API.

---

## Tech Stack
- **Frontend:** Next.js (App Router), React-Leaflet, OpenStreetMap, Tailwind CSS, Zustand
- **Backend:** FastAPI (Python), PyTorch Geometric, scikit-learn, NetworkX, ChromaDB, Google Gemini API
- **Database:** Supabase (PostgreSQL + PostGIS, Supabase Auth)
- **Region Focus:** West India (Mumbai / Pune urban region)

---

## Project Layout
```
SafePath_AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── db/
│   │   ├── llm/
│   │   ├── ml/
│   │   ├── routing/
│   │   └── schemas/
│   ├── data/
│   └── tests/
├── frontend/
└── docs/
```

