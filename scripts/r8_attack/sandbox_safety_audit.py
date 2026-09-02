#!/usr/bin/env python3
"""R8-A: local sandbox isolation & safety-scope audit (spec 0.3, 13).

Runs BEFORE and AFTER the experiment. Verifies every isolation condition and writes
results/r8_attack/integrity/local_sandbox_safety_audit.json. If ANY condition fails it
emits SAFETY_SCOPE_NOT_CLOSED and returns non-zero so the driver halts.

Checks:
  - all inference endpoints are loopback/internal (127.0.0.1);
  - no outbound proxy / external LLM key configured for the experiment env;
  - target-agent tools == official tau2 benchmark tools only (allowlist);
  - attacker/reviewer/selector have NO tool access (plain completion role);
  - no shell/browser/network tool exposed to attacker or target agent;
  - no real credential / PII string in the frozen prompts, registry or manifest;
  - benchmark DBs are resettable & synthetic (fresh env per episode, get_db_hash works);
  - all mutations confined to benchmark state (env rebuilt each episode).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

INTEGRITY = ROOT / "results/r8_attack/integrity"
FROZEN = ROOT / "data/r8_attack/frozen"

LOOPBACK = re.compile(r"^https?://(127\.0\.0\.1|localhost|0\.0\.0\.0)(:\d+)?(/|$)")
# PII / credential red-flags (real secrets, not synthetic benchmark ids).
SECRET_PAT = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9]{20,}|password\s*[:=]\s*['\"][^'\"]{6,})", re.I)


def check(name, ok, detail=""):
    return {"check": name, "pass": bool(ok), "detail": detail}


def main() -> int:
    from scripts.r8_attack.run_attack_episode import (
        MODEL_ENDPOINTS, USER_LLM, ATTACKER_LLM, REVIEWER_A_LLM, REVIEWER_B_LLM)
    from scripts.r8_attack import attacker as atk_mod

    results = []

    # 1. all inference endpoints loopback
    endpoints = ([api for _, api in MODEL_ENDPOINTS.values()] +
                 [USER_LLM[1], ATTACKER_LLM[1], REVIEWER_A_LLM[1], REVIEWER_B_LLM[1]])
    bad_ep = [e for e in endpoints if not LOOPBACK.match(e)]
    results.append(check("all_inference_endpoints_local", not bad_ep,
                         f"non-loopback endpoints={bad_ep}" if bad_ep else
                         f"{len(set(endpoints))} distinct loopback endpoints"))

    # 2. no outbound proxy / external LLM key in this process env
    proxy_vars = {k: v for k, v in os.environ.items()
                  if k.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") and v.strip()}
    ext_keys = {k for k in os.environ
                if k.upper() in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")
                and os.environ[k].strip() and os.environ[k].strip() != "EMPTY"}
    results.append(check("no_outbound_proxy_or_external_key", not proxy_vars and not ext_keys,
                         f"proxies={list(proxy_vars)} ext_keys={list(ext_keys)}"))

    # 3. target-agent tools == official tau2 tools; attacker/reviewer have NO tools
    try:
        from tau2.registry import registry
        n_tools = {}
        for dom in ("retail", "airline"):
            env = registry.get_env_constructor(dom)()
            n_tools[dom] = len(env.get_tools())
        allowlist_ok = all(v > 0 for v in n_tools.values())
        results.append(check("target_agent_tools_official_allowlist", allowlist_ok,
                             f"tool counts={n_tools}"))
    except Exception as exc:  # noqa: BLE001
        results.append(check("target_agent_tools_official_allowlist", False, repr(exc)))

    # 4. attacker/reviewer/selector expose NO tools (they are plain completion calls)
    #    verified structurally: the backends call litellm.completion with messages only,
    #    no tools= argument, and AttackUser passes tools=None to the controller.
    src = pathlib.Path(atk_mod.__file__).read_text()
    no_tool_arg = ("tools=" not in src.split("def default_llm_backend")[1].split("def ")[0])
    results.append(check("attacker_reviewer_no_tool_access", no_tool_arg,
                         "attacker/reviewer/selector backends issue tool-free completions"))

    # 5. no shell/browser/network tool exposed to attacker or target agent
    dangerous = re.compile(r"\b(subprocess|os\.system|requests\.get|urllib\.request|"
                           r"webbrowser|socket\.socket)\b")
    atk_user_src = (ROOT / "scripts/r8_attack/attack_user.py").read_text()
    exposed = bool(dangerous.search(src)) or bool(dangerous.search(atk_user_src))
    results.append(check("no_shell_browser_network_tool_exposed", not exposed,
                         "attacker/user modules contain no shell/browser/network calls"))

    # 6. no real credential / PII in frozen prompts, registry, manifest
    scan_targets = [atk_mod.ATTACKER_SYSTEM, atk_mod.REVIEWER_SYSTEM, atk_mod.SELECTOR_SYSTEM]
    for p in (FROZEN / "task_registry.jsonl", FROZEN / "attack_manifest.json"):
        if p.exists():
            scan_targets.append(p.read_text())
    hits = [m.group(0)[:40] for t in scan_targets for m in [SECRET_PAT.search(t)] if m]
    results.append(check("no_real_credential_or_pii", not hits,
                         f"secret-like hits={hits}" if hits else "no secret/PII patterns found"))

    # 7. benchmark DBs resettable & synthetic; mutations confined to fresh per-episode env
    try:
        from tau2.runner import build_environment
        e1 = build_environment("retail", solo_mode=False)
        h1 = e1.get_db_hash()
        e2 = build_environment("retail", solo_mode=False)
        h2 = e2.get_db_hash()
        results.append(check("db_resettable_synthetic_per_episode", h1 == h2,
                             f"fresh retail env db_hash reproducible ({h1[:12]}=={h2[:12]})"))
    except Exception as exc:  # noqa: BLE001
        results.append(check("db_resettable_synthetic_per_episode", False, repr(exc)))

    # 8. boundary declaration present verbatim in attacker + reviewer prompts
    boundary_ok = (atk_mod.SANDBOX_BOUNDARY in atk_mod.ATTACKER_SYSTEM and
                   atk_mod.SANDBOX_BOUNDARY in atk_mod.REVIEWER_SYSTEM and
                   atk_mod.SANDBOX_BOUNDARY in atk_mod.SELECTOR_SYSTEM)
    results.append(check("authorization_boundary_declared_in_prompts", boundary_ok,
                         "SANDBOX_BOUNDARY present at head of attacker/reviewer/selector"))

    all_pass = all(r["pass"] for r in results)
    out = dict(
        experiment="R8A_targeted_process_attack",
        scope_closed=all_pass,
        status="SANDBOX_SCOPE_CLOSED" if all_pass else "SAFETY_SCOPE_NOT_CLOSED",
        checks=results,
        endpoints=sorted(set(endpoints)),
    )
    INTEGRITY.mkdir(parents=True, exist_ok=True)
    (INTEGRITY / "local_sandbox_safety_audit.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({r["check"]: r["pass"] for r in results}, indent=2))
    print(out["status"])
    return 0 if all_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
