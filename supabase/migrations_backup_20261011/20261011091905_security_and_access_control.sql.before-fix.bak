
-- HydroVision: Security and access control
-- Officer district assignments.
-- Client access remains denied until reviewed RLS policies are added.

CREATE TABLE public.officer_district_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id uuid NOT NULL
        REFERENCES public.profiles(id) ON DELETE CASCADE,

    district text NOT NULL,
    state text NOT NULL,

    granted_by uuid
        REFERENCES public.profiles(id) ON DELETE SET NULL,

    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_officer_district_assignment
        UNIQUE (user_id, district, state)
);

CREATE INDEX idx_officer_assignments_user
    ON public.officer_district_assignments (user_id);

CREATE INDEX idx_officer_assignments_district_state
    ON public.officer_district_assignments (district, state);

-- Deny access through ordinary client sessions until policies
-- have been reviewed and explicitly created.
ALTER TABLE public.officer_district_assignments
    ENABLE ROW LEVEL SECURITY;