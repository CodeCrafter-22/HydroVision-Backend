```sql
-- HydroVision: Operations schema
-- Review locally before applying to Supabase.

-- 1. Community reports
CREATE TABLE public.reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    category text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'pending',
    location extensions.geography(Point, 4326),
    photo_path text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Alert templates
CREATE TABLE public.alert_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    channel text NOT NULL,
    language text NOT NULL DEFAULT 'en',
    body_template text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 3. Alerts
CREATE TABLE public.alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    risk_snapshot_id uuid
        REFERENCES public.risk_snapshots(id) ON DELETE SET NULL,
    template_id uuid
        REFERENCES public.alert_templates(id) ON DELETE SET NULL,
    severity text NOT NULL
        CHECK (severity IN ('Watch', 'Warning', 'Danger', 'Evacuate')),
    title text NOT NULL,
    message text NOT NULL,
    status text NOT NULL DEFAULT 'draft',
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);

-- 4. Alert delivery attempts
CREATE TABLE public.alert_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL
        REFERENCES public.alerts(id) ON DELETE CASCADE,
    recipient_user_id uuid
        REFERENCES public.profiles(id) ON DELETE SET NULL,
    channel text NOT NULL,
    destination text,
    status text NOT NULL DEFAULT 'pending',
    provider_message_id text,
    error_details jsonb,
    attempted_at timestamptz,
    delivered_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 5. Alert acknowledgement events
CREATE TABLE public.ack_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL
        REFERENCES public.alerts(id) ON DELETE CASCADE,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    acknowledgement text NOT NULL,
    details jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 6. SOS events
CREATE TABLE public.sos_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    description text,
    location extensions.geography(Point, 4326),
    status text NOT NULL DEFAULT 'open',
    assigned_to uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 7. Shelters
CREATE TABLE public.shelters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    name text NOT NULL,
    address text,
    location extensions.geography(Point, 4326),
    capacity integer CHECK (capacity IS NULL OR capacity >= 0),
    available_capacity integer
        CHECK (available_capacity IS NULL OR available_capacity >= 0),
    status text NOT NULL DEFAULT 'open',
    contact_phone text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 8. Resources
CREATE TABLE public.resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    name text NOT NULL,
    resource_type text NOT NULL,
    quantity numeric NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    unit text,
    location extensions.geography(Point, 4326),
    status text NOT NULL DEFAULT 'available',
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 9. Resource suggestions
CREATE TABLE public.resource_suggestions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    risk_snapshot_id uuid
        REFERENCES public.risk_snapshots(id) ON DELETE SET NULL,
    resource_id uuid
        REFERENCES public.resources(id) ON DELETE SET NULL,
    suggestion jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    reviewed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    reviewed_at timestamptz
);

-- 10. Operational tasks
CREATE TABLE public.tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    title text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'pending',
    priority text NOT NULL DEFAULT 'normal',
    assigned_to uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    due_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 11. After-action records
CREATE TABLE public.after_action (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    title text NOT NULL,
    summary text,
    findings jsonb,
    lessons_learned jsonb,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 12. Situation reports
CREATE TABLE public.sitreps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    title text NOT NULL,
    summary text,
    situation jsonb,
    status text NOT NULL DEFAULT 'draft',
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 13. Backtest results
CREATE TABLE public.backtest_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid
        REFERENCES public.villages(id) ON DELETE SET NULL,
    model_version text NOT NULL,
    metrics jsonb NOT NULL,
    evaluation_start timestamptz,
    evaluation_end timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        evaluation_start IS NULL
        OR evaluation_end IS NULL
        OR evaluation_end >= evaluation_start
    )
);

-- Common lookup indexes
CREATE INDEX idx_reports_village_created
    ON public.reports (village_id, created_at DESC);

CREATE INDEX idx_alerts_village_created
    ON public.alerts (village_id, created_at DESC);

CREATE INDEX idx_alert_deliveries_alert
    ON public.alert_deliveries (alert_id);

CREATE INDEX idx_ack_events_alert_created
    ON public.ack_events (alert_id, created_at DESC);

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

-- Enable RLS. Policies must be reviewed and added before client access.
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
```
