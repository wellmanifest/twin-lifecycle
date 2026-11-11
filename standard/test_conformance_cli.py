#!/usr/bin/env python3
"""Unit and CLI conformance regression tests for standard/conformance.py."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import conformance
import twin_fixtures
import twin_primitives


class ConformanceCliTargetTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> tuple[int, dict[str, Any]]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = conformance.main(list(args))
        return code, json.loads(buf.getvalue())

    def _load_positive_docs(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        bp = conformance.validate_blueprint(
            twin_primitives.strict_loads(conformance.BLUEPRINT_PATH.read_text(encoding="utf-8"))
        )
        seq_bp = conformance.validate_blueprint(
            twin_primitives.strict_loads(
                conformance.VALIDATE_REPAIR_PATH.read_text(encoding="utf-8")
            )
        )
        _, req, state, receipt = twin_fixtures.build_positive_documents(
            conformance.ref_of(bp), conformance.ref_of(seq_bp)
        )
        return bp, req, state, receipt

    def test_default_self_suite_preserved(self) -> None:
        code, report = self._run_cli("--all")
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["positiveDocuments"], 6)

    def test_explicit_file_and_directory_targets_validated(self) -> None:
        code, report = self._run_cli(
            str(conformance.BLUEPRINT_PATH),
            str(conformance.BINDING_PATH),
            str(conformance.LIFECYCLE_PATH),
        )
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["checkedCount"], 3)
        self.assertEqual(report["findings"], [])

        dir_code, dir_report = self._run_cli(str(conformance.ROOT))
        self.assertEqual(dir_code, 0)
        self.assertTrue(dir_report["ok"])
        self.assertGreaterEqual(dir_report["checkedCount"], 4)

    def test_invalid_target_document_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_bp = Path(tmp) / "bad-blueprint.json"
            doc = copy.deepcopy(json.loads(conformance.BLUEPRINT_PATH.read_text(encoding="utf-8")))
            doc["immutable"] = False
            bad_bp.write_text(json.dumps(doc), encoding="utf-8")

            code, report = self._run_cli(str(bad_bp))
            self.assertEqual(code, 1)
            self.assertFalse(report["ok"])
            self.assertEqual(report["findings"][0]["code"], "TWINLC-BLUEPRINT-001")

    def test_custom_blueprint_resolves_dependent_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bp = copy.deepcopy(json.loads(conformance.BLUEPRINT_PATH.read_text(encoding="utf-8")))
            bp["blueprintId"] = "custom-heyasa-twin"
            bp["definitionUri"] = "lifecycle://wellmanifest.com/custom-heyasa-twin/v1"
            bp_file = root / "blueprint.json"
            bp_file.write_text(json.dumps(bp), encoding="utf-8")

            pinned = conformance.ref_of(conformance.validate_blueprint(bp))
            req = {
                "schema": conformance.SCHEMA_FAMILY,
                "kind": "transition-request",
                "requestId": "request:release-custom",
                "twinRef": "twin://wellmanifest.com/heyasa-ui-twin",
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
                "idempotencyKey": "idempotency:release-custom.1",
            }
            req_file = root / "request.json"
            req_file.write_text(json.dumps(req), encoding="utf-8")

            code, report = self._run_cli("--blueprint", str(bp_file), str(req_file))
            self.assertEqual(code, 0)
            self.assertTrue(report["ok"])
            self.assertEqual(report["checkedCount"], 1)

    def test_missing_or_empty_target_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty_dir = Path(tmp) / "empty"
            empty_dir.mkdir()
            code_empty, rep_empty = self._run_cli(str(empty_dir))
            self.assertEqual(code_empty, 1)
            self.assertFalse(rep_empty["ok"])
            self.assertEqual(rep_empty["findings"][0]["code"], "TWINLC-TARGET-001")

            code_missing, rep_missing = self._run_cli(str(Path(tmp) / "nonexistent.json"))
            self.assertEqual(code_missing, 1)
            self.assertFalse(rep_missing["ok"])
            self.assertEqual(rep_missing["findings"][0]["code"], "TWINLC-TARGET-001")

    def test_duplicate_json_keys_and_malformed_twin_docs_fail_in_directory_scan(self) -> None:
        _, req, _, _ = self._load_positive_docs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_req = root / "valid-request.json"
            valid_req.write_text(json.dumps(req), encoding="utf-8")
            unrelated = root / "package-notes.json"
            unrelated.write_text('{"name": "unrelated", "version": "1.0.0"}', encoding="utf-8")

            ok_code, ok_rep = self._run_cli(str(root))
            self.assertEqual(ok_code, 0)
            self.assertEqual(ok_rep["checkedCount"], 1)

            dup_text = json.dumps(req)[:-1] + ', "action": "observe"}'
            dup_file = root / "dup-request.json"
            dup_file.write_text(dup_text, encoding="utf-8")

            file_code, file_rep = self._run_cli(str(dup_file))
            self.assertEqual(file_code, 1)
            self.assertEqual(file_rep["findings"][0]["code"], "TWINLC-DOC-001")

            dir_code, dir_rep = self._run_cli(str(root))
            self.assertEqual(dir_code, 1)
            self.assertFalse(dir_rep["ok"])
            self.assertEqual(dir_rep["findings"][0]["code"], "TWINLC-DOC-001")

            dup_file.unlink()
            truncated = root / "broken-twin.json"
            truncated.write_text(f'{{"schema": "{conformance.SCHEMA_FAMILY}", ', encoding="utf-8")
            broken_code, broken_rep = self._run_cli(str(root))
            self.assertEqual(broken_code, 1)
            self.assertEqual(broken_rep["findings"][0]["code"], "TWINLC-DOC-001")

    def test_symlink_target_and_nested_symlink_fail_closed(self) -> None:
        _, req, _, _ = self._load_positive_docs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside.json"
            outside.write_text(json.dumps(req), encoding="utf-8")
            direct_link = root / "direct-link.json"
            direct_link.symlink_to(outside)

            code_direct, rep_direct = self._run_cli(str(direct_link))
            self.assertEqual(code_direct, 1)
            self.assertEqual(rep_direct["findings"][0]["code"], "TWINLC-TARGET-001")

            scan_dir = root / "scan"
            scan_dir.mkdir()
            (scan_dir / "valid.json").write_text(json.dumps(req), encoding="utf-8")
            (scan_dir / "escaped.json").symlink_to(outside)

            code_nested, rep_nested = self._run_cli(str(scan_dir))
            self.assertEqual(code_nested, 1)
            self.assertEqual(rep_nested["findings"][0]["code"], "TWINLC-TARGET-001")

    def test_schema_parity_bool_timestamp_unhashable_and_secret_guards(self) -> None:
        bp, req, state, receipt = self._load_positive_docs()

        bad_state = copy.deepcopy(state)
        bad_state["aggregateVersion"] = True
        with self.assertRaises(conformance.ContractError) as state_err:
            conformance.validate_state(bad_state, bp)
        self.assertEqual(state_err.exception.code, "TWINLC-DOC-001")

        bad_receipt_ver = copy.deepcopy(receipt)
        bad_receipt_ver["aggregateVersion"] = False
        with self.assertRaises(twin_primitives.ContractError) as ver_err:
            conformance.validate_receipt(bad_receipt_ver, bp)
        self.assertEqual(ver_err.exception.code, "TWINLC-DOC-001")

        bad_receipt_ts = copy.deepcopy(receipt)
        bad_receipt_ts["recordedAt"] = "2026-08-13"
        with self.assertRaises(twin_primitives.ContractError) as ts_err:
            conformance.validate_receipt(bad_receipt_ts, bp)
        self.assertEqual(ts_err.exception.code, "TWINLC-DOC-001")

        unhashable_req = copy.deepcopy(req)
        unhashable_req["evidenceRefs"] = [["nested"]]
        with self.assertRaises(twin_primitives.ContractError) as list_err:
            conformance.validate_request(unhashable_req, bp)
        self.assertEqual(list_err.exception.code, "TWINLC-REF-001")

        canary = "gh" + "p_" + ("A" * 26)
        secret_req = copy.deepcopy(req)
        secret_req["idempotencyKey"] = f"idempotency:{canary}"
        with self.assertRaises(twin_primitives.ContractError) as sec_err:
            conformance.validate_request(secret_req, bp)
        self.assertEqual(sec_err.exception.code, "TWINLC-SECRET-001")

    def test_self_suite_contract_error_returns_structured_json(self) -> None:
        boom = twin_primitives.ContractError("TWINLC-BLUEPRINT-001", "simulated drift")
        with mock.patch.object(conformance, "run_all", side_effect=boom):
            code, report = self._run_cli()
        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertEqual(report["findings"][0]["path"], "<self-suite>")
        self.assertEqual(report["findings"][0]["code"], "TWINLC-BLUEPRINT-001")


if __name__ == "__main__":
    unittest.main()
