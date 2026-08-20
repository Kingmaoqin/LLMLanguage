#!/usr/bin/env python3
"""R9 BFCL multi-turn-base adapter (spec 3.1, 7.1, 10.3, 11.1).

Primary benchmark. We drive the rollout ourselves (BFCL's own generation loop has no
hook for user-side style injection) but we execute function calls with BFCL's OWN
`execute_multi_turn_func_call` and score with BFCL's OWN `multi_turn_checker`. The
evaluator is never copied or reimplemented (spec 11.1).

Three things here are load-bearing for R9's validity:

1. STATE RESET. `execute_multi_turn_func_call` caches live API instances in the module
   globals of `multi_turn_utils`, keyed by `<model_name>_<test_entry_id>_<class>`. If two
   episodes ever shared a key, condition B would inherit condition A's mutated world.
   Every episode therefore gets a unique instance namespace, and `_purge_namespace`
   verifies afterwards that it is gone. That check is reported as `state_reset_ok`.

2. MUTATION DETECTION. Calls are executed ONE AT A TIME with a deep-copied snapshot of
   every involved instance taken before and after, so `mutating` is measured from the
   benchmark's own state rather than from a hand-written read/write table (spec 10.1).

3. MINIMUM VIABLE PATH. The denominators in spec 10.1/10.2 come from replaying the
   official `possible_answer` ground truth in a throwaway namespace and classifying each
   GT call with the same mutation detector. No ordering is imposed (spec 10.3).
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
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
from scripts.r9_attack.common.llm_client import Endpoint, InfraFailure, chat  # noqa: E402

TEST_CATEGORY = "multi_turn_base"
# R9v1 (spec 3.1) loaded ONLY `multi_turn_base`. R9v2 (pre-registered redesign, see
# reports/r9_attack/R9v2_PREREGISTRATION_CN.md) deliberately ADDS `multi_turn_miss_param`:
# a missing required parameter forces a clarify/verify step before acting, which is exactly
# the verification behaviour the compression/inflation attacks target (deeper attack surface
# + alive VerificationDepth). Categories are now configurable; the default stays base-only
# for backward compatibility, and R9v2 passes both via the adapter factory / config.
TEST_CATEGORIES_DEFAULT = ["multi_turn_base"]


class BfclUnavailable(RuntimeError):
    """bfcl_eval is not importable in this interpreter."""


def _bfcl():
    """Import bfcl_eval lazily so the module is importable for schema-only tests."""
    try:
        import bfcl_eval  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise BfclUnavailable(
            "bfcl_eval not installed in this interpreter; run inside the r9_bfcl env"
        ) from exc
    return bfcl_eval


def bfcl_version() -> str:
    import importlib.metadata as md

    try:
        return md.version("bfcl-eval")
    except Exception:  # pragma: no cover
        return "unknown"


# ---------------------------------------------------------------------------
# State snapshotting / mutation detection
# ---------------------------------------------------------------------------
def _snapshot(instances: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Deep-copy the public attributes of every involved API instance."""
    snap: dict[str, dict[str, Any]] = {}
    for cls_name, inst in instances.items():
        attrs: dict[str, Any] = {}
        for key, value in vars(inst).items():
            if key.startswith("_"):
                continue  # private counters/RNG are not observable world state
            try:
                attrs[key] = copy.deepcopy(value)
            except Exception:
                attrs[key] = repr(value)
        snap[cls_name] = attrs
    return snap


def _state_changed(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> bool:
    if set(before) != set(after):
        return True
    for cls_name, before_attrs in before.items():
        after_attrs = after[cls_name]
        if set(before_attrs) != set(after_attrs):
            return True
        for key, old in before_attrs.items():
            new = after_attrs[key]
            try:
                if old != new:
                    return True
            except Exception:
                if repr(old) != repr(new):
                    return True
    return False


# ---------------------------------------------------------------------------
# Tool-call <-> BFCL decoded-string conversion
# ---------------------------------------------------------------------------
def _literal(value: Any) -> str:
    return repr(value)


def tool_call_to_bfcl_string(name: str, arguments: dict[str, Any]) -> str:
    """Render an OpenAI tool call as the `func(a=1, b='x')` string BFCL evaluates."""
    args = ", ".join(f"{k}={_literal(v)}" for k, v in arguments.items())
    return f"{name}({args})"


_CALL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9.]*)\s*\(")


def bfcl_string_func_name(call: str) -> str:
    m = _CALL_RE.match(call)
    return m.group(1).split(".")[-1] if m else ""


class BfclAdapter:
    """Adapter over BFCL `multi_turn_base` (spec 3.1)."""

    name = "bfcl"

    def __init__(self, endpoints: dict[str, Endpoint], *, max_step_limit: Optional[int] = None,
                 categories: Optional[list[str]] = None):
        _bfcl()
        from bfcl_eval.constants.default_prompts import MAXIMUM_STEP_LIMIT

        self.endpoints = endpoints
        self.categories = list(categories) if categories else list(TEST_CATEGORIES_DEFAULT)
        self.max_step_limit = int(max_step_limit or MAXIMUM_STEP_LIMIT)
        self._entries: Optional[dict[str, dict]] = None
        self._ground_truth: Optional[dict[str, list[list[str]]]] = None
        self._task_cache: dict[str, TaskSpec] = {}

    # -- data ---------------------------------------------------------------
    def _load_raw(self) -> tuple[dict[str, dict], dict[str, list[list[str]]]]:
        if self._entries is not None and self._ground_truth is not None:
            return self._entries, self._ground_truth
        from bfcl_eval.utils import (
            load_dataset_entry,
            load_ground_truth_entry,
            populate_test_cases_with_predefined_functions,
        )

        merged_entries: dict[str, dict] = {}
        merged_gt: dict[str, list[list[str]]] = {}
        for category in self.categories:
            entries = load_dataset_entry(category)
            if isinstance(entries, tuple):  # some versions return (entries, ids)
                entries = entries[0]
            entries = populate_test_cases_with_predefined_functions(entries)
            for e in entries:
                merged_entries[e["id"]] = e
            for g in load_ground_truth_entry(category):
                merged_gt[g["id"]] = g["ground_truth"]
        self._entries = merged_entries
        self._ground_truth = merged_gt
        return self._entries, self._ground_truth

    def _openai_tools(self, entry: dict) -> list[dict]:
        """Official BFCL func-doc -> OpenAI tool conversion (never hand-written)."""
        from bfcl_eval.constants.type_mappings import GORILLA_TO_OPENAPI
        from bfcl_eval.constants.enums import ModelStyle
        from bfcl_eval.model_handler.utils import convert_to_tool

        excluded = set(entry.get("excluded_function") or [])
        funcs = [f for f in entry["function"] if f["name"] not in excluded]
        converted = convert_to_tool(funcs, GORILLA_TO_OPENAPI, ModelStyle.OSSMODEL)
        return [{"type": "function", "function": f} for f in converted]

    def load_tasks(self, task_ids: Optional[list[str]] = None) -> list[TaskSpec]:
        entries, gts = self._load_raw()
        ids = task_ids if task_ids is not None else sorted(entries, key=_id_sort_key)
        out: list[TaskSpec] = []
        for tid in ids:
            if tid in self._task_cache:
                out.append(self._task_cache[tid])
                continue
            entry = entries[tid]
            canonical = [_turn_text(turn) for turn in entry["question"]]
            gt = gts[tid]
            profile = self._reference_profile(entry, gt)
            spec = TaskSpec(
                benchmark=self.name,
                task_id=tid,
                n_user_turns=len(canonical),
                canonical_messages=canonical,
                canonical_hashes=[sha256_text(m) for m in canonical],
                n_distinct_tools=profile["n_distinct_tools"],
                n_reference_actions=profile["n_reference_actions"],
                min_prereq_verification_calls=profile["min_prereq_verification_calls"],
                min_viable_total_verification_calls=profile["min_viable_total_verification_calls"],
                gt_path=profile["gt_flat"],
                categories=list(entry.get("involved_classes") or []),
                meta={
                    "involved_classes": entry.get("involved_classes"),
                    "gt_mutating_functions": profile["gt_mutating_functions"],
                    "gt_read_functions": profile["gt_read_functions"],
                    "official_path": entry.get("path"),
                },
            )
            self._task_cache[tid] = spec
            out.append(spec)
        return out

    # -- minimum viable path (spec 10.3) ------------------------------------
    def _reference_profile(self, entry: dict, ground_truth: list[list[str]]) -> dict[str, Any]:
        """Replay the official ground truth and classify each call read vs mutating."""
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
            execute_multi_turn_func_call,
        )

        namespace = f"r9ref_{entry['id']}_{int(time.time_ns())}"
        flat: list[str] = [c for turn in ground_truth for c in turn]
        mutating: list[str] = []
        reads: list[str] = []
        reads_before_first_mutation = 0
        seen_mutation = False
        try:
            for call in flat:
                _, instances = execute_multi_turn_func_call(
                    func_call_list=[],
                    initial_config=entry["initial_config"],
                    involved_classes=entry["involved_classes"],
                    model_name=namespace,
                    test_entry_id=entry["id"],
                    long_context=False,
                )
                before = _snapshot(instances)
                execute_multi_turn_func_call(
                    func_call_list=[call],
                    initial_config=entry["initial_config"],
                    involved_classes=entry["involved_classes"],
                    model_name=namespace,
                    test_entry_id=entry["id"],
                    long_context=False,
                )
                after = _snapshot(instances)
                fname = bfcl_string_func_name(call)
                if _state_changed(before, after):
                    mutating.append(fname)
                    seen_mutation = True
                else:
                    reads.append(fname)
                    if not seen_mutation:
                        reads_before_first_mutation += 1
        finally:
            self._purge_namespace(namespace, entry)

        return {
            "gt_flat": flat,
            "n_reference_actions": len(flat),
            "n_distinct_tools": len({bfcl_string_func_name(c) for c in flat}),
            "gt_mutating_functions": sorted(set(mutating)),
            "gt_read_functions": sorted(set(reads)),
            # Spec 10.1 denominator; spec pins it at >= 1 via max(1, .)
            "min_prereq_verification_calls": max(1, reads_before_first_mutation),
            # Spec 10.2 denominator: every verification call on the minimum viable path
            "min_viable_total_verification_calls": max(1, len(reads)),
        }

    @staticmethod
    def _purge_namespace(namespace: str, entry: dict) -> bool:
        """Drop every cached instance for this namespace; True iff none remain."""
        from bfcl_eval.eval_checker.multi_turn_eval import multi_turn_utils

        # `execute_multi_turn_func_call` stashes instances in its own module globals.
        g = multi_turn_utils.__dict__
        prefix = re.sub(r"[-./:]", "_", namespace)
        stale = [k for k in list(g) if k.startswith(prefix) and k.endswith("_instance")]
        for key in stale:
            del g[key]
        remaining = [k for k in g if k.startswith(prefix) and k.endswith("_instance")]
        return not remaining

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
        entries, gts = self._load_raw()
        entry = entries[task.task_id]
        endpoint = self.endpoints[model_alias]
        tools = self._openai_tools(entry)
        namespace = f"r9_{stage}_{model_alias}_{condition}_r{repeat}_{task.task_id}"

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
            n_attackable_turns=max(0, task.n_user_turns),
            min_prereq_verification_calls=task.min_prereq_verification_calls,
            min_viable_total_verification_calls=task.min_viable_total_verification_calls,
            gt_path=task.gt_path,
            manifest={
                "bfcl_version": bfcl_version(),
                "test_category": TEST_CATEGORY,
                "max_step_limit": self.max_step_limit,
                "served_id": endpoint.served_id,
                "system_prompt": "",
                "instance_namespace": namespace,
            },
        )

        t0 = time.time()
        messages: list[dict[str, Any]] = []
        public_transcript: list[dict[str, str]] = []
        decoded: list[list[list[str]]] = []
        prompt_tokens = completion_tokens = 0
        termination = "completed"

        try:
            for turn_index, canonical in enumerate(task.canonical_messages):
                rendered, intervention = user_hook(
                    turn_index=turn_index,
                    canonical_message=canonical,
                    public_transcript=list(public_transcript),
                )
                if canonical not in rendered:
                    raise SemanticInvarianceError(
                        f"turn {turn_index}: canonical payload not preserved verbatim"
                    )
                rec.interventions.append(intervention)
                turn_rec = TurnRecord(
                    index=turn_index,
                    canonical_message=canonical,
                    canonical_hash=sha256_text(canonical),
                    rendered_message=rendered,
                    rendered_hash=sha256_text(rendered),
                )
                messages.append({"role": "user", "content": rendered})
                public_transcript.append({"role": "user", "content": rendered})

                turn_decoded: list[list[str]] = []
                for step in range(self.max_step_limit):
                    result = chat(endpoint, messages, tools=tools, seed=seed)
                    prompt_tokens += result.prompt_tokens
                    completion_tokens += result.completion_tokens
                    if result.content:
                        turn_rec.agent_messages.append(result.content)
                        public_transcript.append({"role": "assistant", "content": result.content})
                    if not result.tool_calls:
                        messages.append({"role": "assistant", "content": result.content})
                        turn_rec.n_steps = step + 1
                        break

                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": result.content or None,
                        "tool_calls": [
                            {
                                "id": tc["id"] or f"call_{turn_index}_{step}_{i}",
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]),
                                },
                            }
                            for i, tc in enumerate(result.tool_calls)
                        ],
                    }
                    messages.append(assistant_msg)

                    step_calls: list[str] = []
                    for i, tc in enumerate(result.tool_calls):
                        call_str, call_rec, result_text = self._execute_one(
                            entry, namespace, turn_index, step, tc, rec.tool_calls
                        )
                        step_calls.append(call_str)
                        rec.tool_calls.append(call_rec)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": assistant_msg["tool_calls"][i]["id"],
                                "content": result_text,
                            }
                        )
                    turn_decoded.append(step_calls)
                    turn_rec.n_steps = step + 1
                else:
                    termination = "step_limit"
                decoded.append(turn_decoded)
                rec.turns.append(turn_rec)

            rec.endpoint = self._score(entry, gts[task.task_id], decoded, namespace)
            rec.endpoint.termination_reason = termination
        except InfraFailure as exc:
            rec.infra_failure = True
            rec.error = f"InfraFailure: {exc}"
            rec.outcome_class = "infrastructure_failure"
            rec.endpoint.termination_reason = "infrastructure_failure"
        except SemanticInvarianceError:
            self._purge_namespace(namespace, entry)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            rec.infra_failure = True
            rec.error = f"{type(exc).__name__}: {exc}"
            rec.outcome_class = "infrastructure_failure"
            rec.endpoint.termination_reason = "infrastructure_failure"
        finally:
            rec.state_reset_ok = self._purge_namespace(namespace, entry)
            rec.duration_s = time.time() - t0
            rec.tokens = {"prompt": prompt_tokens, "completion": completion_tokens}
        return rec

    def _execute_one(
        self,
        entry: dict,
        namespace: str,
        turn_index: int,
        step: int,
        tool_call: dict[str, Any],
        prior: list[ToolCallRecord],
    ) -> tuple[str, ToolCallRecord, str]:
        """Execute a single tool call and measure whether it changed world state."""
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
            execute_multi_turn_func_call,
        )

        name = tool_call["name"]
        args = tool_call["arguments"]
        if "__unparsed__" in args:
            call_rec = ToolCallRecord(
                turn=turn_index, step=step, name=name, arguments=args,
                ok=False, error="unparsed_arguments", result_repr="",
            )
            return f"{name}()", call_rec, "Error: could not parse tool arguments."

        call_str = tool_call_to_bfcl_string(name, args)
        # Materialise instances first so `before` is a true pre-call snapshot.
        _, instances = execute_multi_turn_func_call(
            func_call_list=[],
            initial_config=entry["initial_config"],
            involved_classes=entry["involved_classes"],
            model_name=namespace,
            test_entry_id=entry["id"],
            long_context=False,
        )
        before = _snapshot(instances)
        results, instances = execute_multi_turn_func_call(
            func_call_list=[call_str],
            initial_config=entry["initial_config"],
            involved_classes=entry["involved_classes"],
            model_name=namespace,
            test_entry_id=entry["id"],
            long_context=False,
        )
        after = _snapshot(instances)
        result_text = results[0] if results else ""
        ok = not str(result_text).startswith("Error during execution:")
        dup = next(
            (
                idx
                for idx, c in enumerate(prior)
                if c.name == name and c.arguments == args and c.ok
            ),
            None,
        )
        call_rec = ToolCallRecord(
            turn=turn_index,
            step=step,
            name=name,
            arguments=args,
            ok=ok,
            error=None if ok else str(result_text)[:300],
            mutating=_state_changed(before, after),
            duplicate_of=dup,
            result_repr=str(result_text)[:2000],
        )
        return call_str, call_rec, str(result_text)[:4000]

    # -- native scoring (spec 11.1) -----------------------------------------
    def _score(
        self,
        entry: dict,
        ground_truth: list[list[str]],
        decoded: list[list[list[str]]],
        namespace: str,
    ) -> EndpointResult:
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker

        # The checker replays everything in ITS OWN `_eval` / `_ground_truth` namespaces,
        # so it never sees the rollout instances.
        while len(decoded) < len(ground_truth):
            decoded.append([])
        verdict = multi_turn_checker(
            multi_turn_model_result_list_decoded=decoded,
            multi_turn_ground_truth_list=ground_truth,
            test_entry=entry,
            test_category=TEST_CATEGORY,
            model_name=f"{namespace}_score",
        )
        self._purge_namespace(f"{namespace}_score", entry)
        self._purge_namespace(f"{namespace}_score_ground_truth", entry)
        return EndpointResult(
            success=1 if verdict.get("valid") else 0,
            components={
                "error_type": verdict.get("error_type"),
                "error_message": verdict.get("error_message"),
            },
            evaluator="bfcl.multi_turn_checker",
            evaluator_version=bfcl_version(),
            raw={k: v for k, v in verdict.items() if k != "details"},
        )

    def manifest(self) -> dict[str, Any]:
        from bfcl_eval.constants.default_prompts import MAXIMUM_STEP_LIMIT
        from bfcl_eval.constants.eval_config import PROMPT_PATH

        data_file = pathlib.Path(PROMPT_PATH) / f"BFCL_v4_{TEST_CATEGORY}.json"
        from scripts.r9_attack.common.io_utils import sha256_file

        return {
            "benchmark": "bfcl",
            "package": "bfcl-eval",
            "version": bfcl_version(),
            "test_category": TEST_CATEGORY,
            "dataset_file": str(data_file),
            "dataset_sha256": sha256_file(data_file) if data_file.exists() else None,
            "evaluator": "bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker",
            "official_max_step_limit": MAXIMUM_STEP_LIMIT,
            "configured_max_step_limit": self.max_step_limit,
        }


class SemanticInvarianceError(RuntimeError):
    """Spec 7: the canonical payload was not preserved verbatim -> block is void."""


def _turn_text(turn: list[dict]) -> str:
    """A BFCL turn is a list of messages; multi_turn_base uses exactly one user message."""
    return "\n".join(m["content"] for m in turn if m.get("role") == "user")


def _id_sort_key(task_id: str) -> tuple[str, int]:
    head, _, tail = task_id.rpartition("_")
    return (head, int(tail) if tail.isdigit() else 0)
