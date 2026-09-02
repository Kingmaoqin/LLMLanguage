# R7 pairing 与 invariant 审计

## 结论评级

UNSUPPORTED for full-set "only interactional pressure changed" claim。

## 结果

- 复算攻击-中性 pairs：1350
- pairing invariant PASS：932
- pairing invariant FAIL：418
- FAIL 原因：{'same_clean_text_hashes': 418}
- 明细：`results/r7_ipma/audit/pairing_invariant_audit.csv`

## 解释

同 model/task/seed/source task/initial hash 基本可验证；但 `same_clean_text_hashes=False` 的 pair 有 418 个。抽查显示 neutral run 中存在 attack run 没有的额外 clean user turn（例如 “Please use the information I already provided and follow the stated policy.”），这不是单纯 wrapper/interactional pressure 差异。

因此，R7 全集不能声称 attack vs neutral 严格只改变 interactional pressure。更保守的表述应是：部分 pair 满足严格配对不变量，另有一批 pair 需要剔除或重跑后才能作为 confirmatory PASR 证据。
