#!/usr/bin/env python3
"""Reference positive and adversarial fixtures for twin-lifecycle v1 conformance."""

from __future__ import annotations

import copy
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from twin_primitives import (
    LIFECYCLE_PATH,
    LIFECYCLE_VALIDATOR_PATH,
    SCHEMA_FAMILY,
    ContractError,
    validate_lifecycle_profile,
)


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
            raise AssertionError(
                f"adversarial case rejected with {error.code}, expected {code}: {name}"
            ) from error
        return {"case": name, "code": code}
    raise AssertionError(f"adversarial case accepted: {name}")


def lifecycle_projection_cases(blueprint: dict[str, Any]) -> list[dict[str, str]]:
    check: Callable[[dict[str, Any]], Any] = validate_lifecycle_profile
    specs: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("lifecycle-projection-state-drift", lambda d: d["stages"][1].__setitem__("id", "renamed")),
        (
            "lifecycle-projection-transition-drift",
            lambda d: d["transitions"][0].__setitem__("action", "sketch"),
        ),
        ("lifecycle-projection-initial-drift", lambda d: d.__setitem__("initialStage", "modeled")),
        (
            "lifecycle-projection-terminal-drift",
            lambda d: d["stages"][4].__setitem__("terminal", True),
        ),
    ]
    cases = [expect_rejected(name, "TWINLC-GRAPH-001", check, blueprint, fn) for name, fn in specs]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        drifted_profile = root / "twin-lifecycle.lifecycle"
        drifted_profile.write_bytes(LIFECYCLE_PATH.read_bytes() + b"\n")
        drifted_validator = root / "lifecycle.py"
        drifted_validator.write_bytes(LIFECYCLE_VALIDATOR_PATH.read_bytes() + b"\n")
        cases.append(
            expect_rejected(
                "lifecycle-pinned-profile-byte-drift",
                "TWINLC-BLUEPRINT-001",
                lambda doc: validate_lifecycle_profile(doc, profile_path=drifted_profile),
                blueprint,
                lambda d: None,
            )
        )
        cases.append(
            expect_rejected(
                "lifecycle-pinned-validator-byte-drift",
                "TWINLC-BLUEPRINT-001",
                lambda doc: validate_lifecycle_profile(doc, validator_path=drifted_validator),
                blueprint,
                lambda d: None,
            )
        )
    return cases


def build_positive_documents(
    pinned: dict[str, Any], sequential_pinned: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    sequential_request = {
        "schema": SCHEMA_FAMILY,
        "kind": "transition-request",
        "requestId": "request:bind-plesk-target",
        "twinRef": "twin://digitaltwin-run/plesk-service-twin",
        "blueprint": sequential_pinned,
        "action": "bind-target",
        "fromStage": "inventoried",
        "toStage": "target-bound",
        "baseRevision": "c" * 40,
        "requestedBy": {
            "actorRef": "actor://wellmanifest.com/project-operator",
            "actorClass": "service",
        },
        "evidenceRefs": [
            "evidence://digitaltwin-run/plesk/inventory/r1",
            "evidence://digitaltwin-run/plesk/target-binding/r1",
            "evidence://digitaltwin-run/plesk/docroot-binding/r1",
            "evidence://digitaltwin-run/plesk/credential-ref/r1",
        ],
        "gateDecisionRef": None,
        "idempotencyKey": "idempotency:bind-plesk-target.1",
    }
    request = {
        "schema": SCHEMA_FAMILY,
        "kind": "transition-request",
        "twinRef": "twin://wellmanifest.com/generic-all-traits",
        "requestId": "request:release-twin",
        "blueprint": pinned,
        "action": "release",
        "fromStage": "validated",
        "toStage": "released",
        "baseRevision": "a" * 40,
        "requestedBy": {
            "actorRef": "actor://wellmanifest.com/release-bot",
            "actorClass": "service",
        },
        "evidenceRefs": [
            "evidence://wellmanifest.com/conformance/r1",
            "evidence://wellmanifest.com/replay-observation/r1",
        ],
        "gateDecisionRef": None,
        "idempotencyKey": "idempotency:release-twin.1",
    }
    state = {
        "schema": SCHEMA_FAMILY,
        "kind": "lifecycle-state",
        "twinRef": request["twinRef"],
        "blueprint": pinned,
        "currentStage": "validated",
        "aggregateVersion": 12,
        "derivedFrom": "event-stream",
        "lastTransitionId": "transition:validate.1",
        "unmetCriteria": [],
        "replayExecutedEffects": False,
    }
    receipt = {
        "schema": SCHEMA_FAMILY,
        "kind": "transition-receipt",
        "transitionId": "transition:release.1",
        "requestId": request["requestId"],
        "twinRef": request["twinRef"],
        "blueprint": pinned,
        "action": "release",
        "fromStage": "validated",
        "toStage": "released",
        "status": "APPROVED",
        "baseRevision": "a" * 40,
        "aggregateVersion": 13,
        "evidenceRefs": request["evidenceRefs"],
        "unmetCriteria": [],
        "approvedBy": {
            "actorRef": "actor://wellmanifest.com/owner",
            "actorClass": "human",
            "role": "role:release-approver",
        },
        "gateDecisionRef": "decision://wellmanifest.com/gates/release.1",
        "eventRefs": ["event://wellmanifest.com/twin/lifecycle-transition-recorded.1"],
        "idempotencyKey": "idempotency:release-twin.1",
        "authorityGranted": False,
        "secretsRedacted": True,
        "recordedAt": "2026-08-14T09:00:00Z",
    }
    return sequential_request, request, state, receipt


def run_adversarial_suite(
    *,
    blueprint: dict[str, Any],
    pinned: dict[str, Any],
    sequential: dict[str, Any],
    sequential_request: dict[str, Any],
    binding: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    receipt: dict[str, Any],
    check_blueprint: Callable[[dict[str, Any]], Any],
    check_request: Callable[[dict[str, Any]], Any],
    check_seq_request: Callable[[dict[str, Any]], Any],
    check_state: Callable[[dict[str, Any]], Any],
    check_receipt: Callable[[dict[str, Any]], Any],
    check_binding: Callable[[dict[str, Any]], Any],
) -> list[dict[str, str]]:
    def _edge(action: str, src: str, tgt: str, crit: list[str]) -> dict[str, Any]:
        return {
            "action": action,
            "from": src,
            "to": tgt,
            "requiredCriteria": crit,
            "approverRoles": [],
            "failClosed": True,
            "reversible": False,
        }

    def _orphan(doc: dict[str, Any]) -> None:
        doc["stages"].append(
            {
                "id": "orphan",
                "entryCriteria": [],
                "exitCriteria": [],
                "requiredArtifacts": [],
                "repeatable": False,
                "terminal": True,
            }
        )

    tok = "gh" + "p_" + ("A" * 26)
    bp_cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        ("mutable-blueprint", "TWINLC-BLUEPRINT-001", lambda d: d.update(immutable=False)),
        (
            "replay-executes-transitions",
            "TWINLC-REPLAY-001",
            lambda d: d.update(replayExecutesTransitions=True),
        ),
        (
            "approval-grants-authority",
            "TWINLC-AUTHORITY-001",
            lambda d: d.update(approvalGrantsAuthority=True),
        ),
        ("unreachable-stage", "TWINLC-GRAPH-001", _orphan),
        (
            "terminal-stage-has-exit",
            "TWINLC-GRAPH-001",
            lambda d: d["transitions"].append(
                _edge("revive", "retired", "operating", ["criterion:outbox-drained"])
            ),
        ),
        (
            "feedback-into-non-repeatable-stage",
            "TWINLC-GRAPH-001",
            lambda d: d["transitions"].append(
                _edge("remodel", "released", "modeled", ["criterion:release-receipt-recorded"])
            ),
        ),
        (
            "criterion-outside-stage-contract",
            "TWINLC-GRAPH-001",
            lambda d: d["transitions"][0].update(requiredCriteria=["criterion:invented"]),
        ),
        (
            "undeclared-approver-role",
            "TWINLC-GRAPH-001",
            lambda d: d["transitions"][2].update(approverRoles=["role:anyone"]),
        ),
        (
            "transition-not-fail-closed",
            "TWINLC-GRAPH-001",
            lambda d: d["transitions"][0].update(failClosed=False),
        ),
        ("invalid-blueprint-version", "TWINLC-REF-001", lambda d: d.update(version="1.0.0")),
        (
            "invalid-required-artifact",
            "TWINLC-REF-001",
            lambda d: d["stages"][0].update(requiredArtifacts=["bad"]),
        ),
    ]
    req_cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        (
            "unhashable-evidence-ref",
            "TWINLC-REF-001",
            lambda d: d.update(evidenceRefs=[{"bad": 1}]),
        ),
        ("inline-secret-in-request", "TWINLC-SECRET-001", lambda d: d.update(twinRef=tok)),
        ("undeclared-transition", "TWINLC-TRANSITION-001", lambda d: d.update(toStage="retired")),
        (
            "authority-in-request",
            "TWINLC-DOC-001",
            lambda d: d.update(authorityRef="authority://x/y"),
        ),
        ("shell-in-request", "TWINLC-DOC-001", lambda d: d.update(command="rm -rf /")),
        (
            "score-as-evidence",
            "TWINLC-REF-001",
            lambda d: d.update(
                evidenceRefs=[
                    "score://wellmanifest.com/evaluation/0.92",
                    "evidence://wellmanifest.com/conformance/r1",
                ]
            ),
        ),
        (
            "insufficient-evidence",
            "TWINLC-EVIDENCE-001",
            lambda d: d.update(evidenceRefs=["evidence://wellmanifest.com/conformance/r1"]),
        ),
        (
            "unpinned-blueprint-revision",
            "TWINLC-BLUEPRINT-001",
            lambda d: d.update(blueprint={**pinned, "definitionDigest": "sha256:" + "b" * 64}),
        ),
    ]
    st_cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        (
            "replay-executed-effects",
            "TWINLC-REPLAY-001",
            lambda d: d.update(replayExecutedEffects=True),
        ),
        (
            "state-outside-blueprint",
            "TWINLC-GRAPH-001",
            lambda d: d.update(currentStage="imagined"),
        ),
        (
            "bool-state-aggregate-version",
            "TWINLC-DOC-001",
            lambda d: d.update(aggregateVersion=True),
        ),
    ]
    rc_cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        (
            "receipt-grants-authority",
            "TWINLC-AUTHORITY-001",
            lambda d: d.update(authorityGranted=True),
        ),
        (
            "bool-receipt-aggregate-version",
            "TWINLC-DOC-001",
            lambda d: d.update(aggregateVersion=False),
        ),
        (
            "invalid-receipt-recorded-at",
            "TWINLC-DOC-001",
            lambda d: d.update(recordedAt="2026-08-14 09:00:00Z"),
        ),
        (
            "approved-with-unmet-criteria",
            "TWINLC-EVIDENCE-001",
            lambda d: d.update(unmetCriteria=["criterion:replay-safety-observed"]),
        ),
        ("approved-without-events", "TWINLC-REF-001", lambda d: d.update(eventRefs=[])),
        (
            "approved-by-wrong-role",
            "TWINLC-AUTHORITY-001",
            lambda d: d["approvedBy"].update(role="role:change-approver"),
        ),
        (
            "persona-approves-itself",
            "TWINLC-AUTHORITY-001",
            lambda d: d["approvedBy"].update(actorClass="twin-persona"),
        ),
        (
            "approved-without-gate-decision",
            "TWINLC-AUTHORITY-001",
            lambda d: d.update(gateDecisionRef=None),
        ),
        (
            "blocked-without-unmet-criteria",
            "TWINLC-EVIDENCE-001",
            lambda d: d.update(status="BLOCKED", approvedBy=None, unmetCriteria=[]),
        ),
    ]
    rejected = [expect_rejected(n, c, check_blueprint, blueprint, fn) for n, c, fn in bp_cases]
    rejected += [expect_rejected(n, c, check_request, request, fn) for n, c, fn in req_cases]
    rejected += [expect_rejected(n, c, check_state, state, fn) for n, c, fn in st_cases]
    rejected += [expect_rejected(n, c, check_receipt, receipt, fn) for n, c, fn in rc_cases]
    rejected.append(
        expect_rejected(
            "sequential-skip-ahead-blueprint",
            "TWINLC-SEQUENCE-001",
            check_blueprint,
            sequential,
            lambda d: d["transitions"].append(
                _edge(
                    "skip-to-plan",
                    "observed",
                    "planned",
                    ["criterion:account-snapshot-observed", "criterion:plan-hash-current"],
                )
            ),
        )
    )
    rejected.append(
        expect_rejected(
            "sequential-skip-ahead-request",
            "TWINLC-TRANSITION-001",
            check_seq_request,
            sequential_request,
            lambda d: d.update(action="plan", fromStage="inventoried", toStage="planned"),
        )
    )
    rejected.append(
        expect_rejected(
            "binding-acts",
            "TWINLC-AUTHORITY-001",
            check_binding,
            binding,
            lambda d: d.update(acts=True),
        )
    )
    rejected.append(
        expect_rejected(
            "binding-skip-repair",
            "TWINLC-SEQUENCE-001",
            check_binding,
            binding,
            lambda d: d["transitions"].__setitem__(2, {"from": "prioritize", "to": "validate"}),
        )
    )
    rejected.append(
        expect_rejected(
            "binding-llm-adds-operation",
            "TWINLC-AUTHORITY-001",
            check_binding,
            binding,
            lambda d: d["decision"].update(llmMayAddOperations=True),
        )
    )
    rejected.extend(lifecycle_projection_cases(blueprint))
    return rejected
