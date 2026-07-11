"""Shared helpers for R7 IPMA measurement-repair and smoke scripts.

The helpers are intentionally dependency-light.  R7 scripts must be able to run
on existing R6 trace/metric artifacts before any new full experiment is approved.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


MISSING = "MISSING"
UNAVAILABLE = "UNAVAILABLE"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_traces(root: Path) -> Iterable[Path]:
    trace_dir = root / "traces"
    if trace_dir.exists():
        yield from sorted(trace_dir.glob("*.trace.json"))
        return
    yield from sorted(root.glob("**/*.trace.json"))


def trace_meta(trace: dict[str, Any]) -> dict[str, Any]:
    meta = dict(trace.get("run_meta") or {})
    if "run_id" not in meta:
        meta["run_id"] = trace.get("run_id") or ""
    return meta


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def list_join(values: Any) -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        return values
    if isinstance(values, list):
        return " ".join(str(v) for v in values)
    return str(values)


def tool_sequence(trace: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for event in trace.get("tool_events") or []:
        name = event.get("tool_name") or event.get("name") or event.get("tool")
        if name:
            out.append(str(name))
    return out


def count_mutations(trace: dict[str, Any]) -> int:
    n = 0
    for event in trace.get("tool_events") or []:
        mt = str(event.get("mutation_type") or "").lower()
        if event.get("mutated") is True or mt in {"write", "mutation", "mutate"}:
            n += 1
    return n


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def status_word(ok: bool) -> str:
    return "PASS" if ok else "FAIL"

