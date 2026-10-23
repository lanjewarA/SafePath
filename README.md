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

## Deploy the full app

The GitHub repository is the source code; GitHub Pages cannot run the FastAPI service. A simple hosted setup is Vercel for the frontend, Render (or another Python host) for the backend, and Supabase for Postgres/PostGIS.

1. Run the database setup/migration steps above and seed the Nagpur road network if it is not already present.
2. Create a Render Web Service from this GitHub repository with **Root Directory** `backend`, **Build Command** `pip install -r requirements.txt`, and **Start Command** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Set these Render environment variables:
   - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (server-side credentials; never put the service key in the frontend).
   - `GEMINI_API_KEY` if enabling Gemini-backed features.
   - `SAFEPATH_CORS_ORIGINS` to the exact Vercel origin, for example `https://your-app.vercel.app` (comma-separated if there are multiple frontend origins).
4. Import the same repository into Vercel with **Root Directory** `frontend`. Set `NEXT_PUBLIC_API_URL` to the backend's public origin, for example `https://your-backend.onrender.com`, then deploy.
5. Confirm `https://your-backend.onrender.com/api/health` responds and test route calculation, reports, chat, and SafeWalk on the deployed frontend. Redeploy the frontend after changing `NEXT_PUBLIC_API_URL`; it is read during the frontend build.
