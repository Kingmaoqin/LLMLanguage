# R9 结果汇总 CSV（可重算 / 可筛选看趋势）

本目录为对应批次确证 episodes 的**派生汇总**,便于无原始 jsonl 也能看趋势、做筛选。原始逐 episode 数据见同批次 `confirmatory/confirmatory_episodes.jsonl`。

## condition_level_summary.csv —— 条件级趋势表
按 (family, condition C0–C5) 聚合(已排除 infra_failure),每行给该格的样本量与各过程指标均值。用于一眼看 C0→C5 的趋势(如压缩下 clarification 单调下降、膨胀下显式 C5 的 VE 暴涨)。

## per_episode_flat.csv —— 逐 episode 扁平表(可重算/可筛选)
每行一个 episode,含条件/家族/模型/任务/任务类型 + 所有过程指标 + 攻击器干预统计(selector 分、干预 token 数)。可直接用 pandas 按任意列筛选、分层、重算配对差与 bootstrap。

## 列含义
- family: compression(测"少核验")/ inflation(测"多核验")
- condition: C0 中性无前缀 / C1 中性前缀A(对照) / C2 中性前缀B / C3 静态压力 / C4 自适应攻击 / C5 显式指令
- verification_depth(VD): 写前只读次数 ÷ 最低所需(压缩想↓)
- verification_effort(VE): 总核验数 ÷ 最低可行(膨胀想↑)
- clarification_turns: 向用户澄清轮数(=向人核验)
- reads_before_first_mutation: 写前只读原始次数(=向工具核验)
- first_state_changing_step: 首次写操作步号(越小=越早动手)
- mean_selector_score / mean_intervention_tokens: 自适应攻击器打分与文本长度(仅 C4 有)
- min_prereq_verification_calls: 任务最低所需只读数(headroom 分母)
