# Ticket 015: Validate CLI target paths in conformance

- **ID**: ticket-015
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-01

## Goal and scope

`standard/conformance.py` previously accepted only `--all` and ignored or rejected CLI target paths, preventing callers and adopters from validating external twin-lifecycle documents or directories. Extend `standard/conformance.py` to accept positional target files/directories and `--blueprint` definitions fail-closed while preserving default `--all` self-conformance.

## Acceptance criteria

- [x] AC-01: `standard/conformance.py` validates supplied file and directory targets fail-closed (returning exit code 1 with `TWINLC-*` findings on missing/empty/invalid targets) and preserves `run_all()` self-conformance, verified by `standard/test_conformance_cli.py`, `./project/governance-check.sh`, and `wellman check`.

## Tracking boundary

`SESSION_EXECUTION_AUTHORIZATION` recorded from user autonomous remediation request.
