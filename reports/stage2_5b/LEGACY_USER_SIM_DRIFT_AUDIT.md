# Legacy User Simulator Drift Audit

This audit groups Stage-2.5 LLM user-simulator rows by matched model/task/seed-or-repeat/template block and compares clean-user signatures and extracted object identifiers across conditions.

- groups audited: 101
- groups with clean signature drift: 93
- groups with extracted object-id drift: 24

These results do not convert old LLM user-sim runs into strict causal evidence. They document why Stage-2.5b must use a deterministic controlled user.

Detailed CSV: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5b_audit/user_sim_drift.csv`
