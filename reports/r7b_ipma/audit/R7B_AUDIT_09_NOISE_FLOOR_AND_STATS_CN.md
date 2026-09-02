# Audit 09：neutral noise floor and statistics

## 结论

- reported-floor recomputed PASR：45/1080 = 0.0417
- stricter approximate floor PASR：17/1080 = 0.0157
- stricter approximate family E：2

## 统计解释

当前脚本复算了条件级描述统计和更严格 noise floor 近似敏感性。placebo neutral-vs-neutral 需要设计独立 placebo pair 表；当前输出标记为 not_fully_applicable，不能作为强 claim 支撑。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_noise_floor_sensitivity.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_statistical_recompute.csv`
