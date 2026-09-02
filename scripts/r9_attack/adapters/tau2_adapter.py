#!/usr/bin/env python3
"""R9v2 tau2-bench adapter (r9_bfcl side). Drives `tau2_worker.py` in the tau2 venv, one
subprocess per call, and speaks the benchmark-agnostic TaskSpec / EpisodeRecord contract.

Unlike the ToolSandbox adapter, the tau2 worker runs the WHOLE episode self-contained: the
process attack is serialized into an `attack_spec` (frozen per condition/family) and applied
inside the worker's ScriptedLedgerUser, so no per-turn bidirectional streaming is needed.
Confirmatory uses the frozen attacker (spec 8.6), which is exactly this deterministic
serialized policy.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Callable, Optional

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.adapters.base import TaskSpec  # noqa: E402
from scripts.r9_attack.common.episode_schema import (  # noqa: E402
    EndpointResult,
    EpisodeRecord,
    InterventionRecord,
    ToolCallRecord,
    TurnRecord,
    block_id,
    episode_id,
)
from scripts.r9_attack.common.io_utils import sha256_text  # noqa: E402
from scripts.r9_attack.common.llm_client import Endpoint  # noqa: E402

DEFAULT_TAU2_PYTHON = os.environ.get("R9_TAU2_PYTHON", "/home/xqin5/tau2_venv/bin/python")
TAU2_DATA_DIR = os.environ.get("TAU2_DATA_DIR", "/home/xqin5/tau2-bench/data")
WORKER = ROOT / "scripts" / "r9_attack" / "adapters" / "tau2_worker.py"


class Tau2Unavailable(RuntimeError):
    pass


# --------------------------------------------------------------------------- attack spec
def build_attack_spec(condition: str, family: str) -> dict:
    """Serialize the R9 process attack for (condition, family) into per-condition framing.

    Frozen and deterministic (spec 8.6). C0 neutral; C1/C2 matched-neutral prefixes; C3 generic
    static pressure; C5 the explicit positive control. The FIRST turn is always neutral (spec 2)
    — enforced by the worker.

    IMPORTANT (R9v2 audit fix, option-b): tau2 runs the attack as a SUBPROCESS with a scripted
    user; it CANNOT invoke the live per-turn AttackController the way BFCL does. So tau2 is a
    STATIC-PRESSURE arm only. C4 here is therefore NOT adaptive — it reuses the strongest static
    tactic and is explicitly marked `adaptive=False`, `tactic="c4_static_tau2"`. The analysis
    layer MUST NOT treat tau2's C4 as an adaptive/optimised attack, must not read a fake
    adaptive-share from it, and must not pool tau2's C4-C3 into the cross-benchmark
    adaptive-effect test. The real adaptive attacker (AttackController) remains BFCL-only.
    The previous code (a) imported generic_c3_candidate from the wrong module so the fallback
    ran every time, and (b) marked C4 adaptive=True unconditionally (fake adaptivity). Both fixed.
    """
    # Loud imports: a broken import must FAIL, never silently substitute different attack text.
    from scripts.r9_attack.attack_families import C5_PROCESS_INSTRUCTION
    from scripts.r9_attack.candidate_generator import generic_c3_candidate
    from scripts.r9_attack.attacker import NEUTRAL_A_PREFIX, NEUTRAL_B_PREFIX

    c3 = generic_c3_candidate(family)
    c3_prefix, c3_suffix = c3.prefix, c3.suffix
    c5_suffix = C5_PROCESS_INSTRUCTION[family]
    na, nb = NEUTRAL_A_PREFIX, NEUTRAL_B_PREFIX
    return {
        "C1": {"prefix": na, "suffix": "", "non_neutral": False, "tactic": "matched_neutral_C1"},
        "C2": {"prefix": nb, "suffix": "", "non_neutral": False, "tactic": "matched_neutral_C2"},
        "C3": {"prefix": c3_prefix, "suffix": c3_suffix, "non_neutral": True, "adaptive": False,
               "tactic": "generic_pressure"},
        # tau2 C4 == C3 static pressure, NOT adaptive (see docstring). Honest label, no fake flag.
        "C4": {"prefix": c3_prefix, "suffix": c3_suffix, "non_neutral": True, "adaptive": False,
               "tactic": "c4_static_tau2"},
        "C5": {"prefix": "", "suffix": c5_suffix, "non_neutral": True, "adaptive": False,
               "tactic": "c5_process_instruction"},
    }


# --------------------------------------------------------------------------- adapter
class Tau2Adapter:
    name = "tau2"

    def __init__(self, endpoints: dict[str, Endpoint], *, domains: Optional[list[str]] = None,
                 python: str = DEFAULT_TAU2_PYTHON, max_steps: int = 30,
                 max_user_turns: int = 10, episode_timeout_s: float = 300.0):
        self.endpoints = endpoints
        self.domains = domains or ["airline", "retail"]
        self.python = python
        self.max_steps = max_steps
        self.max_user_turns = max_user_turns
        self.episode_timeout_s = episode_timeout_s
        self._profiles: Optional[dict[str, dict]] = None

    def available(self) -> bool:
        return pathlib.Path(self.python).exists() and WORKER.exists()

    def _env(self) -> dict:
        env = dict(os.environ)
        env["TAU2_DATA_DIR"] = TAU2_DATA_DIR
        return env

    def _run(self, job: dict[str, Any], timeout: float) -> dict[str, Any]:
        if not self.available():
            raise Tau2Unavailable(f"missing interpreter {self.python} or worker {WORKER}")
        proc = subprocess.run(
            [self.python, str(WORKER), json.dumps(job)],
            capture_output=True, text=True, cwd=str(WORKER.parent), env=self._env(),
            timeout=timeout,
        )
        last = None
        for line in reversed([ln for ln in proc.stdout.splitlines() if ln.strip()]):
            try:
                last = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        if last is None:
            raise Tau2Unavailable(f"no JSON from tau2 worker; stderr tail: {proc.stderr[-500:]}")
        if last.get("event") == "error":
            raise Tau2Unavailable(f"tau2 worker error: {last.get('error')}")
        return last

    # -- data ---------------------------------------------------------------
    def _load_profiles(self) -> dict[str, dict]:
        if self._profiles is None:
            out = self._run({"cmd": "list-tasks", "domains": self.domains}, timeout=180)
            self._profiles = {f"{p['domain']}:{p['task_id']}": p for p in out["tasks"]}
        return self._profiles

    def load_tasks(self, task_ids: Optional[list[str]] = None) -> list[TaskSpec]:
        profiles = self._load_profiles()
        ids = task_ids if task_ids is not None else sorted(profiles)
        out: list[TaskSpec] = []
        for tid in ids:
            p = profiles[tid]
            out.append(TaskSpec(
                benchmark=self.name,
                task_id=tid,  # "domain:task_id"
                n_user_turns=max(2, p.get("n_reference_read_write", 2)),  # depth proxy
                canonical_messages=[],
                canonical_hashes=[],
                n_distinct_tools=int(p.get("n_distinct_tools", 0)),
                n_reference_actions=int(p.get("n_reference_actions", 0)),
                min_prereq_verification_calls=int(p.get("min_prereq_verification_calls", 1)),
                min_viable_total_verification_calls=int(p.get("min_viable_total_verification_calls", 1)),
                gt_path=list(p.get("gt_path", [])),
                categories=[p.get("domain", "")],
                meta={
                    "domain": p.get("domain"),
                    "raw_task_id": p.get("task_id"),
                    "mutating_tools": p.get("mutating_tools", []),
                    "read_tools": p.get("read_tools", []),
                    "gt_mutating_functions": p.get("mutating_tools", []),  # build_splits.is_mutating
                    "has_mutation": p.get("has_mutation", False),
                    "reward_basis": p.get("reward_basis", []),
                },
            ))
        return out

    # -- rollout ------------------------------------------------------------
    def run_episode(
        self,
        task: TaskSpec,
        *,
        model_alias: str,
        condition: str,
        repeat: int,
        stage: str,
        user_hook: Callable[..., tuple[str, InterventionRecord]] = None,
        seed: int = 0,
        family: Optional[str] = None,
    ) -> EpisodeRecord:
        endpoint = self.endpoints[model_alias]
        fam = family or "compression"
        domain = task.meta["domain"]
        raw_id = task.meta["raw_task_id"]
        rec = EpisodeRecord(
            episode_id=episode_id(stage, self.name, task.task_id, model_alias, condition, repeat),
            benchmark=self.name,
            task_id=task.task_id,
            model=model_alias,
            condition=condition,
            repeat=repeat,
            block_id=block_id(self.name, task.task_id, model_alias, repeat),
            family=fam,
            stage=stage,
            seed=seed,
            n_attackable_turns=task.n_user_turns,
            min_prereq_verification_calls=task.min_prereq_verification_calls,
            min_viable_total_verification_calls=task.min_viable_total_verification_calls,
            gt_path=task.gt_path,
            manifest={"served_id": endpoint.served_id, "worker_python": self.python,
                      "domain": domain, "data_dir": TAU2_DATA_DIR},
        )
        job = {
            "cmd": "run-episode",
            "domain": domain,
            "task_id": raw_id,
            "family": fam,
            "condition": condition,
            "seed": seed,
            "endpoint": {"base_url": endpoint.base_url, "served_id": endpoint.served_id,
                         "api_key": endpoint.api_key},
            "attack_spec": build_attack_spec(condition, fam),
            "max_steps": self.max_steps,
            "max_user_turns": self.max_user_turns,
        }
        t0 = time.time()
        try:
            payload = self._run(job, timeout=self.episode_timeout_s)
            self._absorb(rec, payload)
        except Exception as exc:  # infra failure (timeout / worker crash / server down)
            rec.infra_failure = True
            rec.error = f"{type(exc).__name__}: {exc}"[:300]
            rec.outcome_class = "infrastructure_failure"
            rec.endpoint.termination_reason = "infrastructure_failure"
        finally:
            rec.duration_s = time.time() - t0
        return rec

    # tau2 TerminationReason -> the strings classify_outcome (extract_metrics) recognises.
    _TERM_MAP = {
        "user_stop": "completed", "agent_stop": "completed",
        "max_steps": "step_limit", "timeout": "watchdog_timeout",
        "too_many_errors": "message_budget", "context_window_exceeded": "message_budget",
    }
    _TERM_INFRA = {"infrastructure_error", "unexpected_error", "agent_error", "user_error"}

    def _absorb(self, rec: EpisodeRecord, payload: dict[str, Any]) -> None:
        proc = payload.get("process", {})
        raw_term = str(payload.get("termination_reason", "unknown"))
        term = self._TERM_MAP.get(raw_term, raw_term)
        rec.endpoint = EndpointResult(
            success=int(payload.get("success", 0)),
            components={"reward": payload.get("reward", 0.0)},
            termination_reason=term,
            evaluator="tau2.evaluator.evaluate_simulation (EvaluationType.ENV)",
            evaluator_version="tau2",
            raw={"raw_termination_reason": raw_term},
        )
        rec.tool_calls = [
            ToolCallRecord(turn=0, step=i, name=c["name"], mutating=bool(c.get("mutating")),
                           tool_type=c.get("tool_type"))
            for i, c in enumerate(payload.get("tool_calls", []))
        ]
        rec.turns = [
            TurnRecord(index=t.get("turn", i), canonical_message=t.get("canonical", ""),
                       canonical_hash=sha256_text(t.get("canonical", "")),
                       rendered_message=t.get("rendered", ""),
                       rendered_hash=sha256_text(t.get("rendered", "")))
            for i, t in enumerate(payload.get("rendered_turns", []))
        ]
        rec.process = {"compression": proc.get("compression", {}),
                       "inflation": proc.get("inflation", {})}
        rec.interventions = [InterventionRecord(**{k: v for k, v in iv.items()
                                                   if k in InterventionRecord.__dataclass_fields__})
                             for iv in payload.get("interventions", [])]
        rec.manifest["ledger_misses"] = payload.get("ledger_misses", 0)
        rec.manifest["n_user_turns"] = payload.get("n_user_turns", 0)
        # A hard tau2 error is an infra failure, not a task outcome.
        if raw_term in self._TERM_INFRA and not payload.get("success"):
            rec.infra_failure = True
            rec.outcome_class = "infrastructure_failure"
            return
        # Outcome (mirrors extract_metrics.classify_outcome; extract() will re-derive identically
        # once tau2 is wired into run_block). success == ENV endpoint correct.
        if payload.get("success"):
            rec.outcome_class = "correct_endpoint"
        elif term in ("step_limit", "watchdog_timeout", "message_budget", "budget_exhausted"):
            rec.outcome_class = "budget_exhausted"
        elif not payload.get("has_mutation"):
            rec.outcome_class = "no_state_change"
        else:
            rec.outcome_class = "wrong_state_changing"

    def manifest(self) -> dict[str, Any]:
        return {
            "benchmark": "tau2",
            "domains": self.domains,
            "worker_python": self.python,
            "data_dir": TAU2_DATA_DIR,
            "evaluator": "tau2.evaluator.evaluator.evaluate_simulation",
            "read_write": "native @is_tool(ToolType.READ/WRITE)",
            "isolation": "one subprocess per episode in tau2 venv",
        }
