#!/usr/bin/env python3
"""Shared contract primitives and Lifecycle DSL profile check for twin-lifecycle v1."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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
    "blueprintId": r"^[a-z][a-z0-9._-]{0,63}$",
    "blueprintVersion": r"^v[1-9][0-9]*$",
    "actionId": r"^[a-z][a-z0-9-]{0,47}$",
    "artifact": r"^artifact:[a-z][a-z0-9._:-]{0,127}$",
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
MAX_LENGTHS = {
    "twinRef": 320,
    "definitionUri": 320,
    "evidenceRef": 320,
    "decisionRef": 320,
    "eventRef": 320,
    "actorRef": 240,
}
TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
SENSITIVE = re.compile(
    r"(?:shell|argv|command|password|passwd|token|secret|credential|api[-_]?key|cookie|"
    r"private[-_]?key|remote|url|score|proposal|simulation|verdict|prompt)",
    re.I,
)
SECRET_MATERIAL = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{20,}|"
    r"\bAKIA[0-9A-Z]{16}\b|"
    r"(?:password|passwd|token|secret|api[-_]?key)\s*[:=]\s*[^\s,;]{4,})",
    re.I,
)
SAFE_ASSERTIONS = {"secretsRedacted"}


class ContractError(ValueError):
    """A bounded rejection that never repeats untrusted document content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def strict_loads(raw: str) -> Any:
    def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, val in pairs:
            if key in obj:
                raise ContractError("TWINLC-DOC-001", "duplicate JSON key")
            obj[key] = val
        return obj

    return json.loads(raw, object_pairs_hook=_unique_pairs)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    if digest(validator_path.read_bytes()) != LIFECYCLE_VALIDATOR_DIGEST:
        raise ContractError("TWINLC-BLUEPRINT-001", "pinned lifecycle validator digest mismatch")
    for filename, expected_sha in LIFECYCLE_VALIDATOR_DIGESTS.items():
        if filename == "lifecycle.py":
            continue
        if digest((ROOT / filename).read_bytes()) != expected_sha:
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
    if digest(profile_path.read_bytes()) != LIFECYCLE_PROFILE_DIGEST:
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


def reject_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key not in SAFE_ASSERTIONS and SENSITIVE.search(key):
                raise ContractError("TWINLC-SECRET-001", "unsafe key")
            reject_sensitive(nested)
    elif isinstance(value, list):
        for nested in value:
            reject_sensitive(nested)
    elif isinstance(value, str) and SECRET_MATERIAL.search(value):
        raise ContractError("TWINLC-SECRET-001", "credential material is forbidden")


def closed(doc: Any, keys: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise ContractError("TWINLC-DOC-001", "expected an object")
    optional_keys = optional or set()
    if set(doc) - keys or (keys - optional_keys) - set(doc):
        raise ContractError("TWINLC-DOC-001", "document fields are not closed")
    return doc


def match(name: str, value: Any) -> str:
    max_len = MAX_LENGTHS.get(name)
    if (
        not isinstance(value, str)
        or (max_len is not None and len(value) > max_len)
        or not re.fullmatch(PATTERNS[name], value)
    ):
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
