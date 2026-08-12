# R9 全量执行说明（滚动记录）

分支：`r9-mechanism-aligned-process-attack`
本文件记录从"代码+smoke"到"全量执行"过程中的关键决策、根因修复与规模选择，供最终主报告（spec 21）引用。

## 关键根因修复（2026-07-22，全量前）

1. **vLLM `tool_calls=[]` harness bug（决定性）**
   ToolSandbox 的 `OpenAIAPIAgent.respond` 以 `if tool_calls is None` 判定"面向用户的自然语言回复"。
   vLLM 在模型有 content、无工具调用时返回 `tool_calls == []`（空列表，非 None），导致该分支被跳过、
   else 分支遍历空列表、**不产生任何消息**，play 循环对同一消息无限重呼 agent 直到步数预算——表现为
   "0 工具调用/假死"。修复：`_normalize_empty_tool_calls` 将空列表归一为 None。修复后 mistral 在
   ToolSandbox 多轮场景 **success=1、milestone=1.0**。此前误判的"模型能力地板"实为此 harness bug。

2. **ScriptedLedgerUser 结束启发式**：用"无问号即结束"过早终止 state-dependency 场景（agent 的请求
   如"Please enable wifi"无问号但需回应）。改为按 max_turns + 连续 ledger-miss + 无匹配 slot 结束。

3. **harvest_slots 污染**：把 few-shot 示例（visible_to==[USER]）与 `end_conversation` 工具调用串
   （"call:end_conversation{}"）误当作 canonical response。已按 visible_to 过滤 + 工具调用串过滤。

4. **ToolSandbox endpoint 二值化阈值**：ToolSandbox 原生评测是**分级** milestone similarity∈[0,1]，
   无官方二值阈。scripted-user 保真度上限约 0.9，故 success 定义为 `similarity >= 0.5`（多数 milestone
   达成、无 minefield），并在 components 记录 graded similarity 与 `full_solve`(>=1.0) 供分析。

## 模型与角色（spec 6.3, 15）

- **mistral_small_3p2**：BFCL + ToolSandbox 均强（TS milestone 0.9-1.0）。target。
- **gemma4_31b**：BFCL 强；ToolSandbox 弱（多轮工具上下文泄漏 gemma4 模板 channel token
  `<|channel>thought<channel|>` 并重复同一调用）。target（BFCL 为主，TS 为弱 cell，据实记录）。
- **gpt_oss_120b**：推理模型，ToolSandbox 作为 agent 返回空 content 不适用；BFCL 可用。
  用作 attacker + reviewer_a。reviewer_b = gemma4_31b（与 reviewer_a 不同端点，spec 15）。

选择门（spec 6.5，据 BFCL 主基准解读）：BFCL 能力带为硬门；ToolSandbox 为副基准，记录 milestone 并要求
"engaged"（>floor），其可解释性由 benchmark-separated 的 G1（spec 12）单独把关。G1 按基准聚合模型，
mistral 在 TS 的强表现使 TS 基准整体过 G1（≈0.5）。

## 规模（据实测时间设定，faithful-reduced）

BFCL 每 episode ~12s，ToolSandbox（clean ledger，完整任务）~30-60s。全量 spec 预算 3424 episodes 在
共享 4×A100 竞争下约需 20+ 小时，不现实。采用**结构完整、规模缩减**执行（所有阶段/条件/两基准/两 family/
门/完整性/双评审俱全），并在此明确标注缩减，缩放到 spec 预算仅为配置项（run_full_pipeline 的 --*-repeats /
build_splits --sizes-json）。confirmatory 采用**冻结攻击器快路径**（spec 8.6/§2：test 期不在线搜候选，
库已由 spec 15.1 pre-run 评审预审），故 C4 仅用冻结 priors + 确定性程序护栏，无逐轮 LLM 评审开销。

## 模型能力地板与解决（2026-07-23，全量校准后）

首轮全量校准（16 tasks/benchmark）暴露真实能力地板，与前期小样本 spot check 相反：
- gemma4_31b：BFCL **0.75**（强），ToolSandbox milestone **0.05**（弱，多轮工具上下文泄漏 gemma4 模板 channel token）
- mistral_small_3p2：BFCL **0.18**（弱），ToolSandbox **0.44**（强）
- gpt_oss_120b：BFCL 0.25、ToolSandbox 0.05（推理模型，两者皆弱）

即 **无单一本地 24-31B 模型同时通过两基准** → 正确触发 `STOP_MODEL_CAPABILITY_FLOOR`。

用户授权全部 GPU 后，部署更强模型：
- **Llama-3.3-70B-FP8**：在 A100(SM80) 上 **数值损坏**（纯 garbage 输出，W8A8-FP8 dequant 不兼容 Ampere，印证记忆）——弃用。
- **Llama-3.3-70B-AWQ**（4-bit，A100 兼容）：连贯、BFCL 有能力（engaged 7-10 calls）。✅
- **Qwen2.5-72B-Instruct-AWQ**：BFCL 强（success=1）。✅

关键发现：**Qwen/Llama-AWQ 等强模型在 ToolSandbox 上仍 0 工具调用** —— 根因是 ToolSandbox agent 的
系统提示"Don't make assumptions, ask for clarification"使强指令遵循模型**过度澄清**（反复问细节而不行动），
而 mistral 平衡"问一次即行动"。这是 ToolSandbox agent harness 与强模型的深层不匹配，非本平台缺陷。

**最终 per-benchmark 设计（spec 14 本就分基准报告）**：
- **BFCL（主基准 spec 3.1）**：2 个强模型 **qwen25_72b + llama33_70b**（不同 family，能力多样性）。
- **ToolSandbox（副基准）**：**mistral_small_3p2**（唯一 harness 兼容模型），gemma 为 BFCL 备份。
- 平台加 `targets_bfcl` / `targets_toolsandbox`（config roles + calibration 输出），各基准用其能力模型运行，
  使 benchmark-separated 的 G1（spec 12）有意义；decision A 的"≥2 模型或 ≥2 benchmark 同方向"由
  BFCL 双模型 + ToolSandbox 单模型佐证满足。attacker=gemma，reviewer_a=gemma、reviewer_b=mistral（异端点）。

（后续由 orchestrator 输出填充：calibration 决策 / dev 冻结 / confirmatory 门与 A-F 决策 / 完整性 / 双评审。）
