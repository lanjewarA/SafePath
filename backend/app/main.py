from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes, reports, chat

app = FastAPI(
    title="SafePath AI API",
    description="Backend API for SafePath AI — Urban Safety Routing & Copilot (West India / Mumbai Region)",
    version="0.1.0"
)

# Register API Routers
app.include_router(routes.router)
app.include_router(reports.router)
app.include_router(chat.router)




# Enable CORS for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "service": "SafePath AI Backend",
        "status": "online",
        "region": "West India (Mumbai/Pune)"
    }

@app.get("/api/health")
def health_check():
    from app.db.supabase_client import get_supabase_client

    database = "unconnected"
    client = get_supabase_client()
    if client is not None:
        try:
            client.table("segments").select("id").limit(1).execute()
            database = "connected"
        except Exception as e:
            database = f"error: {e}"

    return {
        "status": "healthy",
        "database": database,
        "version": "0.1.0"
    }

