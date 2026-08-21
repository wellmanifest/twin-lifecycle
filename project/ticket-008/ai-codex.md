---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-008
---
# Participant: codex (AI agent)

## Understanding

The ecosystem Twin needs a standard contract for handing a problem through
Doctor, Repair and Validator without turning a diagnosis, LLM response or Twin
receipt into authority. The existing blueprint defines service stages but the
`subactor/twin` integration is prose only. This ticket publishes that missing
data-only mapping and deterministic conformance.

## Execution plan

1. Define one closed machine-readable binding over the existing immutable
   service-observe-repair blueprint.
2. Validate role ownership, adjacency, evidence binding and authority rules.
3. Add adversarial cases for skip-ahead, authority expansion and LLM operation
   invention.
4. Document adoption by ecosystem Twin runtimes and publish via Validator.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Preserved HOME/ADOPT: Wellmanifest owns only the binding standard; the
  `twin-subactor` projector and Control runtime remain HOME in Subactor.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination or material objective expansion. Protected delivery
  may be invoked without another prompt when publication is in scope; its
  exact-head trusted approval remains independent evidence.
