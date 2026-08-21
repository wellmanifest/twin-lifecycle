# Ticket 008: Export the ecosystem Twin agent binding

- **ID**: ticket-008
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-21

## Goal and scope

Export the prose-only `subactor/twin` mapping as a machine-readable ecosystem
agent binding. The profile composes the observational Twin with Doctor, Repair
and Validator roles while preserving sequential stages, digest-bound evidence,
external repair authority and independent exact-result acceptance.

This is a standards profile, not Subactor runtime. It grants no authority and
does not start agents, controllers, schedulers or repository effects.

## Acceptance criteria

- [x] AC-01: The binding pins `service-observe-repair/v1` and declares adjacent
  `observe → diagnose → prioritize → repair → validate → accept` stages.
- [x] AC-02: Mutation is impossible without an external grant bound to snapshot,
  finding and plan digests; validation remains independent.
- [x] AC-03: Dirty worktrees, secrets, stash decisions and ambiguous ownership
  route to human decision rather than automatic repair.
- [x] AC-04: Conformance accepts the profile and rejects authority expansion,
  skip-ahead and LLM-added operation cases with stable `TWINLC-*` codes.
- [x] AC-05: Governance and full lifecycle conformance pass before publication.

## Publication evidence

- Pull request: `wellmanifest/twin-lifecycle#16`.
- Frozen and approved head: `705308d365b9f2347fa450e67958c1b24d5a6117`.
- Validator run: `32459412892`; review: `4990902678`.
- Merge commit: `3518a7f`; merged `2026-08-21T07:38:52Z`.
- The protected delivery process deleted the remote implementation branch.

## Closure boundary

This governance-only closure records the integrated standard. It changes no
binding, schema, conformance implementation or authority semantics.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
