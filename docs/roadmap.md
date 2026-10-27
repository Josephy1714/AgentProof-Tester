# Roadmap and status

## Foundation
- [x] Typed core contracts
- [x] Deterministic assertions
- [x] Suite validation
- [x] Simulated adapter
- [x] Basic runner and JSON report
- [x] Pass/fail regression and recovery comparison
- [x] Local CLI and CI workflow
- [x] OpenAI-compatible Chat Completions adapter with environment-based secrets
- [x] Offline adapter tests that do not make provider requests

## Next milestones
- [ ] Apply category weights with documented semantics
- [ ] Add process-isolated timeout execution
- [ ] Add adapter contract tests and trace schema
- [ ] Add provider-specific integrations and tool-call/trajectory capture
- [ ] Add persistent run history and comparison API
- [ ] Build a dashboard backed by actual run data
- [ ] Threat model, authentication, authorization, retention, and deployment verification

Unchecked items are planned, not implemented. The live provider adapter is opt-in and may incur API charges. No live request or production deployment is implied by CI passing.
