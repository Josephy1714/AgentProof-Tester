-- AgentProof hosted-storage migration. Apply to a dedicated project only.

create table public.agentproof_evaluation_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    run_key text not null,
    suite_name text not null,
    suite_version text not null,
    provider text,
    model text,
    score double precision not null,
    started_at timestamptz not null,
    created_at timestamptz not null default now(),
    payload jsonb not null,
    constraint agentproof_evaluation_runs_user_run_key_unique unique (user_id, run_key),
    constraint agentproof_evaluation_runs_payload_object check (jsonb_typeof(payload) = 'object')
);

create index agentproof_evaluation_runs_user_created_idx
    on public.agentproof_evaluation_runs (user_id, created_at desc);
create index agentproof_evaluation_runs_user_suite_idx
    on public.agentproof_evaluation_runs (user_id, suite_name);
create index agentproof_evaluation_runs_user_model_idx
    on public.agentproof_evaluation_runs (user_id, model);

create table public.agentproof_trace_evaluations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    trace_key text not null,
    passed boolean not null,
    score double precision not null,
    evaluated_at timestamptz not null default now(),
    summary jsonb not null default '{}'::jsonb,
    trace jsonb not null,
    checks jsonb not null,
    results jsonb not null,
    constraint agentproof_trace_evaluations_user_trace_key_unique unique (user_id, trace_key),
    constraint agentproof_trace_summary_object check (jsonb_typeof(summary) = 'object'),
    constraint agentproof_trace_trace_array check (jsonb_typeof(trace) = 'array'),
    constraint agentproof_trace_checks_array check (jsonb_typeof(checks) = 'array'),
    constraint agentproof_trace_results_array check (jsonb_typeof(results) = 'array')
);

create index agentproof_trace_evaluations_user_evaluated_idx
    on public.agentproof_trace_evaluations (user_id, evaluated_at desc);
create index agentproof_trace_evaluations_user_passed_idx
    on public.agentproof_trace_evaluations (user_id, passed);

-- RLS is defense in depth. Revoke broad defaults, then grant only authenticated
-- users the operations required by the first hosted version.
alter table public.agentproof_evaluation_runs enable row level security;
alter table public.agentproof_trace_evaluations enable row level security;

revoke all on table public.agentproof_evaluation_runs from anon, authenticated;
revoke all on table public.agentproof_trace_evaluations from anon, authenticated;

grant select, insert, update, delete on table public.agentproof_evaluation_runs to authenticated;
grant select, insert, update, delete on table public.agentproof_trace_evaluations to authenticated;

create policy "Users can read their own evaluation runs"
    on public.agentproof_evaluation_runs for select to authenticated
    using ((select auth.uid()) = user_id);

create policy "Users can insert their own evaluation runs"
    on public.agentproof_evaluation_runs for insert to authenticated
    with check ((select auth.uid()) = user_id);

create policy "Users can update their own evaluation runs"
    on public.agentproof_evaluation_runs for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create policy "Users can delete their own evaluation runs"
    on public.agentproof_evaluation_runs for delete to authenticated
    using ((select auth.uid()) = user_id);

create policy "Users can read their own trace evaluations"
    on public.agentproof_trace_evaluations for select to authenticated
    using ((select auth.uid()) = user_id);

create policy "Users can insert their own trace evaluations"
    on public.agentproof_trace_evaluations for insert to authenticated
    with check ((select auth.uid()) = user_id);

create policy "Users can update their own trace evaluations"
    on public.agentproof_trace_evaluations for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create policy "Users can delete their own trace evaluations"
    on public.agentproof_trace_evaluations for delete to authenticated
    using ((select auth.uid()) = user_id);
