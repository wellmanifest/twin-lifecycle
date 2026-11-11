#!/usr/bin/env python3
"""Bounded regular-file I/O, strict JSON/UTF-8, and secret-scanning helpers for twin-lifecycle."""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_INT_DIGITS = 400
MAX_JSON_INT_ABS = 10**MAX_JSON_INT_DIGITS - 1

SENSITIVE = re.compile(
    r"(?:shell|argv|command|password|passwd|token|secret|credential|api[-_]?key|cookie|"
    r"private[-_]?key|remote|url|score|proposal|simulation|verdict|prompt)",
    re.I,
)
SECRET_MATERIAL = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRI"
    r"VATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{20,}|"
    r"\bAK"
    r"IA[0-9A-Z]{16}\b|"
    r"(?:password|passwd|token|secret|api[-_]?key)\s*[:=]\s*[^\s,;]{4,})",
    re.I,
)
SAFE_ASSERTIONS = {"secretsRedacted"}


class ContractError(ValueError):
    """A bounded rejection that never repeats untrusted document content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def is_valid_utf8(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def has_symlink_ancestor(path: Path) -> bool:
    raw = os.fspath(path)
    raw_parts = Path(raw).parts
    start_idx = 3 if os.path.isabs(raw) else 1
    for idx in range(start_idx, len(raw_parts)):
        prefix = Path(*raw_parts[:idx])
        if prefix.parts and all(part in {".", ".."} for part in prefix.parts):
            continue
        try:
            if stat.S_ISLNK(os.lstat(prefix).st_mode):
                return True
        except FileNotFoundError:
            break
        except OSError:
            return True
    normalized = Path(os.path.abspath(raw))
    for anc in normalized.parents:
        if len(anc.parts) <= 2:
            continue
        try:
            if stat.S_ISLNK(os.lstat(anc).st_mode):
                return True
        except FileNotFoundError:
            continue
        except OSError:
            return True
    return False


def bounded_intent(value: Any, label: str = "intent") -> str:
    if (
        not isinstance(value, str)
        or not is_valid_utf8(value)
        or not value.strip()
        or len(value) > 240
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
        raise ContractError("TWINLC-DOC-001", f"invalid {label}")
    return value


def _check_json_scalar(value: Any) -> None:
    if isinstance(value, str) and not is_valid_utf8(value):
        raise ContractError("TWINLC-DOC-001", "invalid UTF-8 surrogate in JSON string")
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("TWINLC-DOC-001", "non-finite JSON float is forbidden")
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > MAX_JSON_INT_ABS:
        raise ContractError("TWINLC-DOC-001", "JSON integer out of range")


def _enforce_json_bounds(root: Any, *, max_depth: int = MAX_JSON_DEPTH) -> None:
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise ContractError("TWINLC-DOC-001", "JSON nesting depth exceeded")
        if isinstance(current, dict):
            next_depth = depth + 1
            if next_depth > max_depth and current:
                raise ContractError("TWINLC-DOC-001", "JSON nesting depth exceeded")
            for key, child in current.items():
                if not isinstance(key, str) or not is_valid_utf8(key):
                    raise ContractError(
                        "TWINLC-DOC-001", "JSON object key must be valid UTF-8 text"
                    )
                if isinstance(child, (dict, list)):
                    stack.append((child, next_depth))
                else:
                    _check_json_scalar(child)
        elif isinstance(current, list):
            next_depth = depth + 1
            if next_depth > max_depth and current:
                raise ContractError("TWINLC-DOC-001", "JSON nesting depth exceeded")
            for child in current:
                if isinstance(child, (dict, list)):
                    stack.append((child, next_depth))
                else:
                    _check_json_scalar(child)
        else:
            _check_json_scalar(current)


def read_regular_bytes(
    path: str | Path,
    *,
    max_bytes: int = MAX_INPUT_BYTES,
    error_code: str = "TWINLC-DOC-001",
) -> bytes:
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise ContractError("TWINLC-DOC-001", "max_bytes must be a positive integer")
    path_obj = Path(os.fspath(path))
    if has_symlink_ancestor(path_obj):
        raise ContractError("TWINLC-TARGET-001", "symbolic link target is forbidden")
    raw_path = os.fspath(path_obj)
    try:
        st = os.lstat(raw_path)
    except OSError as err:
        raise ContractError(error_code, "target path cannot be read") from err
    if stat.S_ISLNK(st.st_mode):
        raise ContractError("TWINLC-TARGET-001", "symbolic link target is forbidden")
    if not stat.S_ISREG(st.st_mode):
        raise ContractError(error_code, "input must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(raw_path, flags)
    except OSError as err:
        if err.errno == errno.ELOOP:
            raise ContractError("TWINLC-TARGET-001", "symbolic link target is forbidden") from err
        raise ContractError(error_code, "target path cannot be opened") from err
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode) or (st.st_dev, st.st_ino) != (fst.st_dev, fst.st_ino):
            raise ContractError(error_code, "input must be an unchanged regular file")
        if fst.st_size > max_bytes:
            raise ContractError("TWINLC-DOC-001", "JSON document exceeds maximum size")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ContractError("TWINLC-DOC-001", "JSON document exceeds maximum size")
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_regular_utf8(
    path: str | Path,
    *,
    max_bytes: int = MAX_INPUT_BYTES,
    error_code: str = "TWINLC-DOC-001",
) -> str:
    raw = read_regular_bytes(path, max_bytes=max_bytes, error_code=error_code)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise ContractError("TWINLC-DOC-001", "invalid UTF-8 JSON document") from err


def strict_loads(raw: str) -> Any:
    if not isinstance(raw, str) or not is_valid_utf8(raw):
        raise ContractError("TWINLC-DOC-001", "JSON input must be valid UTF-8 text")
    if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ContractError("TWINLC-DOC-001", "JSON document exceeds maximum size")

    def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, val in pairs:
            if not isinstance(key, str):
                raise ContractError("TWINLC-DOC-001", "JSON object key must be a string")
            if key in obj:
                raise ContractError("TWINLC-DOC-001", "duplicate JSON key")
            obj[key] = val
        return obj

    def _reject_constant(token: str) -> Any:
        raise ContractError("TWINLC-DOC-001", "non-finite JSON constant is forbidden")

    def _parse_finite_float(token: str) -> float:
        parsed = float(token)
        if not math.isfinite(parsed):
            raise ContractError("TWINLC-DOC-001", "JSON float out of finite IEEE-754 range")
        return parsed

    def _parse_bounded_int(token: str) -> int:
        digits = token[1:] if token.startswith(("+", "-")) else token
        if len(digits) > MAX_JSON_INT_DIGITS:
            raise ContractError("TWINLC-DOC-001", "JSON integer out of range")
        parsed = int(token)
        if abs(parsed) > MAX_JSON_INT_ABS:
            raise ContractError("TWINLC-DOC-001", "JSON integer out of range")
        return parsed

    try:
        data = json.loads(
            raw,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
            parse_int=_parse_bounded_int,
        )
    except ContractError:
        raise
    except RecursionError as err:
        raise ContractError("TWINLC-DOC-001", "JSON nesting depth exceeded") from err
    except ValueError as err:
        raise ContractError("TWINLC-DOC-001", "invalid JSON document") from err
    _enforce_json_bounds(data)
    return data


def canonical(value: Any) -> bytes:
    _enforce_json_bounds(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    if not isinstance(value, (bytes, bytearray)):
        raise ContractError("TWINLC-DOC-001", "digest input must be bytes")
    return hashlib.sha256(value).hexdigest()


def reject_sensitive(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ContractError("TWINLC-DOC-001", "JSON nesting depth exceeded")
        if isinstance(current, dict):
            for key, nested in current.items():
                if not isinstance(key, str) or not is_valid_utf8(key):
                    raise ContractError(
                        "TWINLC-DOC-001", "JSON object key must be valid UTF-8 text"
                    )
                if key not in SAFE_ASSERTIONS and SENSITIVE.search(key):
                    raise ContractError("TWINLC-SECRET-001", "unsafe key")
                if SECRET_MATERIAL.search(key):
                    raise ContractError("TWINLC-SECRET-001", "credential material is forbidden")
                stack.append((nested, depth + 1))
        elif isinstance(current, list):
            for nested in current:
                stack.append((nested, depth + 1))
        elif isinstance(current, str):
            if not is_valid_utf8(current):
                raise ContractError("TWINLC-DOC-001", "invalid UTF-8 surrogate in JSON string")
            if SECRET_MATERIAL.search(current):
                raise ContractError("TWINLC-SECRET-001", "credential material is forbidden")
