#!/usr/bin/env python3
"""Build the two benchmark adapters from the frozen model roster + ledgers."""
from __future__ import annotations

import pathlib
from typing import Any

from scripts.r9_attack.common import paths
from scripts.r9_attack.common.llm_client import load_endpoints


def build_adapters(
    models_path: pathlib.Path = paths.CONFIGS / "models.json",
    ledger_path: pathlib.Path = paths.FACT_LEDGERS,
    *,
    max_step_limit: int = 20,
    include_toolsandbox: bool = True,
) -> dict[str, Any]:
    """Return {"bfcl": BfclAdapter, "toolsandbox": ToolSandboxAdapter?, "endpoints": {...}}."""
    from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter

    endpoints = load_endpoints(models_path)
    out: dict[str, Any] = {"endpoints": endpoints}
    out["bfcl"] = BfclAdapter(endpoints=endpoints, max_step_limit=max_step_limit)
    if include_toolsandbox:
        from scripts.r9_attack.adapters.toolsandbox_adapter import ToolSandboxAdapter

        ts = ToolSandboxAdapter(endpoints=endpoints, ledger_path=ledger_path)
        out["toolsandbox"] = ts
    return out
