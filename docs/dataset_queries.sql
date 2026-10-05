-- ============================================================
-- SafePath AI — Required Dataset Queries (PostgreSQL + PostGIS)
-- Tables: segments, safety_reports, trust_scores, routes
-- Run in Supabase SQL Editor. All queries are read-only unless noted.
-- ============================================================

-- ============================================================
-- 0. DATA HEALTH / VERIFICATION QUERIES
--    (Run these first to confirm the dataset loaded correctly)
-- ============================================================

-- 0.1 Row counts for every table
SELECT
    (SELECT COUNT(*) FROM public.segments)        AS segments_total,
    (SELECT COUNT(*) FROM public.safety_reports)  AS reports_total,
    (SELECT COUNT(*) FROM public.trust_scores)    AS trust_rows_total,
    (SELECT COUNT(*) FROM public.routes)          AS routes_total;

-- 0.2 Dataset bounding box + coverage sanity check
SELECT
    MIN(start_lat) AS min_lat, MAX(start_lat) AS max_lat,
    MIN(start_lon) AS min_lon, MAX(start_lon) AS max_lon,
    ROUND(AVG(length_meters)::numeric, 1)   AS avg_segment_length_m,
    ROUND(AVG(safety_score)::numeric, 2)    AS avg_safety_score
FROM public.segments;

-- 0.3 Safety score distribution (histogram buckets of 10)
SELECT
    WIDTH_BUCKET(safety_score, 0, 100, 10) AS score_bucket,
    CONCAT(WIDTH_BUCKET(safety_score, 0, 100, 10) * 10 - 10, '-', WIDTH_BUCKET(safety_score, 0, 100, 10) * 10) AS range_label,
    COUNT(*) AS segment_count
FROM public.segments
GROUP BY 1, 2
ORDER BY 1;

-- ============================================================
-- 1. ROUTING ENGINE QUERIES (network loading + nearest-segment lookup)
--    The backend normally uses supabase-py; these are the SQL
--    equivalents and the PostGIS spatial lookups.
-- ============================================================

-- 1.1 Load full street network (equivalent of fetch_all_segments())
SELECT id, osm_id, name,
       start_lat, start_lon, end_lat, end_lon,
       length_meters, crime_score, lighting_score,
       cctv_density, crowd_density, safety_score
FROM public.segments
ORDER BY id;

-- 1.2 Nearest segment to a coordinate (snap a user/report to the graph)
--     Example: snap point (19.0178, 72.8478) — Dadar West Station
SELECT id, name,
       ST_Distance(
           geom,
           ST_SetSRID(ST_MakePoint(72.8478, 19.0178), 4326)::geography
       ) AS distance_meters,
       safety_score
FROM public.segments
WHERE geom IS NOT NULL
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(72.8478, 19.0178), 4326)::geography
LIMIT 1;

-- 1.3 All segments within a radius of a point (map viewport / isochrone area)
--     Example: 1 km around Dharavi Junction (19.0400, 72.8530)
SELECT id, name, length_meters, safety_score,
       ST_Distance(geom, ST_SetSRID(ST_MakePoint(72.8530, 19.0400), 4326)::geography) AS distance_meters
FROM public.segments
WHERE geom IS NOT NULL
  AND ST_DWithin(
      geom,
      ST_SetSRID(ST_MakePoint(72.8530, 19.0400), 4326)::geography,
      1000
  )
ORDER BY distance_meters;

-- 1.4 Segments reachable by walking within X minutes (1.4 m/s pace)
SELECT id, name, length_meters, safety_score,
       CEIL(length_meters / 1.4 / 60.0) AS walk_minutes
FROM public.segments
ORDER BY walk_minutes
LIMIT 50;

-- ============================================================
-- 2. SAFETY ANALYTICS QUERIES (dashboards + copilot context)
-- ============================================================

-- 2.1 Top 10 riskiest street segments (route warnings / "avoid" list)
SELECT id, name, safety_score, crime_score, lighting_score, cctv_density, crowd_density
FROM public.segments
ORDER BY safety_score ASC
LIMIT 10;

-- 2.2 Top 10 safest street segments
SELECT id, name, safety_score, crime_score, lighting_score, cctv_density, crowd_density
FROM public.segments
ORDER BY safety_score DESC
LIMIT 10;

-- 2.3 Correlation view: how each risk factor tracks the composite score
SELECT
    ROUND(CORR(crime_score,     safety_score)::numeric, 3) AS corr_crime,
    ROUND(CORR(lighting_score,  safety_score)::numeric, 3) AS corr_lighting,
    ROUND(CORR(cctv_density,    safety_score)::numeric, 3) AS corr_cctv,
    ROUND(CORR(crowd_density,   safety_score)::numeric, 3) AS corr_crowd
FROM public.segments;

-- 2.4 Night-risk view: dark AND low-crowd segments (worst after 10 PM)
SELECT id, name, lighting_score, crowd_density, safety_score
FROM public.segments
WHERE lighting_score < 0.50
  AND crowd_density < 0.40
ORDER BY safety_score ASC;

-- 2.5 Segments flagged as needing infrastructure intervention
--     (low lighting OR low CCTV) and still dangerous
SELECT id, name,
       CASE WHEN lighting_score < 0.4 THEN 'poor_lighting' END AS lighting_flag,
       CASE WHEN cctv_density  < 0.3 THEN 'low_cctv'      END AS cctv_flag,
       safety_score
FROM public.segments
WHERE (lighting_score < 0.40 OR cctv_density < 0.30)
  AND safety_score < 60
ORDER BY safety_score ASC;

-- 2.6 Landmark-pair lookup used by the copilot RAG ("why is X risky?")
SELECT id, name, safety_score, crime_score, lighting_score, cctv_density, crowd_density
FROM public.segments
WHERE name ILIKE '%dharavi%' OR name ILIKE '%dadar%'
ORDER BY safety_score ASC;

-- ============================================================
-- 3. COMMUNITY REPORT QUERIES (ingest + Gemini trust pipeline)
-- ============================================================

-- 3.1 Pending reports awaiting moderation
SELECT r.id, r.user_id, r.segment_id, r.report_type, r.description,
       r.credibility_score, r.status, r.created_at
FROM public.safety_reports r
WHERE r.status = 'pending'
ORDER BY r.created_at ASC;

-- 3.2 Reports joined to their street segment (feed segment re-scoring)
SELECT r.id, r.segment_id, r.report_type, r.credibility_score,
       s.name AS segment_name, s.safety_score AS current_safety_score
FROM public.safety_reports r
LEFT JOIN public.segments s ON s.id = r.segment_id
WHERE r.status = 'approved'
ORDER BY r.created_at DESC;

-- 3.3 Report volume by hazard type
SELECT report_type, COUNT(*) AS report_count,
       ROUND(AVG(credibility_score)::numeric, 3) AS avg_credibility
FROM public.safety_reports
GROUP BY report_type
ORDER BY report_count DESC;

-- 3.4 Duplicate/spam check: same user + segment + type in 24h
SELECT user_id, segment_id, report_type, COUNT(*) AS submissions
FROM public.safety_reports
WHERE created_at > timezone('utc', now()) - INTERVAL '24 hours'
GROUP BY user_id, segment_id, report_type
HAVING COUNT(*) > 1
ORDER BY submissions DESC;

-- 3.5 Hotspots: segments with >= 2 approved negative reports
SELECT r.segment_id, s.name,
       COUNT(*) AS approved_reports,
       ROUND(AVG(r.credibility_score)::numeric, 3) AS avg_credibility,
       MIN(s.safety_score) AS current_safety_score
FROM public.safety_reports r
JOIN public.segments s ON s.id = r.segment_id
WHERE r.status = 'approved'
GROUP BY r.segment_id, s.name
HAVING COUNT(*) >= 2
ORDER BY approved_reports DESC;

-- 3.6 Weighted community risk adjustment per segment
--     (candidate replacement for the naive fixed-score update in
--      update_segment_safety_score): each approved report lowers the
--      segment score proportionally to its credibility.
SELECT
    r.segment_id,
    s.name,
    s.safety_score AS current_score,
    ROUND(SUM(r.credibility_score)::numeric, 3) AS total_credibility,
    ROUND(GREATEST(0, s.safety_score - 10.0 * SUM(r.credibility_score))::numeric, 2)
        AS suggested_new_safety_score
FROM public.safety_reports r
JOIN public.segments s ON s.id = r.segment_id
WHERE r.status = 'approved'
GROUP BY r.segment_id, s.name, s.safety_score
ORDER BY suggested_new_safety_score ASC;

-- ============================================================
-- 4. TRUST SCORE QUERIES (reputation system)
-- ============================================================

-- 4.1 Trust leaderboard
SELECT user_id, total_reports, verified_reports, trust_rating,
       ROUND((verified_reports::numeric / NULLIF(total_reports, 0)) * 100, 1) AS approval_pct
FROM public.trust_scores
ORDER BY trust_rating DESC;

-- 4.2 Recompute trust_rating from approved-report ratio (maintenance job)
UPDATE public.trust_scores t
SET trust_rating = LEAST(1.0, GREATEST(0.0, v.approved_ratio)),
    updated_at   = timezone('utc', now())
FROM (
    SELECT user_id,
           COUNT(*) FILTER (WHERE status = 'approved')::float
           / NULLIF(COUNT(*), 0) AS approved_ratio
    FROM public.safety_reports
    GROUP BY user_id
) v
WHERE t.user_id = v.user_id;

-- 4.3 Users submitting above-threshold volume (possible spam farms)
SELECT user_id, COUNT(*) AS reports_last_7d
FROM public.safety_reports
WHERE created_at > timezone('utc', now()) - INTERVAL '7 days'
GROUP BY user_id
HAVING COUNT(*) > 5
ORDER BY reports_last_7d DESC;

-- ============================================================
-- 5. ROUTE HISTORY QUERIES (analytics + RAG context for the copilot)
-- ============================================================

-- 5.1 Most requested origin-destination pairs
SELECT origin_name, destination_name, COUNT(*) AS query_count,
       ROUND(AVG(composite_safety_score)::numeric, 2) AS avg_safety,
       ROUND(AVG(distance_meters)::numeric / 1000.0, 2) AS avg_distance_km
FROM public.routes
GROUP BY origin_name, destination_name
ORDER BY query_count DESC;

-- 5.2 Daily route-query trend (last 30 days)
SELECT DATE(created_at) AS query_day,
       COUNT(*) AS total_queries,
       ROUND(AVG(composite_safety_score)::numeric, 2) AS avg_composite_safety
FROM public.routes
WHERE created_at > timezone('utc', now()) - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1 DESC;

-- 5.3 Routes passing through low-safety segments (exposure audit)
SELECT r.origin_name, r.destination_name, r.composite_safety_score,
       s.name AS risky_segment, s.safety_score AS segment_safety
FROM public.routes r
CROSS JOIN UNNEST(r.segment_ids) AS sid
JOIN public.segments s ON s.id = sid
WHERE s.safety_score < 55
ORDER BY r.created_at DESC
LIMIT 50;

-- ============================================================
-- 6. ML TRAINING-DATA EXPORT QUERIES
--    (Random Forest baseline + GNN node features)
-- ============================================================

-- 6.1 RF training set: one row per segment (features -> target)
SELECT crime_score, lighting_score, cctv_density, crowd_density,
       length_meters / 1000.0 AS length_km,
       safety_score AS target
FROM public.segments;

-- 6.2 GNN edge list: (u_node, v_node, edge features) — mirrors
--     graph_builder.py's [crime, lighting, cctv, crowd, length_km] features
SELECT seg.id AS segment_id,
       seg.start_lat || ',' || seg.start_lon AS u_node,
       seg.end_lat   || ',' || seg.end_lon   AS v_node,
       seg.crime_score, seg.lighting_score, seg.cctv_density,
       seg.crowd_density, seg.length_meters / 1000.0 AS length_km,
       seg.safety_score AS target
FROM public.segments seg;

-- 6.3 Node-aggregated features (mean over incident edges) for GNN nodes
SELECT u.node_key,
       AVG(u.crime_score)    AS avg_crime,
       AVG(u.lighting_score) AS avg_lighting,
       AVG(u.cctv_density)   AS avg_cctv,
       AVG(u.crowd_density)  AS avg_crowd,
       AVG(u.safety_score)   AS avg_safety,
       COUNT(*)              AS degree
FROM (
    SELECT start_lat || ',' || start_lon AS node_key,
           crime_score, lighting_score, cctv_density, crowd_density, safety_score
    FROM public.segments
    UNION ALL
    SELECT end_lat || ',' || end_lon AS node_key,
           crime_score, lighting_score, cctv_density, crowd_density, safety_score
    FROM public.segments
) u
GROUP BY u.node_key
ORDER BY u.node_key;

-- 6.4 Replay dataset for the seed script (JSON build check)
--     Verify local mumbai_safety_network.json matches the DB:
SELECT COUNT(*) AS db_segments FROM public.segments;  -- expect 338
