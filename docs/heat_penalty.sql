-- ============================================================
-- SafePath AI — Heat-point spatial join for routing
-- Run in Supabase SQL Editor after segments + safety_reports exist.
--
-- Uses geography (meters) so ST_DWithin(..., 150) is a true 150 m buffer.
-- IDW: SUM(intensity / (distance_m^2 + 10)), then max-normalized to 0..1.
--
-- Backend calls:  rpc('segment_heat_penalties', { buffer_meters: 150 })
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Optional seeded overlay hazards (same coordinates as the Leaflet heat layer).
CREATE TABLE IF NOT EXISTS public.seeded_hazards (
    id TEXT PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    intensity FLOAT NOT NULL DEFAULT 0.75 CHECK (intensity BETWEEN 0 AND 1),
    report_type TEXT NOT NULL,
    description TEXT NOT NULL,
    location_landmark TEXT NOT NULL
);

INSERT INTO public.seeded_hazards (id, latitude, longitude, intensity, report_type, description, location_landmark)
VALUES
    ('hazard-ng-001', 21.1150, 79.0200, 0.92, 'poor_lighting',
     'Hingna Road Industrial Corridor - Very dark stretch with non-functional street lamps after 10 PM.',
     'Hingna Road Industrial Zone, Nagpur'),
    ('hazard-ng-002', 21.0510, 79.0040, 0.88, 'isolated_area',
     'Butibori MIDC Road - Deserted industrial zone late night with minimal pedestrian presence.',
     'Butibori MIDC Road, Nagpur'),
    ('hazard-ng-003', 21.1080, 79.0120, 0.75, 'cctv_broken',
     'MIDC Hingna Road - Damaged surveillance cameras near logistics hub.',
     'MIDC Hingna Road, Nagpur'),
    ('hazard-ng-004', 21.1290, 79.0870, 0.80, 'harassment_risk',
     'Wardha Road Outer Ring - Elevated caution reported near deserted fuel stations late night.',
     'Wardha Road Outer Ring, Nagpur'),
    ('hazard-ng-005', 21.1650, 79.1000, 0.78, 'poor_lighting',
     'Kamptee Road Main - Multiple broken streetlights along northern stretch.',
     'Kamptee Road Main, Nagpur'),
    ('hazard-ng-006', 21.1487, 79.0940, 0.72, 'harassment_risk',
     'Itwari Station Road - Poorly monitored lane near freight yard.',
     'Itwari Station Road, Nagpur')
ON CONFLICT (id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    intensity = EXCLUDED.intensity;

-- Unified Nagpur-only heat-point view: approved community reports + seeded hazards.
CREATE OR REPLACE VIEW public.v_heat_points AS
SELECT
    id::text AS id,
    latitude,
    longitude,
    LEAST(1.0, GREATEST(0.0, COALESCE(credibility_score, 0.80))) AS intensity,
    report_type,
    'supabase'::text AS source
FROM public.safety_reports
WHERE status = 'approved'
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude BETWEEN 20.8 AND 21.3
  AND longitude BETWEEN 78.7 AND 79.4
UNION ALL
SELECT
    id,
    latitude,
    longitude,
    intensity,
    report_type,
    'seeded_hazard'::text AS source
FROM public.seeded_hazards
WHERE latitude BETWEEN 20.8 AND 21.3
  AND longitude BETWEEN 78.7 AND 79.4;

-- Geography indexes for the 150 m buffer query.
CREATE INDEX IF NOT EXISTS safety_reports_geog_idx
    ON public.safety_reports
    USING GIST (geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)));

CREATE INDEX IF NOT EXISTS seeded_hazards_geog_idx
    ON public.seeded_hazards
    USING GIST (geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)));

CREATE INDEX IF NOT EXISTS segments_geog_idx
    ON public.segments
    USING GIST (
        COALESCE(
            geography(geom),
            geography(ST_SetSRID(ST_MakeLine(
                ST_MakePoint(start_lon, start_lat),
                ST_MakePoint(end_lon, end_lat)
            ), 4326))
        )
    );

CREATE OR REPLACE FUNCTION public.segment_heat_penalties(buffer_meters DOUBLE PRECISION DEFAULT 150.0)
RETURNS TABLE(segment_id TEXT, heat_penalty DOUBLE PRECISION, raw_idw DOUBLE PRECISION)
LANGUAGE sql
STABLE
AS $$
WITH segment_geog AS (
    SELECT
        s.id AS segment_id,
        COALESCE(
            geography(s.geom),
            geography(ST_SetSRID(ST_MakeLine(
                ST_MakePoint(s.start_lon, s.start_lat),
                ST_MakePoint(s.end_lon, s.end_lat)
            ), 4326))
        ) AS geog
    FROM public.segments s
),
heat_geog AS (
    SELECT
        hp.id,
        hp.intensity,
        geography(ST_SetSRID(ST_MakePoint(hp.longitude, hp.latitude), 4326)) AS geog
    FROM public.v_heat_points hp
),
raw AS (
    SELECT
        sg.segment_id,
        COALESCE(SUM(
            hg.intensity / (POWER(ST_Distance(sg.geog, hg.geog), 2) + 10.0)
        ), 0.0) AS raw_idw
    FROM segment_geog sg
    LEFT JOIN heat_geog hg
      ON ST_DWithin(sg.geog, hg.geog, buffer_meters)
    GROUP BY sg.segment_id
),
stats AS (
    SELECT MAX(raw_idw) AS max_idw FROM raw
)
SELECT
    r.segment_id,
    CASE
        WHEN s.max_idw IS NULL OR s.max_idw <= 0 THEN 0.0
        ELSE ROUND((r.raw_idw / s.max_idw)::numeric, 4)::double precision
    END AS heat_penalty,
    r.raw_idw
FROM raw r
CROSS JOIN stats s;
$$;

GRANT EXECUTE ON FUNCTION public.segment_heat_penalties(DOUBLE PRECISION) TO anon, authenticated, service_role;

-- Example:
-- SELECT * FROM public.segment_heat_penalties(150)
-- WHERE heat_penalty > 0
-- ORDER BY heat_penalty DESC;
