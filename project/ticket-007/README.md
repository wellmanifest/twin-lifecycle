# Ticket 007: Sequential validate-and-repair blueprint from the Plesk service twin

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-18

## Goal and scope

Turn the Plesk multi-subscription repair into the Wellmanifest standard for
how a Digital Twin is validated and then repaired one adjacent stage at a
time. `twin-reference/v1` stays the product lifecycle. `service-observe-repair/v1`
owns the service-twin loop. Apply authority stays in
`wellmanifest/repair-lifecycle`. No secrets, no schema digest change.

## Acceptance criteria

- [x] AC-01: `python3 standard/conformance.py --all` accepts the new blueprint
  and rejects skip-ahead with `TWINLC-SEQUENCE-001`.
- [x] AC-02: `docs/VALIDATE_AND_REPAIR.md` states the sequential rule and the
  Plesk inventory example without credentials.
- [x] AC-03: Managed governance passes for exactly this integration ticket.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-cursor-grok.md](ai-cursor-grok.md)
