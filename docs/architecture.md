# SafePath AI Architecture Document

## System Architecture

```mermaid
flowchart TD
    User["User / Mobile Client (Next.js + Leaflet)"]
    FastAPI["Backend API (FastAPI)"]
    OSM["OSM Road Network Engine (NetworkX)"]
    RF["Random Forest Safety Model"]
    GNN["PyTorch Geometric GNN Model"]
    Gemini["Google Gemini LLM (Report Filter & RAG)"]
    Chroma["ChromaDB Vector Store"]
    DB["Supabase (PostgreSQL + PostGIS)"]

    User -->|Route Request / Chat / Report| FastAPI
    FastAPI -->|Fetch Map Graphs| OSM
    FastAPI -->|Query Features & Reports| DB
    FastAPI -->|Predict Baseline Risk| RF
    FastAPI -->|Predict Spatial Risk| GNN
    FastAPI -->|Verify Reports & Explanations| Gemini
    Gemini <-->|Retrieve Context| Chroma
```

## Core Subsystems
1. **Routing Subsystem**: Integrates OpenStreetMap data for Mumbai/Pune region to generate candidate walking routes.
2. **Safety Scoring Engine**: Features street lighting, CCTV density, crowd levels, and historical crime reports.
3. **Spatial Risk Modeling**: GNN propagates risk across adjacent road segments.
4. **Report Trust Filter**: Gemini scores user reports (0.0 to 1.0 credibility) before DB insertion.
5. **RAG Copilot**: Embeds local safety advice and route data to provide explainable safety insights.

