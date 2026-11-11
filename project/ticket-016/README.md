# Ticket 016: Modularize twin-lifecycle under 500 lines and harden strict validation

- **ID**: ticket-016
- **Owner**: tom
- **Status**: DONE
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

Sync the modularized `< 500`-line Lifecycle DSL validator from
`wellmanifest/lifecycle@12bdc4c899bd6119cc30fca51d00a62b8582fa79` (`lifecycle.py`,
`lifecycle_audit.py`, `lifecycle_catalog.py`), split `standard/conformance.py`
(down from 909 lines) strictly under 500 lines (`twin_primitives.py`,
`twin_fixtures.py`, `conformance.py`), enforce full JSON Schema parity
(`receipt.aggregateVersion` and `receipt.recordedAt` RFC3339, `blueprintId`,
`blueprintVersion`, `requiredArtifacts`, `actionId`, `compensatingAction`,
`stage`/`transition` boolean flags, `$defs` `maxLength`), fix `bool`-for-`int`,
unhashable list crashes, duplicate JSON keys via `strict_loads`, symlink target
escape in `_iter_target_files`, and inline credential scanning, add
`pyproject.toml`, and reconcile merged `ticket-013`, `ticket-014`, and
`ticket-015`.

## Acceptance criteria

- [x] AC-01: Sync modularized `wellmanifest/lifecycle@12bdc4c8` validator and
      split `standard/conformance.py` so every `.py` module is strictly `< 500`
      lines and passes `ruff check standard`.
- [x] AC-02: Enforce full schema parity, duplicate-key JSON rejection,
      `bool`-for-`int` rejection, unhashable list handling, symlink rejection,
      and inline credential scanning, passing `python3 standard/conformance.py --all`
      and `python3 -m pytest -q`.
- [x] AC-03: Add `pyproject.toml`, close merged `ticket-013`, `ticket-014`, and
      `ticket-015`, and pass `./project/governance-check.sh --base origin/main`
      and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
