#!/usr/bin/env python3
"""Build + freeze ToolSandbox Fact Ledgers (spec 7.2).

For each selected scenario, run the neutral LLM pre-pass once (via the r9_ts worker) and
freeze the User Fact Ledger: the mapping from each agent information request to a single
canonical response, plus identity/task facts, decisions, confirmation content and
termination state. Every condition later returns the SAME canonical response for the same
slot; the attack may only wrap style around it. Frozen to
`data/r9_attack/frozen/toolsandbox_fact_ledgers.jsonl`.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.adapters.toolsandbox_adapter import ToolSandboxAdapter  # noqa: E402
from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import read_jsonl, sha256_obj, write_jsonl  # noqa: E402
from scripts.r9_attack.common.llm_client import load_endpoints  # noqa: E402


def build_ledgers(
    scenarios: list[str],
    *,
    models_path: pathlib.Path,
    user_sim_alias: str,
    agent_alias: str | None = None,
    seed: int = 0,
    prepass_max_user_turns: int = 6,
    prepass_timeout_s: int = 120,
    max_agent_steps: int = 16,
) -> list[dict]:
    endpoints = load_endpoints(models_path)
    adapter = ToolSandboxAdapter(endpoints=endpoints, user_sim_alias=user_sim_alias)
    ledgers = []
    for scenario in scenarios:
        led = adapter.build_ledger(
            scenario,
            user_sim_alias=user_sim_alias,
            agent_alias=agent_alias,
            seed=seed,
            prepass_max_messages=30,
            prepass_max_user_turns=prepass_max_user_turns,
            prepass_timeout_s=prepass_timeout_s,
            max_agent_steps=max_agent_steps,
        )
        led["ledger_hash"] = sha256_obj(led["slots"])
        ledgers.append(led)
        pre = led.get("prepass", {})
        print(f"[ledger] {scenario}: {len(led['slots'])} slots, "
              f"milestone_sim={pre.get('milestone_similarity')}, calls={pre.get('n_tool_calls')}")
    return ledgers


def freeze(ledgers: list[dict], path: pathlib.Path = paths.FACT_LEDGERS) -> pathlib.Path:
    paths.ensure_dirs()
    return write_jsonl(path, ledgers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build + freeze ToolSandbox fact ledgers (spec 7.2)")
    parser.add_argument("--models", default=str(paths.CONFIGS / "models.json"))
    parser.add_argument("--user-sim", default="mistral_small_3p2")
    parser.add_argument("--agent", default=None, help="agent alias for the pre-pass (default: same as user-sim)")
    parser.add_argument("--scenarios", nargs="*", help="explicit scenario names")
    parser.add_argument("--from-eligible", type=int, default=0, help="take first N eligible multi-user-turn scenarios")
    parser.add_argument("--out", default=str(paths.FACT_LEDGERS))
    parser.add_argument("--append", action="store_true", help="merge with existing frozen ledgers")
    parser.add_argument("--max-agent-steps", type=int, default=16)
    parser.add_argument("--prepass-timeout", type=int, default=120)
    args = parser.parse_args()

    endpoints = load_endpoints(pathlib.Path(args.models))
    scenarios = list(args.scenarios or [])
    if args.from_eligible:
        adapter = ToolSandboxAdapter(endpoints=endpoints)
        eligible = adapter.list_scenarios(only_eligible=True)
        mu = [s["scenario"] for s in eligible if "MULTIPLE_USER_TURN" in s["categories"]]
        scenarios += mu[: args.from_eligible]
    if not scenarios:
        print("[ledger] no scenarios specified", file=sys.stderr)
        return 2

    ledgers = build_ledgers(
        scenarios,
        models_path=pathlib.Path(args.models),
        user_sim_alias=args.user_sim,
        agent_alias=args.agent,
        prepass_timeout_s=args.prepass_timeout,
        max_agent_steps=args.max_agent_steps,
    )
    if args.append:
        existing = {r["scenario"]: r for r in read_jsonl(pathlib.Path(args.out))}
        for led in ledgers:
            existing[led["scenario"]] = led
        ledgers = list(existing.values())
    out = freeze(ledgers, pathlib.Path(args.out))
    print(f"[ledger] froze {len(ledgers)} ledgers -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
