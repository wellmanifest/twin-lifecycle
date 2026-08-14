# twin-lifecycle

Versioned Wellmanifest standard for the stage lifecycle of a Digital Twin:
an immutable blueprint of stages, entry/exit criteria, permitted transitions,
required artifacts, evidence requirements and approver roles, plus the typed
transition requests, observe-only projections and redacted receipts built on
it.

It supplies the definition document behind `LifecycleBlueprintRef` in the
`subactor/twin` Twin Standard, which declares lifecycle *policy* but never
defined the stage graph that policy is evaluated against. See
[`docs/TWIN_BINDING.md`](docs/TWIN_BINDING.md).

The normative artifacts live in `standard/`; architecture and flow live in
`docs/`. A lifecycle document records that declared criteria were evaluated.
It never grants execution authority, never transports secrets or shell input,
and never promotes a score, proposal, simulation or model verdict to evidence.

```text
python3 standard/conformance.py --all
```

The suite is dependency-free. It pins the schema and grammar digests, accepts
four canonical documents and proves that 24 adversarial mutations reject with
their declared `TWINLC-*` diagnostic code.

## Layout

| Path | Contents |
| --- | --- |
| `standard/twin-lifecycle.schema.json` | closed blueprint, request, state and receipt contracts |
| `standard/twin-lifecycle.v1.gbnf` | grammar emitting only canonical transition requests |
| `standard/blueprint.examples.json` | the reference `twin-reference/v1` blueprint |
| `standard/conformance.py` | semantic conformance beyond JSON Schema |
| `docs/ARCHITECTURE.md` | responsibility, graph rules, diagnostics |
| `docs/LOGIC_FLOW.md` | resolution, gate and replay boundaries |
| `docs/TWIN_BINDING.md` | how `subactor/twin` reuses this standard |

## Composition

This standard composes with the separately versioned `wellmanifest/lifecycle`
DSL, `ticket-lifecycle` and `git-lifecycle` through opaque evidence, decision
and receipt references. It owns twin stages only: it does not own the twin
contract, the module graph, the process runtime, the event store or any
authority decision.
