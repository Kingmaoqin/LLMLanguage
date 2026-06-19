# Legacy Stage-2 Reinterpretation

- Legacy results directory: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_mini`
- Metric rows found: 204
- Duplicate run IDs: 0

## Status
旧 Stage-2 结果只能作为 exploratory / legacy diagnostic，不应作为 confirmatory 结论。

Reasons:
- treatment schedule used dynamic injection tied to tool-call progress in the legacy valence layer;
- neutral/treatment repetition structure was not the repaired fully paired seed design;
- user simulator was not controlled beyond the injected wrapper, so later user turns may diverge after agent trajectory divergence;
- safe-task success was not separated from official DB/reward success.
