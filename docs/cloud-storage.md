# Hosted storage foundation

AgentProof remains local-first. This milestone includes a versioned migration and a readable schema snapshot; it does **not** connect the Python application to Supabase and has not been applied to a live project.

## Schema snapshot

`supabase/migrations/20261027000000_agentproof_hosted_storage.sql` is the one-time migration for a fresh, dedicated AgentProof Supabase project. `supabase/schema.sql` is the readable schema snapshot. The migration defines two owner-scoped tables:

- `agentproof_evaluation_runs`: a JSONB payload for a completed evaluation run plus queryable suite, provider, model, score, and timestamps.
- `agentproof_trace_evaluations`: trace, check definitions, results, summary, pass/fail, score, and timestamp.

Both tables use `user_id` tied to `auth.users`, unique keys scoped to the owner, indexes for owner-filtered history, row-level security (RLS), and explicit policies for each operation. Unauthenticated access is revoked; authenticated users can only operate on rows whose `user_id` matches `auth.uid()`. Update policies use both `USING` and `WITH CHECK` so an owner cannot transfer a row to another account.

## Python adapter (opt-in, not wired into the dashboard)

`agentproof/cloud_storage.py` provides a stdlib-only REST adapter for saving and reading evaluation-run and trace-evaluation records. It keeps SQLite untouched and is not selected automatically by the CLI or local dashboard yet.

Configure these environment variables only when testing against a dedicated project where the reviewed migration has been applied:

- `AGENTPROOF_SUPABASE_URL`: the project's HTTPS URL.
- `AGENTPROOF_SUPABASE_ANON_KEY`: the project's publishable/anon key.
- `AGENTPROOF_SUPABASE_ACCESS_TOKEN`: a real user access token issued by Supabase Auth.

The adapter calls Supabase Auth to verify the token and obtains the owner ID from that verified response; it does not trust a user ID passed by the caller. Data requests include the user token so RLS remains authoritative. Never use a service-role/secret key as the publishable key or access token. Mocked unit tests validate request construction and owner scoping; they do not prove that the migration works against a live database.

## Important security and deployment notes

- Treat `schema.sql` as a reviewed baseline for a **dedicated AgentProof Supabase project**, not as an instruction to run against an unrelated existing project.
- The migration is versioned but has not been applied or tested against a live Supabase database. Apply it only to a fresh, dedicated development project first; do not run it against an existing unrelated project or after manually applying the schema snapshot.
- Run database policy tests for authenticated owner, authenticated non-owner, and anonymous users for SELECT, INSERT, UPDATE, and DELETE. Confirm both denied writes and zero-row reads behave as expected.
- The schema has not been applied to a live database and no hosted integration is implemented by this change.
- The future server must derive `user_id` from a verified Supabase Auth identity, never from an untrusted request body.
- Never expose a Supabase service-role/secret key to the browser. Prefer user-scoped JWT access and RLS; keep any privileged key server-side only if a later architecture demonstrably needs it.
- Keep local SQLite as the default and opt-in hosted storage so existing users are not forced to create an account or connect a cloud service.

## Next implementation steps

1. Run the migration in a dedicated development project and add database-level RLS tests for owner, non-owner, and anonymous access.
2. Wire this adapter behind the CLI/dashboard repository boundary, without changing SQLite defaults.
3. Add integration tests for identity ownership and cross-user isolation.
4. Add hosted sign-in only after the backend can verify identity and enforce per-user access end to end.
