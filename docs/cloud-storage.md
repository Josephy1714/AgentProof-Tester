# Hosted storage foundation

AgentProof remains local-first. This file describes the first hosted-storage schema proposal; it does **not** connect the Python application to Supabase and has not been applied to a live project.

## Schema snapshot

`supabase/schema.sql` defines two owner-scoped tables:

- `agentproof_evaluation_runs`: a JSONB payload for a completed evaluation run plus queryable suite, provider, model, score, and timestamps.
- `agentproof_trace_evaluations`: trace, check definitions, results, summary, pass/fail, score, and timestamp.

Both tables use `user_id` tied to `auth.users`, unique keys scoped to the owner, indexes for owner-filtered history, row-level security (RLS), and explicit policies for each operation. Unauthenticated access is revoked; authenticated users can only operate on rows whose `user_id` matches `auth.uid()`. Update policies use both `USING` and `WITH CHECK` so an owner cannot transfer a row to another account.

## Important security and deployment notes

- Treat `schema.sql` as a reviewed baseline for a **dedicated AgentProof Supabase project**, not as an instruction to run against an unrelated existing project.
- This is a schema snapshot, not yet a versioned Supabase migration. Before deployment, generate a proper migration using the Supabase CLI and apply it to a development project first.
- Run database policy tests for authenticated owner, authenticated non-owner, and anonymous users for SELECT, INSERT, UPDATE, and DELETE. Confirm both denied writes and zero-row reads behave as expected.
- The schema has not been applied to a live database and no hosted integration is implemented by this change.
- The future server must derive `user_id` from a verified Supabase Auth identity, never from an untrusted request body.
- Never expose a Supabase service-role/secret key to the browser. Prefer user-scoped JWT access and RLS; keep any privileged key server-side only if a later architecture demonstrably needs it.
- Keep local SQLite as the default and opt-in hosted storage so existing users are not forced to create an account or connect a cloud service.

## Next implementation steps

1. Generate a versioned migration and test RLS policies in a dedicated development project.
2. Add a small cloud repository adapter behind the existing repository interfaces, without changing SQLite defaults.
3. Add integration tests for identity ownership and cross-user isolation.
4. Add hosted sign-in only after the backend can verify identity and enforce per-user access end to end.
