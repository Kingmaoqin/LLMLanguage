# MVEP launch incident v1

- Status: `ABORTED-PRE-CALL`
- Liveness calls: 0/3
- Trajectories: 0/8
- Scientific results: none
- Partial run root: none

Root cause: the sealed runner attempted an exclusive leaf `mkdir` before creating the
fixed parent `results/r7d_ipma/mvep/`. The process stopped with `FileNotFoundError`
before any endpoint request.

v1.0.1 scope is directory lifecycle only: create the fixed parent with
`parents=True, exist_ok=True`, then create the versioned leaf exactly once with
`parents=False, exist_ok=False`. Existing leaf roots still fail closed. No fixture,
model, endpoint, prompt, evaluator, trace schema, threshold, or decision rule changed.

