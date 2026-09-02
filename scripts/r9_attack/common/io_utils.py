#!/usr/bin/env python3
"""R9 IO + hashing helpers (spec 5, 7, 18).

Every frozen artifact is written atomically and hashed with the same canonical JSON
serialisation, so `split_hashes.sha256` / `attacker_hashes.sha256` are reproducible
across machines and across the production and reference implementations.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any, Iterable, Iterator


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no ASCII escaping, compact separators."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_atomic(path: pathlib.Path, text: str) -> pathlib.Path:
    """Write via a temp file + rename so a crash never leaves a half-written artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def write_json(path: pathlib.Path, obj: Any, *, indent: int = 2) -> pathlib.Path:
    return write_atomic(path, json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: pathlib.Path, rows: Iterable[Any]) -> pathlib.Path:
    return write_atomic(path, "".join(canonical_json(r) + "\n" for r in rows))


def append_jsonl(path: pathlib.Path, row: Any) -> None:
    """Append one record. Used by episode drivers; not atomic by design (append-only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(canonical_json(row) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: pathlib.Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_json(path: pathlib.Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_sha256_manifest(path: pathlib.Path, files: Iterable[pathlib.Path]) -> pathlib.Path:
    """sha256sum-compatible manifest, paths relative to the repo root."""
    from scripts.r9_attack.common.paths import ROOT

    lines = []
    for f in sorted(files):
        rel = f.relative_to(ROOT) if f.is_absolute() else f
        lines.append(f"{sha256_file(f)}  {rel}")
    return write_atomic(path, "\n".join(lines) + "\n")


def git_commit() -> str:
    """Current HEAD, with a `-dirty` suffix when the tree has uncommitted changes."""
    from scripts.r9_attack.common.paths import ROOT

    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        return head + ("-dirty" if dirty else "")
    except Exception:  # pragma: no cover - only when git is unavailable
        return "unknown"
