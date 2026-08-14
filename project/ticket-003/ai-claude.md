---
participant-id: agent:claude
participant: claude
role: agent
ticket: ticket-003
---
# Participant: claude (AI agent)

## Understanding

The repository has a governance gate but no test gate. `standard/conformance.py`
is the only thing that proves the blueprint rules, the projection parity and
the pinned validator digests hold, and nothing ran it automatically.

A workflow for exactly this already existed as a local, unpublished commit.
Writing a second one would have produced two competing workflow files, so this
ticket publishes that one instead of replacing it.

## Execution plan

1. Cherry-pick `ci: require Lifecycle DSL conformance`, preserving its author.
2. Repin `actions/checkout` and `actions/setup-python` to the exact revisions
   the adopted governance workflow uses, so both workflows age together.
3. Record evidence and pass the managed gate.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Published `.github/workflows/lifecycle-conformance.yml` through a cherry-pick
  that keeps its original authorship.
- Repinned `actions/checkout` to `3d3c42e5` and `actions/setup-python` to
  `5fda3b95`, the revisions already used by the adopted governance workflow.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
