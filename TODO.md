# Roadmap

## Active

- [ ] [ticket-001](project/ticket-001/README.md) — adopt the byte-pinned shared
  Lifecycle DSL validator and enforce exact Twin stage graph equality.

- [ ] [ticket-002](project/ticket-002/README.md) — assign normative
  `standard/**` contracts to the integration workstream.

- [x] Publish `wellmanifest.twin-lifecycle/v1`: the immutable blueprint,
  GBNF-constrained transition requests, observe-only stage projection and
  redacted receipts, with a dependency-free conformance suite and stable
  `TWINLC-*` diagnostics.
- [x] Adopt `wellmanifest/new-project` 0.16.2 governance so every later change
  resolves to exactly one ticket and passes the managed gate.

- [ ] [`ticket-003`](project/ticket-003/README.md): run the conformance suite
  on every pull request and default-branch push. Status: `IN_PROGRESS / EDIT`;
  classification: `SERVICE / P1 / health`.

## Later

- [ ] Add tailored blueprint examples beyond `twin-reference/v1` once a second
  Twin declares its own stage graph.
- [ ] Add a machine-readable mapping export for the `subactor/twin` binding
  instead of the prose table in `docs/TWIN_BINDING.md`.
- [ ] Extend conformance with idempotent-replay receipt cases once a reference
  controller exists to produce them.
