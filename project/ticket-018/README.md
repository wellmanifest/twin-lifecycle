# Ticket 018: Harden twin-lifecycle regular-file I/O, URI segments, JSON bounds, and unhashable guards

- **ID**: ticket-018
- **Owner**: tom
- **Status**: DONE
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

Harden `wellmanifest/twin-lifecycle` (`standard/twin_primitives.py`,
`standard/twin_targets.py`, and `standard/conformance.py`): enforce
`O_NOFOLLOW | O_NONBLOCK` 4 MiB regular-file reads and UTF-8 error handling across
CLI target scans and blueprint loading; reject `.` / `..` / empty `//` URI path
segments in `match()`; reject `NaN`/`Infinity`, overflow floats (`1e999`/`-1e999`),
`RecursionError`, non-string object keys, and nesting deeper than `MAX_JSON_DEPTH = 64`
across `strict_loads`, `canonical(allow_nan=False)`, and iterative `reject_sensitive`;
guard unhashable JSON values (`[]`, `{}`) in enum/schema/kind fields via `enum_str`;
add `standard/test_twin_hardening.py` without touching pinned vendored
`standard/lifecycle*.py` or schema/grammar/profile artifacts; and mark merged
`ticket-017` `DONE`.

## Acceptance criteria

- [x] AC-01: `standard/twin_primitives.py`, `standard/twin_targets.py`, and
      `standard/conformance.py` enforce `O_NOFOLLOW | O_NONBLOCK` regular-file reads,
      URI segment traversal guards, strict JSON float/depth/key bounds, iterative
      `reject_sensitive`, and `enum_str` unhashable guards while keeping all modules
      `< 500` lines and preserving frozen digests.
- [x] AC-02: `ruff check --no-cache standard`, `python3 standard/conformance.py`,
      and `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q` pass.
- [x] AC-03: Close merged `ticket-017`, and pass `./project/governance-check.sh --base origin/main`
      and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
