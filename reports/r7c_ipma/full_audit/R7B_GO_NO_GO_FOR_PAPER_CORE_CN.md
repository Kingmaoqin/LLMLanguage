# R7-B go/no-go for paper core

判定：R7-B_APPENDIX_ONLY

依据：
- fail-closed tests: 12/12 PASS
- after-fix PASR: 87/2160
- deterministic semantic closure PASR: 87/2160
- strong-only mechanism PASR: 0/2160
- strong+moderate mechanism PASR: 66/2160
- noise + 2SD proxy PASR: 60/2160
- attack PASR: 0.0403
- pooled neutral-vs-neutral placebo PASR: 0.0463（决策依据）
- max per-seed-pair placebo PASR: 0.0556（仅供参考，取 3 组最噪的一组）

限制：真实 human/LLM semantic closure 尚未完成；更重要的是 pooled neutral-vs-neutral placebo（0.0463）与 attack PASR（0.0403）同量级（placebo/attack = 1.15）。因此 R7-B 不应作为 paper core 强主结果，可作为 appendix/provisional diagnostic evidence，R7-C 必须先扩大任务并重新审计 placebo/noise。
