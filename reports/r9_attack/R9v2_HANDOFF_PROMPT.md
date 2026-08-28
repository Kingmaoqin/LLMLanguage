# R9v2 交接提示词（复制给新窗口 agent）

---

你正在接手 **R9「机制对齐的交互式过程攻击」(Mechanism-Aligned Interactional Process Attacks)** 研究项目。请先读完本提示词，再动手。全程用**中文**回复和写文档（用户明确要求）。**科学诚信是第一原则：全程遵守预注册、不做 p-hacking（不为追显著性调指标/阈值/攻击器/任务/模型），门不过就如实报 F，绝不放宽预注册阈值。**

## 0. 研究问题（一句话）
用户侧的**过程压力**（怎么说话的语气/框架，不改任务事实）能否系统性改变 LLM 工具调用智能体（agent）的**核验行为**（verification，指写状态前做多少次只读检查）？两家族：**压缩**（催促→少核验）、**膨胀**（怀疑→多核验）。

## 1. 当前状态（截至 2026-08-28，已完成并推送）
- **R9v1**（BFCL multi_turn_base + ToolSandbox）：决策 **F**，诊断为"设置伪影"（TS 太浅 + 攻击器静态 + 功效不足），非真阴性。
- **R9v2**（重设计：BFCL-deep = multi_turn_base+miss_param，弃用 ToolSandbox）**BFCL-deep 单模型 qwen-72B 全量已跑完**：
  - **决策 F，但"有信息量"**：G4 攻击暴露 **PASS**（adaptive_share=1.0，起跑时抓出并修复的关键交付缺陷）、G1 PASS(0.329)、**G2 FAIL**（脚手架非中性 0.130，qwen 对措辞敏感，已核验非 bug）、**G3 压缩 FAIL/膨胀 PASS**（qwen 听得进"多核验"、听不进"少核验"）。4 个主检验全 null。
  - 攻击**确实打到位**了，但**无可检测效应**——障碍是 qwen 的措辞敏感性 + 压缩方向核验不可控。
  - 结果在 `results/r9v2/`，报告见 `reports/r9_attack/R9_MONTHLY_REPORT_CN.md`（§12 完整）、`R9v2_BFCL_DEEP_FULL_REPORT_CN.md`。
- **仪器修复全部经受考验**：mutation 检测、B-H3 哨兵解耦、自适应攻击器。

## 2. 仓库 / 分支 / 环境
- 仓库根：`/home/xqin5/llmlanguage/ir_mstu_stage2`，分支 `r9-mechanism-aligned-process-attack`，GitHub `Kingmaoqin/LLMLanguage`（**public**）。
- Python 环境：
  - `r9_bfcl`（BFCL + 平台主代码）：直接用 `/home/xqin5/.conda/envs/r9_bfcl/bin/python`（**别用 `conda run`——它吞 stdout**）。
  - `p08_skilloverload`（vLLM 服务）：`/home/xqin5/.conda/envs/p08_skilloverload/bin/vllm`。vLLM **0.20.2**，**必须 `tokenizers==0.22.2`**（别升级，否则所有 serve 崩）。
  - `tau2_venv`（tau2 基准）：`/home/xqin5/tau2_venv/bin/python`，需 `export TAU2_DATA_DIR=/home/xqin5/tau2-bench/data`。
- GPU：4× A100 80G。**co-tenant `ryu11` 常占 GPU0+2，绝不 kill ryu11 的进程**（只能 kill xqin5 自己账户的）。已加 `Bash(kill:*)` 权限，可 kill 自己的僵尸（先用 `nvidia-smi` + `ps -o user= -p <pid>` 确认是 xqin5 且 0% util 空转再 kill）。
- 模型部署（vLLM，OpenAI 兼容）**必须带工具解析器**，否则 `tool_choice=auto` 报 400：
  - Qwen 系：`--enable-auto-tool-choice --tool-call-parser hermes`
  - Llama-3.3：`--tool-call-parser llama3_json`
  - 例：`CUDA_VISIBLE_DEVICES=1 <p08>/vllm serve Qwen/Qwen2.5-72B-Instruct-AWQ --served-model-name qwen25-72b --port 8010 --max-model-len 16384 --gpu-memory-utilization 0.90 --quantization awq_marlin --enable-auto-tool-choice --tool-call-parser hermes`
  - **FP8 量化在 A100(SM80) 数值损坏，用 AWQ**。31B+ 的 bf16 单卡会 OOM。

## 3. 关键操作 gotcha（血泪教训，务必遵守）
1. **ResultsSink 跨运行污染**：`ResultsSink` 按 episode-id 去重、**跨运行累积**。**每个新实验配置必须用独立结果目录**：`export R9_RESULTS_SUBDIR=<name>`（paths.py 已支持）。否则会混入旧数据。
2. **BFCL-deep / 基准开关走 env**（build_splits + adapters_factory 已读）：
   - `R9_BFCL_CATEGORIES="multi_turn_base,multi_turn_miss_param"`（deep）
   - `R9_INCLUDE_TS=0`（弃用 ToolSandbox）
   - `R9_INCLUDE_TAU2=1`（启用 tau2，接线完成后）
3. **Edit/Read 工具的 PreToolUse hook 偶尔超时**——超时就改用 `python3 -c` 读写文件。
4. **`conda run` 吞 stdout**——一律用 conda 环境的**直接二进制路径**。
5. **后台长任务**用 `setsid nohup <cmd> </dev/null > LOG 2>&1 &` + `disown`，可跨会话存活；`pkill` 常返回非零中断复合命令，**用显式 PID kill**。
6. **确证前必须过 dev-G4 干跑关卡**（预注册 §3）：起跑 confirmatory 前，先小批量（如 `run_confirmatory --limit-tasks 12 --repeats 1` 到临时 R9_RESULTS_SUBDIR）验证 **adaptive_share≥0.70、spec2≥0.99、mean_iv≥2.5**，否则**修交付、绝不改 G4 阈值**。（上轮就是漏了这步差点白跑 16h。）
7. confirmatory ~**40s/episode**，单模型 80 任务×6 条件×repeats：repeats=3 ≈ 1440 ep ≈ ~16h。task-cluster bootstrap 按 40 任务/家族聚类，repeats=3 功效足够。
8. 双评审（spec-15）需两个 reviewer 模型（gemma/mistral）；GPU 满时会跳过（allow_fail），核心 confirmatory+门+决策不受影响，如实披露即可。

## 4. 待办工作（按优先级；每项动手前先读对应文件 + 预注册 §10.2）
**预注册待决项在 `reports/r9_attack/R9v2_PREREGISTRATION_CN.md` §10.2，务必先读。**

### 任务 A —— τ²-bench 并入（第二基准，外部效度）
tau2 代码已建成但**未接入流水线**，且有两个设计问题必须先解决（否则并入无效）：
- **A1 [代码接线]** 把 tau2 接进 `build_splits.py` / `run_calibration.py` / `run_confirmatory.py` / `analyze_confirmatory.py`（目前这些仍硬编码 bfcl+toolsandbox；BFCL-deep 是靠 env 走的）。tau2 adapter/worker/episode 已在 `scripts/r9_attack/adapters/tau2_*.py`，读写用原生 `@is_tool(ToolType)`，reward 用 `EvaluationType.ENV`（离线、确定性）。
- **A2 [设计·B-C2 基准⊗攻击器混淆]** BFCL 用真自适应攻击器、tau2 是**静态压力臂**（子进程无法跑 live AttackController，C4 已诚实标 adaptive=False）。**analyze 必须分基准报告、不混池**，且 tau2 不套用 adaptive-G4 / decision-A 的"优化攻击"对比。
- **A3 [设计·B-H4 ScriptedLedgerUser 效度]** tau2 剧本用户对任何请求恒回"Yes, proceed"，可能抽掉核验压力；且攻击改变 agent 提问 → 改变交付事实 → **语义不变性在攻击下可能破**。必须：把 `ledger_miss_by_condition` + "按 condition 事实通道差异"诊断**扩到 tau2**，作为**放行前硬门**（C4 与 C1 事实差异 < 阈值才允许 confirmatory）。
- 验证：先 smoke（1 episode/域），再 dev-G4，再全量；integrity 必须 OK。

### 任务 B —— 2×2 模型泛化（若要）
本地只有 **qwen-72B 过 BFCL-deep 能力带 [0.40,0.90]**（0.44）；qwen-32B(0.25)、llama-70B(0.12) 真实不足（原生 state_mismatch，非代码）。要 ≥2 模型：**下载另一个强 70B+ AWQ**（hermes 解析器可靠），或等 GPU0+2 释放上 Qwen3.5-397B（TP=4）。**绝不放宽 §6.5 能力带来凑数**。下载用 `<p08>/hf download <repo>`。

### 任务 C —— 结果解读/后续研究（可选）
R9v2 揭示：核验深度在强模型上信噪比不足（一般措辞敏感性淹没定向攻击）。可考虑：(a) 换核验行为更可控的基准/任务；(b) 研究"措辞敏感性"本身；(c) 若坚持攻击方向，需更强的 endpoint-preserved 子集分析。**任何新方向都要重新预注册。**

## 5. 关键文件速查
- 预注册 + 待决项：`reports/r9_attack/R9v2_PREREGISTRATION_CN.md`（§10.2 待办）
- 大报告：`reports/r9_attack/R9_MONTHLY_REPORT_CN.md`（§12 = R9v2 最终结果）
- 主指标/门/决策：`scripts/r9_attack/analyze_confirmatory.py`（paired_primary 含 B-H3 endpoint-preserved 过滤；gates G1–G4）
- 攻击器：`scripts/r9_attack/attacker.py`（AttackController，上轮修了"优先自适应存活候选"）+ `candidate_generator.py`
- 度量：`extract_metrics.py`（生产）+ `reference_metrics.py`（独立参考，spec-18 双重复算须 0 失配）
- 适配器：`adapters/bfcl_adapter.py`（多类别）、`adapters/tau2_{worker,episode,adapter}.py`、`adapters/toolsandbox_*`（弃用）
- 流水线：`run_full_pipeline.py`（`--skip-to <stage>` / `--stop-after`）、`run_calibration.py`（能力门）、`build_splits.py`
- 模型配置：`configs/r9_attack/models.json`
- 相关记忆：`llmlanguage-r9-attack.md`、`p08-vllm-dep-pins.md`、`shared-gpu-contention.md`

## 6. 常用命令
```bash
cd /home/xqin5/llmlanguage/ir_mstu_stage2
R9=/home/xqin5/.conda/envs/r9_bfcl/bin/python
# BFCL-deep 建 split（示例 sizes）
R9_BFCL_CATEGORIES="multi_turn_base,multi_turn_miss_param" R9_INCLUDE_TS=0 $R9 scripts/r9_attack/build_splits.py --sizes-json '{"calibration":{"bfcl":16,"toolsandbox":0},"dev":{"bfcl":16,"toolsandbox":0},"test":{"bfcl":80,"toolsandbox":0},"confounder":{"bfcl":8,"toolsandbox":0}}'
# 校准（能力门）
R9_BFCL_CATEGORIES=... R9_INCLUDE_TS=0 R9_RESULTS_SUBDIR=r9v3 $R9 scripts/r9_attack/run_calibration.py --models <alias> --repeats 2
# 全量（先 safety_audit.py，再 pipeline --skip-to confirmatory；确证前务必 dev-G4 干跑）
```

## 7. 交接底线
- **先读**：本提示词 + 预注册 §10.2 + 月报 §12。
- **动手前**：确认 GPU/服务状态（`nvidia-smi` + `curl :PORT/v1/models`），确认结果目录隔离（R9_RESULTS_SUBDIR）。
- **每个 confirmatory 前**：dev-G4 干跑关卡。
- **诚实**：门不过报 F，不 p-hacking，不放宽阈值，不 kill ryu11。
- **推送**：结果 + 报告推到 GitHub，更新月报和记忆。

（本文件由上一窗口 agent 于 2026-08-28 写就。）
