"""Adversarial hardening suite for twin-lifecycle I/O, URI segments, JSON, and enum guards."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import conformance
import twin_fixtures
import twin_primitives as tp


class TwinLifecycleHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bp = conformance.validate_blueprint(
            tp.strict_loads(tp.read_regular_utf8(conformance.BLUEPRINT_PATH))
        )
        seq_bp = conformance.validate_blueprint(
            tp.strict_loads(tp.read_regular_utf8(conformance.VALIDATE_REPAIR_PATH))
        )
        _, self.req, self.state, self.receipt = twin_fixtures.build_positive_documents(
            conformance.ref_of(self.bp), conformance.ref_of(seq_bp)
        )

    def _run_cli(self, *args: str) -> tuple[int, dict[str, object]]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = conformance.main(list(args))
        return code, json.loads(buf.getvalue())

    def test_uri_dot_segments_and_double_slashes_rejected(self) -> None:
        for bad_uri in (
            "twin://wellmanifest.com/../secret",
            "twin://wellmanifest.com/./secret",
            "twin://wellmanifest.com//secret",
        ):
            cand = copy.deepcopy(self.req)
            cand["twinRef"] = bad_uri
            with self.assertRaises(tp.ContractError) as ctx:
                conformance.validate_request(cand, self.bp)
            self.assertEqual(ctx.exception.code, "TWINLC-REF-001")

    def test_strict_loads_rejects_nan_infinity_overflow_and_deep_nesting(self) -> None:
        deep = ("[" * (tp.MAX_JSON_DEPTH + 2)) + "1" + ("]" * (tp.MAX_JSON_DEPTH + 2))
        extreme = ("[" * 1500) + "1" + ("]" * 1500)
        for raw in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999", deep, extreme):
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(tp.ContractError) as ctx:
                    tp.strict_loads(raw)
                self.assertEqual(ctx.exception.code, "TWINLC-DOC-001")

    def test_directory_scan_handles_non_utf8_unhashable_schema_and_fifo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "valid.json").write_text(json.dumps(self.req), encoding="utf-8")
            (root / "bad-utf8.json").write_bytes(b"\xff\xfe")
            code, report = self._run_cli(str(root))
            self.assertEqual(code, 1)
            self.assertFalse(report["ok"])

            (root / "bad-utf8.json").unlink()
            (root / "unhashable-schema.json").write_text('{"schema": ["bad"]}', encoding="utf-8")
            code2, report2 = self._run_cli(str(root))
            self.assertEqual(code2, 0)
            self.assertTrue(report2["ok"])

            code3, report3 = self._run_cli(str(root / "unhashable-schema.json"))
            self.assertEqual(code3, 1)
            self.assertFalse(report3["ok"])

            if hasattr(os, "mkfifo"):
                fifo = root / "pipe.json"
                os.mkfifo(fifo)
                code_fifo, _ = self._run_cli(str(fifo))
                self.assertEqual(code_fifo, 1)

    def test_unhashable_enums_and_non_string_keys_raise_contract_error(self) -> None:
        bad_req = copy.deepcopy(self.req)
        bad_req["requestedBy"]["actorClass"] = ["service"]
        with self.assertRaises(tp.ContractError):
            conformance.validate_request(bad_req, self.bp)

        bad_state = copy.deepcopy(self.state)
        bad_state["currentStage"] = ["validated"]
        with self.assertRaises(tp.ContractError):
            conformance.validate_state(bad_state, self.bp)

        bad_rcpt = copy.deepcopy(self.receipt)
        bad_rcpt["status"] = ["APPROVED"]
        with self.assertRaises(tp.ContractError):
            conformance.validate_receipt(bad_rcpt, self.bp)

        bad_rcpt2 = copy.deepcopy(self.receipt)
        bad_rcpt2["approvedBy"]["role"] = ["role:release-approver"]
        with self.assertRaises(tp.ContractError):
            conformance.validate_receipt(bad_rcpt2, self.bp)

        bad_key = copy.deepcopy(self.req)
        bad_key[7] = "bad"  # type: ignore[index]
        with self.assertRaises(tp.ContractError):
            conformance.validate_request(bad_key, self.bp)


if __name__ == "__main__":
    unittest.main()
