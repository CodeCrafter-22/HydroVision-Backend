
-- HydroVision: provisional freshness policy and dashboard views.
--
-- PROVISIONAL SETTINGS, NOT VALIDATED FLOOD-WARNING THRESHOLDS:
-- Gauge readings: 30 minutes.
-- Rainfall readings: 60 minutes.
-- Risk snapshots: 60 minutes.
--
-- Future timestamps are classified as unknown to expose clock/data issues.
-- Missing readings or missing successful source checks are unknown.
-- Stale/unknown data must not be interpreted as evidence of safety.
--
-- A fresh snapshot does not guarantee its inputs are fresh or the
-- resulting prediction is reliable. Consumers must inspect all statuses.

-- 1. Latest known risk snapshot per village, including stale snapshots.
-- This diagnostic view allows the UI to show why risk data is unavailable
-- or outdated rather than silently hiding that condition.
CREATE OR REPLACE VIEW public.v_village_latest_risk_status
WITH (security_invoker = true)
AS
WITH latest AS (
    SELECT DISTINCT ON (rs.village_id)
        rs.id AS risk_snapshot_id,
        rs.village_id,
        rs.tier,
        rs.probability,
        rs.confidence,
        rs.created_at,
        rs.source_freshness,
        rs.is_simulated,
        rs.replay_run_id
    FROM public.risk_snapshots AS rs
    ORDER BY rs.village_id, rs.created_at DESC, rs.id DESC
)
SELECT
    l.*,
    CASE
        WHEN l.created_at IS NULL OR l.created_at > now()
            THEN 'unknown'
        WHEN l.created_at < now() - interval '60 minutes'
            THEN 'stale'
        ELSE 'fresh'
    END AS risk_freshness_status,
    CASE
        WHEN l.created_at IS NULL OR l.created_at > now()
            THEN NULL
        ELSE EXTRACT(EPOCH FROM (now() - l.created_at))
    END AS risk_age_seconds
FROM latest AS l;

COMMENT ON VIEW public.v_village_latest_risk_status IS
'Latest snapshot per village, including stale/unknown status. The 60-minute risk limit is provisional, not a validated warning threshold.';

-- 2. Fresh risk snapshots only.
-- Input freshness statuses remain visible and must be considered separately.
CREATE OR REPLACE VIEW public.v_village_current_risk
WITH (security_invoker = true)
AS
WITH latest_gauge AS (
    SELECT
        village_id,
        MAX(observed_at) AS latest_gauge_at
    FROM public.gauge_readings
    WHERE is_simulated = false
    GROUP BY village_id
),
latest_rain AS (
    SELECT
        village_id,
        MAX(observed_at) AS latest_rain_at
    FROM public.rain_readings
    WHERE is_simulated = false
    GROUP BY village_id
),
latest_source_health AS (
    SELECT DISTINCT ON (source)
        source,
        status,
        last_success_at,
        last_checked_at,
        is_backup_active
    FROM public.source_health
    ORDER BY source, last_checked_at DESC, id DESC
),
source_health_summary AS (
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'source', source,
                'status', status,
                'last_success_at', last_success_at,
                'last_checked_at', last_checked_at,
                'is_backup_active', is_backup_active,
                'freshness_status',
                    CASE
                        WHEN last_success_at IS NULL
                          OR last_success_at > now()
                            THEN 'unknown'
                        WHEN last_success_at < now() - interval '60 minutes'
                            THEN 'stale'
                        ELSE 'fresh'
                    END
            )
            ORDER BY source
        ),
        '[]'::jsonb
    ) AS source_health
    FROM latest_source_health
)
SELECT
    v.id AS village_id,
    v.code AS village_code,
    v.name AS village_name,
    rs.risk_snapshot_id,
    rs.tier,
    rs.probability,
    rs.confidence,
    rs.created_at,
    rs.source_freshness,
    rs.is_simulated,
    rs.replay_run_id,
    g.latest_gauge_at,
    CASE
        WHEN g.latest_gauge_at IS NULL
          OR g.latest_gauge_at > now()
            THEN 'unknown'
        WHEN g.latest_gauge_at < now() - interval '30 minutes'
            THEN 'stale'
        ELSE 'fresh'
    END AS gauge_freshness_status,
    r.latest_rain_at,
    CASE
        WHEN r.latest_rain_at IS NULL
          OR r.latest_rain_at > now()
            THEN 'unknown'
        WHEN r.latest_rain_at < now() - interval '60 minutes'
            THEN 'stale'
        ELSE 'fresh'
    END AS rainfall_freshness_status,
    sh.source_health
FROM public.v_village_latest_risk_status AS rs
JOIN public.villages AS v ON v.id = rs.village_id
LEFT JOIN latest_gauge AS g ON g.village_id = v.id
LEFT JOIN latest_rain AS r ON r.village_id = v.id
CROSS JOIN source_health_summary AS sh
WHERE rs.risk_freshness_status = 'fresh';

COMMENT ON VIEW public.v_village_current_risk IS
'Fresh risk snapshots with separate gauge, rainfall and source-health indicators. Freshness limits are provisional and do not validate the prediction.';

-- 3. Ward-level risk context.
-- This view does NOT calculate a physical flood boundary or prove inundation.
CREATE OR REPLACE VIEW public.v_ward_flood_status
WITH (security_invoker = true)
AS
SELECT
    w.id AS ward_id,
    w.village_id,
    w.code AS ward_code,
    w.name AS ward_name,
    w.geom AS ward_geometry,
    w.population,
    w.elevation_min_m,
    w.elevation_mean_m,
    rs.tier AS latest_village_risk_tier,
    rs.probability AS latest_village_risk_probability,
    rs.confidence AS latest_village_risk_confidence,
    rs.created_at AS risk_snapshot_created_at,
    rs.risk_freshness_status,
    rs.is_simulated,
    rs.replay_run_id,
    'estimated_risk_context_not_authoritative_flood_extent'
        AS interpretation_label
FROM public.wards AS w
LEFT JOIN public.v_village_latest_risk_status AS rs
    ON rs.village_id = w.village_id;

COMMENT ON VIEW public.v_ward_flood_status IS
'Ward geometry with village-level risk context. It is not an authoritative flood extent or a ward-level inundation model.';

-- 4. Population totals by fresh village risk tier.
-- NULL population remains unknown and is counted separately.
CREATE OR REPLACE VIEW public.v_people_at_risk
WITH (security_invoker = true)
AS
SELECT
    cr.tier AS risk_tier,
    COUNT(w.id) AS ward_count,
    COUNT(w.population) AS wards_with_known_population,
    COUNT(*) FILTER (WHERE w.population IS NULL)
        AS wards_with_unknown_population,
    SUM(w.population) AS known_population,
    'fresh_village_risk_only; population may be incomplete'
        AS interpretation_label
FROM public.v_village_current_risk AS cr
JOIN public.wards AS w ON w.village_id = cr.village_id
WHERE cr.is_simulated = false
GROUP BY cr.tier;

COMMENT ON VIEW public.v_people_at_risk IS
'Known ward population grouped by fresh non-simulated village risk tier. Unknown population is not treated as zero; this is not a count of confirmed people physically inundated.';