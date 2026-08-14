# Ticket 002: Assign standard contracts to integration workstream

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-14

## Goal and scope

Correct the adopted repository ownership map so versioned contract artifacts
under `standard/**` belong to the `integration` workstream. Without this entry,
the fail-closed gate rejects every legitimate schema, grammar and conformance
change because no workstream owns the repository's primary contract directory.

## Acceptance criteria

- [x] AC-01: `integration.ownedPaths` contains the exact `standard/**` pattern.
- [x] AC-02: The effective manifest and ticket intent validate successfully.
- [x] AC-03: Governance accepts a bounded integration ticket that owns a
  `standard/**` path and continues rejecting unrelated scope.
- [x] AC-04: No managed package file, runtime dependency or public contract is
  changed by this ownership correction.

## Risks

- Broad ownership could allow unrelated changes. The added pattern is limited
  to the existing normative `standard/` directory.
- This changes coordination metadata only; it does not authorize transitions
  or alter any Twin contract bytes.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
