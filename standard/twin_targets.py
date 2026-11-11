#!/usr/bin/env python3
"""Ecosystem agent-binding and CLI target path validation for twin-lifecycle v1."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

from twin_primitives import (
    BINDING_FAMILY,
    BINDING_KEYS,
    BLUEPRINT_PATH,
    SCHEMA_FAMILY,
    VALIDATE_REPAIR_PATH,
    ContractError,
    blueprint_ref,
    closed,
    has_symlink_ancestor,
    load_pinned_lifecycle,
    match,
    read_regular_utf8,
    ref_of,
    reject_sensitive,
    strict_loads,
    verify_lifecycle_validator_digests,
)

SKIP_DIRS = {".git", ".worktrees", ".venv", "__pycache__", "node_modules", ".koru", ".planfile"}


def validate_agent_binding(doc: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    doc = closed(doc, BINDING_KEYS)
    reject_sensitive(doc)
    if doc["schema"] != BINDING_FAMILY or doc["kind"] != "ecosystem-agent-binding":
        raise ContractError("TWINLC-DOC-001", "wrong ecosystem binding family")
    if doc["immutable"] is not True or doc["acts"] is not False:
        raise ContractError(
            "TWINLC-AUTHORITY-001", "an ecosystem binding is immutable and advisory"
        )
    if doc["blueprintRef"] != ref_of(blueprint):
        raise ContractError(
            "TWINLC-BLUEPRINT-001", "ecosystem binding does not pin the service blueprint"
        )
    expected_stages = ["observe", "diagnose", "prioritize", "repair", "validate", "accept"]
    observed_stages: list[str] = []
    owners: dict[str, str] = {}
    requirements: dict[str, set[str]] = {}
    if not isinstance(doc["stages"], list) or not isinstance(doc["transitions"], list):
        raise ContractError("TWINLC-DOC-001", "binding stages and transitions must be lists")
    for stage in doc["stages"]:
        stage = closed(stage, {"id", "owner", "effect", "requires"})
        stage_id = match("stageId", stage["id"])
        if (
            stage_id in owners
            or not isinstance(stage["owner"], str)
            or not isinstance(stage["effect"], str)
        ):
            raise ContractError("TWINLC-DOC-001", "invalid ecosystem binding stage")
        if not isinstance(stage["requires"], list) or not all(
            isinstance(x, str) for x in stage["requires"]
        ):
            raise ContractError("TWINLC-EVIDENCE-001", "binding stage evidence must be declared")
        observed_stages.append(stage_id)
        owners[stage_id] = stage["owner"]
        requirements[stage_id] = set(stage["requires"])
    if observed_stages != expected_stages:
        raise ContractError(
            "TWINLC-SEQUENCE-001", "ecosystem binding stages must be adjacent and ordered"
        )
    transitions = []
    for transition in doc["transitions"]:
        transition = closed(transition, {"from", "to"})
        transitions.append((transition["from"], transition["to"]))
    if transitions != list(zip(expected_stages, expected_stages[1:], strict=False)):
        raise ContractError("TWINLC-SEQUENCE-001", "ecosystem binding cannot skip a stage")
    authority = closed(
        doc["authority"], {"observation", "mutation", "acceptance", "approvalGrantsAuthority"}
    )
    if authority != {
        "observation": "none-required",
        "mutation": "external-digest-bound-grant",
        "acceptance": "independent-exact-result-receipt",
        "approvalGrantsAuthority": False,
    }:
        raise ContractError("TWINLC-AUTHORITY-001", "binding authority boundary is invalid")
    if "evidence:authority-grant-digest" not in requirements["repair"]:
        raise ContractError("TWINLC-AUTHORITY-001", "repair must bind an external grant digest")
    if (
        not {
            "evidence:snapshot-digest",
            "evidence:finding-digest",
            "evidence:plan-digest",
        }
        <= requirements["repair"]
    ):
        raise ContractError("TWINLC-EVIDENCE-001", "repair evidence binding is incomplete")
    if "evidence:exact-result-digest" not in requirements["validate"]:
        raise ContractError("TWINLC-EVIDENCE-001", "validator must observe the exact result")
    if owners["repair"] == owners["validate"]:
        raise ContractError("TWINLC-AUTHORITY-001", "repair and validator owners must differ")
    decision = closed(
        doc["decision"],
        {"mode", "llmRole", "llmMayAddOperations", "llmMayAddTargets", "llmMayGrantAuthority"},
    )
    if decision != {
        "mode": "deterministic-first",
        "llmRole": "rank-equal-declared-candidates-only",
        "llmMayAddOperations": False,
        "llmMayAddTargets": False,
        "llmMayGrantAuthority": False,
    }:
        raise ContractError(
            "TWINLC-AUTHORITY-001", "LLM role expands the declared decision surface"
        )
    deduplication = closed(doc["deduplication"], {"keyFields", "replayExecutesEffects"})
    if deduplication["keyFields"] != ["error-code", "target-ref", "finding-digest"]:
        raise ContractError("TWINLC-EVIDENCE-001", "deduplication key is not evidence-bound")
    if deduplication["replayExecutesEffects"] is not False:
        raise ContractError("TWINLC-REPLAY-001", "binding replay cannot execute effects")
    required_human = {
        "ambiguous-ownership",
        "dirty-worktree",
        "secret-intake",
        "stash-decision",
        "unknown-repair-class",
    }
    human_list = doc["humanDecisionRequiredFor"]
    if (
        not isinstance(human_list, list)
        or not all(isinstance(x, str) for x in human_list)
        or set(human_list) != required_human
    ):
        raise ContractError("TWINLC-AUTHORITY-001", "unsafe ambiguity must route to human decision")
    return doc


def _iter_target_files(target: Path) -> tuple[list[Path], bool]:
    if has_symlink_ancestor(target):
        raise ContractError("TWINLC-TARGET-001", "symbolic link target is forbidden")
    raw_target = os.fspath(target)
    try:
        st = os.lstat(raw_target)
    except OSError as err:
        raise ContractError("TWINLC-TARGET-001", "target path does not exist") from err
    if stat.S_ISLNK(st.st_mode):
        raise ContractError("TWINLC-TARGET-001", "symbolic link target is forbidden")
    if stat.S_ISREG(st.st_mode):
        return [target], True
    if not stat.S_ISDIR(st.st_mode):
        raise ContractError("TWINLC-TARGET-001", "target path is neither a file nor a directory")
    collected: list[Path] = []
    for candidate in sorted(target.rglob("*")):
        rel_parts = candidate.relative_to(target).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        cst = os.lstat(candidate)
        if stat.S_ISLNK(cst.st_mode):
            raise ContractError(
                "TWINLC-TARGET-001", "symbolic link inside target directory is forbidden"
            )
        if stat.S_ISREG(cst.st_mode) and candidate.suffix in {".json", ".lifecycle"}:
            collected.append(candidate)
    return collected, False


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    try:
        payload = strict_loads(raw_text)
    except ContractError:
        raise
    except ValueError as error:
        raise ContractError("TWINLC-DOC-001", "invalid JSON document") from error
    if not isinstance(payload, dict):
        raise ContractError("TWINLC-DOC-001", "expected a JSON object")
    return payload


def _load_json_object(path: Path, *, error_code: str = "TWINLC-DOC-001") -> dict[str, Any]:
    raw_text = read_regular_utf8(path, error_code=error_code)
    return _parse_json_object(raw_text)


def _is_probable_twin_json_text(raw_text: str) -> bool:
    try:
        parsed = json.loads(raw_text)
    except (ValueError, RecursionError):
        return SCHEMA_FAMILY in raw_text or BINDING_FAMILY in raw_text
    if not isinstance(parsed, dict):
        return False
    schema_val = parsed.get("schema")
    return isinstance(schema_val, str) and schema_val in {SCHEMA_FAMILY, BINDING_FAMILY}


def _blueprint_key(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ref.get("blueprintId", "")),
        str(ref.get("definitionUri", "")),
        str(ref.get("definitionDigest", "")),
    )


def validate_targets_impl(
    targets: list[Path],
    *,
    blueprint_paths: list[Path] | None = None,
    validate_blueprint_fn: Callable[[dict[str, Any]], dict[str, Any]],
    validate_request_fn: Callable[[dict[str, Any], dict[str, Any]], None],
    validate_state_fn: Callable[[dict[str, Any], dict[str, Any]], None],
    validate_receipt_fn: Callable[[dict[str, Any], dict[str, Any]], None],
) -> dict[str, Any]:
    blueprints: dict[tuple[str, str, str], dict[str, Any]] = {}
    for bp_path in [BLUEPRINT_PATH, VALIDATE_REPAIR_PATH, *(blueprint_paths or [])]:
        bp = validate_blueprint_fn(_load_json_object(bp_path, error_code="TWINLC-TARGET-001"))
        blueprints[_blueprint_key(ref_of(bp))] = bp
    expanded: list[tuple[Path, bool]] = []
    for raw_target in targets:
        files, explicit_file = _iter_target_files(Path(os.path.abspath(os.fspath(raw_target))))
        if not files:
            raise ContractError(
                "TWINLC-TARGET-001", "no twin-lifecycle documents found under target"
            )
        expanded.extend((item, explicit_file) for item in files)
    pending_docs: list[tuple[Path, dict[str, Any]]] = []
    checked: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    lifecycle_mod: Any | None = None
    for file_path, explicit_file in expanded:
        if file_path.suffix == ".lifecycle":
            try:
                verify_lifecycle_validator_digests()
                if lifecycle_mod is None:
                    lifecycle_mod = load_pinned_lifecycle()
                report = lifecycle_mod.validate_path(file_path, lifecycle_mod.embedded_catalog())
                if not report.valid or not report.lifecycles:
                    raise ContractError("TWINLC-GRAPH-001", "Lifecycle DSL profile is invalid")
                if lifecycle_mod.audit_path(file_path)["finding_count"] != 0:
                    raise ContractError(
                        "TWINLC-GRAPH-001", "Lifecycle DSL profile has compaction findings"
                    )
                checked.append({"path": str(file_path), "kind": "lifecycle-dsl"})
            except ContractError as error:
                findings.append({"path": str(file_path), "code": error.code, "message": str(error)})
            continue
        try:
            raw_text = read_regular_utf8(file_path, error_code="TWINLC-DOC-001")
        except ContractError as error:
            findings.append({"path": str(file_path), "code": error.code, "message": str(error)})
            continue
        try:
            doc = _parse_json_object(raw_text)
        except ContractError as error:
            if explicit_file or _is_probable_twin_json_text(raw_text):
                findings.append({"path": str(file_path), "code": error.code, "message": str(error)})
            continue
        schema_id = doc.get("schema")
        raw_kind = doc.get("kind")
        if not explicit_file and (
            not isinstance(schema_id, str) or schema_id not in {SCHEMA_FAMILY, BINDING_FAMILY}
        ):
            continue
        if schema_id == SCHEMA_FAMILY and raw_kind == "lifecycle-blueprint":
            try:
                bp = validate_blueprint_fn(doc)
                blueprints[_blueprint_key(ref_of(bp))] = bp
                checked.append({"path": str(file_path), "kind": "lifecycle-blueprint"})
            except ContractError as error:
                findings.append({"path": str(file_path), "code": error.code, "message": str(error)})
        else:
            pending_docs.append((file_path, doc))
    for file_path, doc in pending_docs:
        raw_kind = doc.get("kind")
        kind = raw_kind if isinstance(raw_kind, str) else ""
        schema_id = doc.get("schema")
        try:
            if not isinstance(schema_id, str):
                raise ContractError(
                    "TWINLC-DOC-001", "unsupported twin-lifecycle document family or kind"
                )
            if schema_id == BINDING_FAMILY and kind == "ecosystem-agent-binding":
                bp = blueprints.get(_blueprint_key(blueprint_ref(doc.get("blueprintRef"))))
                if bp is None:
                    raise ContractError(
                        "TWINLC-BLUEPRINT-001", "referenced blueprint revision is not loaded"
                    )
                validate_agent_binding(doc, bp)
            elif schema_id == SCHEMA_FAMILY and kind in {
                "transition-request",
                "lifecycle-state",
                "transition-receipt",
            }:
                bp = blueprints.get(_blueprint_key(blueprint_ref(doc.get("blueprint"))))
                if bp is None:
                    raise ContractError(
                        "TWINLC-BLUEPRINT-001", "referenced blueprint revision is not loaded"
                    )
                if kind == "transition-request":
                    validate_request_fn(doc, bp)
                elif kind == "lifecycle-state":
                    validate_state_fn(doc, bp)
                else:
                    validate_receipt_fn(doc, bp)
            else:
                raise ContractError(
                    "TWINLC-DOC-001", "unsupported twin-lifecycle document family or kind"
                )
            checked.append({"path": str(file_path), "kind": kind})
        except ContractError as error:
            findings.append({"path": str(file_path), "code": error.code, "message": str(error)})
    if not checked and not findings:
        raise ContractError("TWINLC-TARGET-001", "no twin-lifecycle documents matched under target")
    return {
        "schema": "wellmanifest.twin-lifecycle-conformance/v1",
        "ok": len(findings) == 0,
        "checkedCount": len(checked),
        "checkedTargets": checked,
        "findings": findings,
    }
