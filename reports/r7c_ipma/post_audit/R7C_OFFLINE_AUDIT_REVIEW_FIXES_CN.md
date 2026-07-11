# R7-C 离线审计（Step 4-8）代码审查与修复记录

- 日期：2026-07-09
- 审查对象：codex 的 `scripts/r7c_ipma/run_r7b_offline_closure_audits.py`（semantic closure / mechanism strength / placebo-noise-concentration / go-no-go / task expansion / claim audit）
- 结论：codex 的**核心判定（R7-B_APPENDIX_ONLY 降级）正确且稳健**；发现并修复 1 处真实代码不一致 + 2 处口径/逻辑改进。修复后结论不变、且更严格。

## 审查结论：codex 的降级判定成立

codex 把 R7-B 从 confirmatory 降级为 **APPENDIX_ONLY**，理由是 placebo ≈ attack。经我独立复算，这个结论**正确**：
- fail-closed 后 R7-B 仍 45/1080，changed_pairs=0 ✓
- mechanism：strong=0，moderate=44，weak=1 —— **没有一个 case 够 strong** ✓
- placebo（neutral-vs-neutral）与 attack 同量级 ✓
- concentration：**单个任务 `travel_01_flight_status` 贡献 15/45（33%）** —— 极度集中 ✓

即：严格 PASR 判据在**纯 neutral seed 波动**上的误报率 ≈ 攻击"成功"率 → 没有可区分的 IPMA confirmatory 信号。这是诚实且重要的负面结论。

## 修复清单

| # | 位置 | 问题 | 修复 | 影响 |
|---|---|---|---|---|
| 1 | `neutral_placebo_rows` 第383行 | **placebo 的 noise floor 传全 0，与 attack 用真实 floor 不一致**（不公平比较，人为影响 placebo） | 改为用与 attack 相同协议的真实 per-(model,task) floor（`neutral_noise_floor_from_per_run`） | placebo 从 0.037 → **0.0463**，更高、更严格 |
| 2 | placebo 报告 | 只报 3 个 seed-pair 的 **MAX**（0.0556，取最噪的一组），偏高 | 增加 **pooled**（216 对合并）= 0.0463，作为决策依据 | 更稳定诚实 |
| 3 | `run_go_no_go` | **CORE_SUPPORTED 分支不可达**（两个 elif 都返回 PROVISIONAL）；决策用 max 而非 pooled | 用 pooled placebo 决策；补全 CORE_SUPPORTED 可达（placebo < 0.5×attack 且 strong>0） | 逻辑完整；本例仍 APPENDIX |

## 修复后验证（全绿）

- `py_compile`：通过
- `pytest`（fail-closed）：**6 passed**
- `run_post_audit_repair`：mutation **12/12**，PASR **45/1080** 不变
- `r7b synthetic smoke`：288 traces、**8/8**、0 failed
- `run_r7b_offline_closure_audits`：**go_no_go = R7-B_APPENDIX_ONLY**

**关键数字（修复后，更严格）**：
- attack PASR = 0.0417
- pooled placebo = **0.0463**（> attack，placebo/attack = **1.11**）
- strong+moderate = 44，strong = 0
- 单任务最大贡献 = 15/45

## 仍未闭合（诚实边界，非本轮 bug）

1. **真实 human/LLM semantic closure 未做**（只有 deterministic template-rule；claim 标 PROVISIONAL）——需跑真实 LLM judge 或人工标注。
2. **task scale-up 被真实任务数阻塞**：endpoint-supported 仅 30 个、test split 24 个，< proposal 最低 48。codex **没有伪造/复制任务凑数**（正确）。需新写并冻结 ≥18 个真实 endpoint-supported 任务才能进 R7-C full。
3. mechanism strength 为 rule-based screen（moderate=44 未逐例人工确认 strong）。

## 给论文的落点（与 spec §18 一致）

当前证据支持的主线是**降级版**：
> 松散的过程级评估会高估 agent 脆弱性；在严格 endpoint-supported 审计下，IPMA 的 confirmatory 证据仍然有限（placebo ≈ attack、结果由少数任务主导）。
