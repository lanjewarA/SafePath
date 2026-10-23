# SafePath AI — Urban Safety Routing & Copilot

SafePath AI is an intelligent safety routing system currently focused on Nagpur, Maharashtra. It prioritizes user safety over pure distance by combining:

1. **Graph Neural Network (GNN) Risk Propagation**: Road network modeling where street risk depends on connected spatial neighbors.
2. **Gemini LLM Report Verification**: Automated filter ensuring user safety reports are coherent and authentic before altering route scores.
3. **RAG Safety Copilot**: Context-aware AI assistant explaining route safety factors and suggesting safe alternatives.
4. **SafeWalk & Mobile SOS**: Real-time journey deviation detection and location sharing via Web Share API.

---

## Tech Stack
- **Frontend:** Next.js (App Router), React-Leaflet, OpenStreetMap, Tailwind CSS, Zustand
- **Backend:** FastAPI (Python), PyTorch Geometric, scikit-learn, NetworkX, ChromaDB, Google Gemini API
- **Database:** Supabase (PostgreSQL + PostGIS, Supabase Auth)
- **Region Focus:** Nagpur, Maharashtra

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

## Run the Nagpur Backend

1. Create the Supabase tables by running [`docs/supabase_setup.sql`](./docs/supabase_setup.sql) in the Supabase SQL Editor.
   For an existing database, review and run [`docs/cleanup_legacy_risk_data.sql`](./docs/cleanup_legacy_risk_data.sql) separately in the SQL Editor to remove the legacy column/reports and recalculate segment scores. This migration is not applied by the app.
2. Configure `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env` (use a server-side service key for database writes).
3. Install backend dependencies from `backend/requirements.txt`.
4. Seed a connected 3 km pedestrian road network around central Nagpur into `public.segments`:

   ```powershell
   cd backend
   python -m app.db.seed_nagpur_roads
   ```

   The seed command fetches OpenStreetMap pedestrian roads and upserts them into Supabase. Use `python -m app.db.seed_nagpur_roads --dry-run` to check the generated row count without writing to the database.
5. Start the API with `uvicorn app.main:app --reload` from the `backend` directory.

The route engine uses the connected database network when available. Roads without nearby recorded safety metrics use documented model defaults; scores are estimates, not verified safety guarantees. If the database road network does not connect the selected endpoints, the API may return an external pedestrian route with safety explicitly marked as unavailable rather than inventing a score.
