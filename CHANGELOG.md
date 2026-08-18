# Changelog

## 0.2.0-dev - 2026-08-18

- Add `service-observe-repair/v1`: sequential validate-then-repair for a
  service twin, worked from the Plesk account inventory.
- Reject skip-ahead on that blueprint with `TWINLC-SEQUENCE-001`.
- Document the loop in `docs/VALIDATE_AND_REPAIR.md` and compose mutation
  authority from `wellmanifest/repair-lifecycle`.

## 0.1.0-dev - 2026-08-14

- Start the standalone twin lifecycle standard: immutable blueprint, typed
  transition requests, observe-only projections and redacted receipts.
- Add the reference `twin-reference/v1` blueprint and the dependency-free
  conformance suite with stable `TWINLC-*` diagnostic codes.
- Document the binding that lets `subactor/twin` reuse the blueprint behind
  `LifecycleBlueprintRef`.
