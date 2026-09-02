#!/usr/bin/env python3
"""Extract token, duration and latency metrics from R6/R7 traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import MISSING, as_float, ensure_dir, iter_traces, load_json, trace_meta, write_csv


FIELDS = [
    "run_id", "model_alias", "task_id", "condition_id", "seed", "domain",
    "input_tokens", "output_tokens", "tokens_total", "token_source",
    "duration_s", "duration_source", "first_tool_latency_s", "latency_source",
    "avg_tool_latency_s", "n_tool_events", "n_retries", "n_invalid_tool_calls",
]


def _num(value: Any) -> str:
    if value is None or value == "":
        return MISSING
    return str(value)


def token_usage(trace: dict[str, Any]) -> tuple[Any, Any, Any, str]:
    usage = trace.get("token_usage") or trace.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    total = usage.get("tokens_total") or usage.get("total_tokens") or usage.get("reported_total")
    inp = usage.get("input_tokens") or usage.get("prompt_tokens")
    out = usage.get("output_tokens") or usage.get("completion_tokens")
    if total not in (None, ""):
        return inp, out, total, str(usage.get("token_source") or "reported_total")
    fi, fo = as_float(inp), as_float(out)
    if fi is not None and fo is not None:
        return inp, out, int(fi + fo), "prompt_plus_completion"
    return MISSING, MISSING, MISSING, "missing"


def timing(trace: dict[str, Any]) -> tuple[str, str, str, str]:
    meta = trace_meta(trace)
    duration = meta.get("duration_s")
    source = "run_meta.duration_s" if duration not in (None, "") else "missing_no_timestamp"
    tool_events = trace.get("tool_events") or []
    latencies = []
    for event in tool_events:
        for key in ("latency_s", "duration_s", "elapsed_s"):
            val = as_float(event.get(key))
            if val is not None:
                latencies.append(val)
                break
    first = latencies[0] if latencies else MISSING
    avg = (sum(latencies) / len(latencies)) if latencies else MISSING
    lat_source = "tool_event_latency" if latencies else "missing_no_timestamp"
    return _num(duration), source, _num(first), lat_source if first != MISSING else "missing_no_timestamp", _num(avg)


def process(root: Path, out_dir: Path, report_path: Path) -> tuple[int, int, int]:
    rows: list[dict[str, Any]] = []
    token_missing = 0
    timing_missing = 0
    for path in iter_traces(root):
        trace = load_json(path)
        meta = trace_meta(trace)
        inp, out, total, token_source = token_usage(trace)
        duration, duration_source, first_lat, latency_source, avg_lat = timing(trace)
        if total == MISSING:
            token_missing += 1
        if duration == MISSING:
            timing_missing += 1
        tool_events = trace.get("tool_events") or []
        invalid = sum(1 for e in tool_events if e.get("valid_json") is False or e.get("undefined_tool") is True or e.get("tool_error") is True)
        retries = max(0, len(tool_events) - len({(e.get("tool_name"), json.dumps(e.get("arguments", {}), sort_keys=True, ensure_ascii=False)) for e in tool_events}))
        rows.append(
            {
                "run_id": meta.get("run_id", ""),
                "model_alias": meta.get("model_alias", ""),
                "task_id": meta.get("task_id", ""),
                "condition_id": meta.get("condition_id", ""),
                "seed": meta.get("seed", ""),
                "domain": meta.get("domain", ""),
                "input_tokens": _num(inp),
                "output_tokens": _num(out),
                "tokens_total": _num(total),
                "token_source": token_source,
                "duration_s": duration,
                "duration_source": duration_source,
                "first_tool_latency_s": first_lat,
                "latency_source": latency_source,
                "avg_tool_latency_s": avg_lat,
                "n_tool_events": len(tool_events),
                "n_retries": retries,
                "n_invalid_tool_calls": invalid,
            }
        )
    ensure_dir(out_dir)
    write_csv(out_dir / "usage_timing_metrics.csv", rows, FIELDS)
    n = len(rows)
    token_missing_rate = token_missing / n if n else 0.0
    duration_missing_rate = timing_missing / n if n else 0.0
    # PDF §2.2 规则 7：任一缺失率超过 10% 时，必须声明不能做 efficiency claim。
    efficiency_claim_blocked = token_missing_rate > 0.10 or duration_missing_rate > 0.10
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# R6 token/duration/latency 修复报告",
        "",
        f"- 输入根目录：`{root}`",
        f"- trace 数：{n}",
        f"- token 缺失：{token_missing}（缺失率 {token_missing_rate:.1%}）",
        f"- duration 缺失：{timing_missing}（缺失率 {duration_missing_rate:.1%}）",
        f"- 输出：`{out_dir / 'usage_timing_metrics.csv'}`",
        "",
        "提取优先级：provider reported total / prompt+completion / missing。缺失值使用 `MISSING`，timestamp 缺失使用 `missing_no_timestamp`，避免空字符串进入后续统计。",
    ]
    if efficiency_claim_blocked:
        lines += [
            "",
            "> ⚠️ PDF §2.2 规则 7：token 或 duration 缺失率超过 10%，**不能做 efficiency / latency claim**。"
            "当前 tau2 traces 缺 provider usage 与 timestamp，R7 runner 必须写入 usage/timing 后方可对这部分做效率结论。",
        ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n, token_missing, timing_missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results_root", type=Path, default=ROOT / "results/r6_sensitivity/full_main_seq_eligible_20260626")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results/r7_ipma/measurement_repair")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R6_TOKEN_DURATION_REPAIR_CN.md")
    args = ap.parse_args()
    n, tm, dm = process(args.results_root, args.out_dir, args.report)
    print(json.dumps({"traces": n, "token_missing": tm, "duration_missing": dm}, ensure_ascii=False))


if __name__ == "__main__":
    main()

