# Ticket 017: Harden directory target duplicate-key scan and expand CLI conformance tests

- **ID**: ticket-017
- **Owner**: tom
- **Status**: DONE
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

Close a fail-open gap in directory target scanning (`standard/twin_targets.py`) where
`wellmanifest.twin-lifecycle/v1` or `wellmanifest.twin-lifecycle-binding/v1` JSON
documents containing duplicate JSON keys or malformed JSON syntax were silently skipped
when `explicit_file` was `False`, ensure self-suite `ContractError` failures in
`standard/conformance.py` emit structured JSON on stdout with exit code `1`, expand
`standard/test_conformance_cli.py` with full regression coverage while removing its
legacy `ruff` ignore overrides in `pyproject.toml`, and reconcile merged `ticket-016`.

## Acceptance criteria

- [x] AC-01: `standard/twin_targets.py` fails closed (`TWINLC-DOC-001`) on duplicate-key
      or malformed twin-lifecycle JSON files during directory target scans while ignoring
      unrelated non-twin JSON documents, and `standard/conformance.py` emits structured
      JSON when `run_all()` raises `ContractError`.
- [x] AC-02: `standard/test_conformance_cli.py` covers duplicate-key & broken-JSON
      directory scans, direct/nested symlinks, `bool`-for-`int`, `recordedAt` RFC3339,
      unhashable lists, inline secret scanning, and structured self-suite failures,
      passing `ruff check --no-cache standard` without test ignore overrides and
      `python3 -m pytest -q`.
- [x] AC-03: Close merged `ticket-016` and pass `./project/governance-check.sh --base origin/main`
      and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
