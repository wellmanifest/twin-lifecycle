# Ticket 012: Adopt wellmanifest/new-project 0.20.32 managed package refresh

- **ID**: ticket-012
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-19

## Goal and scope

Adopt `wellmanifest/new-project@0.20.32` (commit `b6ba9c21a65a6a5648ecf904b64c3b75295e136f`), refreshing governance infrastructure, worktrees/leases/continuity checks, and aligning fleet conformance.

## Acceptance criteria

- [ ] AC-01: Run `create_adoption_lock.py` to upgrade from 0.18.6 to 0.20.32.
- [ ] AC-02: Run `install-agent-hosts.sh` and align `manifest.json`.
- [ ] AC-03: Pass `python3 standard/conformance.py --all`.
- [ ] AC-04: Pass `fleet_conformance.py` and `governance_check.py`.

## Participants

- Human participant: user via chat authorization.
- Agent participant: Antigravity assistant.
