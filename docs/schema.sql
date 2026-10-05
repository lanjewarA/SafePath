-- SafePath AI — PostgreSQL + PostGIS Schema for Supabase
-- Target Region: West India (Mumbai / Pune, Maharashtra)

-- Enable PostGIS spatial extension if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Street Segments Table
-- NOTE: id is TEXT (e.g. 'seg-mh-1001') because the backend seed dataset and
-- safety_reports.segment_id both use these string IDs. If you prefer UUIDs,
-- change this AND safety_reports.segment_id AND backend/data/generate_dataset.py.
CREATE TABLE IF NOT EXISTS public.segments (
    id TEXT PRIMARY KEY,
    osm_id BIGINT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Unnamed Road',
    start_lat DOUBLE PRECISION NOT NULL,
    start_lon DOUBLE PRECISION NOT NULL,
    end_lat DOUBLE PRECISION NOT NULL,
    end_lon DOUBLE PRECISION NOT NULL,
    length_meters FLOAT NOT NULL DEFAULT 100.0,
    crime_score FLOAT NOT NULL DEFAULT 0.2,       -- 0.0 (low crime) to 1.0 (high crime)
    lighting_score FLOAT NOT NULL DEFAULT 0.7,    -- 0.0 (dark) to 1.0 (well lit)
    cctv_density FLOAT NOT NULL DEFAULT 0.5,      -- 0.0 (no cameras) to 1.0 (high CCTV)
    crowd_density FLOAT NOT NULL DEFAULT 0.6,     -- 0.0 (isolated) to 1.0 (crowded)
    safety_score FLOAT NOT NULL DEFAULT 75.0,     -- 0.0 (dangerous) to 100.0 (safe)
    geom GEOMETRY(LineString, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index spatial geometry for fast location lookups
CREATE INDEX IF NOT EXISTS segments_geom_idx ON public.segments USING GIST (geom);
CREATE INDEX IF NOT EXISTS segments_osm_id_idx ON public.segments (osm_id);

-- 2. Community Safety Reports Table
CREATE TABLE IF NOT EXISTS public.safety_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    segment_id TEXT REFERENCES public.segments(id) ON DELETE SET NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    report_type TEXT NOT NULL,                  -- 'poor_lighting', 'harassment_risk', 'cctv_broken', 'isolated_area'
    description TEXT NOT NULL,
    credibility_score FLOAT DEFAULT 0.5,        -- Assessed by Gemini LLM (0.0 to 1.0)
    status TEXT NOT NULL DEFAULT 'pending',     -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS safety_reports_segment_id_idx ON public.safety_reports (segment_id);

-- 3. User Trust Scores Table
CREATE TABLE IF NOT EXISTS public.trust_scores (
    user_id TEXT PRIMARY KEY,
    total_reports INT NOT NULL DEFAULT 0,
    verified_reports INT NOT NULL DEFAULT 0,
    trust_rating FLOAT NOT NULL DEFAULT 0.5,    -- 0.0 (untrustworthy) to 1.0 (highly reliable)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Routes Query History Table
CREATE TABLE IF NOT EXISTS public.routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_name TEXT NOT NULL,
    destination_name TEXT NOT NULL,
    origin_lat DOUBLE PRECISION NOT NULL,
    origin_lon DOUBLE PRECISION NOT NULL,
    dest_lat DOUBLE PRECISION NOT NULL,
    dest_lon DOUBLE PRECISION NOT NULL,
    distance_meters FLOAT NOT NULL,
    composite_safety_score FLOAT NOT NULL,
    segment_ids TEXT[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

