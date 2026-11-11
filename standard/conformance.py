#!/usr/bin/env python3
"""Dependency-free semantic conformance for wellmanifest.twin-lifecycle/v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import twin_fixtures as _fx  # noqa: E402
from twin_primitives import (  # noqa: E402
    BINDING_FAMILY,
    BINDING_PATH,
    BLUEPRINT_KEYS,
    BLUEPRINT_PATH,
    GRAMMAR_DIGEST,
    GRAMMAR_PATH,
    LIFECYCLE_PATH,
    LIFECYCLE_PROFILE_DIGEST,
    LIFECYCLE_SOURCE_REVISION,
    LIFECYCLE_VALIDATOR_DIGEST,
    LIFECYCLE_VALIDATOR_DIGESTS,
    LIFECYCLE_VALIDATOR_PATH,
    RECEIPT_KEYS,
    REQUEST_KEYS,
    SCHEMA_DIGEST,
    SCHEMA_FAMILY,
    SCHEMA_PATH,
    SCHEMA_URI,
    SEQUENTIAL_BLUEPRINT_ID,
    STATE_KEYS,
    STATUSES,
    UNMET_REQUIRED_STATUSES,
    VALIDATE_REPAIR_PATH,
    ContractError,
    bind,
    blueprint_ref,
    canonical,
    closed,
    digest,
    match,
    non_neg_int,
    ref_of,
    refs,
    reject_sensitive,
    strict_bool,
    strict_loads,
    timestamp_value,
    validate_lifecycle_profile,
)
from twin_targets import SKIP_DIRS, validate_agent_binding, validate_targets_impl  # noqa: E402

__all__ = [
    "BINDING_FAMILY",
    "BINDING_PATH",
    "BLUEPRINT_PATH",
    "ContractError",
    "GRAMMAR_DIGEST",
    "LIFECYCLE_PATH",
    "LIFECYCLE_PROFILE_DIGEST",
    "LIFECYCLE_SOURCE_REVISION",
    "LIFECYCLE_VALIDATOR_DIGEST",
    "LIFECYCLE_VALIDATOR_DIGESTS",
    "LIFECYCLE_VALIDATOR_PATH",
    "ROOT",
    "SCHEMA_DIGEST",
    "SCHEMA_FAMILY",
    "SCHEMA_URI",
    "SKIP_DIRS",
    "VALIDATE_REPAIR_PATH",
    "main",
    "ref_of",
    "run_all",
    "strict_loads",
    "validate_agent_binding",
    "validate_blueprint",
    "validate_lifecycle_profile",
    "validate_receipt",
    "validate_request",
    "validate_state",
    "validate_targets",
]


def validate_blueprint(doc: dict[str, Any]) -> dict[str, Any]:
    doc = closed(doc, BLUEPRINT_KEYS, optional={"intent"})
    reject_sensitive({k: v for k, v in doc.items() if k != "intent"})
    if "intent" in doc and (not isinstance(doc["intent"], str) or len(doc["intent"]) > 240):
        raise ContractError("TWINLC-DOC-001", "invalid blueprint intent")
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "lifecycle-blueprint":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    if doc["immutable"] is not True:
        raise ContractError("TWINLC-BLUEPRINT-001", "a blueprint definition must be immutable")
    if doc["replayExecutesTransitions"] is not False:
        raise ContractError("TWINLC-REPLAY-001", "replay must never execute a lifecycle transition")
    if doc["approvalGrantsAuthority"] is not False:
        raise ContractError(
            "TWINLC-AUTHORITY-001", "a lifecycle gate must not manufacture execution authority"
        )
    match("blueprintId", doc["blueprintId"])
    match("blueprintVersion", doc["version"])
    match("definitionUri", doc["definitionUri"])
    roles = set(refs(doc["approverRoles"], "role", minimum=1, maximum=16))
    if not isinstance(doc["stages"], list) or not 2 <= len(doc["stages"]) <= 64:
        raise ContractError("TWINLC-GRAPH-001", "blueprint must declare 2..64 stages")
    if not isinstance(doc["transitions"], list) or not 1 <= len(doc["transitions"]) <= 128:
        raise ContractError("TWINLC-GRAPH-001", "blueprint must declare 1..128 transitions")
    order: dict[str, int] = {}
    stages: dict[str, dict[str, Any]] = {}
    for index, stage in enumerate(doc["stages"]):
        stage = closed(
            stage,
            {
                "id",
                "intent",
                "entryCriteria",
                "exitCriteria",
                "requiredArtifacts",
                "repeatable",
                "terminal",
            },
            optional={"intent"},
        )
        if "intent" in stage and (
            not isinstance(stage["intent"], str) or len(stage["intent"]) > 240
        ):
            raise ContractError("TWINLC-DOC-001", "invalid stage intent")
        stage_id = match("stageId", stage["id"])
        if stage_id in stages:
            raise ContractError("TWINLC-GRAPH-001", "duplicate stage identity")
        refs(stage["entryCriteria"], "criterion", minimum=0, maximum=32)
        refs(stage["exitCriteria"], "criterion", minimum=0, maximum=32)
        refs(stage["requiredArtifacts"], "artifact", minimum=0, maximum=32)
        strict_bool(stage["repeatable"], "stage repeatable must be boolean")
        is_terminal = strict_bool(stage["terminal"], "stage terminal must be boolean")
        if is_terminal and stage["exitCriteria"]:
            raise ContractError("TWINLC-GRAPH-001", "a terminal stage cannot declare exit criteria")
        stages[stage_id] = stage
        order[stage_id] = index
    initial = match("stageId", doc["initialStage"])
    if initial not in stages:
        raise ContractError("TWINLC-GRAPH-001", "initial stage is not declared")
    actions: set[str] = set()
    outgoing: dict[str, list[str]] = {stage_id: [] for stage_id in stages}
    incoming: dict[str, int] = {stage_id: 0 for stage_id in stages}
    for rule in doc["transitions"]:
        rule = closed(
            rule,
            {
                "action",
                "from",
                "to",
                "requiredCriteria",
                "approverRoles",
                "failClosed",
                "reversible",
                "compensatingAction",
            },
            optional={"compensatingAction"},
        )
        if rule["failClosed"] is not True:
            raise ContractError("TWINLC-GRAPH-001", "every transition must fail closed")
        strict_bool(rule["reversible"], "transition reversible must be boolean")
        action = match("actionId", rule["action"])
        if "compensatingAction" in rule:
            match("actionId", rule["compensatingAction"])
        source, target = match("stageId", rule["from"]), match("stageId", rule["to"])
        if source not in stages or target not in stages:
            raise ContractError("TWINLC-GRAPH-001", "transition references an undeclared stage")
        if source == target:
            raise ContractError("TWINLC-GRAPH-001", "a stage cannot transition to itself")
        if action in actions:
            raise ContractError("TWINLC-GRAPH-001", "duplicate transition action")
        actions.add(action)
        if stages[source]["terminal"]:
            raise ContractError(
                "TWINLC-GRAPH-001", "a terminal stage cannot have an outgoing transition"
            )
        contract = set(stages[source]["exitCriteria"]) | set(stages[target]["entryCriteria"])
        required = set(refs(rule["requiredCriteria"], "criterion", minimum=1, maximum=32))
        if not required <= contract:
            raise ContractError(
                "TWINLC-GRAPH-001", "required criteria are outside the stage entry/exit contract"
            )
        if not set(refs(rule["approverRoles"], "role", minimum=0, maximum=8)) <= roles:
            raise ContractError(
                "TWINLC-GRAPH-001", "approver role is not declared by the blueprint"
            )
        if order[target] <= order[source] and stages[target]["repeatable"] is not True:
            raise ContractError(
                "TWINLC-GRAPH-001", "a feedback transition requires a repeatable target stage"
            )
        outgoing[source].append(target)
        incoming[target] += 1
    if incoming[initial]:
        raise ContractError("TWINLC-GRAPH-001", "the initial stage cannot be a transition target")
    if not any(stage["terminal"] for stage in stages.values()):
        raise ContractError("TWINLC-GRAPH-001", "a blueprint must declare a terminal stage")
    for stage_id, stage in stages.items():
        if not stage["terminal"] and not outgoing[stage_id]:
            raise ContractError(
                "TWINLC-GRAPH-001", "a non-terminal stage must declare an outgoing transition"
            )
    seen, queue = {initial}, [initial]
    while queue:
        for target in outgoing[queue.pop()]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    if seen != set(stages):
        raise ContractError(
            "TWINLC-GRAPH-001", "every stage must be reachable from the initial stage"
        )
    if doc["blueprintId"] == SEQUENTIAL_BLUEPRINT_ID:
        for rule in doc["transitions"]:
            src, tgt = str(rule["from"]), str(rule["to"])
            if (
                stages[tgt]["terminal"] is not True
                and order[tgt] > order[src]
                and order[tgt] != order[src] + 1
            ):
                raise ContractError(
                    "TWINLC-SEQUENCE-001", "a sequential blueprint cannot skip a forward stage"
                )
    return doc


def resolve(blueprint: dict[str, Any], action: Any, source: Any, target: Any) -> dict[str, Any]:
    for rule in blueprint["transitions"]:
        if (rule["action"], rule["from"], rule["to"]) == (action, source, target):
            return rule
    raise ContractError(
        "TWINLC-TRANSITION-001", "the requested transition is not declared by the blueprint"
    )


def validate_request(doc: dict[str, Any], blueprint: dict[str, Any]) -> None:
    doc = closed(doc, REQUEST_KEYS)
    reject_sensitive(doc)
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "transition-request":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    blueprint_ref(doc["blueprint"])
    bind(blueprint, doc)
    for name in ("requestId", "twinRef", "baseRevision", "idempotencyKey"):
        match("revision" if name == "baseRevision" else name, doc[name])
    actor = closed(doc["requestedBy"], {"actorRef", "actorClass"})
    match("actorRef", actor["actorRef"])
    if actor["actorClass"] not in {"human", "service", "twin-persona"}:
        raise ContractError("TWINLC-DOC-001", "unknown actor class")
    if doc["gateDecisionRef"] is not None:
        match("decisionRef", doc["gateDecisionRef"])
    rule = resolve(blueprint, doc["action"], doc["fromStage"], doc["toStage"])
    evidence = refs(doc["evidenceRefs"], "evidenceRef", minimum=1, maximum=32)
    if len(evidence) < len(rule["requiredCriteria"]):
        raise ContractError(
            "TWINLC-EVIDENCE-001", "each required criterion needs its own evidence reference"
        )


def validate_state(doc: dict[str, Any], blueprint: dict[str, Any]) -> None:
    doc = closed(doc, STATE_KEYS)
    reject_sensitive(doc)
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "lifecycle-state":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    blueprint_ref(doc["blueprint"])
    bind(blueprint, doc)
    match("twinRef", doc["twinRef"])
    if doc["derivedFrom"] != "event-stream" or doc["replayExecutedEffects"] is not False:
        raise ContractError("TWINLC-REPLAY-001", "a projection is rebuilt by observation only")
    if doc["currentStage"] not in {stage["id"] for stage in blueprint["stages"]}:
        raise ContractError("TWINLC-GRAPH-001", "current stage is not declared by the blueprint")
    non_neg_int(doc["aggregateVersion"], "invalid aggregate version")
    if doc["lastTransitionId"] is not None:
        match("transitionId", doc["lastTransitionId"])
    refs(doc["unmetCriteria"], "criterion", minimum=0, maximum=32)


def validate_receipt(doc: dict[str, Any], blueprint: dict[str, Any]) -> None:
    doc = closed(doc, RECEIPT_KEYS)
    reject_sensitive(doc)
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "transition-receipt":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    blueprint_ref(doc["blueprint"])
    bind(blueprint, doc)
    for name in ("transitionId", "requestId", "twinRef", "idempotencyKey"):
        match(name, doc[name])
    match("revision", doc["baseRevision"])
    non_neg_int(doc["aggregateVersion"], "invalid receipt aggregate version")
    timestamp_value(doc["recordedAt"])
    if doc["authorityGranted"] is not False:
        raise ContractError(
            "TWINLC-AUTHORITY-001", "a lifecycle receipt must not report granted authority"
        )
    if doc["secretsRedacted"] is not True:
        raise ContractError("TWINLC-SECRET-001", "a receipt must be redacted")
    if doc["status"] not in STATUSES:
        raise ContractError("TWINLC-DOC-001", "unknown transition status")
    if doc["gateDecisionRef"] is not None:
        match("decisionRef", doc["gateDecisionRef"])
    rule = resolve(blueprint, doc["action"], doc["fromStage"], doc["toStage"])
    refs(doc["evidenceRefs"], "evidenceRef", minimum=0, maximum=32)
    unmet = refs(doc["unmetCriteria"], "criterion", minimum=0, maximum=32)
    if doc["status"] in UNMET_REQUIRED_STATUSES:
        refs(doc["eventRefs"], "eventRef", minimum=0, maximum=32)
        if not unmet or doc["approvedBy"] is not None:
            raise ContractError(
                "TWINLC-EVIDENCE-001",
                "a blocked or rejected transition records unmet criteria and no approver",
            )
        return
    if doc["status"] == "REQUESTED":
        refs(doc["eventRefs"], "eventRef", minimum=0, maximum=32)
        if doc["approvedBy"] is not None:
            raise ContractError(
                "TWINLC-AUTHORITY-001", "a requested transition has no approver yet"
            )
        return
    if unmet:
        raise ContractError(
            "TWINLC-EVIDENCE-001", "an approved transition cannot carry unmet criteria"
        )
    if len(doc["evidenceRefs"]) < len(rule["requiredCriteria"]):
        raise ContractError(
            "TWINLC-EVIDENCE-001", "approval requires evidence for every required criterion"
        )
    refs(doc["eventRefs"], "eventRef", minimum=1, maximum=32)
    if rule["approverRoles"]:
        approver = closed(doc["approvedBy"], {"actorRef", "actorClass", "role"})
        match("actorRef", approver["actorRef"])
        if approver["actorClass"] not in {"human", "service"}:
            raise ContractError(
                "TWINLC-AUTHORITY-001", "a twin persona cannot approve its own lifecycle gate"
            )
        if approver["role"] not in rule["approverRoles"]:
            raise ContractError(
                "TWINLC-AUTHORITY-001", "approver role is not accepted for this transition"
            )
        if doc["gateDecisionRef"] is None:
            raise ContractError(
                "TWINLC-AUTHORITY-001", "an approved gate must reference its decision record"
            )
    elif doc["approvedBy"] is not None:
        approver = closed(doc["approvedBy"], {"actorRef", "actorClass", "role"})
        match("actorRef", approver["actorRef"])
        match("role", approver["role"])
        if approver["actorClass"] not in {"human", "service"}:
            raise ContractError(
                "TWINLC-AUTHORITY-001", "a twin persona cannot approve its own lifecycle gate"
            )


def run_all() -> dict[str, Any]:
    schema = strict_loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    grammar = GRAMMAR_PATH.read_bytes()
    if digest(canonical(schema)) != SCHEMA_DIGEST or digest(grammar) != GRAMMAR_DIGEST:
        raise ContractError("TWINLC-BLUEPRINT-001", "contract digest mismatch")
    if schema.get("$id") != SCHEMA_URI:
        raise ContractError("TWINLC-BLUEPRINT-001", "schema identity mismatch")
    lowered = grammar.lower()
    for forbidden in (
        b"shell",
        b"argv",
        b"password",
        b"credential",
        b"secret",
        b"authority",
        b"http://",
    ):
        if forbidden in lowered:
            raise ContractError("TWINLC-SECRET-001", "unsafe grammar surface")
    blueprint = validate_blueprint(strict_loads(BLUEPRINT_PATH.read_text(encoding="utf-8")))
    validate_lifecycle_profile(blueprint)
    sequential = validate_blueprint(strict_loads(VALIDATE_REPAIR_PATH.read_text(encoding="utf-8")))
    sequential_pinned = ref_of(sequential)
    binding = validate_agent_binding(
        strict_loads(BINDING_PATH.read_text(encoding="utf-8")), sequential
    )
    pinned = ref_of(blueprint)
    seq_req, request, state, receipt = _fx.build_positive_documents(pinned, sequential_pinned)
    validate_request(seq_req, sequential)
    validate_request(request, blueprint)
    validate_state(state, blueprint)
    validate_receipt(receipt, blueprint)
    rejected = _fx.run_adversarial_suite(
        blueprint=blueprint,
        pinned=pinned,
        sequential=sequential,
        sequential_request=seq_req,
        binding=binding,
        request=request,
        state=state,
        receipt=receipt,
        check_blueprint=validate_blueprint,
        check_request=lambda doc: validate_request(doc, blueprint),
        check_seq_request=lambda doc: validate_request(doc, sequential),
        check_state=lambda doc: validate_state(doc, blueprint),
        check_receipt=lambda doc: validate_receipt(doc, blueprint),
        check_binding=lambda doc: validate_agent_binding(doc, sequential),
    )
    return {
        "schema": "wellmanifest.twin-lifecycle-conformance/v1",
        "ok": True,
        "positiveDocuments": 6,
        "ecosystemBindings": [
            {
                "bindingId": binding["bindingId"],
                "blueprint": binding["blueprintRef"],
                "acts": binding["acts"],
            }
        ],
        "tailoredBlueprints": [sequential_pinned],
        "adversarialRejected": rejected,
        "referenceBlueprint": pinned,
        "lifecycleSourceRevision": LIFECYCLE_SOURCE_REVISION,
        "lifecycleValidatorDigest": "sha256:" + LIFECYCLE_VALIDATOR_DIGEST,
        "lifecycleProfileDigest": "sha256:" + LIFECYCLE_PROFILE_DIGEST,
        "schemaDigest": "sha256:" + SCHEMA_DIGEST,
        "grammarDigest": "sha256:" + GRAMMAR_DIGEST,
    }


def validate_targets(
    targets: list[Path], *, blueprint_paths: list[Path] | None = None
) -> dict[str, Any]:
    return validate_targets_impl(
        targets,
        blueprint_paths=blueprint_paths,
        validate_blueprint_fn=validate_blueprint,
        validate_request_fn=validate_request,
        validate_state_fn=validate_state,
        validate_receipt_fn=validate_receipt,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="wellmanifest.twin-lifecycle/v1 conformance")
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--blueprint", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if not args.targets:
            print(json.dumps(run_all(), indent=2, sort_keys=True))
            return 0
        target_report = validate_targets(
            [Path(item) for item in args.targets],
            blueprint_paths=[Path(item) for item in args.blueprint],
        )
        if args.all:
            suite_report = run_all()
            combined = {
                **suite_report,
                "ok": bool(suite_report["ok"] and target_report["ok"]),
                "checkedCount": target_report["checkedCount"],
                "checkedTargets": target_report["checkedTargets"],
                "findings": target_report["findings"],
            }
            print(json.dumps(combined, indent=2, sort_keys=True))
            return 0 if combined["ok"] else 1
        print(json.dumps(target_report, indent=2, sort_keys=True))
        return 0 if target_report["ok"] else 1
    except ContractError as error:
        target_label = ",".join(args.targets) if args.targets else "<self-suite>"
        failure = {
            "schema": "wellmanifest.twin-lifecycle-conformance/v1",
            "ok": False,
            "checkedCount": 0,
            "checkedTargets": [],
            "findings": [{"path": target_label, "code": error.code, "message": str(error)}],
        }
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
