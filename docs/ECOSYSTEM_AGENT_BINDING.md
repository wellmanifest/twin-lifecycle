# Ecosystem Twin agent binding

[`standard/binding.subactor-ecosystem.json`](../standard/binding.subactor-ecosystem.json)
is the machine-readable composition profile for an ecosystem Twin and the
Doctor → Repair → Validator delivery path. It binds the existing immutable
`service-observe-repair/v1` blueprint; it is not another lifecycle engine.

The profile is deliberately data-only. `acts=false`, observations need no
mutation authority, and Repair remains blocked until a trusted controller
resolves an external grant bound to the exact snapshot, finding and plan
digests. Validator observes the exact result independently. Acceptance belongs
to protected delivery and requires the Validator receipt.

Deterministic policy selects declared candidates first. An LLM may only order
candidates with the same deterministic priority. It cannot invent an operation,
target, evidence body or authority. Replayed observations never execute effects.

Dirty worktrees, stash ownership, secret intake, ambiguous ownership and unknown
repair classes stop at a human-decision route. This is intentional: a richer
Twin improves orientation but does not make ambiguous or credential-bearing
changes safe to automate.

Subactor adopters map the abstract roles as follows:

| Binding role | Runtime owner |
| --- | --- |
| `role:ecosystem-twin` | `subactor/twin-subactor` read model |
| `role:doctor-agent` | `subactor/doctor-agent` using a pinned skills-agent diagnostic |
| `role:repair-agent` | `subactor/repair-agent` under an external grant |
| `role:validator-agent` | `subactor/validator-agent` on the exact result |
| `role:protected-delivery` | the repository's protected PR/merge boundary |

The mapping does not transfer HOME: Wellmanifest owns this standard profile;
all running services remain HOME in Subactor.
