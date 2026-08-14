# Roadmap

## Active

- [x] Publish `wellmanifest.twin-lifecycle/v1`: the immutable blueprint,
  GBNF-constrained transition requests, observe-only stage projection and
  redacted receipts, with a dependency-free conformance suite and stable
  `TWINLC-*` diagnostics.
- [ ] Adopt `wellmanifest/new-project` 0.16.2 governance so every later change
  resolves to exactly one ticket and passes the managed gate.

## Later

- [ ] Add tailored blueprint examples beyond `twin-reference/v1` once a second
  Twin declares its own stage graph.
- [ ] Add a machine-readable mapping export for the `subactor/twin` binding
  instead of the prose table in `docs/TWIN_BINDING.md`.
- [ ] Extend conformance with idempotent-replay receipt cases once a reference
  controller exists to produce them.
