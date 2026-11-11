# Ticket 019: Modularize twin_io and harden JSON overflow/surrogates, ancestor symlinks, secret keys, and ref bounds

- **ID**: ticket-019
- **Owner**: tom
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-11-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-11-11 user authorized auditing, fixing security and conformance bugs, and optimizing across `wellmanifest/*` standard repositories.

Extract `standard/twin_io.py` so `standard/twin_primitives.py` drops well below 500 lines, anchor all 18 `PATTERNS` and `TIMESTAMP_RE` with `\A...\Z`, reject `10**400` JSON integer overflow, 4300+ digit integers, malformed JSON, and lone UTF-16 surrogates across `_enforce_json_bounds`, `strict_loads`, `canonical`, and `reject_sensitive` with `ContractError`, scan JSON object keys with `SECRET_MATERIAL`, enforce positive integer `max_bytes` and relative + deep absolute symlink-ancestor rejection across `read_regular_bytes`, `verify_lifecycle_validator_digests`, `validate_lifecycle_profile`, and `_iter_target_files`, harden `match` against `.`/`..` authorities and colon-delimited `.`/`..`/empty segments, expand `standard/test_twin_hardening.py`, and mark merged `project/ticket-018/README.md` `DONE`.

## Acceptance criteria

- [x] AC-01: Extract `standard/twin_io.py` and slim `standard/twin_primitives.py` well below 500 lines while preserving public exports.
- [x] AC-02: Reject `10**400` and 4300+ digit JSON integers, malformed JSON, lone UTF-16 surrogates, secret-bearing JSON keys, relative/deep-absolute symlink ancestors, unanchored regexes, and colon/dot URI/reference segments with bounded `ContractError` codes.
- [x] AC-03: Expand `standard/test_twin_hardening.py`, mark merged `project/ticket-018/README.md` `DONE`, and pass `conformance.py`, `ruff check`, `pytest`, `governance-check.sh`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
