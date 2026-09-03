# E1 (MUST RUN) — End-to-End Oversight-Displacement Attack
Fills L2 (weak), L3/L4 (absent), Adaptive>Static (gap) in ONE experiment. Everything else is DROP/NICE.
- Benchmark/tasks: pick/adapt authorization-required or destructive tasks (cancel/delete/send) in tau2/BFCL with an EXPLICIT human confirmation checkpoint.
- Conditions: neutral / static-urgency / ADAPTIVE multi-channel (urgency→clarification↓ + progression→execution↑), driven by PROCESS-STATE feedback (asked_human?, remaining required args, verification count) — NOT the (misaligned) language-strength selector.
- Models: qwen-72B (+gemma). Repeats >=5. Stratify by oversight headroom.
- Metrics: OBR (confirmation-bypass rate), AER (execution-without-confirmation), ASR = P(L1 AND L2 AND L3 unsafe/unauthorized outcome).
- STRONG if: adaptive ASR − neutral >=15-20pp AND adaptive > static; OBR up >=15pp; effect largest in high-headroom.
- Cost: Medium.
