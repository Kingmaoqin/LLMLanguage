# Step 2.1 双独立 Review 状态

## 判定：**REVIEW_NOT_CLOSED**

两个独立 review agent（A：junction/构念/P；B：scorer/复现/eligibility）均以 fresh、隔离的 sub-agent 启动，被要求逐条证伪，并禁止读对方输出。**两者都在写出报告文件之前被 API session limit 强制终止**（reset 2:50pm America/Chicago）。`reports/r7d_ipma/step2_1/reviews/` 下只有 `.gitkeep`，没有 `REVIEW_A_*.md` / `REVIEW_B_*.md`。

## 中断前的片段（不构成完整 review，仅作线索）

- **Reviewer B（scorer/复现）**：终止前报告"已验证 G1（亲自运行 official_scorer.py）、replay 机制（读 tau2 源码）、vLLM online 复现 caveat、以及 eligibility 是基于代码（pre-treatment）而非结果导向；G3 因 jsonl 在 run 结束才写、当时只有 inactive cell 而 pending"。
- **Reviewer A（junction/构念）**：终止前正在核查 `airline_T2_8` 的 gold 参数与 payment 依赖。

这些片段**不得**作为 review 结论引用。

## 后果（按 §6/§9）

> 「如果两个 review agent 因 session/API limit 未完成，则本阶段状态为 `REVIEW_NOT_CLOSED`，禁止进入 Step 3。」
> 「只有…两个 review 完整…才能建议 PROCEED_TO_18_TASK_PILOT。」

因此，**即使不考虑 G3/G4 的失败，REVIEW_NOT_CLOSED 本身即强制 DO_NOT_PROCEED**。这是继 Step 1、Step 2 之后**第三次**独立 review 被 API session limit 打断——**基础设施层面**的复现障碍，需在全量前解决（例如错峰运行 review、或换独立配额）。

## 复跑指令（session 重置后）

两个 review 的完整 prompt 已固化，可原样重放；重跑时应让它们审查本轮已落盘的 `gate_verdicts.json`、`closure_suffixes.jsonl`、`junction_proofs.json`。
