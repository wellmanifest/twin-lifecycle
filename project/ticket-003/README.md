# Ticket 003: Gate the conformance suite in CI

- **ID**: ticket-003
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-14

## Goal and scope

Run the normative conformance suite on every pull request and every push to
the default branch. Until now `standard/conformance.py` was only ever run by
hand, while `subactor/twin` already pins this repository as a normative source
contract — a regression here would have surfaced downstream, not upstream.

The workflow itself was authored locally as `ci: require Lifecycle DSL
conformance`; this ticket publishes that commit with its original authorship
and repins its actions to the exact Node 24 revisions the adopted governance
workflow already uses.

Out of scope: the standard, the blueprint and the conformance rules are
untouched, no runtime dependency is added, and the managed governance workflow
is not modified.

## Acceptance criteria

- [x] AC-01: The suite the workflow runs passes at the accepted base: 4
  canonical documents accepted, 30 adversarial mutations rejected, exit `0`.
- [x] AC-02: Every action is pinned to a full 40-character revision, matching
  the pins in the adopted governance workflow.
- [x] AC-03: The managed gate passes with the change resolving to exactly one
  infrastructure ticket.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
