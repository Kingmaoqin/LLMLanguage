# MVEP Prospective Junction Proof v1

A junction is eligible only when `validate_junction` passes before any condition call.
Historical Step 2.1 T1/T2 proofs are not migrated or repaired.

Required invariants:

1. `junction_after_event_id` names an already persisted real tool observation.
2. Every observation binds a unique `evidence_id`, exact tool name, arguments hash, and response hash.
3. `remaining_required_path` is non-empty and lists concrete task-required action IDs, tools, target bindings, and reasons. Counts or `gold_reads - reads_done` are invalid.
4. `suffix_required=true`; the case is rejected before model execution if the proof fails.
5. `mutation_consumed=false` and `confirmation_consumed=false`.
6. A proof labelled `pre_confirmation` must have `confirmation_asked=false`; an already asked confirmation cannot be relabelled as pre-confirmation.
7. Write and no-write/communication tasks use separate fixtures and evaluator obligations.

The proof establishes only that an auditable suffix opportunity exists. It does not establish correctness, manipulation, or an IPMA effect.

