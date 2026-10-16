
CREATE TABLE IF NOT EXISTS public.ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id TEXT NOT NULL UNIQUE,
    active_source TEXT NOT NULL CHECK (
        active_source IN ('cwc_gauge', 'open_meteo', 'nasa_gpm')
    ),
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    triggered_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'running', 'succeeded', 'degraded', 'failed')
    ),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts = 3),
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    result JSONB,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_pending
ON public.ingestion_jobs (available_at, created_at)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_running
ON public.ingestion_jobs (locked_at)
WHERE status = 'running';

ALTER TABLE public.ingestion_jobs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.ingestion_jobs FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.ingestion_jobs TO service_role;

CREATE OR REPLACE FUNCTION public.claim_ingestion_job()
RETURNS SETOF public.ingestion_jobs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    selected_job_id UUID;
BEGIN
    -- A job abandoned on its final attempt must not remain running forever.
    UPDATE public.ingestion_jobs
    SET
        status = 'failed',
        last_error = COALESCE(
            last_error,
            'Worker lease expired after the final attempt.'
        ),
        locked_at = NULL,
        finished_at = NOW(),
        updated_at = NOW()
    WHERE status = 'running'
      AND locked_at < NOW() - INTERVAL '30 minutes'
      AND attempts >= max_attempts;

    -- Atomically claim one eligible job.
    SELECT id
    INTO selected_job_id
    FROM public.ingestion_jobs
    WHERE attempts < max_attempts
      AND (
          (status = 'pending' AND available_at <= NOW())
          OR
          (
              status = 'running'
              AND locked_at < NOW() - INTERVAL '30 minutes'
          )
      )
    ORDER BY created_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF selected_job_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    UPDATE public.ingestion_jobs
    SET
        status = 'running',
        attempts = attempts + 1,
        locked_at = NOW(),
        started_at = COALESCE(started_at, NOW()),
        updated_at = NOW()
    WHERE id = selected_job_id
    RETURNING *;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_ingestion_job()
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_ingestion_job()
TO service_role;
