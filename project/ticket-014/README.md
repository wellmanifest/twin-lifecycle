# Ticket 014: Vendor compact Lifecycle DSL validator and compact twin-lifecycle profile

- **ID**: ticket-014
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Vendor the compact `wellmanifest/lifecycle` validator (`1ea2a90bd5b90a768ad2b36a9c1c330523bc80b4`), compact `standard/twin-lifecycle.lifecycle` using `STATES [...]`, `EVENTS [...]`, and `EVIDENCES [...]`, and enforce zero compaction findings in `standard/conformance.py`.

## Acceptance criteria

- [x] AC-01: `standard/twin-lifecycle.lifecycle` validates with `finding_count == 0`, and `python3 standard/conformance.py --all` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
