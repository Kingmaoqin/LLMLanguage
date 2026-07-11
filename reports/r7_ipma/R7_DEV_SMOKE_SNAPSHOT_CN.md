# R7 dev smoke：tau2 snapshot instrumentation 验证

日期：2026-07-01
状态：**tau2 snapshot 修复 + 单模型 live dev smoke 通过。未启动全量。**

## 1. 修复内容

R6 的 tau2 executor 只保存 `get_db_hash()`（hash），因此 720 条 tau2 retail/airline
trace 无法重建字段级 final-state diff（此前全部标记 `cannot_reconstruct_missing_snapshot`）。

在 `scripts/r6/run_r6_live.py` 的 `run_cell_live` 中新增**可选** snapshot 捕获：

- 新增 `_db_snapshot(orch)`：读取 `orch.environment.tools.db.model_dump(mode="json")`，
  best-effort，失败返回 None，**绝不中断 run**。
- 新增参数 `capture_full_snapshots`（默认 `False`）：为 True 时把完整 DB 快照写入
  `initial_environment_state["state"]` / `final_environment_state["state"]`，并置
  `run_meta.field_level_state_diff_source = "reconstructed_from_full_snapshot"`、
  `full_db_snapshot_captured = True`。
- 默认关闭 → **R6 既有 pipeline 行为不变**（仅新增一个 `full_db_snapshot_captured=False`
  只读字段，向后兼容）。

## 2. dev smoke（真实模型调用）

命令：

```bash
conda run -n agentsearch python scripts/r7_ipma/run_r7_tau2_snapshot_smoke.py
```

配置：`gemma4_31b`（端口 8005，唯一在线）× `r6_retail_03_return_confirmed`
× `neutral_clean` × seed 300，1 cell。

结果：

- endpoint gemma4_31b：OK
- snapshots_captured = **True**
- field_level_state_diff_source = `reconstructed_from_full_snapshot`
- trace schema 校验：**0 error**
- reconstruct：`tau2_seen=1, reconstructable=1, rerun_needed=0`
- 字段级 diff（3 changed，真实退货 mutation）：
  - `orders.#W2378156.status`：`delivered` → `return requested`
  - `orders.#W2378156.return_items`：设置为 3 个 item id
  - `orders.#W2378156.return_payment_method_id`：设置为 `credit_card_9513926`

结论：新 runner 写出的 tau2 trace 已能被 `reconstruct_tau2_field_diffs.py` 直接重建
字段级 final-state diff，源头修复了 R6 测量缺口。

## 3. 尚未做 / 全量前提

- 端点：gpt_oss_120b（8192）、mistral_small_3p2（8007）当前**下线**，全量三模型需先拉起。
- 历史 720 条 tau2 R6 trace 仍是 hash-only；如需其字段级 endpoint preservation，必须**重跑**
  （新 runner 加 `capture_full_snapshots`），不能对旧 trace 事后重建。
- 全量仍需你显式批准（PDF 流程 + 共享 A100 调度）。
