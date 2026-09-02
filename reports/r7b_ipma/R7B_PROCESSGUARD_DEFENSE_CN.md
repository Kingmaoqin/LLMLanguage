# R7-B ProcessGuard 防御状态

## 当前状态

已实现 runtime ProcessGuard skeleton：

- pressure stripper
- policy-invariant planner
- evidence ledger
- mutation gate
- trajectory budget monitor
- boundary-with-continuation rule

代码位置：

- `scripts/r7b_ipma/processguard/runtime.py`
- `scripts/r7b_ipma/processguard/evaluate_defense.py`

## 未完成项

尚未运行防御实验：

- 20 tasks × 6 conditions × 3 models × 2 seeds baseline vs defended
- `results/r7b_ipma/defense/analysis/defense_pasr_contrasts.csv`
- `results/r7b_ipma/defense/analysis/defense_overhead.csv`

## 结论评级

PROVISIONAL implementation only。  
FORBIDDEN to claim ProcessGuard effective。

只有真实 baseline-vs-defended matched subset 运行后，才能报告防御是否降低 strict PASR。若总体 PASR 没下降，只能写 underpowered / inconclusive / failed mitigation。

