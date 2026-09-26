# Ticket 013: Standardize native Rust twin runtime and anti-tamper C-ABI guard

- **ID**: ticket-013
- **Owner**: human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Standardize native Rust Digital Twin virtualization runtime (`twinerd`), zero-copy OverlayFS Copy-on-Write stage isolation, anti-debugging tripwires (`TracerPid != 0`), C-ABI runtime guard (`libtwinerd_guard.so`), and hardware-bound DRM licensing under Tomasz Sapletta Prototypowanie.pl.

## Acceptance criteria

- [x] AC-01: Update `docs/ARCHITECTURE.md` with native Rust runtime and anti-tamper invariants.
- [x] AC-02: Create `docs/NATIVE_RUST_TWIN_AND_ANTI_TAMPER.md`.
- [x] AC-03: Passes `./project/governance-check.sh`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
