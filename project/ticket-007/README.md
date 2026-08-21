# Ticket 007: Sequential validate-and-repair blueprint from the Plesk service twin

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
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

## Publication evidence

- Implementation pull request: `wellmanifest/twin-lifecycle#14`.
- Exact reviewed head: `79989c7f4fb4132d5f37ca5a73b81c0c42ce413e`.
- Trusted Validator App approval: review `PRR_kwDOT4HscM8AAAABJ8LeLw`,
  bound to the exact implementation head.
- Integrated default-branch commit:
  `d556831ee109655d257e99cc14456599d68c3bbc` on 2026-08-18.
- The implementation branch `ticket/007-validate-repair` is absent remotely
  after merge.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-cursor-grok.md](ai-cursor-grok.md)
