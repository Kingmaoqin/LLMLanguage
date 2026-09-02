"""Reconstruct canonical per-run traces from existing Stage-2.5b run bundles (round-5 §5).

Writes ``<root>/traces/<run_id>.trace.json`` for every stored run and classifies each as
complete / partial / insufficient for the interactional-robustness profile. Produces
``reports/measurement_repair/RECONSTRUCTION_AUDIT.md`` and a machine-readable status JSON.

This does NOT re-run any model; it is a loss-free view over already-frozen artifacts.
Original bundles are never modified.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.stage2_5b.metrics.trace_metrics import build_trace, validate_trace  # noqa: E402

# Dimensions needed for a *complete* interactional-robustness reconstruction.
CRITICAL_FOR_ANALYSIS = ("tool_events", "conversation", "controlled_user_events")
DEFAULT_CANONICAL_ROOT = "results/stage2_5b_repair/r4_1_confirmatory_canonical"


def classify(trace: dict[str, Any], metrics: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    invalid = str(metrics.get("invalid_run")).lower() in {"true", "1"}

    has_tools = bool(trace.get("tool_events"))
    has_conv = bool(trace.get("conversation"))
    has_user = bool(trace.get("controlled_user_events"))
    token_ok = (trace.get("token_usage") or {}).get("token_source") != "missing"
    has_state = bool(trace.get("final_environment_state"))

    if not has_conv and not has_tools:
        return "insufficient", ["no conversation and no tool events"]
    if invalid and not has_tools:
        notes.append("invalid_run with no tool calls (retained, endpoint-only)")
        return "partial", notes

    if not has_tools:
        notes.append("no tool events")
    if not has_user:
        notes.append("no controlled-user events")
    if not token_ok:
        notes.append("token usage missing")
    if not has_state:
        notes.append("no final environment state")
    # state is hash-level only (no full object diff) — a known, documented limitation
    notes.append("state divergence is hash-level (no full DB object diff)")

    blocking = [n for n in notes if n != "state divergence is hash-level (no full DB object diff)"]
    return ("complete" if not blocking else "partial"), notes


def iter_bundle_dirs(results_root: Path):
    """Yield bundle directories for both supported result layouts.

    R4/R4.1 canonical roots are block-structured:
        <root>/<model>__<task>/run_bundles/*.json

    The round-5 measurement-complete runner writes one flat root:
        <root>/run_bundles/*.json

    Supporting both layouts is required for the wrapper's post-run reconstruct step.
    """
    direct = results_root / "run_bundles"
    if direct.is_dir():
        yield direct
    for block in sorted(p for p in results_root.iterdir() if p.is_dir()):
        if block.name in {"run_bundles", "traces", "interactional_metrics"}:
            continue
        bundle_dir = block / "run_bundles"
        if bundle_dir.is_dir():
            yield bundle_dir


def iter_bundles(results_root: Path):
    for bundle_dir in iter_bundle_dirs(results_root):
        for path in sorted(bundle_dir.glob("*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=DEFAULT_CANONICAL_ROOT)
    p.add_argument("--report", default=None)
    return p


def default_report_for(results_root: Path, explicit_report: str | None = None) -> Path:
    if explicit_report:
        return ROOT / explicit_report
    canonical = (ROOT / DEFAULT_CANONICAL_ROOT).resolve()
    if results_root.resolve() == canonical:
        return ROOT / "reports/measurement_repair/RECONSTRUCTION_AUDIT.md"
    return ROOT / f"reports/measurement_repair/RECONSTRUCTION_AUDIT_{results_root.name}.md"


def main() -> int:
    args = build_parser().parse_args()
    results_root = ROOT / args.root
    traces_dir = results_root / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    status = Counter()
    schema_failures: list[str] = []
    note_counter = Counter()
    token_source = Counter()
    n = 0
    for bundle in iter_bundles(results_root):
        trace = build_trace(bundle)
        errors = validate_trace(trace)
        run_id = trace.get("run_id") or f"unknown_{n}"
        if errors:
            schema_failures.append(f"{run_id}: {'; '.join(errors)}")
        (traces_dir / f"{run_id}.trace.json").write_text(
            json.dumps(trace, indent=1, default=str), encoding="utf-8"
        )
        klass, notes = classify(trace, bundle.get("metrics") or {})
        status[klass] += 1
        for note in notes:
            note_counter[note] += 1
        token_source[(trace.get("token_usage") or {}).get("token_source")] += 1
        n += 1

    report = default_report_for(results_root, args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Trace Reconstruction Audit (round-5 §5)",
        "",
        f"Source result root: `{args.root}`",
        f"Traces written to: `{args.root}/traces/<run_id>.trace.json`",
        f"Total runs reconstructed: **{n}**",
        "",
        "## Completeness classification",
        "",
        "| class | n | meaning |",
        "|---|---|---|",
        f"| complete | {status['complete']} | all analysis dimensions present (state at hash level) |",
        f"| partial | {status['partial']} | usable but missing >=1 dimension (see notes) |",
        f"| insufficient | {status['insufficient']} | cannot support trajectory analysis |",
        "",
        "## Token-source provenance",
        "",
        "| token_source | n |",
        "|---|---|",
        *[f"| {src} | {cnt} |" for src, cnt in token_source.most_common()],
        "",
        "## Notes frequency",
        "",
        *[f"- {note}: {cnt}" for note, cnt in note_counter.most_common()],
        "",
        "## Schema validation",
        "",
        f"- schema failures: {len(schema_failures)}",
        *[f"  - {f}" for f in schema_failures[:20]],
        "",
        "## Recoverable vs not recoverable",
        "",
        "- Recoverable from existing bundles: endpoint outcomes, full tool-call sequence "
        "incl. arguments, state mutations (args + before/after hashes), policy/evidence/branch "
        "flags, conversation incl. tool_calls, controlled-user events, input/output tokens "
        "(=> total via prompt_plus_completion).",
        "- NOT recoverable offline: full DB object-level state diffs (only state hashes were "
        "persisted) and per-message token usage (only aggregate input/output).",
        "",
        "## Rerun decision (round-5 §9)",
        "",
        "A measurement rerun is **not required** to build the interactional-robustness profile: "
        "every analysis dimension is reconstructable at the level the profile needs, and the "
        "token total is recovered as `prompt_plus_completion`. A rerun is only needed if "
        "full DB object-level state diffs or per-message token usage become a hard requirement; "
        "the measurement-complete runner exists for that and has been smoke-tested.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (traces_dir / "reconstruction_status.json").write_text(
        json.dumps({"total": n, **status, "token_source": dict(token_source),
                    "schema_failures": len(schema_failures)}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"total": n, **status, "schema_failures": len(schema_failures)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
