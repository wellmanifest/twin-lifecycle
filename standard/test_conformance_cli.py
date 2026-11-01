#!/usr/bin/env python3
"""Unit tests for CLI target validation in standard/conformance.py."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from standard import conformance


class ConformanceCliTargetTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> tuple[int, dict]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = conformance.main(list(args))
        return code, json.loads(buf.getvalue())

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
                "requestedBy": {"actorRef": "actor://wellmanifest.com/release-bot", "actorClass": "service"},
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


if __name__ == "__main__":
    unittest.main()
