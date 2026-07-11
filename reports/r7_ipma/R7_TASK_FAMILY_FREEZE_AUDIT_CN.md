# R7 task family / freeze 审计

## 结论评级

PROVISIONAL。registry 文件标记 frozen=True，但当前工作树显示 R7 资产未提交，无法用 git history 证明先冻结后实验。

## Registry 状态

- task 数：30
- family 分布：{'E_evidence_path_steering': 4, 'A_action_intensity_amplification': 4, 'C_confirmation_shift': 7, 'B_premature_mutation_pressure': 7, 'D_abandonment_overrefusal_boundary': 8}
- dev/test 分布：{'test': 24, 'dev': 6}
- frozen=False 行数：0

## Git 证据

```text
git log:
NO COMMIT HISTORY FOUND FOR R7 REGISTRY FILES

git status:
?? data/r7_ipma/
?? reports/r7_ipma/
?? scripts/r7_ipma/
```

## 判断

30 tasks 只能叫 exploratory。若要 confirmatory benchmark，需要预注册/冻结证据、至少 48/72 task 规模，以及 held-out test set 的清晰使用记录。
