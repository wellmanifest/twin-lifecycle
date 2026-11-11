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

    def test_int_overflow_surrogates_secret_keys_ancestor_symlinks_and_ref_bounds(self) -> None:
        for raw in (
            '{"x": ' + "9" * 500 + "}",
            '{"x": -' + "9" * 500 + "}",
            '{"x": ' + "9" * 5000 + "}",
            r'{"x": "\ud800"}',
            r'{"\udfff": 1}',
            '{"x": "\ud800"}',
            "{malformed",
        ):
            with self.subTest(raw=raw[:24]), self.assertRaises(tp.ContractError) as ctx:
                tp.strict_loads(raw)
            self.assertEqual(ctx.exception.code, "TWINLC-DOC-001")

        for bad_val in ({"x": 10**400}, {"x": "\ud800"}, {"\ud800": 1}):
            with self.assertRaises(tp.ContractError):
                tp.canonical(bad_val)

        canary_key = "gh" + "p_" + ("X9y8Z7" * 5)
        with self.assertRaises(tp.ContractError) as sec_ctx:
            tp.reject_sensitive({canary_key: "v"})
        self.assertEqual(sec_ctx.exception.code, "TWINLC-SECRET-001")
        for bad_utf8 in ({"\ud800": "v"}, {"safe": "\udfff"}):
            with self.assertRaises(tp.ContractError) as utf_ctx:
                tp.reject_sensitive(bad_utf8)
            self.assertEqual(utf_ctx.exception.code, "TWINLC-DOC-001")

        for name, bad_ref in (
            ("blueprintId", "bp-1\n"),
            ("artifact", "artifact:foo::bar"),
            ("artifact", "artifact:foo:..:bar"),
            ("artifact", "artifact:foo:.:bar"),
            ("artifact", "artifact:foo:"),
            ("twinRef", "twin://./item"),
            ("twinRef", "twin://../item"),
            ("twinRef", "twin://wellmanifest.com/a::b"),
            ("twinRef", "twin://wellmanifest.com/a:..:b"),
            ("actorRef", "actor://wellmanifest.com/op:..:v1"),
        ):
            with self.subTest(ref=bad_ref), self.assertRaises(tp.ContractError) as ref_ctx:
                tp.match(name, bad_ref)
            self.assertEqual(ref_ctx.exception.code, "TWINLC-REF-001")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real_dir = base / "real" / "nested"
            real_dir.mkdir(parents=True)
            doc_path = real_dir / "req.json"
            doc_path.write_text(json.dumps(self.req), encoding="utf-8")

            for bad_max in (0, -1, True, False):
                with self.assertRaises(tp.ContractError):
                    tp.read_regular_bytes(doc_path, max_bytes=bad_max)  # type: ignore[arg-type]

            sym_dir = base / "sym_dir"
            sym_dir.symlink_to(base / "real")
            deep_sym = sym_dir / "nested" / "req.json"
            with self.assertRaises(tp.ContractError) as sym_ctx:
                tp.read_regular_utf8(deep_sym)
            self.assertEqual(sym_ctx.exception.code, "TWINLC-TARGET-001")
            code_cli, report_cli = self._run_cli(str(sym_dir / "nested"))
            self.assertEqual(code_cli, 1)
            self.assertFalse(report_cli["ok"])


if __name__ == "__main__":
    unittest.main()
