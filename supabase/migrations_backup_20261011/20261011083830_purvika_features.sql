-- HydroVision: Purvika feature tables
-- Review locally before applying to Supabase.

-- 1. Replay scenario definitions
CREATE TABLE public.replay_scenarios (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    description text,
    configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Replay execution records
CREATE TABLE public.replay_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id uuid
        REFERENCES public.replay_scenarios(id) ON DELETE SET NULL,
    status text NOT NULL DEFAULT 'pending',
    configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    results jsonb,
    error_details jsonb,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        started_at IS NULL
        OR completed_at IS NULL
        OR completed_at >= started_at
    )
);

-- Link simulated data and risk snapshots to replay runs
ALTER TABLE public.gauge_readings
    ADD CONSTRAINT fk_gauge_readings_replay_run
    FOREIGN KEY (replay_run_id)
    REFERENCES public.replay_runs(id) ON DELETE SET NULL;

ALTER TABLE public.rain_readings
    ADD CONSTRAINT fk_rain_readings_replay_run
    FOREIGN KEY (replay_run_id)
    REFERENCES public.replay_runs(id) ON DELETE SET NULL;

ALTER TABLE public.risk_snapshots
    ADD CONSTRAINT fk_risk_snapshots_replay_run
    FOREIGN KEY (replay_run_id)
    REFERENCES public.replay_runs(id) ON DELETE SET NULL;

-- 3. Knowledge-base documents
CREATE TABLE public.kb_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    document_type text,
    storage_path text,
    status text NOT NULL DEFAULT 'pending',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    uploaded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 4. Document knowledge chunks
CREATE TABLE public.knowledge_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL
        REFERENCES public.kb_documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    content text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

-- 5. Event memory for historical context
CREATE TABLE public.event_memory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    event_type text NOT NULL,
    content text NOT NULL,
    occurred_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 6. Rumor and claim verification records
CREATE TABLE public.rumor_checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    claim text NOT NULL,
    assessment text,
    evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT 'pending',
    checked_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    checked_at timestamptz
);

-- 7. Audit trail
CREATE TABLE public.audit_log (
    id bigserial PRIMARY KEY,
    actor_user_id uuid
        REFERENCES public.profiles(id) ON DELETE SET NULL,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id text,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_replay_runs_scenario_created
    ON public.replay_runs (scenario_id, created_at DESC);

CREATE INDEX idx_knowledge_chunks_document
    ON public.knowledge_chunks (document_id, chunk_index);

CREATE INDEX idx_event_memory_village_occurred
    ON public.event_memory (village_id, occurred_at DESC);

CREATE INDEX idx_rumor_checks_village_created
    ON public.rumor_checks (village_id, created_at DESC);

CREATE INDEX idx_audit_log_created
    ON public.audit_log (created_at DESC);

-- Enable RLS; access policies must be reviewed separately.
ALTER TABLE public.replay_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.replay_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rumor_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;