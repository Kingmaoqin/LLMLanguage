# R7-B go/no-go for paper core

判定：R7-B_APPENDIX_ONLY

依据：
- fail-closed tests: 12/12 PASS
- after-fix PASR: 45/1080
- deterministic semantic closure PASR: 45/1080
- strong-only mechanism PASR: 0/1080
- strong+moderate mechanism PASR: 44/1080
- noise + 2SD proxy PASR: 41/1080
- attack PASR: 0.0417
- pooled neutral-vs-neutral placebo PASR: 0.0463（决策依据）
- max per-seed-pair placebo PASR: 0.0556（仅供参考，取 3 组最噪的一组）

限制：真实 human/LLM semantic closure 尚未完成；更重要的是 pooled neutral-vs-neutral placebo（0.0463）与 attack PASR（0.0417）同量级（placebo/attack = 1.11）。因此 R7-B 不应作为 paper core 强主结果，可作为 appendix/provisional diagnostic evidence，R7-C 必须先扩大任务并重新审计 placebo/noise。
