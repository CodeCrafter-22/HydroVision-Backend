
-- HydroVision: Operations schema
-- Aligned with the HydroVision schema contract.
-- Replay-run foreign keys are added after replay_runs is created
-- in the following Purvika migration.

-- 1. Community reports
CREATE TABLE public.reports (
    id uuid PRIMARY KEY,
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    reporter_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    photo_path text,
    latitude numeric,
    longitude numeric,
    location_status text NOT NULL,
    level_estimate numeric,
    confidence numeric,
    verification_status text NOT NULL DEFAULT 'pending',
    verified_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    verified_at timestamptz,
    trust_score numeric,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 2. Alert templates
CREATE TABLE public.alert_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tier text NOT NULL
        CHECK (tier IN ('Watch', 'Warning', 'Danger', 'Evacuate')),
    language text NOT NULL,
    title text NOT NULL,
    body text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 3. Alerts
CREATE TABLE public.alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    risk_snapshot_id uuid
        REFERENCES public.risk_snapshots(id) ON DELETE SET NULL,
    tier text NOT NULL
        CHECK (tier IN ('Watch', 'Warning', 'Danger', 'Evacuate')),
    status text NOT NULL DEFAULT 'draft',
    message text NOT NULL,
    edited_message text,
    rejection_reason text,
    approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 4. Alert delivery records
CREATE TABLE public.alert_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL
        REFERENCES public.alerts(id) ON DELETE CASCADE,
    recipient_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    channel text NOT NULL,
    destination_masked text,
    status text NOT NULL DEFAULT 'pending',
    sent_at timestamptz,
    delivered_at timestamptz,
    acknowledged_at timestamptz,
    last_reply text,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 5. Acknowledgement events
CREATE TABLE public.ack_events (
    id bigserial PRIMARY KEY,
    alert_delivery_id uuid NOT NULL
        REFERENCES public.alert_deliveries(id) ON DELETE CASCADE,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    reply_code text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_simulated boolean NOT NULL DEFAULT false
);

-- 6. SOS events
CREATE TABLE public.sos_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    reporter_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    status text NOT NULL DEFAULT 'open',
    latitude numeric NOT NULL,
    longitude numeric NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    cancelled_at timestamptz,
    safe_at timestamptz,
    assigned_volunteer_id uuid
        REFERENCES public.profiles(id) ON DELETE SET NULL,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 7. Shelters
CREATE TABLE public.shelters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    name text NOT NULL,
    location extensions.geography(Point, 4326) NOT NULL,
    capacity integer NOT NULL CHECK (capacity >= 0),
    status text NOT NULL DEFAULT 'Open'
        CHECK (status IN ('Open', 'Full', 'Closed')),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 8. Resources
CREATE TABLE public.resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    type text NOT NULL,
    name text NOT NULL,
    location extensions.geography(Point, 4326),
    status text NOT NULL,
    available_count integer NOT NULL DEFAULT 1
        CHECK (available_count >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 9. Resource suggestions
CREATE TABLE public.resource_suggestions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    risk_snapshot_id uuid
        REFERENCES public.risk_snapshots(id) ON DELETE SET NULL,
    resource_type text NOT NULL,
    resource_id uuid
        REFERENCES public.resources(id) ON DELETE SET NULL,
    suggested_recipient_id uuid
        REFERENCES public.profiles(id) ON DELETE SET NULL,
    reason jsonb NOT NULL DEFAULT '{}'::jsonb,
    distance_km numeric CHECK (distance_km IS NULL OR distance_km >= 0),
    status text NOT NULL DEFAULT 'pending',
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_at timestamptz,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 10. Operational tasks
CREATE TABLE public.tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    sos_event_id uuid
        REFERENCES public.sos_events(id) ON DELETE SET NULL,
    suggestion_id uuid
        REFERENCES public.resource_suggestions(id) ON DELETE SET NULL,
    task_type text NOT NULL,
    assigned_to uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    status text NOT NULL DEFAULT 'pending',
    accepted_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 11. After-action records
CREATE TABLE public.after_action (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    kind text NOT NULL,
    title text NOT NULL,
    body jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 12. Situation reports
CREATE TABLE public.sitreps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    language text NOT NULL,
    content text NOT NULL,
    source_window jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 13. Backtest results
CREATE TABLE public.backtest_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id text NOT NULL,
    event_type text NOT NULL,
    source_scope text NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    model_version text NOT NULL,
    metrics jsonb NOT NULL,
    is_summary boolean NOT NULL DEFAULT false,
    is_simulated boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_at >= start_at)
);

-- Lookup indexes
CREATE INDEX idx_reports_village_created
    ON public.reports (village_id, created_at DESC);

CREATE INDEX idx_alerts_village_created
    ON public.alerts (village_id, created_at DESC);

CREATE INDEX idx_alert_deliveries_alert
    ON public.alert_deliveries (alert_id);

CREATE INDEX idx_ack_events_delivery_received
    ON public.ack_events (alert_delivery_id, received_at DESC);

CREATE INDEX idx_sos_village_created
    ON public.sos_events (village_id, created_at DESC);

CREATE INDEX idx_shelters_village
    ON public.shelters (village_id);

CREATE INDEX idx_resources_village
    ON public.resources (village_id);

CREATE INDEX idx_resource_suggestions_village_created
    ON public.resource_suggestions (village_id, created_at DESC);

CREATE INDEX idx_tasks_village_status
    ON public.tasks (village_id, status);

CREATE INDEX idx_sitreps_village_created
    ON public.sitreps (village_id, created_at DESC);

CREATE INDEX idx_backtest_results_event
    ON public.backtest_results (event_id, created_at DESC);

-- Enable RLS. Policies must be reviewed before client access.
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ack_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sos_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shelters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resource_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.after_action ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sitreps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtest_results ENABLE ROW LEVEL SECURITY;