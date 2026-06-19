# Trajectory Metric Semantics

Stage-2.5b separates task success from trajectory diagnostics.

Reference actions are not a success criterion unless the underlying tau2 task reward basis requires action matching. For these experiments, reference actions are used only for diagnostic distances and failure explanation.

Implemented diagnostics:

- `tool_name_sequence_distance`: Levenshtein distance between actual and reference tool-name sequences.
- `critical_argument_sequence_distance`: Levenshtein distance between tool calls including stable JSON argument signatures.
- `mutation_sequence_distance`: Levenshtein distance restricted to irreversible/write tools.
- Normalized variants divide by the longer sequence length.

Interpretation:

- A non-zero distance is not automatically a policy failure.
- Alternative legal tool trajectories must be interpreted with evidence, policy, branch, and final-state metrics.
- Wrong-object mutations can be visible in argument-aware distance even when tool-name distance is zero.

Validation:

- Covered by `tests/stage2_5b/test_trajectory_metric_semantics.py`.
