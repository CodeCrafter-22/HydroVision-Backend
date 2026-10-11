
-- HydroVision: Initial core schema
-- Review locally before applying to Supabase.

-- PostGIS supports geographic points and ward boundaries.
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;

-- 1. Villages
CREATE TABLE public.villages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    name text NOT NULL,
    district text NOT NULL,
    state text NOT NULL,
    panchayat_contact_name text,
    panchayat_phone text,
    geom extensions.geography(Point, 4326),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Wards
CREATE TABLE public.wards (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    code text NOT NULL,
    name text NOT NULL,
    population integer CHECK (population IS NULL OR population >= 0),
    geom extensions.geometry(MultiPolygon, 4326),
    elevation_min_m numeric,
    elevation_mean_m numeric,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (village_id, code)
);

-- 3. User profiles, linked to Supabase Auth
CREATE TABLE public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name text,
    phone text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 4. User roles
CREATE TABLE public.user_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL
        REFERENCES public.profiles(id) ON DELETE CASCADE,
    role text NOT NULL
        CHECK (role IN (
            'resident',
            'panchayat',
            'volunteer',
            'officer',
            'admin'
        )),
    village_id uuid REFERENCES public.villages(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 5. River gauge readings
CREATE TABLE public.gauge_readings (
    id bigserial PRIMARY KEY,
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    source text NOT NULL,
    gauge_id text,
    observed_at timestamptz NOT NULL,
    level_m numeric,
    discharge_m3s numeric,
    quality text,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid,
    raw_payload jsonb,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

-- 6. Rainfall readings
CREATE TABLE public.rain_readings (
    id bigserial PRIMARY KEY,
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    source text NOT NULL,
    observed_at timestamptz NOT NULL,
    rain_mm numeric NOT NULL CHECK (rain_mm >= 0),
    accumulation_minutes integer
        CHECK (
            accumulation_minutes IS NULL
            OR accumulation_minutes > 0
        ),
    grid_id text,
    quality text,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid,
    raw_payload jsonb,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

-- 7. Flood-risk snapshots
CREATE TABLE public.risk_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    village_id uuid NOT NULL
        REFERENCES public.villages(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    tier text NOT NULL
        CHECK (tier IN ('Watch', 'Warning', 'Danger', 'Evacuate')),
    probability numeric
        CHECK (
            probability IS NULL
            OR probability BETWEEN 0 AND 1
        ),
    hours_to_impact numeric
        CHECK (hours_to_impact IS NULL OR hours_to_impact >= 0),
    confidence numeric
        CHECK (
            confidence IS NULL
            OR confidence BETWEEN 0 AND 1
        ),
    explanation jsonb,
    model_version text,
    source_freshness jsonb,
    is_simulated boolean NOT NULL DEFAULT false,
    replay_run_id uuid
);

-- 8. External data-source health
CREATE TABLE public.source_health (
    id bigserial PRIMARY KEY,
    source text NOT NULL,
    status text NOT NULL,
    last_success_at timestamptz,
    last_checked_at timestamptz NOT NULL DEFAULT now(),
    details jsonb,
    is_backup_active boolean NOT NULL DEFAULT false
);

-- Indexes for common village and time-based lookups
CREATE INDEX idx_wards_village
    ON public.wards (village_id);

CREATE INDEX idx_user_roles_user
    ON public.user_roles (user_id);

CREATE INDEX idx_user_roles_village
    ON public.user_roles (village_id);

CREATE INDEX idx_gauge_village_observed
    ON public.gauge_readings (village_id, observed_at DESC);

CREATE INDEX idx_rain_village_observed
    ON public.rain_readings (village_id, observed_at DESC);

CREATE INDEX idx_risk_village_created
    ON public.risk_snapshots (village_id, created_at DESC);

CREATE INDEX idx_source_health_source_checked
    ON public.source_health (source, last_checked_at DESC);

-- Deny-by-default until reviewed policies are added.
ALTER TABLE public.villages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gauge_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rain_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_health ENABLE ROW LEVEL SECURITY;