# R7-B full queue 启动状态

时间：2026-07-08 02:21 UTC

## 已完成的代码

新增/修复：

- `scripts/r7b_ipma/run_r7b_live.py`
  - R7-B 专用真实模型 runner。
  - 使用 `data/r7b_ipma/frozen/r7b_frozen_templates.jsonl`，不复用旧 R7-v1 wrappers。
  - 每条 trace 写入 R7-B pairing 所需 hash：
    - `clean_task_semantics_hash`
    - `pressure_prefix_hash`
    - `policy_spec_hash`
    - `tool_permission_hash`
    - `initial_state_hash`
    - `required_information_hash`
    - `endpoint_evaluator_hash`
  - 写入 `conversation_turns`、`tool_events`、initial/final state snapshot、`expected_field_diffs`、usage/errors。

- `scripts/r7b_ipma/queue_r7b_full.sh`
  - R7-B 专用 full queue。
  - model-by-model resume。
  - gemma/mistral 单卡 self-serve 或使用现有 endpoint。
  - gpt_oss 改为 TP=2 双卡等待，避免单卡 OOM。
  - 结束后自动跑 template audit、pairing invariant、endpoint oracle、PASR、统计分析。

- `configs/r7b_ipma/r7b_dev.yaml`
- `configs/r7b_ipma/r7b_full.yaml`
- `tests/r7b_ipma/test_r7b_fail_closed.py`

## 已通过的验证

```text
python -m py_compile scripts/r7b_ipma/run_r7b_live.py scripts/r7b_ipma/*.py scripts/r7b_ipma/processguard/*.py
bash -n scripts/r7b_ipma/queue_r7b_full.sh
python -m pytest tests/r7b_ipma/test_r7b_fail_closed.py -q
5 passed
python scripts/r7b_ipma/run_r7b_smoke.py
{"synthetic_traces": 288, "commands": 8, "failed": 0}
```

## full queue 当前状态

当前有效队列：

- log: `logs/r7b_full_queue_20260708_022104.log`
- output root: `results/r7b_ipma/main/full_20260708_022104`
- planned full size: 1296 cells
  - 当前 frozen test tasks: 24
  - conditions: 6
  - models: 3
  - seeds: 3
  - per model expected: 432 traces

启动后已确认：

- queue 进入 `RUN model=gemma4_31b`
- `results/r7b_ipma/main/full_20260708_022104/traces/` 已开始产生真实 trace
- 抽查 trace 已包含 R7-B required metadata/hash、template_id、initial/final state snapshot、expected_field_diffs
- 截至启动复核时暂无 `live_failures.jsonl`

## 注意事项

1. 当前 full 使用 R6 minimal deterministic tool/state backend，而不是 tau2 原生 backend；优先保证 R7-B frozen template、pairing、endpoint field oracle 和 raw-trace reproducibility。
2. 旧失败队列 `full_20260708_021958` 曾因临时 config 写入 bug失败，并进入 gpt_oss 等待；正式有效输出根以 `full_20260708_022104` 为准。
3. gpt_oss 需要双卡 TP=2；若 6 小时内没有两张足够空闲 GPU，queue 会记录 skip，后续可用同一 output root resume。

