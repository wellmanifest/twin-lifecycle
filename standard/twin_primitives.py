#!/usr/bin/env python3
"""Shared contract primitives and Lifecycle DSL profile check for twin-lifecycle v1."""

from __future__ import annotations

import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from twin_io import (
    MAX_INPUT_BYTES,
    MAX_JSON_DEPTH,
    MAX_JSON_INT_ABS,
    MAX_JSON_INT_DIGITS,
    SAFE_ASSERTIONS,
    SECRET_MATERIAL,
    SENSITIVE,
    ContractError,
    _enforce_json_bounds,
    bounded_intent,
    canonical,
    digest,
    has_symlink_ancestor,
    is_valid_utf8,
    read_regular_bytes,
    read_regular_utf8,
    reject_sensitive,
    strict_loads,
)

__all__ = [
    "BINDING_FAMILY",
    "BINDING_KEYS",
    "BINDING_PATH",
    "BLUEPRINT_KEYS",
    "BLUEPRINT_PATH",
    "ContractError",
    "GRAMMAR_DIGEST",
    "GRAMMAR_PATH",
    "LIFECYCLE_PATH",
    "LIFECYCLE_PROFILE_DIGEST",
    "LIFECYCLE_SOURCE_REVISION",
    "LIFECYCLE_VALIDATOR_DIGEST",
    "LIFECYCLE_VALIDATOR_DIGESTS",
    "LIFECYCLE_VALIDATOR_PATH",
    "MAX_INPUT_BYTES",
    "MAX_JSON_DEPTH",
    "MAX_JSON_INT_ABS",
    "MAX_JSON_INT_DIGITS",
    "MAX_LENGTHS",
    "PATTERNS",
    "RECEIPT_KEYS",
    "REQUEST_KEYS",
    "ROOT",
    "SAFE_ASSERTIONS",
    "SCHEMA_DIGEST",
    "SCHEMA_FAMILY",
    "SCHEMA_PATH",
    "SCHEMA_URI",
    "SECRET_MATERIAL",
    "SENSITIVE",
    "SEQUENTIAL_BLUEPRINT_ID",
    "STATE_KEYS",
    "STATUSES",
    "TIMESTAMP_RE",
    "UNMET_REQUIRED_STATUSES",
    "VALIDATE_REPAIR_PATH",
    "_enforce_json_bounds",
    "bind",
    "blueprint_ref",
    "bounded_intent",
    "canonical",
    "closed",
    "digest",
    "enum_str",
    "has_symlink_ancestor",
    "is_valid_utf8",
    "lifecycle_name",
    "load_pinned_lifecycle",
    "match",
    "non_neg_int",
    "read_regular_bytes",
    "read_regular_utf8",
    "ref_of",
    "refs",
    "reject_sensitive",
    "resolve",
    "strict_bool",
    "strict_loads",
    "timestamp_value",
    "validate_lifecycle_profile",
    "validate_request",
    "validate_state",
    "verify_lifecycle_validator_digests",
]

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
LIFECYCLE_SOURCE_REVISION = "12bdc4c899bd6119cc30fca51d00a62b8582fa79"
LIFECYCLE_VALIDATOR_DIGEST = "c0fdaad649f9740a894e785686a3d78f0d9a18e914ba7d5d5c673498326b8f71"
LIFECYCLE_VALIDATOR_DIGESTS = {
    "lifecycle.py": LIFECYCLE_VALIDATOR_DIGEST,
    "lifecycle_audit.py": "758c08401214c0be16dc5be8c28fc6be026e95050b1df87e62ea77b06a412459",
    "lifecycle_catalog.py": "9fcbd3a5922c617801640cb4cfd27a29398b8dda387d55060dbfef68be12898d",
}
LIFECYCLE_PROFILE_DIGEST = "8cb1af012d2debd62feb8ed1fad821d5c95aa832f0f038458c2d0de25bd3129a"
SCHEMA_FAMILY = "wellmanifest.twin-lifecycle/v1"
BINDING_FAMILY = "wellmanifest.twin-lifecycle-binding/v1"
SCHEMA_URI = "https://wellmanifest.com/schemas/twin-lifecycle/v1"

BLUEPRINT_KEYS = {
    "schema",
    "kind",
    "blueprintId",
    "version",
    "definitionUri",
    "intent",
    "immutable",
    "initialStage",
    "approverRoles",
    "stages",
    "transitions",
    "replayExecutesTransitions",
    "approvalGrantsAuthority",
}
REQUEST_KEYS = {
    "schema",
    "kind",
    "requestId",
    "twinRef",
    "blueprint",
    "action",
    "fromStage",
    "toStage",
    "baseRevision",
    "requestedBy",
    "evidenceRefs",
    "gateDecisionRef",
    "idempotencyKey",
}
STATE_KEYS = {
    "schema",
    "kind",
    "twinRef",
    "blueprint",
    "currentStage",
    "aggregateVersion",
    "derivedFrom",
    "lastTransitionId",
    "unmetCriteria",
    "replayExecutedEffects",
}
RECEIPT_KEYS = {
    "schema",
    "kind",
    "transitionId",
    "requestId",
    "twinRef",
    "blueprint",
    "action",
    "fromStage",
    "toStage",
    "status",
    "baseRevision",
    "aggregateVersion",
    "evidenceRefs",
    "unmetCriteria",
    "approvedBy",
    "gateDecisionRef",
    "eventRefs",
    "idempotencyKey",
    "authorityGranted",
    "secretsRedacted",
    "recordedAt",
}
BINDING_KEYS = {
    "schema",
    "kind",
    "bindingId",
    "immutable",
    "acts",
    "blueprintRef",
    "stages",
    "transitions",
    "authority",
    "decision",
    "deduplication",
    "humanDecisionRequiredFor",
}
STATUSES = {"REQUESTED", "APPROVED", "BLOCKED", "REJECTED"}
UNMET_REQUIRED_STATUSES = {"BLOCKED", "REJECTED"}
PATTERNS = {
    "blueprintId": r"\A[a-z][a-z0-9._-]{0,63}\Z",
    "blueprintVersion": r"\Av[1-9][0-9]*\Z",
    "actionId": r"\A[a-z][a-z0-9-]{0,47}\Z",
    "artifact": r"\Aartifact:[a-z][a-z0-9._:-]{0,127}\Z",
    "requestId": r"\Arequest:[a-z0-9][a-z0-9._-]{0,95}\Z",
    "transitionId": r"\Atransition:[a-z0-9][a-z0-9._-]{0,95}\Z",
    "idempotencyKey": r"\Aidempotency:[a-z0-9][a-z0-9._-]{0,95}\Z",
    "twinRef": r"\Atwin://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+\Z",
    "definitionUri": r"\Alifecycle://[a-z0-9][a-z0-9.-]*/[a-z0-9][a-z0-9._-]*/v[1-9][0-9]*\Z",
    "definitionDigest": r"\Asha256:[0-9a-f]{64}\Z",
    "evidenceRef": r"\Aevidence://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+/r[1-9][0-9]*\Z",
    "decisionRef": r"\Adecision://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+\Z",
    "eventRef": r"\Aevent://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:/-]+\Z",
    "actorRef": r"\Aactor://[a-z0-9][a-z0-9.-]*/[A-Za-z0-9._:-]+\Z",
    "revision": r"\A(?:[0-9a-f]{40}|sha256:[0-9a-f]{64})\Z",
    "stageId": r"\A[a-z][a-z0-9-]{0,47}\Z",
    "criterion": r"\Acriterion:[a-z][a-z0-9._-]{0,63}\Z",
    "role": r"\Arole:[a-z][a-z0-9._-]{0,63}\Z",
}
MAX_LENGTHS = {
    "twinRef": 320,
    "definitionUri": 320,
    "evidenceRef": 320,
    "decisionRef": 320,
    "eventRef": 320,
    "actorRef": 240,
}
TIMESTAMP_RE = re.compile(
    r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


def lifecycle_name(value: str) -> str:
    return value.upper().replace("-", "_")


def load_pinned_lifecycle(validator_path: Path = LIFECYCLE_VALIDATOR_PATH) -> Any:
    """Load the vendored validator from the exact file whose digest was checked."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("twin_lifecycle_pinned_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle validator is not loadable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_lifecycle_validator_digests(validator_path: Path = LIFECYCLE_VALIDATOR_PATH) -> None:
    if (
        digest(read_regular_bytes(validator_path, error_code="TWINLC-BLUEPRINT-001"))
        != LIFECYCLE_VALIDATOR_DIGEST
    ):
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle validator digest mismatch")
    for filename, expected_sha in LIFECYCLE_VALIDATOR_DIGESTS.items():
        if filename == "lifecycle.py":
            continue
        helper_bytes = read_regular_bytes(ROOT / filename, error_code="TWINLC-BLUEPRINT-001")
        if digest(helper_bytes) != expected_sha:
            raise ContractError(
                "TWINLC-BLUEPRINT-001", f"pinned lifecycle helper digest mismatch: {filename}"
            )


def validate_lifecycle_profile(
    blueprint: dict[str, Any],
    *,
    validator_path: Path = LIFECYCLE_VALIDATOR_PATH,
    profile_path: Path = LIFECYCLE_PATH,
) -> None:
    verify_lifecycle_validator_digests(validator_path)
    if (
        digest(read_regular_bytes(profile_path, error_code="TWINLC-BLUEPRINT-001"))
        != LIFECYCLE_PROFILE_DIGEST
    ):
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle profile digest mismatch")
    lc = load_pinned_lifecycle(validator_path)
    report = lc.validate_path(profile_path, lc.embedded_catalog())
    if not report.valid or len(report.lifecycles) != 1:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL profile is invalid")
    if lc.audit_path(profile_path)["finding_count"] != 0:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL profile has compaction findings")
    model = report.lifecycles[0]
    expected_states = {lifecycle_name(str(stage["id"])) for stage in blueprint["stages"]}
    expected_transitions = {
        (
            lifecycle_name(str(rule["from"])),
            lifecycle_name(str(rule["to"])),
            lifecycle_name(str(rule["action"])),
        )
        for rule in blueprint["transitions"]
    }
    actual_transitions = {(item.source, item.target, item.event) for item in model.transitions}
    expected_terminal = sorted(
        lifecycle_name(str(stage["id"])) for stage in blueprint["stages"] if stage["terminal"]
    )
    if model.name != "twin-stage" or set(model.states) != expected_states:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL state graph mismatch")
    if actual_transitions != expected_transitions:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL transition graph mismatch")
    if model.summary()["initial_state"] != lifecycle_name(blueprint["initialStage"]):
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL initial stage mismatch")
    if model.summary()["terminal_states"] != expected_terminal:
        raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL terminal stage mismatch")


def closed(doc: Any, keys: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise ContractError("TWINLC-DOC-001", "expected an object")
    if any(not isinstance(k, str) or not is_valid_utf8(k) for k in doc):
        raise ContractError("TWINLC-DOC-001", "JSON object key must be a string")
    optional_keys = optional or set()
    if set(doc) - keys or (keys - optional_keys) - set(doc):
        raise ContractError("TWINLC-DOC-001", "document fields are not closed")
    return doc


def enum_str(value: Any, allowed: set[str], code: str, message: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ContractError(code, message)
    return value


def match(name: str, value: Any) -> str:
    max_len = MAX_LENGTHS.get(name)
    if (
        not isinstance(value, str)
        or not is_valid_utf8(value)
        or (max_len is not None and len(value) > max_len)
        or not re.fullmatch(PATTERNS[name], value)
    ):
        raise ContractError("TWINLC-REF-001", f"invalid reference: {name}")
    if "://" in value:
        host, _, rest = value.split("://", 1)[1].partition("/")
        if host in {"", ".", ".."} or any(
            seg in {"", ".", ".."} for seg in re.split(r"[/:]", rest)
        ):
            raise ContractError("TWINLC-REF-001", f"invalid reference: {name}")
    elif ":" in value and any(seg in {"", ".", ".."} for seg in value.split(":")):
        raise ContractError("TWINLC-REF-001", f"invalid reference: {name}")
    return value


def refs(values: Any, name: str, *, minimum: int, maximum: int = 32) -> list[str]:
    if not isinstance(values, list) or not minimum <= len(values) <= maximum:
        raise ContractError("TWINLC-REF-001", f"{name} must be unique and complete")
    try:
        is_unique = len(values) == len(set(values))
    except TypeError as error:
        raise ContractError("TWINLC-REF-001", f"{name} must be unique and complete") from error
    if not is_unique:
        raise ContractError("TWINLC-REF-001", f"{name} must be unique and complete")
    return [match(name, item) for item in values]


def non_neg_int(value: Any, message: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError("TWINLC-DOC-001", message)
    return value


def strict_bool(value: Any, message: str, *, code: str = "TWINLC-DOC-001") -> bool:
    if not isinstance(value, bool):
        raise ContractError(code, message)
    return value


def timestamp_value(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 40 or TIMESTAMP_RE.fullmatch(value) is None:
        raise ContractError("TWINLC-DOC-001", "invalid recordedAt timestamp")
    normalized = re.sub(r"\.([0-9]{6})[0-9]+", r".\1", value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ContractError("TWINLC-DOC-001", "invalid recordedAt timestamp") from error
    if parsed.tzinfo is None:
        raise ContractError("TWINLC-DOC-001", "recordedAt timezone is required")
    return value


def blueprint_ref(value: Any) -> dict[str, Any]:
    ref = closed(
        value, {"blueprintId", "version", "definitionUri", "definitionDigest", "immutable"}
    )
    match("blueprintId", ref["blueprintId"])
    match("blueprintVersion", ref["version"])
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


def bind(blueprint: dict[str, Any], doc: dict[str, Any]) -> None:
    if doc["blueprint"] != ref_of(blueprint):
        raise ContractError(
            "TWINLC-BLUEPRINT-001",
            "blueprint revision binding does not match the pinned definition",
        )


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
    enum_str(
        actor["actorClass"],
        {"human", "service", "twin-persona"},
        "TWINLC-DOC-001",
        "unknown actor class",
    )
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
    enum_str(
        doc["currentStage"],
        {stage["id"] for stage in blueprint["stages"]},
        "TWINLC-GRAPH-001",
        "current stage is not declared by the blueprint",
    )
    non_neg_int(doc["aggregateVersion"], "invalid aggregate version")
    if doc["lastTransitionId"] is not None:
        match("transitionId", doc["lastTransitionId"])
    refs(doc["unmetCriteria"], "criterion", minimum=0, maximum=32)
