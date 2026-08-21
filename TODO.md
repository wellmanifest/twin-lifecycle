# Roadmap

## Active

- [x] [ticket-001](project/ticket-001/README.md) — adopt the byte-pinned shared
  Lifecycle DSL validator and enforce exact Twin stage graph equality.

- [x] [ticket-002](project/ticket-002/README.md) — assign normative
  `standard/**` contracts to the integration workstream.

- [x] Publish `wellmanifest.twin-lifecycle/v1`: the immutable blueprint,
  GBNF-constrained transition requests, observe-only stage projection and
  redacted receipts, with a dependency-free conformance suite and stable
  `TWINLC-*` diagnostics.
- [x] Adopt `wellmanifest/new-project` 0.16.2 governance so every later change
  resolves to exactly one ticket and passes the managed gate.

- [x] [`ticket-003`](project/ticket-003/README.md): run the conformance suite
  on every pull request and default-branch push. Status: `DONE / DONE`;
  classification: `SERVICE / P1 / health`.

- [x] [`ticket-004`](project/ticket-004/README.md): point schema identifiers at
  the live host and re-pin the digests that move with them, without touching
  files the adoption lock hashes. Status: `DONE / DONE`; classification:
  `BUG / P1 / regression`.

- [x] [`ticket-005`](project/ticket-005/README.md): atomically re-adopt the
  published `new-project v0.18.1` governance package, restoring live-host
  managed identifiers without bypassing the lock. Status:
  `DONE / DONE`; classification: `SERVICE / P1 / health`.

- [x] [`ticket-007`](project/ticket-007/README.md): sequential
  validate-and-repair blueprint (`service-observe-repair/v1`) from the Plesk
  service twin. Status: `DONE / DONE`; classification:
  `FEATURE / P1 / requested`.

## Later
- [x] [`ticket-008`](project/ticket-008/README.md): export the machine-readable
  ecosystem Twin agent binding for Doctor → Repair → Validator. Status:
  `DONE / DONE`; classification: `FEATURE / P1 / requested`.
- [ ] Extend conformance with idempotent-replay receipt cases once a reference
  controller exists to produce them.
