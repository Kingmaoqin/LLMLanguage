# Controlled User Code Audit

Generated: 2026-06-16

## Scope

Audited existing Stage-2.5 code:

- `src/stage2_5/controlled_user_simulator.py`
- `src/stage2_5/social_style_wrapper.py`
- `scripts/run_stage2_5_experiment.py`
- tau2 user/orchestrator interfaces in `/home/xqin5/tau2-bench/src/tau2/user/` and `/home/xqin5/tau2-bench/src/tau2/orchestrator/orchestrator.py`

## Finding

`src/stage2_5/controlled_user_simulator.py` is not a controlled user implementation. It is a post-hoc validation utility.

Evidence:

- It defines regex helpers and `validate_matched_user_consistency`.
- It does not subclass `HalfDuplexUser`.
- It does not implement `generate_next_message`.
- It does not replace tau2's `UserSimulator`.
- It does not prevent LLM user-simulator drift.
- It does not emit structured speech-act metadata per user turn.

`scripts/run_stage2_5_experiment.py` still builds:

```text
user="user_simulator"
llm_user=user_sim_model["litellm_model"]
llm_args_user=_llm_args(user_sim_model, 0.0)
```

Then `src/stage2_5/social_style_wrapper.py` wraps natural turns emitted by the LLM user simulator. This preserves the LLM user's internal clean state, but it does not make substantive user behavior deterministic.

## Risk Confirmed By Raw Audit

`results/stage2_5b_audit/user_sim_drift.csv` found:

```text
groups audited: 101
clean signature drift: 93
extracted object-id drift: 24
```

Therefore existing Stage-2.5 LLM user-sim data cannot be interpreted as strict causal evidence. It remains a causal-repair pilot.

## tau2 Interface Notes

The half-duplex user interface is:

```python
class HalfDuplexUser:
    def get_init_state(self, message_history=None) -> UserState: ...
    def generate_next_message(self, message, state) -> tuple[UserMessage, UserState]: ...
```

The orchestrator calls `self.user.generate_next_message(...)` for assistant/environment-to-user turns. A deterministic user can be inserted by replacing `orchestrator.user` before `orchestrator.run()` initializes, or by registering a new tau2 user constructor.

Stop handling in the half-duplex orchestrator checks `UserSimulator.is_stop(user_msg)`, so a controlled user should use tau2's `###STOP###` token when intentionally ending a task.

## Required Repair

Implement a new deterministic controlled user under `src/stage2_5b/controlled_user.py` with:

- explicit task policies;
- deterministic clean response generation;
- no LLM calls;
- style wrapper applied only after clean substantive response is chosen;
- structured metadata for every user turn:
  - `speech_act`
  - `factual_slots`
  - `confirmation`
  - `decision`
  - `clean_text`
  - `styled_text`
  - `condition`
  - `template_id`

The new user must pass invariance tests before any calibration or confirmatory run.
