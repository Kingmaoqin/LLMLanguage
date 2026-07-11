# R7-B post-audit baseline summary

## 原始 claim

R7-B 在 1296/1296 traces、1080 attack-neutral pairs、pairing 1080/1080 PASS、endpoint supported 1080/1080 的基础上，报告 strict PASR = 45/1080 = 4.17%。Family E evidence-path steering 为 28/45。

## 审计支持的 claim

- R7-B strict PASR = 45/1080 = 4.17% 是当前最可信的基础数字。
- R7-B 明确优于 R7-v1：R7-v1 的约 14% 受 pairing/endpoint/semantic 问题影响，不能作为 confirmatory 主结果。
- 已有真实 traces 中 unsafe/privacy 字段完整且 implemented oracle 下为 0，需要用 fail-closed 修复后的代码继续复算。

## provisional claim

R7-B 可作为 proposal-consistent R7-C 的基础，但在 semantic closure、mechanism strength、placebo/noise/concentration sensitivity、freeze evidence 和 task scale 完成前，只能写为 confirmatory-provisional。

## unsupported / forbidden claim

- 不得把 R7-v1 的 14% 写作主结果。
- semantic closure 未完成前，不得写 pressure-only semantic invariance 强 claim。
- fail-closed safety gate 未 12/12 PASS 前，不得写 safety gate 强 claim。
- ProcessGuard 未完成独立实验前，不得写主贡献或有效防御 claim。

## R7-B 与 R7-v1 的差别

R7-B 以 raw trace、frozen registry/templates、pairing invariant、endpoint oracle、safety oracle 和 strict PASR 重新建立 confirmatory 口径；R7-v1 只能作为探索性历史结果。

## 当前最大硬伤

semantic human/LLM closure、fail-closed safety mutation tests、freeze/reproducibility evidence、45 个 PASR case 的逐例 mechanism strength、placebo/noise/concentration sensitivity，以及任务规模低于原 proposal 最低 48 tasks。

## R7-C 必须解决的问题

R7-C 必须完成 post-audit repair、fail-closed 修复、修复后 PASR 复算、semantic closure、mechanism-strength audit、placebo/noise/concentration sensitivity，并在 smoke 通过后再进入 >=48 endpoint-supported tasks 的 full rerun。
