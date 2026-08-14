# Ticket 001: Adopt shared Lifecycle DSL profile

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-14

## Goal and scope

Record and publish the validation evidence for the Lifecycle DSL v1 projection
already integrated by pull request #1. The record binds the byte-pinned
validator, exact Twin graph parity and adversarial results without changing the
integrated contract or widening execution and approval authority.

## Acceptance criteria

- [x] AC-01: The local Lifecycle DSL profile validates offline with the
  byte-identical shared validator pinned to lifecycle revision
  `4b5e131a670afb46ca87291479fed7c0fefcf370`.
- [x] AC-02: Conformance proves exact state, transition, initial and terminal
  parity between the profile and `standard/blueprint.examples.json`.
- [x] AC-03: Validator/profile byte drift and four kinds of semantic graph
  drift reject with stable `TWINLC-*` diagnostics.
- [x] AC-04: Four canonical documents and all 30 adversarial cases pass from
  the repository, an unrelated working directory and an offline container.
- [x] AC-05: Governance passes with no runtime dependency, execution or
  authority expansion.

## Risks

- A valid DSL file could still contradict the Twin graph. Exact parity checks
  cover all graph boundaries, not syntax alone.
- A normal Python import could execute a different module from the verified
  bytes. The validator is loaded by explicit verified path and tested with a
  decoy module earlier on `PYTHONPATH`.
- The profile remains descriptive: it cannot execute or authorize a stage
  transition.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
