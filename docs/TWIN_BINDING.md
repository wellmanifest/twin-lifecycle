# Binding `subactor/twin` to this standard

## What the Twin Standard already carries

`subactor/twin` is complete for the lifecycle *trait surface*:

- `spec/TWIN_STANDARD.md` §2.8 states the product-lifecycle invariants;
- `proto/twin/v1/twin.proto` declares `LifecycleBlueprintRef`,
  `LifecycleTransitionRecord`, `LifecycleTransitionStatus`,
  `TransitionLifecycleCommand`, `GetLifecycleQuery`, `LifecycleView` and
  `LifecycleTransitionRecorded`;
- `profiles/generic-twin.json` declares the `lifecycle` trait with the
  operations `twin.lifecycle.transition` and `twin.lifecycle.get`, their
  canonical URIs and all four transport bindings;
- `src/twin_standard.py` enforces the lifecycle policy flags and emits
  `TWIN-LIFECYCLE-001`, `TWIN-AUTH-001` and `TWIN-REPLAY-001`.

## What was missing

The blueprint itself. `LifecycleBlueprintRef` points at a `definition_uri`
plus `definition_digest_sha256`, but no contract in the ecosystem defined what
that document contains. The consequences in the current twin repository are:

1. `$.lifecycle` in a profile is a set of policy booleans. A profile can claim
   the `lifecycle` trait, pass validation and still declare **zero stages**,
   no entry/exit criteria, no permitted-transition table, no required
   artifacts and no approver roles — the assertions §2.8 makes about
   blueprints are unmodelled.
2. `unmentionedTransitionsFailClosed: true` has nothing to fail closed
   against, because there is no declared transition set to compare a request
   with.
3. The validator checks the process DAG (dependencies exist, no self-edges,
   acyclic) but performs no equivalent check on a stage graph — reachability,
   terminal stages and repeatable feedback loops are unverified.
4. `repeatableFeedbackStagesAllowed: true` is asserted with no place to mark a
   stage repeatable.

`wellmanifest/twin-lifecycle` supplies exactly that missing document, its
graph rules, its request grammar and its conformance suite.

## How a twin reuses it

1. **Record the source contract.** Add to `profiles/*.json`
   `$.contractSources` (and to the §1 list in `spec/TWIN_STANDARD.md`) an
   immutable entry, in the same shape as the existing `lifecycle-dsl` and
   `modularity-workspace` entries:

   ```json
   {
     "id": "twin-lifecycle-standard",
     "role": "normative",
     "repository": "https://github.com/wellmanifest/twin-lifecycle",
     "revision": "<full 40-char commit sha>",
     "artifact": "standard/twin-lifecycle.schema.json",
     "digest": "sha256:1da3f85aae2895d31eed491e4189026cb725fa0395a7601e0e7b615a20e10cfe"
   }
   ```

   Contract-source digests follow the twin convention: `sha256` over the raw
   artifact bytes at the pinned revision. That is a different value from the
   canonical-JSON digest a blueprint reference carries — the schema file is
   `1da3f85a…` by raw bytes and `72049b26…` canonically, and
   `blueprint.examples.json` is `3400fc69…` by raw bytes and `cd1795c6…`
   canonically. Contract sources pin the file; blueprint references pin the
   document's canonical content, so re-indenting a blueprint cannot silently
   rebind a running twin.

2. **Bind a blueprint revision.** Extend `$.lifecycle` with the pinned
   reference the twin operates under, so the profile names a real stage graph
   instead of only asserting policy:

   ```json
   "blueprintRef": {
     "blueprintId": "twin-reference",
     "version": "v1",
     "definitionUri": "lifecycle://wellmanifest.com/twin-reference/v1",
     "definitionDigest": "sha256:40ec13508cd46a2f1ee0d512998bad54fe3911f8eb6c7bb6a27ff10c1b3f502e",
     "immutable": true
   }
   ```

   The digest above is the canonical digest of
   `standard/blueprint.examples.json`. A service twin that must validate then
   repair one target at a time binds `service-observe-repair/v1` instead:

   ```json
   "blueprintRef": {
     "blueprintId": "service-observe-repair",
     "version": "v1",
     "definitionUri": "lifecycle://wellmanifest.com/service-observe-repair/v1",
     "definitionDigest": "sha256:36aba6a39af52a1d485da3ad48aa7e5fa671472be76090e9fef1ae39bb5b6870",
     "immutable": true
   }
   ```

   That digest is the canonical content of
   `standard/blueprint.validate-repair.json`. See
   [`VALIDATE_AND_REPAIR.md`](VALIDATE_AND_REPAIR.md).

3. **Map the wire types.** The mapping is one-to-one and needs no proto change:

   | `wellmanifest.twin-lifecycle/v1` | `subactor.twin.v1` |
   | --- | --- |
   | `blueprintRef.blueprintId` / `.version` | `LifecycleBlueprintRef.blueprint_id` / `.version` |
   | `blueprintRef.definitionUri` / `.definitionDigest` | `LifecycleBlueprintRef.definition_uri` / `.definition_digest_sha256` |
   | blueprint `stages[].id` | `LifecycleBlueprintRef.stage_ids` |
   | `transition-request` | `TransitionLifecycleCommand.transition` |
   | `transition-receipt.status` | `LifecycleTransitionStatus` |
   | `transition-receipt.unmetCriteria` | `LifecycleTransitionRecord.unmet_criteria` |
   | `transition-receipt.approvedBy` | `LifecycleTransitionRecord.approved_by` |
   | `transition-receipt.gateDecisionRef` | `LifecycleTransitionRecord.gate_decision_id` |
   | `lifecycle-state` | `LifecycleView` |

4. **Extend validation.** `_validate_lifecycle_and_evolution` gains one rule:
   when the `lifecycle` trait is declared, `$.lifecycle.blueprintRef` must
   exist and its `definitionDigest` must match the pinned blueprint, otherwise
   `TWIN-LIFECYCLE-001`. The stage-graph rules stay in this repository —
   `standard/conformance.py` is the reference implementation, and its
   `TWINLC-*` codes map onto twin's families:

   | `TWINLC-*` | Twin diagnostic |
   | --- | --- |
   | `TWINLC-BLUEPRINT-001`, `TWINLC-GRAPH-001`, `TWINLC-TRANSITION-001`, `TWINLC-DOC-001`, `TWINLC-REF-001` | `TWIN-LIFECYCLE-001` |
   | `TWINLC-EVIDENCE-001` | `TWIN-EVIDENCE-001` |
   | `TWINLC-AUTHORITY-001` | `TWIN-AUTH-001` |
   | `TWINLC-REPLAY-001` | `TWIN-REPLAY-001` |
   | `TWINLC-SECRET-001` | `TWIN-SECRET-001` |

5. **Emit it in the bundle.** `transport-map.json` carries the blueprint
   reference next to the existing lifecycle policy, and `conformance.json`
   gains one case per declared transition. Nothing executable is added.

Steps 1–5 change a governed repository, so they belong to a ticket in
`subactor/twin`, not to this standard.

## Related provenance note

`profiles/generic-twin.json` pins `lifecycle-dsl` to
`https://github.com/subactor/lifecycle`. That repository was transferred and
the GitHub API now answers `wellmanifest/lifecycle` for it. The commit
`f3b8e13eb17128fd0f3ff05ac45fc99c99c470c4` still resolves, but the recorded
URL only works through a redirect, which is not immutable provenance. The
`repository` field should be updated in the same ticket that records the
binding above.
