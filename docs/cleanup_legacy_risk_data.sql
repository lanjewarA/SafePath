-- Remove the retired risk input and its historical category from Supabase.
-- Review and run this migration in the Supabase SQL Editor after deploying
-- the backend/frontend changes.

BEGIN;

ALTER TABLE public.segments
    DROP COLUMN IF EXISTS cctv_density;

DELETE FROM public.safety_reports
WHERE report_type = 'cctv_broken';

ALTER TABLE public.safety_reports
    DROP CONSTRAINT IF EXISTS safety_reports_report_type_check;

ALTER TABLE public.safety_reports
    ADD CONSTRAINT safety_reports_report_type_check
    CHECK (report_type IN ('poor_lighting', 'harassment_risk', 'isolated_area'));

UPDATE public.segments
SET safety_score = ROUND(
    ((
        0.4375 * (1.0 - crime_score)
        + 0.3125 * lighting_score
        + 0.25 * crowd_density
    ) * 100.0)::numeric,
    2
);

DO $$
BEGIN
    IF to_regclass('public.seeded_hazards') IS NOT NULL THEN
        DELETE FROM public.seeded_hazards WHERE id = 'hazard-ng-003';
    END IF;
END
$$;

COMMIT;
