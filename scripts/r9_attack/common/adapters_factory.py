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
    bfcl_categories: list[str] | None = None,
    include_tau2: bool = False,
    tau2_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Return {"bfcl": BfclAdapter, "toolsandbox"?, "tau2"?, "endpoints": {...}}.

    R9v1 uses bfcl (base only) + toolsandbox. R9v2 (pre-registered redesign) uses bfcl-deep
    (base + miss_param via `bfcl_categories`) + tau2 (airline/retail via `include_tau2`), and
    drops toolsandbox — see reports/r9_attack/R9v2_PREREGISTRATION_CN.md.
    """
    from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter

    endpoints = load_endpoints(models_path)
    out: dict[str, Any] = {"endpoints": endpoints}
    out["bfcl"] = BfclAdapter(endpoints=endpoints, max_step_limit=max_step_limit,
                              categories=bfcl_categories)
    if include_toolsandbox:
        from scripts.r9_attack.adapters.toolsandbox_adapter import ToolSandboxAdapter

        out["toolsandbox"] = ToolSandboxAdapter(endpoints=endpoints, ledger_path=ledger_path)
    if include_tau2:
        from scripts.r9_attack.adapters.tau2_adapter import Tau2Adapter

        out["tau2"] = Tau2Adapter(endpoints=endpoints, domains=tau2_domains)
    return out
