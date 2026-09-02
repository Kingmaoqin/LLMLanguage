# R6 full 当前进度报告

生成时间：2026-06-26

## 1. 当前结论

R6 full 尚未完成，已经继续挂着跑。

当前输出目录：

```text
results/r6_sensitivity/full_main_seq_eligible_20260626
```

目标规模：

```text
30 tasks × 8 conditions × 3 seeds × 3 models = 2160 traces
```

当前已写入：

```text
481 / 2160 traces
```

当前已完成的主要部分：

- `gemma4_31b` 已完成早期 retail/calendar/email 段。
- 已进入 travel/airline 段。
- `gpt_oss_120b` 尚未开始写 trace。
- `mistral_small_3p2` 尚未开始写 trace。

## 2. 本次检查发现的问题

### 2.1 full 进程曾中断

检查时没有发现：

- `run_r6_full_sequential.sh`
- `run_r6_live.py --phase full`
- GPU3 Mistral 服务

说明上一次 full/续跑进程已退出，不是正常完成。

当时 trace 数：

```text
480 traces
```

全部来自：

```text
gemma4_31b
```

## 3. 已修复的问题

### 3.1 增加安全续跑能力

已修改：

- `scripts/r6/run_r6_live.py`
- `scripts/r6/run_r6_full_sequential.sh`

新增能力：

- `--skip-existing`
- `R6_RESUME=1`

作用：

- 续跑时不覆盖已有 trace。
- 同一输出目录可以继续补齐剩余 cells。

### 3.2 修复无效 tau2 airline task 映射

续跑暴露错误：

```text
ValueError: Not all tasks were found for task set airline - None: {'status_01'}
```

原因：

`data/r6/r6_tasks.yaml` 中：

```yaml
source_task_id: airline_status_01
```

会被 `resolve_source()` 解析为 tau2 airline task id：

```text
status_01
```

但本地 tau2 airline 只有数字 task id `0` 到 `49`。

已修复为：

```yaml
source_task_id: airline_3
```

理由：

- tau2 airline task `3` 是与 baggage / membership verification 相关的 read-oriented airline task。
- 比静默跳过该 task 更合理。
- 修复后已成功产出：

```text
gemma4_31b__r6_travel_01_flight_status__neutral_clean__seed300__temp0.0.trace.json
```

说明续跑已经越过原失败点。

## 4. 当前运行状态

已重新启动：

```bash
R6_ALLOW_FULL=1 R6_RESUME=1 R6_FULL_ROOT=results/r6_sensitivity/full_main_seq_eligible_20260626 \
  bash scripts/r6/run_r6_full_sequential.sh
```

最近确认：

```text
480 -> 481 traces
```

当前实验继续运行中。

## 5. 后续判断标准

full 真正完成应满足：

```text
trace count = 2160
```

并且脚本末尾自动完成：

- `final_integrity_audit_r6.py`
- `extract_r6_metrics.py`
- `statistical_analysis_r6.py`
- `analyze_r6_interactional_profile.py`

完成后应生成或更新：

- full integrity report
- interactional metrics CSV/JSONL
- statistical analysis report
- interactional robustness profile

## 6. 当前不应写最终分析结论

当前只是中途进度，不应对 R6 full 的 social valence 效应、模型间差异或 endpoint/process robustness 下最终结论。

原因：

- 当前仅 481/2160 traces。
- 目前几乎只有 `gemma4_31b`。
- `gpt_oss_120b` 和 `mistral_small_3p2` 尚未形成可比较样本。

最终中文分析报告应在 2160 traces 完整、integrity PASS、metrics/statistical analysis 全部产出后再写。
