# Ticket 020: Modularize conformance and harden symlink traversal, JSON bounds, and intent secret/control checks

- **ID**: ticket-020
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-11-11 user authorized auditing, fixing security and conformance bugs, and optimizing across `wellmanifest/*` standard repositories.

Move `resolve`, `validate_request`, and `validate_state` from `standard/conformance.py` (496L -> ~440L) into `standard/twin_primitives.py` (~465L, re-exported via `__all__` in `standard/conformance.py`) so all `standard/*.py` modules stay well below 500 lines. Harden `has_symlink_ancestor` in `standard/twin_io.py` against relative (`sym_dir/..`, `../sym_dir`) and un-normalized absolute symlink-parent traversal, bound JSON integer digit counts (`<= 400`) before `int()` conversion in `strict_loads`, scan `blueprint["intent"]` with `reject_sensitive` and enforce non-blank single-line UTF-8 control-character-free `bounded_intent` on blueprint and stage intents, pass `allow_nan=False` in `conformance.main`, expand `standard/test_twin_hardening.py`, and reconcile merged `project/ticket-019/README.md` to `DONE`.

## Acceptance criteria

- [x] AC-01: Rebalance `standard/conformance.py` and `standard/twin_primitives.py` with `__all__` re-exports so all `standard/*.py` modules stay strictly `< 500` lines after `ruff format`.
- [x] AC-02: Harden `has_symlink_ancestor` against relative (`sym_dir/..`, `../sym_dir`) and un-normalized absolute symlink-parent traversal, bound JSON integer digits (`<= 400`) before `int()` conversion, scan blueprint `intent` for secret material, reject blank/multi-line/control-char blueprint and stage intents, and enforce `allow_nan=False` in CLI JSON output.
- [x] AC-03: Expand `standard/test_twin_hardening.py`, reconcile merged `project/ticket-019/README.md` to `DONE`, and pass `conformance.py`, `ruff check`, `pytest`, `governance-check.sh`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
