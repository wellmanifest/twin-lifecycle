# Ticket 11: Express lifecycle document fences as valid Policy DSL

- **ID**: ticket-011
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-13

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: on 2026-09-13 the user asked to correct
Wellmanifest standards that contain errors or do not express their logic in the
DSL standard used by `wellmanifest/new-project/CONTRIBUTING.md`.

A `dsl` fence with a concrete `DOCUMENT` header is a Policy DSL carrier
(`wellmanifest/policy-dsl` spec 3.2). In this repository:

- both header fences carry `SCHEMA`, `REQUEST_GRAMMAR`, `BLUEPRINT` or `COMPOSES` statements that Policy DSL v1 does not define, so `validate-markdown` fails at line 5;
- the reference blueprint uses `STAGE ... REPEATABLE ... TERMINAL ...` and `TRANSITION ... ACTION ... APPROVER ...`, which are not Policy DSL statements;
- the fail-closed resolution, sequential and feedback rules exist only as prose.

Declares metadata as bindings, projects the reference blueprint as `STATE`, `REPEATABLE_STAGES`, `TERMINAL_STAGES` and guarded transitions matching `standard/blueprint.examples.json`, and adds rules TWINLC-RESOLVE-001, TWINLC-VR-001 and TWINLC-VR-002. Both document versions 1 -> 2.

Non-goals: no schema, grammar, blueprint, conformance code or diagnostic code
change; prose, tables and diagrams stay as explanation of the same contract.

## Acceptance criteria

- [x] AC-01: `python3 tests/policy_dsl_check.py validate-markdown` from
  `wellmanifest/policy-dsl@48e95c8` accepts every changed document.
- [x] AC-02: The fail-closed carrier selector published in
  `wellmanifest/policy-dsl@d723271` (PR #22) and the checker pinned by
  `wellmanifest/new-project` (`daaf7b7`) also accept every changed document.
- [x] AC-03: The DSL projection matches the existing prose, diagrams and
  machine artifacts; the repository governance gate passes.

Cross-repository evidence:
`subactor/docs/architecture/analysis/semcod-library-quality.md`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
