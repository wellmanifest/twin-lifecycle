# Ticket 008: Export the ecosystem Twin agent binding

- **ID**: ticket-008
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-21

## Goal and scope

Export the prose-only `subactor/twin` mapping as a machine-readable ecosystem
agent binding. The profile composes the observational Twin with Doctor, Repair
and Validator roles while preserving sequential stages, digest-bound evidence,
external repair authority and independent exact-result acceptance.

This is a standards profile, not Subactor runtime. It grants no authority and
does not start agents, controllers, schedulers or repository effects.

## Acceptance criteria

- [ ] AC-01: The binding pins `service-observe-repair/v1` and declares adjacent
  `observe → diagnose → prioritize → repair → validate → accept` stages.
- [ ] AC-02: Mutation is impossible without an external grant bound to snapshot,
  finding and plan digests; validation remains independent.
- [ ] AC-03: Dirty worktrees, secrets, stash decisions and ambiguous ownership
  route to human decision rather than automatic repair.
- [ ] AC-04: Conformance accepts the profile and rejects authority expansion,
  skip-ahead and LLM-added operation cases with stable `TWINLC-*` codes.
- [ ] AC-05: Governance and full lifecycle conformance pass before publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
