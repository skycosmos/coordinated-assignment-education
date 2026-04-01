-- RL model data layout for CCAS + Supabase
-- Run in: Supabase Dashboard → SQL → New query
-- Requires extension for gen_random_uuid (usually enabled in Supabase)

-- ---------------------------------------------------------------------------
-- Training / evaluation jobs (one row per run)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.rl_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    name text NOT NULL,
    algorithm text,
    model_version text,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.rl_runs IS 'RL training or evaluation job metadata.';
COMMENT ON COLUMN public.rl_runs.config IS 'Hyperparameters, seeds, env name, feature flags.';
COMMENT ON COLUMN public.rl_runs.metadata IS 'Arbitrary run-level tags (git sha, host, notes).';

CREATE INDEX IF NOT EXISTS idx_rl_runs_created_at ON public.rl_runs (created_at DESC);

-- ---------------------------------------------------------------------------
-- Per-step or per-decision outputs (core RL telemetry)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.rl_outputs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    run_id uuid NOT NULL REFERENCES public.rl_runs (id) ON DELETE CASCADE,
    step_index integer,
    episode_index integer,
    reward double precision,
    cumulative_return double precision,
    action jsonb NOT NULL,
    observation_digest jsonb,
    value_estimate double precision,
    advantage double precision,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw_output jsonb,
    paper_id uuid REFERENCES public.papers (id) ON DELETE SET NULL,
    city_id uuid,
    subject_type text,
    subject_id uuid
);

COMMENT ON TABLE public.rl_outputs IS 'RL transitions / predictions linked to a run.';
COMMENT ON COLUMN public.rl_outputs.action IS 'Chosen action: discrete id, vector, or structured object.';
COMMENT ON COLUMN public.rl_outputs.observation_digest IS 'Compact state summary; avoid huge tensors here.';
COMMENT ON COLUMN public.rl_outputs.metrics IS 'Training diagnostics: entropy, KL, losses, etc.';
COMMENT ON COLUMN public.rl_outputs.raw_output IS 'Optional full model payload for debugging.';
COMMENT ON COLUMN public.rl_outputs.subject_type IS 'Optional discriminator when not paper/city specific.';
COMMENT ON COLUMN public.rl_outputs.city_id IS 'Optional link to a city UUID when applicable.';

CREATE INDEX IF NOT EXISTS idx_rl_outputs_run_id ON public.rl_outputs (run_id);
CREATE INDEX IF NOT EXISTS idx_rl_outputs_paper_id ON public.rl_outputs (paper_id);
CREATE INDEX IF NOT EXISTS idx_rl_outputs_city_id ON public.rl_outputs (city_id);
CREATE INDEX IF NOT EXISTS idx_rl_outputs_created_at ON public.rl_outputs (created_at DESC);

-- ---------------------------------------------------------------------------
-- Row Level Security: public read, writes via service role only
-- ---------------------------------------------------------------------------
ALTER TABLE public.rl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rl_outputs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon read rl_runs" ON public.rl_runs;
DROP POLICY IF EXISTS "Allow anon read rl_outputs" ON public.rl_outputs;

CREATE POLICY "Allow anon read rl_runs"
    ON public.rl_runs FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow anon read rl_outputs"
    ON public.rl_outputs FOR SELECT
    TO anon, authenticated
    USING (true);

-- No INSERT/UPDATE/DELETE policies for anon — blocked by default when RLS is on.
