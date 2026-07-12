"""Crash-safe, hash-chained, append-only MVEP raw trace storage."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


ALLOWED_EVENTS = {
    "RUN_CREATED", "PREFIX_CAPTURED", "JUNCTION_PROOF", "CALL_PREPARED",
    "CALL_RESPONSE", "CALL_EXCEPTION", "TOOL_RESPONSE", "SCORER_RESULT",
    "TRACE_MATERIALIZED", "RECOVERY_DECLARED", "TERMINAL",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode())


def _exclusive_write(path: Path, body: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(fd, body)
        os.fsync(fd)
    finally:
        os.close(fd)


class TraceStore:
    """Every state transition is a new immutable JSON file.

    A crashed run may be reopened only after validating the full hash chain. Recovery
    appends an explicit marker and never alters an earlier event.
    """

    def __init__(self, root: Path, events: list[dict[str, Any]]):
        self.root = root
        self.events = events

    @classmethod
    def create(cls, root: Path, identity: dict[str, Any], manifest_hash: str) -> "TraceStore":
        root.mkdir(parents=False, exist_ok=False)
        store = cls(root, [])
        store.append("RUN_CREATED", {"identity": identity, "manifest_hash": manifest_hash})
        return store

    @classmethod
    def recover(cls, root: Path, reason: str) -> "TraceStore":
        events = cls.read_and_validate(root)
        if events[-1]["event"] == "TERMINAL":
            raise RuntimeError("terminal_trace_cannot_resume")
        store = cls(root, events)
        store.append("RECOVERY_DECLARED", {"reason": reason,
                                            "recovered_after_event": events[-1]["event"]})
        return store

    @staticmethod
    def read_and_validate(root: Path) -> list[dict[str, Any]]:
        paths = sorted(root.glob("[0-9][0-9][0-9][0-9]_*.json"))
        if not paths:
            raise RuntimeError("empty_trace_root")
        events, previous = [], None
        for index, path in enumerate(paths):
            if not path.name.startswith(f"{index:04d}_"):
                raise RuntimeError("non_contiguous_trace_sequence")
            record = json.loads(path.read_text())
            stored_hash = record.pop("record_hash", None)
            if record.get("sequence") != index or record.get("previous_hash") != previous:
                raise RuntimeError("trace_chain_link_failure")
            actual = sha256_value(record)
            if stored_hash != actual:
                raise RuntimeError("trace_record_hash_failure")
            record["record_hash"] = stored_hash
            events.append(record)
            previous = stored_hash
        return events

    def append(self, event: str, payload: dict[str, Any]) -> Path:
        if event not in ALLOWED_EVENTS:
            raise ValueError("unknown_trace_event")
        if self.events and self.events[-1]["event"] == "TERMINAL":
            raise RuntimeError("terminal_trace_is_immutable")
        sequence = len(self.events)
        previous = self.events[-1]["record_hash"] if self.events else None
        record = {"sequence": sequence, "event": event, "previous_hash": previous,
                  "payload": payload}
        record["record_hash"] = sha256_value(record)
        path = self.root / f"{sequence:04d}_{event}.json"
        _exclusive_write(path, (canonical_json(record) + "\n").encode())
        self.events.append(record)
        return path

    def materialize(self, trace: dict[str, Any]) -> Path:
        path = self.root / "raw_trace.json"
        _exclusive_write(path, (canonical_json(trace) + "\n").encode())
        self.append("TRACE_MATERIALIZED", {"path": path.name,
                                            "sha256": sha256_bytes(path.read_bytes())})
        return path

    def terminal(self, status: str) -> None:
        self.append("TERMINAL", {"status": status})


def trace_complete(trace: dict[str, Any]) -> tuple[bool, list[str]]:
    required = {
        "schema_version", "identity", "manifest_hash", "environment_lock_hash",
        "rendered_messages", "input_hash", "assistant_messages", "tool_calls",
        "tool_responses", "db", "scorer", "tokens", "timing", "retry",
        "code_environment_model_hashes", "junction_proof",
    }
    missing = sorted(required - set(trace))
    if trace.get("retry", {}).get("silent_retry"):
        missing.append("retry.silent_retry_must_be_false")
    for key in ("input", "output", "tool", "total"):
        if trace.get("tokens", {}).get(key) is None:
            missing.append(f"tokens.{key}")
    return not missing, missing

