# R7 endpoint oracle 审计

## 结论评级

PROVISIONAL / 部分 UNSUPPORTED。自定义环境的 final_state_correct 可直接使用；tau2 部分虽有 full DB snapshot，但 final_state_correct 多为 None，endpoint_not_worse 强 claim 不应按 100% 支持处理。

## raw trace oracle 状态

- final_state_correct unsupported by executor：{'tau2_r6_live': 540}
- snapshot 组合计数：{('tau2_r6_live', True, True): 540, ('r6_minimal_live_model', True, True): 1080}
- measurement tau2 field diff 表存在：True

## 关键判断

`endpoint_not_worse = 93.3%` 不是“final outcome unaffected”。更严谨写法：多数 attack-condition pairs 在当前 oracle/proxy 下 endpoint-not-worse；PASR 应只在 endpoint gate 后解释，且缺 final oracle 的样本需单列。
