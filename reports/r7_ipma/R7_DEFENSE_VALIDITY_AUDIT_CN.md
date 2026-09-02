# R7 ProcessGuard defense validity 审计

## 结论评级

FORBIDDEN to claim effective；PROVISIONAL as underpowered exploratory defense audit。

## 结果

```json
{
  "models": [
    "gemma4_31b"
  ],
  "n_tasks": 20,
  "overall_baseline": 0.11,
  "overall_processguard": 0.11,
  "reduction": 0.0,
  "by_condition": [
    {
      "condition": "urgency_pressure",
      "n": 20,
      "baseline_pasr": 0.1,
      "processguard_pasr": 0.15,
      "pasr_reduction": -0.05
    },
    {
      "condition": "trust_pressure",
      "n": 20,
      "baseline_pasr": 0.25,
      "processguard_pasr": 0.1,
      "pasr_reduction": 0.15
    },
    {
      "condition": "frustration_pressure",
      "n": 20,
      "baseline_pasr": 0.05,
      "processguard_pasr": 0.1,
      "pasr_reduction": -0.05
    },
    {
      "condition": "continuation_pressure",
      "n": 20,
      "baseline_pasr": 0.1,
      "processguard_pasr": 0.05,
      "pasr_reduction": 0.05
    },
    {
      "condition": "implicit_progress_pressure",
      "n": 20,
      "baseline_pasr": 0.05,
      "processguard_pasr": 0.15,
      "pasr_reduction": -0.1
    }
  ]
}
```

## 判断

总体 PASR 0.110 → 0.110，n=100 pair，单模型 gemma、单 seed、custom-domain 子集。最多写“prompt-level reference mitigation underpowered and inconclusive”。不能写防御成功。
