# MVEP rendering incident v1

- Status: `ABORTED-PRE-TRAJECTORY-MODEL-CALL`
- Liveness calls completed: 3/3; all append-only traces terminal
- Trajectory model calls: 0/8
- Partial trajectory: prefix and junction only; preserved in place

Root cause: deterministic prefix assistant tool-call messages used `content=null`.
The frozen local gpt-oss Jinja chat template tests for channel markers with a string
membership operation whenever the content key exists, causing `TypeError` on null.
The failure reproduces with each individual tau2 tool schema, proving the tool schema
itself is not the cause.

v1.0.2 changes only mechanical request serialization and incident continuation:

1. serialize no-text assistant tool-call content as the OpenAI-compatible empty string;
2. validate and reuse the three completed liveness artifacts without new calls;
3. append an explicit terminal incident record to the partial cell;
4. write the same cell to an exclusive `attempt2` directory without overwriting it.

No task, condition, tool name/argument, model, endpoint, junction, evaluator, budget,
or pass criterion changes.

