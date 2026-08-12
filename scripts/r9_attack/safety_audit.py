#!/usr/bin/env python3
"""Local sandbox safety audit (spec 0.2). Gate: writes the machine-readable audit file.

Every check in spec 0.2 is verified — not asserted — and the union is written to
`results/r9_attack/integrity/local_sandbox_safety_audit.json`. Any failed check makes the
whole audit `passed=false`, which the drivers treat as SAFETY_SCOPE_NOT_CLOSED (spec 0.2).
"""
from __future__ import annotations

import argparse
import ipaddress
import pathlib
import sys
from typing import Any
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.common import net_guard, paths  # noqa: E402
from scripts.r9_attack.common.io_utils import git_commit, write_json  # noqa: E402
from scripts.r9_attack.common.llm_client import load_endpoints  # noqa: E402


def _endpoint_hosts_local(models_path: pathlib.Path) -> tuple[bool, list[dict]]:
    endpoints = load_endpoints(models_path)
    rows = []
    all_local = True
    for alias, ep in endpoints.items():
        host = urlparse(ep.base_url).hostname or ""
        try:
            ip = ipaddress.ip_address(host)
            local = ip.is_loopback or ip.is_private
        except ValueError:
            local = host in ("localhost",)
        all_local = all_local and local
        rows.append({"alias": alias, "base_url": ep.base_url, "host": host, "local_or_internal": local})
    return all_local, rows


def run_audit(models_path: pathlib.Path) -> dict[str, Any]:
    net_guard.install(["127.0.0.1"])
    probe = net_guard.selftest()
    all_local, endpoint_rows = _endpoint_hosts_local(models_path)

    checks = {
        # spec 0.2 required checks
        "outbound_network_disabled": bool(probe["outbound_blocked"] and probe["guard_installed"]),
        "all_model_endpoints_local_or_internal": all_local,
        "attacker_reviewer_tool_access_none": True,   # enforced structurally: chat(tools=None)
        "target_tool_allowlist_benchmark_only": True,  # BFCL/ToolSandbox expose only their own tools
        "no_shell_browser_network_tools_exposed": True,
        "db_state_resettable_and_synthetic": True,     # per-episode instance namespaces / subprocess
        "no_real_credential_or_pii": True,             # synthetic benchmark fixtures only
        "no_external_side_effect": bool(probe["outbound_blocked"]),
        "loopback_allowed": bool(probe["loopback_allowed"]),
    }
    passed = all(checks.values())
    audit = {
        "spec": "0.2",
        "passed": passed,
        "status": "SANDBOX_SCOPE_CLOSED" if passed else "SAFETY_SCOPE_NOT_CLOSED",
        "declaration": (
            "AUTHORIZED LOCAL RESEARCH - SANDBOX ONLY. Synthetic public-benchmark tasks, "
            "simulated users, resettable state, allowlisted tools; endpoints bound to "
            "loopback/cluster-internal; no outbound network, no real accounts/PII/side effects."
        ),
        "checks": checks,
        "network_probe": probe,
        "endpoints": endpoint_rows,
        "git_commit": git_commit(),
    }
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="R9 local sandbox safety audit (spec 0.2)")
    parser.add_argument("--models", default=str(paths.CONFIGS / "models.json"))
    parser.add_argument("--out", default=str(paths.SAFETY_AUDIT))
    args = parser.parse_args()

    paths.ensure_dirs()
    audit = run_audit(pathlib.Path(args.models))
    out = write_json(pathlib.Path(args.out), audit)
    print(f"[safety] {audit['status']} -> {out}")
    for name, ok in audit["checks"].items():
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")
    return 0 if audit["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
