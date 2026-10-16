
-- Prevent duplicate provider readings for the same village and timestamp.
-- First remove any existing duplicates, keeping the earliest record.
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY village_id, source, observed_at
            ORDER BY id
        ) AS row_num
    FROM public.gauge_readings
    WHERE village_id IS NOT NULL
      AND source IS NOT NULL
      AND observed_at IS NOT NULL
)
DELETE FROM public.gauge_readings AS g
USING ranked AS r
WHERE g.id = r.id
  AND r.row_num > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_gauge_readings_village_source_observed
ON public.gauge_readings (village_id, source, observed_at)
WHERE village_id IS NOT NULL
  AND source IS NOT NULL
  AND observed_at IS NOT NULL;
