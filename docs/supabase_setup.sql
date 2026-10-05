-- ============================================================
-- SafePath AI — Supabase Setup Script (PostgreSQL + PostGIS)
-- Region: West India (Mumbai / Pune, Maharashtra)
--
-- HOW TO RUN
--   1. Go to https://supabase.com/dashboard -> your project
--   2. Open "SQL Editor" -> "New query" -> paste this entire file -> Run
--   3. Verify in "Table Editor" that all 4 tables have rows.
--
-- NOTE: This script is idempotent — safe to run multiple times.
--       It truncates and reseeds the demo data, so back up any real
--       user data first.
-- ============================================================

-- ------------------------------------------------------------
-- 0. EXTENSIONS
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS postgis;      -- spatial queries (nearby streets)
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()

-- ------------------------------------------------------------
-- 1. TABLES
-- ------------------------------------------------------------

-- 1a. Street network segments (the walking graph + safety scores)
CREATE TABLE IF NOT EXISTS public.segments (
    id TEXT PRIMARY KEY,                          -- e.g. 'seg-mh-1001' (matches backend code)
    osm_id BIGINT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Unnamed Road',
    start_lat DOUBLE PRECISION NOT NULL,
    start_lon DOUBLE PRECISION NOT NULL,
    end_lat DOUBLE PRECISION NOT NULL,
    end_lon DOUBLE PRECISION NOT NULL,
    length_meters FLOAT NOT NULL DEFAULT 100.0,
    crime_score FLOAT NOT NULL DEFAULT 0.2 CHECK (crime_score BETWEEN 0 AND 1),
    lighting_score FLOAT NOT NULL DEFAULT 0.7 CHECK (lighting_score BETWEEN 0 AND 1),
    cctv_density FLOAT NOT NULL DEFAULT 0.5 CHECK (cctv_density BETWEEN 0 AND 1),
    crowd_density FLOAT NOT NULL DEFAULT 0.6 CHECK (crowd_density BETWEEN 0 AND 1),
    safety_score FLOAT NOT NULL DEFAULT 75.0 CHECK (safety_score BETWEEN 0 AND 100),
    geom GEOMETRY(LineString, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 1b. Community safety reports (submitted by users, verified by Gemini LLM)
CREATE TABLE IF NOT EXISTS public.safety_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    segment_id TEXT REFERENCES public.segments(id) ON DELETE SET NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    report_type TEXT NOT NULL
        CHECK (report_type IN ('poor_lighting','harassment_risk','cctv_broken','isolated_area')),
    description TEXT NOT NULL,
    credibility_score FLOAT DEFAULT 0.5 CHECK (credibility_score BETWEEN 0 AND 1),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 1c. User trust scores (reputation of report submitters)
CREATE TABLE IF NOT EXISTS public.trust_scores (
    user_id TEXT PRIMARY KEY,
    total_reports INT NOT NULL DEFAULT 0,
    verified_reports INT NOT NULL DEFAULT 1,  -- start at 1: never divide by zero
    trust_rating FLOAT NOT NULL DEFAULT 0.5 CHECK (trust_rating BETWEEN 0 AND 1),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 1d. Route query history (for analytics + RAG copilot context)
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- ------------------------------------------------------------
-- 2. INDEXES
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS segments_geom_idx        ON public.segments USING GIST (geom);
CREATE INDEX IF NOT EXISTS segments_osm_id_idx      ON public.segments (osm_id);
CREATE INDEX IF NOT EXISTS safety_reports_segment_idx ON public.safety_reports (segment_id);
CREATE INDEX IF NOT EXISTS safety_reports_user_idx    ON public.safety_reports (user_id);
CREATE INDEX IF NOT EXISTS routes_created_idx         ON public.routes (created_at DESC);

-- ------------------------------------------------------------
-- 3. ROW LEVEL SECURITY
--    (Backend uses the service-role key, which bypasses RLS.
--     Policies below let the anon/public client only READ
--     segments and approved reports, and INSERT reports.)
-- ------------------------------------------------------------

ALTER TABLE public.segments        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.safety_reports  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trust_scores    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.routes          ENABLE ROW LEVEL SECURITY;

-- Segments: public read
DROP POLICY IF EXISTS "Public read segments" ON public.segments;
CREATE POLICY "Public read segments" ON public.segments
    FOR SELECT TO anon, authenticated USING (true);

-- Reports: anyone can submit; only approved ones are readable
DROP POLICY IF EXISTS "Public insert reports" ON public.safety_reports;
CREATE POLICY "Public insert reports" ON public.safety_reports
    FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Public read approved reports" ON public.safety_reports;
CREATE POLICY "Public read approved reports" ON public.safety_reports
    FOR SELECT TO anon, authenticated USING (status = 'approved');

-- Trust scores / routes: read-only for public clients
DROP POLICY IF EXISTS "Public read trust" ON public.trust_scores;
CREATE POLICY "Public read trust" ON public.trust_scores
    FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read routes" ON public.routes;
CREATE POLICY "Public read routes" ON public.routes
    FOR SELECT TO anon, authenticated USING (true);

-- ------------------------------------------------------------
-- 4. TRIGGER: auto-increment trust score when a report is inserted
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.increment_trust_score()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.trust_scores (user_id, total_reports, verified_reports, trust_rating)
    VALUES (NEW.user_id, 1, 1, 0.5)
    ON CONFLICT (user_id) DO UPDATE
    SET total_reports = trust_scores.total_reports + 1,
        updated_at = timezone('utc', now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_increment_trust ON public.safety_reports;
CREATE TRIGGER trg_increment_trust
    AFTER INSERT ON public.safety_reports
    FOR EACH ROW
    EXECUTE FUNCTION public.increment_trust_score();

-- ------------------------------------------------------------
-- 5. SEED DATA — Mumbai street network sample
--    (Enough to see the map working. Run backend/app/db/seed_supabase.py
--     afterwards to push the FULL 338-segment dataset.)
-- ------------------------------------------------------------

-- Truncate in ONE statement: safety_reports references segments, so
-- truncating segments alone would fail with a foreign-key error.
TRUNCATE public.safety_reports, public.segments, public.trust_scores, public.routes;

INSERT INTO public.segments (id, osm_id, name, start_lat, start_lon, end_lat, end_lon, length_meters, crime_score, lighting_score, cctv_density, crowd_density, safety_score) VALUES
('seg-mh-1001', 400010001, 'Dadar West Railway Station to Senapati Bapat Marg Connector', 19.0178, 72.8478, 19.0020, 72.8280, 2718.4, 0.24, 0.81, 0.71, 0.72, 75.45),
('seg-mh-1002', 400010002, 'Dadar West Railway Station to Lower Parel Commercial Hub Connector', 19.0178, 72.8478, 18.9950, 72.8295, 3236.0, 0.34, 0.76, 0.68, 0.75, 70.70),
('seg-mh-1003', 400010003, 'Dadar West Railway Station to Worli Naka Connector',        19.0178, 72.8478, 19.0060, 72.8180, 3436.0, 0.22, 0.83, 0.74, 0.78, 78.45),
('seg-mh-1004', 400010004, 'Dadar West Railway Station to Prabhadevi Chowk Connector',   19.0178, 72.8478, 19.0160, 72.8290, 1864.0, 0.41, 0.64, 0.55, 0.62, 60.05),
('seg-mh-1005', 400010005, 'Dadar West Railway Station to Mahim Junction Connector',     19.0178, 72.8478, 19.0410, 72.8430, 2869.0, 0.18, 0.86, 0.80, 0.70, 80.20),
('seg-mh-1006', 400010006, 'Dadar West Railway Station to Matunga Road Connector',       19.0178, 72.8478, 19.0270, 72.8450, 1050.0, 0.29, 0.79, 0.66, 0.74, 72.60),
('seg-mh-1007', 400010007, 'Dadar West Railway Station to Sion Circle Connector',        19.0178, 72.8478, 19.0360, 72.8600, 2076.0, 0.36, 0.71, 0.63, 0.69, 66.55),
('seg-mh-1008', 400010008, 'Dadar West Railway Station to Dharavi Junction Connector',   19.0178, 72.8478, 19.0400, 72.8530, 2557.0, 0.61, 0.44, 0.29, 0.35, 37.45),
('seg-mh-1009', 400010009, 'Senapati Bapat Marg to Lower Parel Commercial Hub Connector',19.0020, 72.8280, 18.9950, 72.8295, 1748.0, 0.27, 0.77, 0.72, 0.80, 75.20),
('seg-mh-1010', 400010010, 'Senapati Bapat Marg to Worli Naka Connector',                19.0020, 72.8280, 19.0060, 72.8180, 1120.0, 0.31, 0.75, 0.69, 0.77, 72.10);

-- ------------------------------------------------------------
-- 6. SEED — sample community reports + trust scores
-- ------------------------------------------------------------
INSERT INTO public.safety_reports (user_id, segment_id, latitude, longitude, report_type, description, credibility_score, status) VALUES
('demo_user_1', 'seg-mh-1008', 19.0290, 72.8501, 'poor_lighting', 'Streetlights not working near Dharavi junction for the past week, road is very dark at night.', 0.88, 'approved'),
('demo_user_1', 'seg-mh-1005', 19.0300, 72.8455, 'cctv_broken',  'CCTV camera at the station exit is damaged; footage not being recorded.',               0.74, 'approved'),
('demo_user_2', 'seg-mh-1004', 19.0169, 72.8285, 'harassment_risk','Groups loitering near the flyover after 10pm, feels unsafe to walk alone.',            0.69, 'approved');

INSERT INTO public.trust_scores (user_id, total_reports, verified_reports, trust_rating) VALUES
('demo_user_1', 2, 2, 0.85),
('demo_user_2', 1, 1, 0.62);
