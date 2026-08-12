#!/usr/bin/env python3
"""R9 ToolSandbox adapter, parent side (spec 3.2, 7.2, 11.1).

Runs in the driver environment. Owns no ToolSandbox imports: it spawns
`toolsandbox_worker.py` with the r9_ts interpreter, one process per episode, and talks
the line-delimited JSON protocol. One process per episode is also how spec 3.2's
"run 后销毁容器状态" is satisfied — the world state dies with the process, so no episode
can inherit another episode's database.

The `user_hook` lives here, in the driver, because the attacker and the two reviewers
need their own endpoints and must only ever see the public transcript the worker sends.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
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
from scripts.r9_attack.common.llm_client import Endpoint, InfraFailure  # noqa: E402

DEFAULT_TS_PYTHON = os.environ.get("R9_TS_PYTHON", "/home/xqin5/.conda/envs/r9_ts/bin/python")
WORKER = ROOT / "scripts" / "r9_attack" / "adapters" / "toolsandbox_worker.py"


class ToolSandboxUnavailable(RuntimeError):
    """The r9_ts interpreter or the ToolSandbox checkout is missing."""


class ToolSandboxAdapter:
    """Adapter over Apple ToolSandbox (spec 3.2)."""

    name = "toolsandbox"

    def __init__(
        self,
        endpoints: dict[str, Endpoint],
        *,
        python: str = DEFAULT_TS_PYTHON,
        ledger_path: Optional[pathlib.Path] = None,
        user_sim_alias: Optional[str] = None,
        timeout_s: int = 1800,
        max_agent_steps: int = 20,
        episode_timeout_s: int = 240,
        success_threshold: float = 0.5,
    ):
        self.endpoints = endpoints
        self.python = python
        self.timeout_s = timeout_s
        self.user_sim_alias = user_sim_alias
        self.max_agent_steps = max_agent_steps
        self.episode_timeout_s = episode_timeout_s
        self.success_threshold = success_threshold
        self._ledgers: dict[str, dict] = {}
        self._profiles: dict[str, dict] = {}
        if ledger_path and pathlib.Path(ledger_path).exists():
            self.load_ledgers(pathlib.Path(ledger_path))

    # -- worker plumbing ----------------------------------------------------
    def available(self) -> bool:
        return pathlib.Path(self.python).exists() and WORKER.exists()

    def _spawn(self, job: dict[str, Any]) -> subprocess.Popen:
        if not self.available():
            raise ToolSandboxUnavailable(f"missing interpreter {self.python} or worker {WORKER}")
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(job, tmp)
        tmp.close()
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["TOKENIZERS_PARALLELISM"] = "false"
        proc = subprocess.Popen(
            [self.python, str(WORKER), "--job", tmp.name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env, cwd=str(ROOT),
        )
        proc._r9_jobfile = tmp.name  # type: ignore[attr-defined]
        return proc

    def _run_simple(self, job: dict[str, Any]) -> dict[str, Any]:
        """Run a non-interactive command (list_scenarios / build_ledger)."""
        proc = self._spawn(job)
        try:
            out, err = proc.communicate(timeout=self.timeout_s)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise InfraFailure(f"ToolSandbox worker timeout on {job['command']}") from exc
        finally:
            _cleanup(proc)
        payload = _last_event(out)
        if payload is None:
            raise InfraFailure(f"worker produced no event; stderr tail: {err[-800:]}")
        if payload.get("event") == "error":
            raise InfraFailure(f"worker error: {payload.get('error')}\n{payload.get('traceback', '')}")
        return payload

    # -- ledgers (spec 7.2) -------------------------------------------------
    def load_ledgers(self, path: pathlib.Path) -> None:
        from scripts.r9_attack.common.io_utils import read_jsonl

        for row in read_jsonl(path):
            self._ledgers[row["scenario"]] = row
            self._profiles[row["scenario"]] = row.get("profile", {})

    def build_ledger(
        self,
        scenario: str,
        *,
        user_sim_alias: Optional[str] = None,
        agent_alias: Optional[str] = None,
        seed: int = 0,
        prepass_max_messages: int = 30,
        prepass_max_user_turns: int = 6,
        prepass_timeout_s: int = 120,
        max_agent_steps: int = 16,
    ) -> dict:
        alias = user_sim_alias or self.user_sim_alias
        if alias is None:
            raise ValueError("a user-simulator model alias is required to build a ledger")
        user_ep = self.endpoints[alias]
        agent_ep = self.endpoints[agent_alias] if agent_alias else user_ep
        payload = self._run_simple(
            {
                "command": "build_ledger",
                "scenario": scenario,
                "agent_endpoint": _ep(agent_ep),
                "user_endpoint": _ep(user_ep),
                "seed": seed,
                "prepass_max_messages": prepass_max_messages,
                "prepass_max_user_turns": prepass_max_user_turns,
                "prepass_timeout_s": prepass_timeout_s,
                "max_agent_steps": max_agent_steps,
                "allowed_hosts": sorted({e.host() for e in self.endpoints.values()}),
            }
        )
        ledger = payload["ledger"]
        ledger["user_simulator"] = alias
        self._ledgers[scenario] = ledger
        self._profiles[scenario] = ledger.get("profile", {})
        return ledger

    def build_ledgers_batch(
        self,
        scenarios: list[str],
        *,
        user_sim_alias: Optional[str] = None,
        agent_alias: Optional[str] = None,
        seed: int = 0,
        prepass_max_user_turns: int = 6,
        prepass_timeout_s: int = 120,
        max_agent_steps: int = 16,
    ) -> list[dict]:
        """Build many ledgers in one worker process (fast). Returns them in order."""
        alias = user_sim_alias or self.user_sim_alias
        if alias is None:
            raise ValueError("a user-simulator model alias is required to build ledgers")
        user_ep = self.endpoints[alias]
        agent_ep = self.endpoints[agent_alias] if agent_alias else user_ep
        payload = self._run_simple(
            {
                "command": "build_ledgers_batch",
                "scenarios": scenarios,
                "agent_endpoint": _ep(agent_ep),
                "user_endpoint": _ep(user_ep),
                "seed": seed,
                "prepass_max_messages": 30,
                "prepass_max_user_turns": prepass_max_user_turns,
                "prepass_timeout_s": prepass_timeout_s,
                "max_agent_steps": max_agent_steps,
                "allowed_hosts": sorted({e.host() for e in self.endpoints.values()}),
            }
        )
        out = []
        for led in payload["ledgers"]:
            if "error" in led:
                out.append(led)
                continue
            led["user_simulator"] = alias
            self._ledgers[led["scenario"]] = led
            self._profiles[led["scenario"]] = led.get("profile", {})
            out.append(led)
        return out

    def list_scenarios(self, only_eligible: bool = True, scenarios: Optional[list[str]] = None) -> list[dict]:
        payload = self._run_simple(
            {
                "command": "list_scenarios",
                "only_eligible": only_eligible,
                "scenarios": scenarios,
                "allowed_hosts": ["127.0.0.1"],
            }
        )
        for profile in payload["scenarios"]:
            self._profiles[profile["scenario"]] = profile
        return payload["scenarios"]

    # -- tasks --------------------------------------------------------------
    def load_tasks(self, task_ids: Optional[list[str]] = None) -> list[TaskSpec]:
        """TaskSpecs come from the frozen ledgers; ledgers must be built first."""
        ids = task_ids if task_ids is not None else sorted(self._ledgers)
        out: list[TaskSpec] = []
        for scenario in ids:
            ledger = self._ledgers.get(scenario)
            if ledger is None:
                raise KeyError(f"no frozen fact ledger for scenario {scenario!r} (run toolsandbox_fact_ledger.py)")
            profile = ledger.get("profile", {})
            pre = ledger.get("prepass", {})
            canonical = [ledger["opening_utterance"]] + [s["canonical_response"] for s in ledger["slots"]]
            out.append(
                TaskSpec(
                    benchmark=self.name,
                    task_id=scenario,
                    n_user_turns=len(canonical),
                    canonical_messages=canonical,
                    canonical_hashes=[sha256_text(m) for m in canonical],
                    n_distinct_tools=int(profile.get("n_distinct_tools", 0)),
                    n_reference_actions=int(profile.get("n_reference_actions", 0)),
                    min_prereq_verification_calls=int(pre.get("min_prereq_verification_calls", 1)),
                    min_viable_total_verification_calls=int(pre.get("min_viable_total_verification_calls", 1)),
                    gt_path=list(pre.get("gt_path", [])),
                    n_milestones=int(profile.get("n_milestones", 0)),
                    categories=list(profile.get("categories", [])),
                    meta={
                        "tool_allow_list": profile.get("tool_allow_list", []),
                        "mutating_tools": pre.get("mutating_tools", []),
                        "read_tools": pre.get("read_tools", []),
                        "max_messages": profile.get("max_messages"),
                        "user_simulator": ledger.get("user_simulator"),
                    },
                )
            )
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
        user_hook: Callable[..., tuple[str, InterventionRecord]],
        seed: int = 0,
        family: Optional[str] = None,
    ) -> EpisodeRecord:
        ledger = self._ledgers[task.task_id]
        endpoint = self.endpoints[model_alias]
        rec = EpisodeRecord(
            episode_id=episode_id(stage, self.name, task.task_id, model_alias, condition, repeat),
            benchmark=self.name,
            task_id=task.task_id,
            model=model_alias,
            condition=condition,
            repeat=repeat,
            block_id=block_id(self.name, task.task_id, model_alias, repeat),
            family=family,
            stage=stage,
            seed=seed,
            n_attackable_turns=task.n_user_turns,
            min_prereq_verification_calls=task.min_prereq_verification_calls,
            min_viable_total_verification_calls=task.min_viable_total_verification_calls,
            gt_path=task.gt_path,
            manifest={
                "toolsandbox_commit": _ts_commit(),
                "served_id": endpoint.served_id,
                "worker_python": self.python,
                "ledger_hash": sha256_text(json.dumps(ledger["slots"], sort_keys=True, ensure_ascii=False)),
                "user_simulator": ledger.get("user_simulator"),
            },
        )

        job = {
            "command": "run_episode",
            "scenario": task.task_id,
            "ledger": ledger,
            "agent_endpoint": _ep(endpoint),
            "seed": seed,
            "strict_ledger": False,
            "max_agent_steps": self.max_agent_steps,
            "episode_timeout_s": self.episode_timeout_s,
            "success_threshold": self.success_threshold,
            "allowed_hosts": sorted({e.host() for e in self.endpoints.values()}),
        }
        t0 = time.time()
        proc = self._spawn(job)
        payload: Optional[dict[str, Any]] = None
        try:
            payload = self._pump(proc, rec, user_hook)
        except InfraFailure as exc:
            rec.infra_failure = True
            rec.error = f"InfraFailure: {exc}"
            rec.outcome_class = "infrastructure_failure"
            rec.endpoint.termination_reason = "infrastructure_failure"
        finally:
            _cleanup(proc)
            rec.duration_s = time.time() - t0

        if payload is not None:
            self._absorb(rec, payload["record"], task)
        return rec

    def _pump(
        self,
        proc: subprocess.Popen,
        rec: EpisodeRecord,
        user_hook: Callable[..., tuple[str, InterventionRecord]],
    ) -> dict[str, Any]:
        """Serve `user_turn` requests until the worker emits its terminal event."""
        deadline = time.time() + self.timeout_s
        assert proc.stdout is not None and proc.stdin is not None
        while True:
            if time.time() > deadline:
                proc.kill()
                raise InfraFailure("ToolSandbox worker timeout during episode")
            line = proc.stdout.readline()
            if not line:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise InfraFailure(f"worker exited early (rc={proc.poll()}); stderr tail: {stderr[-800:]}")
            event = json.loads(line)
            if event.get("event") == "user_turn":
                rendered, intervention = user_hook(
                    turn_index=event["turn"],
                    canonical_message=event["canonical"],
                    public_transcript=event["public_transcript"],
                    slot=event["slot"],
                )
                if event["canonical"] not in rendered:
                    proc.kill()
                    raise InfraFailure("user_hook broke canonical payload invariance (spec 7.2)")
                rec.interventions.append(intervention)
                proc.stdin.write(json.dumps({"rendered": rendered}, ensure_ascii=False) + "\n")
                proc.stdin.flush()
                continue
            if event.get("event") == "error":
                raise InfraFailure(f"worker error: {event.get('error')}\n{event.get('traceback', '')}")
            if event.get("event") == "done":
                return event
            raise InfraFailure(f"unknown worker event {event.get('event')!r}")

    def _absorb(self, rec: EpisodeRecord, payload: dict[str, Any], task: TaskSpec) -> None:
        ep = payload["endpoint"]
        rec.endpoint = EndpointResult(
            success=int(ep["success"]),
            components=ep["components"],
            termination_reason=ep["termination_reason"],
            evaluator=ep["evaluator"],
            evaluator_version=_ts_commit(),
        )
        rec.tool_calls = [ToolCallRecord(**c) for c in payload["tool_calls"]]
        rec.turns = [
            TurnRecord(
                index=t["turn"],
                canonical_message=t["canonical"],
                canonical_hash=sha256_text(t["canonical"]),
                rendered_message=t["rendered"],
                rendered_hash=sha256_text(t["rendered"]),
            )
            for t in payload["rendered_turns"]
        ]
        rec.network_events = payload.get("network_events", [])
        rec.safety_events = [e for e in payload.get("user_events", []) if e.get("event") != "ledger_miss"]
        rec.manifest["ledger_misses"] = sum(
            1 for e in payload.get("user_events", []) if e.get("event") == "ledger_miss"
        )
        rec.manifest["scenario_profile"] = payload.get("profile", {})

    def manifest(self) -> dict[str, Any]:
        return {
            "benchmark": "toolsandbox",
            "repo": str(_ts_repo()),
            "commit": _ts_commit(),
            "worker_python": self.python,
            "evaluator": "tool_sandbox.common.evaluation.Evaluation.evaluate",
            "isolation": "one subprocess per episode; state destroyed on exit (spec 3.2)",
        }


# ---------------------------------------------------------------------------
def _ep(endpoint: Endpoint) -> dict[str, Any]:
    endpoint.host()  # spec 0.1: refuse non-local endpoints before spawning
    return {
        "base_url": endpoint.base_url,
        "served_id": endpoint.served_id,
        "api_key": endpoint.api_key,
    }


def _last_event(stdout: str) -> Optional[dict[str, Any]]:
    for line in reversed([ln for ln in stdout.splitlines() if ln.strip()]):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _cleanup(proc: subprocess.Popen) -> None:
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        try:
            if stream:
                stream.close()
        except Exception:
            pass
    if proc.poll() is None:
        proc.kill()
    try:
        os.unlink(getattr(proc, "_r9_jobfile", ""))
    except OSError:
        pass


def _ts_repo() -> pathlib.Path:
    return pathlib.Path(os.environ.get("R9_TOOLSANDBOX_REPO", "/home/xqin5/ToolSandbox"))


def _ts_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_ts_repo(), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"
