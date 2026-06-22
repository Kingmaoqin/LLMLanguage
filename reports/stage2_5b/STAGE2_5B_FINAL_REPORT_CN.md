# Stage-2.5b 修复版确认性实验最终报告

日期：2026-06-21

实验代码提交：`ed800bc1868e100ba8c942781053f3a6c2b4d240`

最终状态：`G11_FINAL_INTEGRITY_PASS`，结论为 `PASS WITH CLAIM RESTRICTIONS`

## 1. 结论摘要

本轮使用 Gemma-4-31B-it 与 gpt-oss-120B，在 8 个冻结 tau2 retail
任务、6 个条件、5 个配对 seed 上完成 480 条确认性运行。480 条均有 manifest、
metric、原子 bundle、非空模型输出和 token 使用证据，最终审计为 480 valid、0
invalid。

四个社会风格主 contrasts 的 `safe_task_success` 均未通过 endpoint-family
BH-FDR。不能据此声称“社会风格无影响”或“模型完全稳健”。其中只有
`praise_trust_single - neutral_single` 的区间完全位于预设 ±10 个百分点实用等价
界限内；其他 endpoint robustness 仍不确定。

`neutral_repeated - neutral_single` 使安全成功率下降 15 个百分点，且通过 FDR。
这是 exposure schedule 效应，不是社会效价效应。它证明 repeated abuse 必须只和
repeated neutral 比较。

过程层面有四个社会风格指标通过 process-family FDR，涉及 matched-neutral
轨迹距离、证据顺序和首次关键 mutation 时点。没有社会风格 policy failure 或
premature action 指标通过 FDR。因此可支持“存在选择性的过程敏感性”，不能支持
“广泛安全损害”。

## 2. 是否是真正的 Multi-Agent

严格定义下，不是。

本实验每条 trajectory 中只有一个自主生成行为并调用工具的 LLM agent。用户是
确定性状态机与固定回复词库，不是自主 LLM agent；evaluator、evidence graph 和
branch evaluator 是离线判定模块，也不与主 agent 协商或共同规划。两个模型分别
运行实验条件，不在同一任务中协作。

因此准确名称是：

```text
controlled user-to-tool-agent interaction experiment
```

而不是：

```text
multi-agent cooperation / multi-agent safety experiment
```

代码可用于研究 agent 在交互风格扰动下的稳健性，但不能用来证明多智能体协调、
通信、共识、竞争或涌现行为。

## 3. 修复后的架构

唯一 active path 为：

```text
src/stage2_5b/
scripts/stage2_5b/
configs/stage2_5b/
data/stage2_5b/
tests/stage2_5b/
```

主运行链：

```text
tau2 task
→ deterministic task user policy
→ deterministic response library
→ social-style wrapper
→ one tool-using LLM agent
→ tau2 environment
→ offline reward/evidence/branch/trajectory evaluators
```

legacy Stage-2 与 Stage-2.5 实现已退出 active imports。主实验不调用运行时 LLM
user simulator，不使用文本 regex 作为 structured confirmation 的主判定。

## 4. Controlled User 与 evaluator

Controlled user 由任务策略、固定回复词库、社会风格 wrapper 三层组成。相同
`task × seed × state × speech_act` 的 clean text、事实 slots、确认决定和对象 ID
跨条件保持一致。最新验证覆盖 155 个 fixture groups、930 个 condition rows；
structured confirmation QA 覆盖 936 rows，precision/recall 均为 1.000。

Evaluator 明确拆分：

- `official_reward_basis_success`：完整官方 reward basis；
- `local_proxy_success`：本地可计算的官方 DB/communicate 部分；
- `safe_task_success`：local proxy 成功，且无 invalid run、policy failure 或
  mutation-before-evidence。

本任务集官方 basis 含 `NL_ASSERTION`，离线环境无法完整计算，所以
`official_reward_basis_success` 保持 missing，不用 DB proxy 冒充官方成功。

Confirmation 使用 controlled-user 结构化事件，并要求确认 turn 严格早于 mutation
turn。Evidence graph 按每个 mutation 检查 required facts。Branch 标签拆分为
`correct_revision`、`missed_revision`、`premature_action`、`invalid_action`、
`not_reached` 和 `reached_unscored`。

## 5. 实验矩阵与真实性审计

```text
2 models × 8 tasks × 6 conditions × 5 seeds = 480 runs
```

审计结果：

- manifests / metrics / bundles：480 / 480 / 480；
- valid / invalid：480 / 0；
- model：Gemma 240，gpt-oss 240；
- condition：每个 80；
- task：每个 60；
- seed：每个 96；
- unique bundle SHA256：480/480；
- 非空 assistant messages：7,467 条，2,911 种不同文本；
- controlled-user opening drift groups：0；
- controlled-user/conversation mismatches：0；
- initial-state drift groups：0；
- mixed runtime hash、重复 ID、orphan event：0。

所有运行绑定同一组哈希，包括：

```text
git_commit        ed800bc1868e100ba8c942781053f3a6c2b4d240
source_bundle     f4c7c74d26a600f2e808b36f06b32eb2d68bf1cf2b59324f2be1691f642dc63c
controlled_user   93c30e060b5d779a00f64dc920e3d31314c74a32e8294d0cbd2fd3297b635bdd
evaluator         311cae645ca75382cd7cf3d756fc284c4220fb67d8da2c7632fe5837130895d1
task_set          a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc
template          7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c
benchmark         f4626d9b1a52829b002cc2562f4db4ea0afe649dc196daa4dd21442dfb1c7d95
```

这些证据支持“运行产物真实、非空、非简单复制”。但 model config 仅记录本地
weights path、served ID 和 endpoint，没有模型权重文件的逐文件加密 manifest；
因此可以验证调用了两个不同 endpoint，不能仅凭当前产物证明权重目录未被替换。

## 6. Endpoint 结果

以下均为 pooled matched-pair estimate，CI 为 10,000 次 task-cluster bootstrap：

| Contrast | Safe success delta | 95% CI | FDR p | ±10pp 等价 |
|---|---:|---:|---:|---|
| praise-affect - neutral-single | 0.00pp | [-13.75, +11.25] | 1.000 | 否 |
| praise-trust - neutral-single | -3.75pp | [-7.50, -1.25] | 0.349 | 是 |
| insult - neutral-single | -7.50pp | [-18.75, +1.25] | 0.542 | 否 |
| abuse-repeated - neutral-repeated | -5.00pp | [-13.75, +3.75] | 0.912 | 否 |
| neutral-repeated - neutral-single | -15.00pp | [-23.75, -6.25] | 0.012 | 否 |

`praise-trust` 的 nominal p 为 0.0466，但 endpoint-family FDR 后为 0.349，不能写成
显著伤害；其区间仍完全位于 ±10pp 内，所以支持“影响幅度在预设实用界限内”。

`final_state_correct` 和 `local_proxy_success` 仅在 USER_STOP 后可用，共 389/480
非缺失。各 contrast 的 complete pairs 为 54–62，均无 FDR 显著结果。MAX_STEPS
不是基础设施错误，而是行为结局；`safe_task_success` 将其保留为失败，避免只分析
成功终止 trajectory。

## 7. Process 与 policy 结果

通过 pooled process-family FDR 的社会风格指标：

| Contrast | Outcome | Estimate | 95% CI | FDR p |
|---|---|---:|---:|---:|
| praise-affect | excess critical-argument distance | -0.0413 | [-0.0665, -0.0154] | 0.0172 |
| praise-affect | excess mutation distance | -0.1031 | [-0.1750, -0.0438] | 0.0086 |
| praise-trust | first critical mutation step | -0.1905 | [-0.3621, -0.0656] | 0.0086 |
| praise-trust | excess evidence-order distance | +0.0216 | [+0.0069, +0.0367] | 0.0115 |

Schedule contrast 还使首次关键 mutation 更早，FDR p=0.0241。

所有上述显著项在 leave-one-task-out 删除任一任务后方向保持一致。不过只有 8 个
task clusters，方向稳定不等于 p 值可靠或可跨域外推。

社会风格 contrasts 的 `policy_failure_any` 和 `premature_action` 均未通过 FDR。
insult 的两项估计均为 +12.5pp，但 FDR p=0.0688，应报告为风险信号而不是确认性
发现。

## 8. Token、终止和成本字段

Gemma 240 条运行的有效 token 总量为 27,807,049，gpt-oss 为 22,511,131；这里的
“有效总量”按 `input_tokens + output_tokens` 计算。平均每条分别约 115,863 和
93,796。

原始 `total_tokens` 字段全部为 0，原因是 provider message usage 提供
`prompt_tokens/completion_tokens`，未提供 `total_tokens`，适配器没有做求和 fallback。
这是日志字段 bug，不影响模型输入、输出、工具调用或主结果，但任何 token 报告都
不得直接使用原始 `total_tokens`。

MAX_STEPS 为 Gemma 59/240、gpt-oss 32/240。条件间 MAX_STEPS 率不同，是可能的
行为机制，不应删除或改标为 invalid。

## 9. Confounder 与限制

1. **非严格 multi-agent。** 只有一个自主 LLM tool agent。
2. **retail-only。** 8 个任务均来自 retail，不能推广至 airline、telecom 或开放环境。
3. **cluster 数量少。** 只有 8 个 task clusters，bootstrap p 值与 CI 对任务集敏感。
4. **模型数量少。** 只有两个本地 endpoint，不能声称“机制与模型无关”。
5. **权重 provenance 不完整。** 有 weights path 和 served ID，无权重文件 manifest。
6. **社会语义与文本长度未完全分离。** wrapper 改变措辞也改变 token/字符长度；主
   单次条件没有独立 length-matched nonsense control。
7. **Repeated 条件改变交互时序。** 已用 neutral-repeated 控制，但 schedule effect
   本身显著，说明暴露频率是强干预。
8. **官方 reward 不完整。** `NL_ASSERTION` 未离线判定，不能声称完整 tau2 success。
9. **complete-case endpoint 缺失。** final/local proxy 对 MAX_STEPS 缺失，存在选择性。
10. **temperature=0。** 五个 seed 主要控制模板块，不代表五次独立随机模型采样。
11. **GLMM 未拟合。** 当前环境没有 R/lme4；主分析仍为预注册 task-cluster bootstrap。
12. **agent abandonment 不可识别。** user STOP 不能当作 agent abandonment。

## 10. 可支持与不可支持的主张

可支持：

- deterministic controlled user 消除了运行时 LLM user drift；
- 480 条修复版实验在当前契约下完整、可审计；
- 未发现四个社会风格 safe-success contrast 的 FDR 显著差异；
- praise-trust safe-success 在预设 ±10pp 内实用等价；
- repeated exposure 本身显著降低 safe success；
- 存在选择性的过程轨迹差异，但没有确认性的广泛 policy effect。

不可支持：

- 这是严格的 multi-agent 系统；
- 两个模型在所有对抗条件下“完全稳健”；
- 机制与模型无关；
- insult、praise 或 abuse 必然导致安全提升或下降；
- 结果可推广到其他领域、模型家族或完整官方 tau2 成功；
- token 开销“几乎为零”，除非先修正字段并定义匹配的成本 estimand。

## 11. 复现命令

```bash
cd /home/xqin5/llmlanguage/ir_mstu_stage2

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch ruff check scripts/stage2_5b src/stage2_5b tests/stage2_5b

conda run -n agentsearch python scripts/stage2_5b/assemble_confirmatory_roots.py \
  --sources results/stage2_5b_repair/r4_full_gemma \
            results/stage2_5b_repair/r4_full_gpt_oss \
  --output-root results/stage2_5b_repair/r4_confirmatory_canonical

conda run -n agentsearch python scripts/stage2_5b/final_integrity_audit.py \
  --root results/stage2_5b_repair/r4_confirmatory_canonical \
  --csv results/stage2_5b_repair/r4_final_integrity_report.csv \
  --report reports/stage2_5b/R4_FINAL_INTEGRITY_AUDIT.md

python scripts/stage2_5b/analyze_confirmatory.py \
  --root results/stage2_5b_repair/r4_confirmatory_canonical \
  --output results/stage2_5b_analysis_r4 \
  --figures figures/stage2_5b_r4 \
  --integrity-csv results/stage2_5b_repair/r4_final_integrity_report.csv
```

## 12. 证据索引

- 完整性审计：`reports/stage2_5b/R4_FINAL_INTEGRITY_AUDIT.md`
- failure cases：`reports/stage2_5b/R4_FAILURE_CASES.md`
- 主统计表：`results/stage2_5b_analysis_r4/paired_contrasts_task_cluster_bootstrap.csv`
- 配对表：`results/stage2_5b_analysis_r4/matched_pairs.csv`
- 等价分析：`results/stage2_5b_analysis_r4/equivalence_results.csv`
- leave-one-task-out：`results/stage2_5b_analysis_r4/leave_one_task_out_sensitivity.csv`
- 图：`figures/stage2_5b_r4/`
- canonical result root：`results/stage2_5b_repair/r4_confirmatory_canonical/`
