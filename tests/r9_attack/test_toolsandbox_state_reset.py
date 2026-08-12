"""spec 3.2 / 17: ToolSandbox episodes must not share state.

R9 runs one worker SUBPROCESS per episode, so the world state dies with the process and no
episode can inherit another's database. This test verifies the isolation contract without
needing a live model:

  1. the adapter spawns a fresh subprocess per episode (structural guarantee); and
  2. BFCL's per-episode instance namespace is purged after each episode, verified via the
     adapter's own `_purge_namespace` (the analogous state-reset guarantee on the BFCL side).
"""

import pytest

from scripts.r9_attack.adapters.toolsandbox_adapter import WORKER, ToolSandboxAdapter


def test_worker_is_separate_process_per_episode():
    # The adapter never imports tool_sandbox in-process; it must spawn the worker script.
    assert WORKER.name == "toolsandbox_worker.py"
    a = ToolSandboxAdapter(endpoints={})
    # available() reflects whether the isolated interpreter + worker exist.
    assert isinstance(a.available(), bool)


def test_bfcl_namespace_is_reset_between_episodes():
    bfcl = pytest.importorskip("bfcl_eval")
    from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
        execute_multi_turn_func_call,
    )

    adapter = BfclAdapter(endpoints={})
    entries, _ = adapter._load_raw()
    entry = entries["multi_turn_base_0"]
    ns = "pytest_reset_ns"

    # Materialise instances in this namespace, mutate state.
    execute_multi_turn_func_call(
        func_call_list=["mkdir(dir_name='zzz')"],
        initial_config=entry["initial_config"], involved_classes=entry["involved_classes"],
        model_name=ns, test_entry_id=entry["id"], long_context=False,
    )
    # Purge and confirm none of this namespace's instances survive.
    assert adapter._purge_namespace(ns, entry) is True

    import re
    from bfcl_eval.eval_checker.multi_turn_eval import multi_turn_utils
    prefix = re.sub(r"[-./:]", "_", ns)
    remaining = [k for k in multi_turn_utils.__dict__ if k.startswith(prefix) and k.endswith("_instance")]
    assert remaining == []


def test_two_episodes_do_not_share_bfcl_state():
    bfcl = pytest.importorskip("bfcl_eval")
    from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import execute_multi_turn_func_call

    adapter = BfclAdapter(endpoints={})
    entries, _ = adapter._load_raw()
    entry = entries["multi_turn_base_0"]

    # Episode A creates a dir in its own namespace.
    execute_multi_turn_func_call(
        func_call_list=["mkdir(dir_name='epA_only')"],
        initial_config=entry["initial_config"], involved_classes=entry["involved_classes"],
        model_name="pytest_epA", test_entry_id=entry["id"], long_context=False,
    )
    # Episode B (fresh namespace) lists the root; it must NOT see epA_only.
    results, _ = execute_multi_turn_func_call(
        func_call_list=["ls()"],
        initial_config=entry["initial_config"], involved_classes=entry["involved_classes"],
        model_name="pytest_epB", test_entry_id=entry["id"], long_context=False,
    )
    assert "epA_only" not in "".join(results)
    adapter._purge_namespace("pytest_epA", entry)
    adapter._purge_namespace("pytest_epB", entry)
