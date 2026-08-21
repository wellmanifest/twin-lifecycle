#!/usr/bin/env python3
"""Dependency-free semantic conformance for wellmanifest.twin-lifecycle/v1.

The checks here express what JSON Schema cannot: blueprint graph safety,
fail-closed transition resolution, the separation of approval from authority,
evidence sufficiency and observe-only replay.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "twin-lifecycle.schema.json"
GRAMMAR_PATH = ROOT / "twin-lifecycle.v1.gbnf"
BLUEPRINT_PATH = ROOT / "blueprint.examples.json"
VALIDATE_REPAIR_PATH = ROOT / "blueprint.validate-repair.json"
BINDING_PATH = ROOT / "binding.subactor-ecosystem.json"
SEQUENTIAL_BLUEPRINT_ID = "service-observe-repair"
LIFECYCLE_PATH = ROOT / "twin-lifecycle.lifecycle"
LIFECYCLE_VALIDATOR_PATH = ROOT / "lifecycle.py"
SCHEMA_DIGEST = "98c2d346340aabd4b28ed860c469c3762971040be3aded721d7d6ae6bfb06e4f"
GRAMMAR_DIGEST = "e8e240b7f89c569de64c4e185dd8a1ce2055bd3b3d189841afaf1783b695d036"
LIFECYCLE_SOURCE_REVISION = "4b5e131a670afb46ca87291479fed7c0fefcf370"
LIFECYCLE_VALIDATOR_DIGEST = "9c3f3076b5b45408d3eefc34cd567b58821aa565d3fe3bf6339641111079ede0"
LIFECYCLE_PROFILE_DIGEST = "7a2cf7b57adf599c5af313bd073b8aa66601af936114e51cc9758a49e672d5d5"
SCHEMA_FAMILY = "wellmanifest.twin-lifecycle/v1"
BINDING_FAMILY = "wellmanifest.twin-lifecycle-binding/v1"
SCHEMA_URI = "https://wellmanifest.com/schemas/twin-lifecycle/v1"

BLUEPRINT_KEYS = {
    "schema", "kind", "blueprintId", "version", "definitionUri", "intent", "immutable",
    "initialStage", "approverRoles", "stages", "transitions", "replayExecutesTransitions",
    "approvalGrantsAuthority",
}
REQUEST_KEYS = {
    "schema", "kind", "requestId", "twinRef", "blueprint", "action", "fromStage", "toStage",
    "baseRevision", "requestedBy", "evidenceRefs", "gateDecisionRef", "idempotencyKey",
}
STATE_KEYS = {
    "schema", "kind", "twinRef", "blueprint", "currentStage", "aggregateVersion", "derivedFrom",
    "lastTransitionId", "unmetCriteria", "replayExecutedEffects",
}
RECEIPT_KEYS = {
    "schema", "kind", "transitionId", "requestId", "twinRef", "blueprint", "action", "fromStage",
    "toStage", "status", "baseRevision", "aggregateVersion", "evidenceRefs", "unmetCriteria",
    "approvedBy", "gateDecisionRef", "eventRefs", "idempotencyKey", "authorityGranted",
    "secretsRedacted", "recordedAt",
}
STATUSES = {"REQUESTED", "APPROVED", "BLOCKED", "REJECTED"}
UNMET_REQUIRED_STATUSES = {"BLOCKED", "REJECTED"}
PATTERNS = {
    "requestId": r"^request:[a-z0-9][a-z0-9._-]{0,95}$",
    "transitionId": r"^transition:[a-z0-9][a-z0-9._-]{0,95}$",
    "idempotencyKey": r"^idempotency:[a-z0-9][a-z0-9._-]{0,95}$",
    "twinRef": r"^twin://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+$",
    "definitionUri": r"^lifecycle://[a-z0-9][a-z0-9.-]*/[a-z0-9][a-z0-9._-]*/v[1-9][0-9]*$",
    "definitionDigest": r"^sha256:[0-9a-f]{64}$",
    "evidenceRef": r"^evidence://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+/r[1-9][0-9]*$",
    "decisionRef": r"^decision://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+$",
    "eventRef": r"^event://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+$",
    "actorRef": r"^actor://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:-]+$",
    "revision": r"^(?:[0-9a-f]{40}|sha256:[0-9a-f]{64})$",
    "stageId": r"^[a-z][a-z0-9-]{0,47}$",
    "criterion": r"^criterion:[a-z][a-z0-9._-]{0,63}$",
    "role": r"^role:[a-z][a-z0-9._-]{0,63}$",
}
SENSITIVE = re.compile(
    r"(?:shell|argv|command|password|passwd|token|secret|credential|api[-_]?key|cookie|"
    r"private[-_]?key|remote|url|score|proposal|simulation|verdict|prompt)",
    re.I,
)
# Declared boolean assertions about redaction are part of the receipt contract; the
# sensitive-key scan must not confuse an assertion with transported secret material.
SAFE_ASSERTIONS = {"secretsRedacted"}
BINDING_KEYS = {
    "schema", "kind", "bindingId", "immutable", "acts", "blueprintRef", "stages",
    "transitions", "authority", "decision", "deduplication", "humanDecisionRequiredFor",
}


class ContractError(ValueError):
    """A bounded rejection that never repeats untrusted document content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def lifecycle_name(value: str) -> str:
    return value.upper().replace("-", "_")


def load_pinned_lifecycle() -> Any:
    """Load the vendored validator from the exact file whose digest was checked.

    A plain `import lifecycle` resolves through `sys.path`, so the module that
    runs is not necessarily the file the digest verified, and the suite stops
    being importable from another working directory. Loading by explicit path
    keeps the pin and the executed code the same object.
    """
    spec = importlib.util.spec_from_file_location(
        "twin_lifecycle_pinned_validator", LIFECYCLE_VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle validator is not loadable")
    module = importlib.util.module_from_spec(spec)
    # Register before execution: a dataclass resolves its own module through
    # sys.modules while the class body is processed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_lifecycle_profile(
    blueprint: dict[str, Any],
    *,
    validator_path: Path = LIFECYCLE_VALIDATOR_PATH,
    profile_path: Path = LIFECYCLE_PATH,
) -> None:
    if digest(validator_path.read_bytes()) != LIFECYCLE_VALIDATOR_DIGEST:
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle validator digest mismatch")
    if digest(profile_path.read_bytes()) != LIFECYCLE_PROFILE_DIGEST:
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle profile digest mismatch")
    lifecycle = load_pinned_lifecycle()
    report = lifecycle.validate_path(profile_path, lifecycle.embedded_catalog())
    if not report.valid or len(report.lifecycles) != 1:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL profile is invalid")
    model = report.lifecycles[0]
    expected_states = {
        lifecycle_name(str(stage["id"])) for stage in blueprint["stages"]
    }
    expected_transitions = {
        (
            lifecycle_name(str(rule["from"])),
            lifecycle_name(str(rule["to"])),
            lifecycle_name(str(rule["action"])),
        )
        for rule in blueprint["transitions"]
    }
    actual_transitions = {
        (item.source, item.target, item.event) for item in model.transitions
    }
    expected_terminal = sorted(
        lifecycle_name(str(stage["id"]))
        for stage in blueprint["stages"]
        if stage["terminal"]
    )
    if model.name != "twin-stage" or set(model.states) != expected_states:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL state graph mismatch")
    if actual_transitions != expected_transitions:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL transition graph mismatch")
    if model.summary()["initial_state"] != lifecycle_name(blueprint["initialStage"]):
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL initial stage mismatch")
    if model.summary()["terminal_states"] != expected_terminal:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL terminal stage mismatch")


def reject_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key not in SAFE_ASSERTIONS and SENSITIVE.search(key):
                raise ContractError("TWINLC-SECRET-001", "unsafe key")
            reject_sensitive(nested)
    elif isinstance(value, list):
        for nested in value:
            reject_sensitive(nested)


def closed(doc: Any, keys: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise ContractError("TWINLC-DOC-001", "expected an object")
    optional = optional or set()
    if set(doc) - keys or (keys - optional) - set(doc):
        raise ContractError("TWINLC-DOC-001", "document fields are not closed")
    return doc


def match(name: str, value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(PATTERNS[name], value):
        raise ContractError("TWINLC-REF-001", f"invalid reference: {name}")
    return value


def refs(values: Any, name: str, *, minimum: int) -> list[str]:
    if not isinstance(values, list) or len(values) < minimum or len(values) != len(set(values)):
        raise ContractError("TWINLC-REF-001", f"{name} must be unique and complete")
    return [match(name, item) for item in values]


def blueprint_ref(value: Any) -> dict[str, Any]:
    ref = closed(value, {"blueprintId", "version", "definitionUri", "definitionDigest", "immutable"})
    match("definitionUri", ref["definitionUri"])
    match("definitionDigest", ref["definitionDigest"])
    if ref["immutable"] is not True:
        raise ContractError("TWINLC-BLUEPRINT-001", "a bound blueprint revision must be immutable")
    return ref


def ref_of(blueprint: dict[str, Any]) -> dict[str, Any]:
    return {
        "blueprintId": blueprint["blueprintId"],
        "version": blueprint["version"],
        "definitionUri": blueprint["definitionUri"],
        "definitionDigest": "sha256:" + digest(canonical(blueprint)),
        "immutable": True,
    }


def validate_agent_binding(doc: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    doc = closed(doc, BINDING_KEYS)
    if doc["schema"] != BINDING_FAMILY or doc["kind"] != "ecosystem-agent-binding":
        raise ContractError("TWINLC-DOC-001", "wrong ecosystem binding family")
    if doc["immutable"] is not True or doc["acts"] is not False:
        raise ContractError("TWINLC-AUTHORITY-001", "an ecosystem binding is immutable and advisory")
    if doc["blueprintRef"] != ref_of(blueprint):
        raise ContractError("TWINLC-BLUEPRINT-001", "ecosystem binding does not pin the service blueprint")

    expected_stages = ["observe", "diagnose", "prioritize", "repair", "validate", "accept"]
    observed_stages: list[str] = []
    owners: dict[str, str] = {}
    requirements: dict[str, set[str]] = {}
    for stage in doc["stages"]:
        stage = closed(stage, {"id", "owner", "effect", "requires"})
        stage_id = match("stageId", stage["id"])
        if stage_id in owners or not isinstance(stage["owner"], str) or not isinstance(stage["effect"], str):
            raise ContractError("TWINLC-DOC-001", "invalid ecosystem binding stage")
        if not isinstance(stage["requires"], list) or not all(isinstance(item, str) for item in stage["requires"]):
            raise ContractError("TWINLC-EVIDENCE-001", "binding stage evidence must be declared")
        observed_stages.append(stage_id)
        owners[stage_id] = stage["owner"]
        requirements[stage_id] = set(stage["requires"])
    if observed_stages != expected_stages:
        raise ContractError("TWINLC-SEQUENCE-001", "ecosystem binding stages must be adjacent and ordered")

    transitions = []
    for transition in doc["transitions"]:
        transition = closed(transition, {"from", "to"})
        transitions.append((transition["from"], transition["to"]))
    expected_transitions = list(zip(expected_stages, expected_stages[1:]))
    if transitions != expected_transitions:
        raise ContractError("TWINLC-SEQUENCE-001", "ecosystem binding cannot skip a stage")

    authority = closed(doc["authority"], {"observation", "mutation", "acceptance", "approvalGrantsAuthority"})
    if authority != {
        "observation": "none-required",
        "mutation": "external-digest-bound-grant",
        "acceptance": "independent-exact-result-receipt",
        "approvalGrantsAuthority": False,
    }:
        raise ContractError("TWINLC-AUTHORITY-001", "binding authority boundary is invalid")
    if "evidence:authority-grant-digest" not in requirements["repair"]:
        raise ContractError("TWINLC-AUTHORITY-001", "repair must bind an external grant digest")
    if not {"evidence:snapshot-digest", "evidence:finding-digest", "evidence:plan-digest"} <= requirements["repair"]:
        raise ContractError("TWINLC-EVIDENCE-001", "repair evidence binding is incomplete")
    if "evidence:exact-result-digest" not in requirements["validate"]:
        raise ContractError("TWINLC-EVIDENCE-001", "validator must observe the exact result")
    if owners["repair"] == owners["validate"]:
        raise ContractError("TWINLC-AUTHORITY-001", "repair and validator owners must differ")

    decision = closed(doc["decision"], {"mode", "llmRole", "llmMayAddOperations", "llmMayAddTargets", "llmMayGrantAuthority"})
    if decision != {
        "mode": "deterministic-first",
        "llmRole": "rank-equal-declared-candidates-only",
        "llmMayAddOperations": False,
        "llmMayAddTargets": False,
        "llmMayGrantAuthority": False,
    }:
        raise ContractError("TWINLC-AUTHORITY-001", "LLM role expands the declared decision surface")
    deduplication = closed(doc["deduplication"], {"keyFields", "replayExecutesEffects"})
    if deduplication["keyFields"] != ["error-code", "target-ref", "finding-digest"]:
        raise ContractError("TWINLC-EVIDENCE-001", "deduplication key is not evidence-bound")
    if deduplication["replayExecutesEffects"] is not False:
        raise ContractError("TWINLC-REPLAY-001", "binding replay cannot execute effects")
    required_human = {"ambiguous-ownership", "dirty-worktree", "secret-intake", "stash-decision", "unknown-repair-class"}
    if set(doc["humanDecisionRequiredFor"]) != required_human:
        raise ContractError("TWINLC-AUTHORITY-001", "unsafe ambiguity must route to human decision")
    return doc


def bind(blueprint: dict[str, Any], doc: dict[str, Any]) -> None:
    """The document must name the exact blueprint revision it was resolved against."""
    if doc["blueprint"] != ref_of(blueprint):
        raise ContractError("TWINLC-BLUEPRINT-001", "blueprint revision binding does not match the pinned definition")


def validate_blueprint(doc: dict[str, Any]) -> dict[str, Any]:
    doc = closed(doc, BLUEPRINT_KEYS, optional={"intent"})
    reject_sensitive({k: v for k, v in doc.items() if k != "intent"})
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "lifecycle-blueprint":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    if doc["immutable"] is not True:
        raise ContractError("TWINLC-BLUEPRINT-001", "a blueprint definition must be immutable")
    if doc["replayExecutesTransitions"] is not False:
        raise ContractError("TWINLC-REPLAY-001", "replay must never execute a lifecycle transition")
    if doc["approvalGrantsAuthority"] is not False:
        raise ContractError("TWINLC-AUTHORITY-001", "a lifecycle gate must not manufacture execution authority")
    match("definitionUri", doc["definitionUri"])
    roles = set(refs(doc["approverRoles"], "role", minimum=1))

    order: dict[str, int] = {}
    stages: dict[str, dict[str, Any]] = {}
    for index, stage in enumerate(doc["stages"]):
        stage = closed(
            stage,
            {"id", "intent", "entryCriteria", "exitCriteria", "requiredArtifacts", "repeatable", "terminal"},
            optional={"intent"},
        )
        stage_id = match("stageId", stage["id"])
        if stage_id in stages:
            raise ContractError("TWINLC-GRAPH-001", "duplicate stage identity")
        refs(stage["entryCriteria"], "criterion", minimum=0)
        refs(stage["exitCriteria"], "criterion", minimum=0)
        if stage["terminal"] and stage["exitCriteria"]:
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
            {"action", "from", "to", "requiredCriteria", "approverRoles", "failClosed", "reversible", "compensatingAction"},
            optional={"compensatingAction"},
        )
        if rule["failClosed"] is not True:
            raise ContractError("TWINLC-GRAPH-001", "every transition must fail closed")
        source, target = match("stageId", rule["from"]), match("stageId", rule["to"])
        if source not in stages or target not in stages:
            raise ContractError("TWINLC-GRAPH-001", "transition references an undeclared stage")
        if source == target:
            raise ContractError("TWINLC-GRAPH-001", "a stage cannot transition to itself")
        if rule["action"] in actions:
            raise ContractError("TWINLC-GRAPH-001", "duplicate transition action")
        actions.add(rule["action"])
        if stages[source]["terminal"]:
            raise ContractError("TWINLC-GRAPH-001", "a terminal stage cannot have an outgoing transition")
        contract = set(stages[source]["exitCriteria"]) | set(stages[target]["entryCriteria"])
        required = set(refs(rule["requiredCriteria"], "criterion", minimum=1))
        if not required <= contract:
            raise ContractError("TWINLC-GRAPH-001", "required criteria are outside the stage entry/exit contract")
        if not set(refs(rule["approverRoles"], "role", minimum=0)) <= roles:
            raise ContractError("TWINLC-GRAPH-001", "approver role is not declared by the blueprint")
        if order[target] <= order[source] and stages[target]["repeatable"] is not True:
            raise ContractError("TWINLC-GRAPH-001", "a feedback transition requires a repeatable target stage")
        outgoing[source].append(target)
        incoming[target] += 1

    if incoming[initial]:
        raise ContractError("TWINLC-GRAPH-001", "the initial stage cannot be a transition target")
    if not any(stage["terminal"] for stage in stages.values()):
        raise ContractError("TWINLC-GRAPH-001", "a blueprint must declare a terminal stage")
    for stage_id, stage in stages.items():
        if not stage["terminal"] and not outgoing[stage_id]:
            raise ContractError("TWINLC-GRAPH-001", "a non-terminal stage must declare an outgoing transition")

    seen, queue = {initial}, [initial]
    while queue:
        for target in outgoing[queue.pop()]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    if seen != set(stages):
        raise ContractError("TWINLC-GRAPH-001", "every stage must be reachable from the initial stage")
    if doc["blueprintId"] == SEQUENTIAL_BLUEPRINT_ID:
        validate_sequential_forward(doc, order, stages)
    return doc


def validate_sequential_forward(
    doc: dict[str, Any],
    order: dict[str, int],
    stages: dict[str, dict[str, Any]],
) -> None:
    """Opt-in sequential repair: a forward non-terminal hop must be adjacent.

    Feedback into a repeatable earlier stage and any transition into a terminal
    stage remain legal. Skip-ahead (observed → planned, inventoried → granted)
    is how a service twin pretends one healthy fact implies the next.
    """
    for rule in doc["transitions"]:
        source, target = str(rule["from"]), str(rule["to"])
        if stages[target]["terminal"] is True:
            continue
        if order[target] <= order[source]:
            continue
        if order[target] != order[source] + 1:
            raise ContractError(
                "TWINLC-SEQUENCE-001",
                "a sequential blueprint cannot skip a forward stage",
            )


def resolve(blueprint: dict[str, Any], action: Any, source: Any, target: Any) -> dict[str, Any]:
    """Fail closed: only an exactly declared (action, from, to) triple resolves."""
    for rule in blueprint["transitions"]:
        if (rule["action"], rule["from"], rule["to"]) == (action, source, target):
            return rule
    raise ContractError("TWINLC-TRANSITION-001", "the requested transition is not declared by the blueprint")


def validate_request(doc: dict[str, Any], blueprint: dict[str, Any]) -> None:
    doc = closed(doc, REQUEST_KEYS)
    reject_sensitive(doc)
    if doc["schema"] != SCHEMA_FAMILY or doc["kind"] != "transition-request":
        raise ContractError("TWINLC-DOC-001", "wrong document family")
    blueprint_ref(doc["blueprint"])
    bind(blueprint, doc)
    for name in ("requestId", "twinRef", "baseRevision", "idempotencyKey"):
        match({"baseRevision": "revision"}.get(name, name), doc[name])
    actor = closed(doc["requestedBy"], {"actorRef", "actorClass"})
    match("actorRef", actor["actorRef"])
    if actor["actorClass"] not in {"human", "service", "twin-persona"}:
        raise ContractError("TWINLC-DOC-001", "unknown actor class")
    if doc["gateDecisionRef"] is not None:
        match("decisionRef", doc["gateDecisionRef"])
    rule = resolve(blueprint, doc["action"], doc["fromStage"], doc["toStage"])
    evidence = refs(doc["evidenceRefs"], "evidenceRef", minimum=1)
    if len(evidence) < len(rule["requiredCriteria"]):
        raise ContractError("TWINLC-EVIDENCE-001", "each required criterion needs its own evidence reference")


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
    if not isinstance(doc["aggregateVersion"], int) or doc["aggregateVersion"] < 0:
        raise ContractError("TWINLC-DOC-001", "invalid aggregate version")
    if doc["lastTransitionId"] is not None:
        match("transitionId", doc["lastTransitionId"])
    refs(doc["unmetCriteria"], "criterion", minimum=0)


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
    if doc["authorityGranted"] is not False:
        raise ContractError("TWINLC-AUTHORITY-001", "a lifecycle receipt must not report granted authority")
    if doc["secretsRedacted"] is not True:
        raise ContractError("TWINLC-SECRET-001", "a receipt must be redacted")
    if doc["status"] not in STATUSES:
        raise ContractError("TWINLC-DOC-001", "unknown transition status")
    rule = resolve(blueprint, doc["action"], doc["fromStage"], doc["toStage"])
    refs(doc["evidenceRefs"], "evidenceRef", minimum=0)
    unmet = refs(doc["unmetCriteria"], "criterion", minimum=0)
    if doc["status"] in UNMET_REQUIRED_STATUSES:
        if not unmet or doc["approvedBy"] is not None:
            raise ContractError("TWINLC-EVIDENCE-001", "a blocked or rejected transition records unmet criteria and no approver")
        return
    if doc["status"] == "REQUESTED":
        if doc["approvedBy"] is not None:
            raise ContractError("TWINLC-AUTHORITY-001", "a requested transition has no approver yet")
        return
    if unmet:
        raise ContractError("TWINLC-EVIDENCE-001", "an approved transition cannot carry unmet criteria")
    if len(doc["evidenceRefs"]) < len(rule["requiredCriteria"]):
        raise ContractError("TWINLC-EVIDENCE-001", "approval requires evidence for every required criterion")
    if not refs(doc["eventRefs"], "eventRef", minimum=1):
        raise ContractError("TWINLC-EVIDENCE-001", "an approved transition must be event backed")
    if rule["approverRoles"]:
        approver = closed(doc["approvedBy"], {"actorRef", "actorClass", "role"})
        match("actorRef", approver["actorRef"])
        if approver["actorClass"] not in {"human", "service"}:
            raise ContractError("TWINLC-AUTHORITY-001", "a twin persona cannot approve its own lifecycle gate")
        if approver["role"] not in rule["approverRoles"]:
            raise ContractError("TWINLC-AUTHORITY-001", "approver role is not accepted for this transition")
        if doc["gateDecisionRef"] is None:
            raise ContractError("TWINLC-AUTHORITY-001", "an approved gate must reference its decision record")
        match("decisionRef", doc["gateDecisionRef"])


def lifecycle_projection_cases(blueprint: dict[str, Any]) -> list[dict[str, str]]:
    """Prove the projection rules the same way every other rule is proven.

    Drift in the pinned validator, the pinned profile or the state graph must
    fail the suite; without these cases a silently disabled projection check
    would still report a green run.
    """
    check: Callable[[dict[str, Any]], Any] = validate_lifecycle_profile
    cases = [
        expect_rejected("lifecycle-projection-state-drift", "TWINLC-GRAPH-001", check, blueprint,
                        lambda d: d["stages"][1].__setitem__("id", "renamed")),
        expect_rejected("lifecycle-projection-transition-drift", "TWINLC-GRAPH-001", check, blueprint,
                        lambda d: d["transitions"][0].__setitem__("action", "sketch")),
        expect_rejected("lifecycle-projection-initial-drift", "TWINLC-GRAPH-001", check, blueprint,
                        lambda d: d.__setitem__("initialStage", "modeled")),
        expect_rejected("lifecycle-projection-terminal-drift", "TWINLC-GRAPH-001", check, blueprint,
                        lambda d: d["stages"][4].__setitem__("terminal", True)),
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        drifted_profile = root / "twin-lifecycle.lifecycle"
        drifted_profile.write_bytes(LIFECYCLE_PATH.read_bytes() + b"\n")
        drifted_validator = root / "lifecycle.py"
        drifted_validator.write_bytes(LIFECYCLE_VALIDATOR_PATH.read_bytes() + b"\n")
        cases.append(
            expect_rejected(
                "lifecycle-pinned-profile-byte-drift", "TWINLC-BLUEPRINT-001",
                lambda doc: validate_lifecycle_profile(doc, profile_path=drifted_profile),
                blueprint, lambda d: None,
            )
        )
        cases.append(
            expect_rejected(
                "lifecycle-pinned-validator-byte-drift", "TWINLC-BLUEPRINT-001",
                lambda doc: validate_lifecycle_profile(doc, validator_path=drifted_validator),
                blueprint, lambda d: None,
            )
        )
    return cases


def expect_rejected(
    name: str,
    code: str,
    validator: Callable[[dict[str, Any]], Any],
    base: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, str]:
    doc = copy.deepcopy(base)
    mutation(doc)
    try:
        validator(doc)
    except ContractError as error:
        if error.code != code:
            raise AssertionError(f"adversarial case rejected with {error.code}, expected {code}: {name}") from error
        return {"case": name, "code": code}
    raise AssertionError(f"adversarial case accepted: {name}")


def run_all() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text())
    grammar = GRAMMAR_PATH.read_bytes()
    if digest(canonical(schema)) != SCHEMA_DIGEST or digest(grammar) != GRAMMAR_DIGEST:
        raise ContractError("TWINLC-BLUEPRINT-001", "contract digest mismatch")
    if schema.get("$id") != SCHEMA_URI:
        raise ContractError("TWINLC-BLUEPRINT-001", "schema identity mismatch")
    lowered = grammar.lower()
    for forbidden in (b"shell", b"argv", b"password", b"credential", b"secret", b"authority", b"http://"):
        if forbidden in lowered:
            raise ContractError("TWINLC-SECRET-001", "unsafe grammar surface")

    blueprint = validate_blueprint(json.loads(BLUEPRINT_PATH.read_text()))
    validate_lifecycle_profile(blueprint)
    sequential = validate_blueprint(json.loads(VALIDATE_REPAIR_PATH.read_text()))
    sequential_pinned = ref_of(sequential)
    binding = validate_agent_binding(json.loads(BINDING_PATH.read_text()), sequential)
    sequential_request = {
        "schema": SCHEMA_FAMILY, "kind": "transition-request", "requestId": "request:bind-plesk-target",
        "twinRef": "twin://digitaltwin-run/plesk-service-twin", "blueprint": sequential_pinned,
        "action": "bind-target", "fromStage": "inventoried", "toStage": "target-bound",
        "baseRevision": "c" * 40,
        "requestedBy": {"actorRef": "actor://wellmanifest.com/project-operator", "actorClass": "service"},
        "evidenceRefs": [
            "evidence://digitaltwin-run/plesk/inventory/r1",
            "evidence://digitaltwin-run/plesk/target-binding/r1",
            "evidence://digitaltwin-run/plesk/docroot-binding/r1",
            "evidence://digitaltwin-run/plesk/credential-ref/r1",
        ],
        "gateDecisionRef": None, "idempotencyKey": "idempotency:bind-plesk-target.1",
    }
    validate_request(sequential_request, sequential)
    pinned = ref_of(blueprint)
    request = {
        "schema": SCHEMA_FAMILY, "kind": "transition-request", "requestId": "request:release-twin",
        "twinRef": "twin://wellmanifest.com/generic-all-traits", "blueprint": pinned, "action": "release",
        "fromStage": "validated", "toStage": "released", "baseRevision": "a" * 40,
        "requestedBy": {"actorRef": "actor://wellmanifest.com/release-bot", "actorClass": "service"},
        "evidenceRefs": [
            "evidence://wellmanifest.com/conformance/r1",
            "evidence://wellmanifest.com/replay-observation/r1",
        ],
        "gateDecisionRef": None, "idempotencyKey": "idempotency:release-twin.1",
    }
    state = {
        "schema": SCHEMA_FAMILY, "kind": "lifecycle-state", "twinRef": request["twinRef"],
        "blueprint": pinned, "currentStage": "validated", "aggregateVersion": 12,
        "derivedFrom": "event-stream", "lastTransitionId": "transition:validate.1",
        "unmetCriteria": [], "replayExecutedEffects": False,
    }
    receipt = {
        "schema": SCHEMA_FAMILY, "kind": "transition-receipt", "transitionId": "transition:release.1",
        "requestId": request["requestId"], "twinRef": request["twinRef"], "blueprint": pinned,
        "action": "release", "fromStage": "validated", "toStage": "released", "status": "APPROVED",
        "baseRevision": "a" * 40, "aggregateVersion": 13, "evidenceRefs": request["evidenceRefs"],
        "unmetCriteria": [],
        "approvedBy": {"actorRef": "actor://wellmanifest.com/owner", "actorClass": "human", "role": "role:release-approver"},
        "gateDecisionRef": "decision://wellmanifest.com/gates/release.1",
        "eventRefs": ["event://wellmanifest.com/twin/lifecycle-transition-recorded.1"],
        "idempotencyKey": "idempotency:release-twin.1", "authorityGranted": False,
        "secretsRedacted": True, "recordedAt": "2026-08-14T09:00:00Z",
    }
    validate_request(request, blueprint)
    validate_state(state, blueprint)
    validate_receipt(receipt, blueprint)

    check_blueprint = validate_blueprint
    check_request: Callable[[dict[str, Any]], Any] = lambda doc: validate_request(doc, blueprint)
    check_state: Callable[[dict[str, Any]], Any] = lambda doc: validate_state(doc, blueprint)
    check_receipt: Callable[[dict[str, Any]], Any] = lambda doc: validate_receipt(doc, blueprint)
    check_binding: Callable[[dict[str, Any]], Any] = lambda doc: validate_agent_binding(doc, sequential)

    def add_stage(doc: dict[str, Any], stage_id: str) -> None:
        doc["stages"].append({
            "id": stage_id, "entryCriteria": [], "exitCriteria": [], "requiredArtifacts": [],
            "repeatable": False, "terminal": True,
        })

    rejected = [
        expect_rejected("mutable-blueprint", "TWINLC-BLUEPRINT-001", check_blueprint, blueprint, lambda d: d.update(immutable=False)),
        expect_rejected("replay-executes-transitions", "TWINLC-REPLAY-001", check_blueprint, blueprint, lambda d: d.update(replayExecutesTransitions=True)),
        expect_rejected("approval-grants-authority", "TWINLC-AUTHORITY-001", check_blueprint, blueprint, lambda d: d.update(approvalGrantsAuthority=True)),
        expect_rejected("unreachable-stage", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: add_stage(d, "orphan")),
        expect_rejected("terminal-stage-has-exit", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: d["transitions"].append({
            "action": "revive", "from": "retired", "to": "operating",
            "requiredCriteria": ["criterion:outbox-drained"], "approverRoles": [], "failClosed": True, "reversible": False,
        })),
        expect_rejected("feedback-into-non-repeatable-stage", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: d["transitions"].append({
            "action": "remodel", "from": "released", "to": "modeled",
            "requiredCriteria": ["criterion:release-receipt-recorded"], "approverRoles": [], "failClosed": True, "reversible": False,
        })),
        expect_rejected("criterion-outside-stage-contract", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: d["transitions"][0].update(
            requiredCriteria=["criterion:invented"])),
        expect_rejected("undeclared-approver-role", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: d["transitions"][2].update(
            approverRoles=["role:anyone"])),
        expect_rejected("transition-not-fail-closed", "TWINLC-GRAPH-001", check_blueprint, blueprint, lambda d: d["transitions"][0].update(failClosed=False)),
        expect_rejected("undeclared-transition", "TWINLC-TRANSITION-001", check_request, request, lambda d: d.update(toStage="retired")),
        expect_rejected("authority-in-request", "TWINLC-DOC-001", check_request, request, lambda d: d.update(authorityRef="authority://x/y")),
        expect_rejected("shell-in-request", "TWINLC-DOC-001", check_request, request, lambda d: d.update(command="rm -rf /")),
        expect_rejected("score-as-evidence", "TWINLC-REF-001", check_request, request, lambda d: d.update(
            evidenceRefs=["score://wellmanifest.com/evaluation/0.92", "evidence://wellmanifest.com/conformance/r1"])),
        expect_rejected("insufficient-evidence", "TWINLC-EVIDENCE-001", check_request, request, lambda d: d.update(
            evidenceRefs=["evidence://wellmanifest.com/conformance/r1"])),
        expect_rejected("unpinned-blueprint-revision", "TWINLC-BLUEPRINT-001", check_request, request, lambda d: d.update(
            blueprint={**pinned, "definitionDigest": "sha256:" + "b" * 64})),
        expect_rejected("replay-executed-effects", "TWINLC-REPLAY-001", check_state, state, lambda d: d.update(replayExecutedEffects=True)),
        expect_rejected("state-outside-blueprint", "TWINLC-GRAPH-001", check_state, state, lambda d: d.update(currentStage="imagined")),
        expect_rejected("receipt-grants-authority", "TWINLC-AUTHORITY-001", check_receipt, receipt, lambda d: d.update(authorityGranted=True)),
        expect_rejected("approved-with-unmet-criteria", "TWINLC-EVIDENCE-001", check_receipt, receipt, lambda d: d.update(
            unmetCriteria=["criterion:replay-safety-observed"])),
        expect_rejected("approved-without-events", "TWINLC-REF-001", check_receipt, receipt, lambda d: d.update(eventRefs=[])),
        expect_rejected("approved-by-wrong-role", "TWINLC-AUTHORITY-001", check_receipt, receipt, lambda d: d["approvedBy"].update(role="role:change-approver")),
        expect_rejected("persona-approves-itself", "TWINLC-AUTHORITY-001", check_receipt, receipt, lambda d: d["approvedBy"].update(actorClass="twin-persona")),
        expect_rejected("approved-without-gate-decision", "TWINLC-AUTHORITY-001", check_receipt, receipt, lambda d: d.update(gateDecisionRef=None)),
        expect_rejected("blocked-without-unmet-criteria", "TWINLC-EVIDENCE-001", check_receipt, receipt, lambda d: d.update(
            status="BLOCKED", approvedBy=None, unmetCriteria=[])),
        expect_rejected("sequential-skip-ahead-blueprint", "TWINLC-SEQUENCE-001", check_blueprint, sequential, lambda d: d["transitions"].append({
            "action": "skip-to-plan", "from": "observed", "to": "planned",
            "requiredCriteria": ["criterion:account-snapshot-observed", "criterion:plan-hash-current"],
            "approverRoles": [], "failClosed": True, "reversible": False,
        })),
        expect_rejected("sequential-skip-ahead-request", "TWINLC-TRANSITION-001",
                        lambda doc: validate_request(doc, sequential), sequential_request, lambda d: d.update(
                            action="plan", fromStage="inventoried", toStage="planned")),
        expect_rejected("binding-acts", "TWINLC-AUTHORITY-001", check_binding, binding,
                        lambda d: d.update(acts=True)),
        expect_rejected("binding-skip-repair", "TWINLC-SEQUENCE-001", check_binding, binding,
                        lambda d: d["transitions"].__setitem__(2, {"from": "prioritize", "to": "validate"})),
        expect_rejected("binding-llm-adds-operation", "TWINLC-AUTHORITY-001", check_binding, binding,
                        lambda d: d["decision"].update(llmMayAddOperations=True)),
    ]
    rejected.extend(lifecycle_projection_cases(blueprint))
    return {
        "schema": "wellmanifest.twin-lifecycle-conformance/v1",
        "ok": True,
        "positiveDocuments": 6,
        "ecosystemBindings": [
            {"bindingId": binding["bindingId"], "blueprint": binding["blueprintRef"], "acts": binding["acts"]}
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


def main() -> int:
    parser = argparse.ArgumentParser(description="wellmanifest.twin-lifecycle/v1 conformance")
    parser.add_argument("--all", action="store_true")
    parser.parse_args()
    print(json.dumps(run_all(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
